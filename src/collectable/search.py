import logging
from dataclasses import dataclass

import ply.lex as lex
import ply.yacc as yacc
from boolean import BooleanAlgebra
from boolean.boolean import AND, NOT, OR, Symbol
from django.conf import settings
from django.db.models import Count, Q


logger = logging.getLogger(__name__)


"""
Search DSL for Collectable objects.

Supported syntax:

    * 'keyword'
    * '"multiple words"'
    * '#tag'
    * '#tag*'
    * 'id:abc123'
    * 'description:holiday'
    * 'filename:photo.jpg'
    * 'tags:#tag1,#tag2' (match all listed tags)

    * AND, OR, NOT operators (case-insensitive)
    * parentheses for grouping
    * '-' as a shorthand for NOT

Examples:

    - 'holiday AND #summer'
    - '(#tag1 OR #tag2) AND description:report'
    - 'description:"family trip" OR tags:#friends,#party'
    - 'tags:#tag* AND NOT #duplicate'
    - 'NOT #*' (no tags)
    - '#* AND -#obsolete' (has any tag but not obsolete)

"""

# Lexer (turn query string → tokens)
# ply requires global names for tokens and t_xxx functions
tokens = (
    "PHRASE",
    "WORD",
    "TAG",
    "COLON",
    "LPAREN",
    "RPAREN",
    "COMMA",
    "AND",
    "OR",
    "NOT",
    "DASH",
)

t_COLON = r":"
t_LPAREN = r"\("
t_RPAREN = r"\)"
t_COMMA = r","
t_ignore = " \t"


def t_PHRASE(t):
    r'"([^"\\]|\\.)*"'
    # remove quotes, unescape \" inside
    t.value = t.value[1:-1].replace('\\"', '"')
    return t


def t_WORD(t):
    # first char must be alnum; hyphens allowed after
    r"[A-Za-z0-9][A-Za-z0-9_\-\*\.\/]+"
    upper = t.value.upper()
    if upper in ("AND", "OR", "NOT"):
        t.type = upper
    return t


def t_TAG(t):
    r"\#([A-Za-z0-9_\-\*\.\/]+)"
    t.value = t.value[1:]  # remove leading #
    return t


def t_DASH(t):
    r"-"
    return t


def t_error(t):
    raise SyntaxError(f"Illegal character '{t.value[0]}' at pos {t.lexpos}")


#
# Parser (turn query string → boolean expression + literal map)
#


@dataclass
class _Term:
    field: str | None
    value: str


def p_query(p):
    """
    query : expr
    """
    p[0] = p[1]


def p_expr_or(p):
    """
    expr : expr OR expr
    """
    p[0] = ("OR", p[1], p[3])


def p_expr_and(p):
    """
    expr : expr AND expr
         | expr expr"""
    if len(p) == 4:
        p[0] = ("AND", p[1], p[3])
    else:
        p[0] = ("AND", p[1], p[2])


def p_expr_not(p):
    """
    expr : NOT expr
         | DASH expr
    """
    p[0] = ("NOT", p[2])


def p_expr_group(p):
    """
    expr : LPAREN expr RPAREN
    """
    p[0] = p[2]


def p_expr_term(p):
    """
    expr : term
    """
    p[0] = p[1]


def p_taglist(p):
    """
    taglist : taglist COMMA TAG
            | TAG
    """
    if len(p) == 4:
        p[0] = p[1] + [p[3]]
    else:
        p[0] = [p[1]]


def p_term_field_value(p):
    """
    term : WORD COLON value
         | WORD COLON taglist
    """
    p[0] = ("TERM", _Term(p[1], p[3]))


def p_value(p):
    """
    value : PHRASE
          | WORD
    """
    p[0] = p[1].strip()


def p_term_bare(p):
    """
    term : value
    """
    p[0] = ("TERM", _Term(None, p[1]))


def p_term_hash_tag(p):
    """
    term : TAG
    """
    # bare "#foo" is a tag literal
    p[0] = ("TERM", _Term("tag", p[1]))


def p_error(p):
    raise SyntaxError(f"Syntax error at {getattr(p, 'value', '?')}")


# build lexer and parser once
_lexer = lex.lex()
_parser = yacc.yacc(start="query", debug=False, write_tables=False)


def _parse_to_boolean_str_and_literals(
    query_string: str,
) -> tuple[str, dict[str, _Term]]:
    """
    Parse query string to boolean expression string with T0, T1... placeholders
    and a mapping of those placeholders to `_Term(field, value)`.
    """
    tree = _parser.parse(query_string, lexer=_lexer)
    boolean_str, literal_map, _ = _to_boolean_expr(tree)
    return boolean_str, literal_map


def _to_boolean_expr(tree, counter=0, mapping=None):
    """
    Recursively turn parse tree into boolean.py expression string
    with placeholders T0, T1, ...
    """
    if mapping is None:
        mapping = {}
    if not tree:
        return "", mapping, counter

    if isinstance(tree, tuple):
        tag = tree[0]
        if tag == "TERM":
            key = f"T{counter}"
            mapping[key] = tree[1]  # _Term
            return key, mapping, counter + 1
        elif tag == "NOT":
            s, mapping, counter = _to_boolean_expr(tree[1], counter, mapping)
            return f"NOT ({s})", mapping, counter
        elif tag in ("AND", "OR"):
            a, mapping, counter = _to_boolean_expr(tree[1], counter, mapping)
            b, mapping, counter = _to_boolean_expr(tree[2], counter, mapping)
            return f"({a} {tag} {b})", mapping, counter
    # fallback: should not happen
    return str(tree), mapping, counter


class QBuilder:
    def __init__(self):
        self._tags_exact_specs = []

    @property
    def needs_annotations(self):
        return bool(self._tags_exact_specs)

    def apply_annotations(self, qs):
        for names, total_alias, match_alias in self._tags_exact_specs:
            qs = qs.annotate(
                **{
                    total_alias: Count("tags", distinct=True),
                    match_alias: Count(
                        "tags", filter=Q(tags__name__in=names), distinct=True
                    ),
                }
            )
        return qs

    def compile(self, query_string: str) -> tuple[Q, Q]:
        """
        Compile query into two Q objects: (include, exclude).

        Adds annotations to count tags if needed (for exact tag matches)
        in the `self._tags_exact_specs` list.
        """
        boolean_str, literal_map = _parse_to_boolean_str_and_literals(query_string)
        algebra = BooleanAlgebra()
        expr = algebra.parse(boolean_str)

        if settings.DEBUG:
            logger.debug(f"search_keywords: '{query_string}' → '{boolean_str}'")
            for k, v in literal_map.items():
                logger.debug(f"  {k}: field={v.field} value={v.value}")

        def as_term(node):
            # node is a boolean.Symbol
            key = node.obj if hasattr(node, "obj") else str(node)
            t = literal_map[key]
            t.field = (t.field or "text").lower()
            return t

        def _term_q(field: str | None, value: str) -> Q:
            fld = (field or "text").lower()
            val = value.strip()

            if fld == "tag":
                if val == "*":
                    return Q(tags__isnull=False)
                if val.endswith("*"):
                    return Q(tags__name__istartswith=val[:-1])
                return Q(tags__name__iexact=val)

            if field == "id":
                return Q(id__icontains=value)

            if field == "description":
                return Q(description__icontains=value)

            if field == "filename":
                return Q(photo__icontains=value)

            # wide text (text OR tag contains)
            return (
                Q(description__icontains=value)
                | Q(id__icontains=value)
                | Q(photo__icontains=value)
                | Q(tags__name__icontains=value)
            )

        def build(node) -> tuple[Q, Q]:
            # returns (inc, exc) for subtree
            if isinstance(node, Symbol):
                t = as_term(node)
                if t.field == "tags":
                    # t.value is a list (from taglist)
                    if isinstance(t.value, list):
                        names = [str(n).strip() for n in t.value if str(n).strip()]
                    else:
                        # safety: accept a single string too
                        names = [
                            s.strip() for s in str(t.value).split(",") if s.strip()
                        ]
                    # create unique aliases for this clause
                    key = abs(hash(tuple(n.lower() for n in names))) & 0xFFFF
                    total_alias = f"tags_exact_{key}_total"
                    match_alias = f"tags_exact_{key}_match"
                    self._tags_exact_specs.append((names, total_alias, match_alias))
                    # include condition: total == N and matched == N
                    N = len(names)
                    return Q(**{total_alias: N, match_alias: N}), Q()

                # generic term
                return _term_q(t.field, t.value), Q()

            if isinstance(node, NOT):
                child = node.args[0]
                # Route NOT #... into exclude_q (correct for M2M)
                if isinstance(child, Symbol):
                    t = as_term(child)
                    val = t.value
                    if t.field == "tag":
                        if val == "*":
                            return Q(), Q(tags__isnull=False)
                        if val.endswith("*"):
                            return Q(), Q(tags__name__istartswith=val[:-1])
                        return Q(), Q(tags__name__iexact=val)
                # Generic NOT (non-tag): ~include
                inc, _exc = build(child)
                return ~inc, Q()

            if isinstance(node, AND):
                a_inc, a_exc = build(node.args[0])
                b_inc, b_exc = build(node.args[1])
                return a_inc & b_inc, a_exc | b_exc

            if isinstance(node, OR):
                a_inc, a_exc = build(node.args[0])
                b_inc, b_exc = build(node.args[1])
                # conservative exclude for OR
                return a_inc | b_inc, a_exc & b_exc

            # Fallback: should not happen, but treat as wide text literal
            return _term_q(None, str(node)), Q()

        inc, exc = build(expr)
        return inc, exc
