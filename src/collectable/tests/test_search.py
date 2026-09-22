import sys
import threading

import pytest
from django.conf import settings
from django.urls import reverse
from django.utils.html import escape
from django.utils.translation import gettext

from collectable.models import Collectable
from collectable.search import QBuilder
from collectable.tests.factories import CollectableFactory


pytestmark = pytest.mark.django_db(transaction=True)


def test_collectable_advanced_search_raises_on_invalid_query():
    qs = Collectable.objects.all()
    with pytest.raises(Exception):
        qs.advanced_search('description:"unclosed phrase')


def test_collectable_basic_search_empty_query_returns_all():
    CollectableFactory(description="alpha", tags=["foo"])
    CollectableFactory(description="beta", tags=["bar"])
    qs = Collectable.objects.all()
    assert list(qs.basic_search("")) == list(qs)


def test_collectable_search_phrase_matches_description():
    a = CollectableFactory(description="summer vacation photo", tags=["travel"])
    CollectableFactory(description="winter work", tags=["office"])
    res = Collectable.objects.all().advanced_search('"vacation photo"')
    assert set(res) == {a}


def test_collectable_search_phrase_matches_tag_contains():
    a = CollectableFactory(description="boring text", tags=["big-team"])
    CollectableFactory(description="other", tags=["mozweek"])
    res = Collectable.objects.all().advanced_search('"team"')
    assert set(res) == {a}


def test_collectable_search_description_field():
    CollectableFactory(description="boring text", tags=["big-team"])
    a = CollectableFactory(description="my team")
    res = Collectable.objects.all().advanced_search('description:"team"')
    assert set(res) == {a}


def test_tag_exact():
    a = CollectableFactory(description="x", tags=["bug"])
    CollectableFactory(description="y", tags=["buggy"])
    res = Collectable.objects.all().advanced_search("#bug")
    assert set(res) == {a}


def test_collectable_search_tag_prefix():
    CollectableFactory(description="x", tags=["project-foo"])
    CollectableFactory(description="y", tags=["bar"])
    c = CollectableFactory(description="z", tags=["foo"])
    res = Collectable.objects.all().advanced_search("#foo*")
    # matches "foo" and "foo..." prefix, but not "project-foo"
    assert set(res) == {c}


def test_collectable_search_tags_exact_only_those_tags():
    exact = CollectableFactory(description="x", tags=["foo", "bar"])
    CollectableFactory(description="y", tags=["foo"])
    CollectableFactory(description="z", tags=["foo", "bar", "baz"])
    order_diff = CollectableFactory(description="w", tags=["bar", "foo"])

    res = Collectable.objects.all().advanced_search("tags:#foo,#bar")
    # must match only those having exactly {foo, bar}
    assert set(res) == {exact, order_diff}


def test_collectable_search_boolean_and_or_not():
    CollectableFactory(description="error report", tags=["wontfix"])
    a = CollectableFactory(description="error report", tags=["bug"])
    b = CollectableFactory(description="crash log", tags=["bug"])
    CollectableFactory(description="crash log", tags=["task"])
    CollectableFactory(description="feature", tags=["enhancement", "wontfix"])

    q = '("error report" OR "crash log") AND #bug AND NOT #wontfix'
    res = Collectable.objects.all().advanced_search(q)
    assert set(res) == {a, b}


def test_collectable_search_parentheses_precedence():
    a = CollectableFactory(description="sticker", tags=["team"])
    b = CollectableFactory(description="sticker", tags=["ux"])
    CollectableFactory(description="sticker", tags=["old"])

    q = "description:sticker AND (#team OR #ux) AND NOT #old"
    res = Collectable.objects.all().advanced_search(q)
    assert set(res) == {a, b}


@pytest.mark.parametrize("query", ['"mozweek 2024" #team', '#team AND "mozweek 2024"'])
def test_collectable_search_combined_text_and_tag(query):
    a = CollectableFactory(description="mozweek 2024", tags=["team"])
    CollectableFactory(description="mozweek something", tags=["other"])
    res = Collectable.objects.all().advanced_search(query)
    assert set(res) == {a}


@pytest.mark.parametrize(
    "query", ["description:logo AND NOT #archived", "description:logo - #archived"]
)
def test_collectable_search_not_tag(query):
    a = CollectableFactory(description="logo", tags=["keep"])
    CollectableFactory(description="logo", tags=["archived"])
    res = Collectable.objects.all().advanced_search(query)
    assert set(res) == {a}


def test_collectable_search_matches_id_and_photo_name(collectable):
    # See factories.py for the filename used in the factory
    res = Collectable.objects.all().advanced_search("sticker-filename")
    assert set(res) == {collectable}


def test_collectable_search_matches_supports_filename(collectable):
    CollectableFactory(description="sticker-filename", filename="other.jpg")
    # See factories.py for the filename used in the factory
    res = Collectable.objects.all().advanced_search("filename:sticker-filename")
    assert set(res) == {collectable}


def test_collectable_search_distinct_results_with_multiple_matching_tags():
    """
    When an item matches via multiple tags, the queryset should still return it once.
    """
    a = CollectableFactory(description="x", tags=["foo", "foo-helper"])
    res = Collectable.objects.all().advanced_search("#foo OR #foo*")
    assert list(res) == [a]


def test_collectable_search_matching_all_tags():
    a = CollectableFactory(description="x", tags=["foo", "foo-helper"])
    CollectableFactory(description="x", tags=[])
    res = Collectable.objects.all().advanced_search("#*")
    assert list(res) == [a]


def test_collectable_search_not_any_tag():
    """
    When an item matches via multiple tags, the queryset should still return it once.
    """
    a = CollectableFactory(description="x", tags=[])
    CollectableFactory(description="y", tags=["foo"])
    res = Collectable.objects.all().advanced_search("NOT #*")
    assert list(res) == [a]


def test_collectable_search_not_phrase():
    """
    When an item matches via multiple tags, the queryset should still return it once.
    """
    a = CollectableFactory(description="x", tags=["bim"])
    CollectableFactory(description="y", tags=["bar"])
    CollectableFactory(description="y", tags=["foo"])
    res = Collectable.objects.all().advanced_search("NOT (#foo OR #bar)")
    assert list(res) == [a]


def test_collectable_search_not_wild():
    """
    When an item matches via multiple tags, the queryset should still return it once.
    """
    a = CollectableFactory(description="x", tags=["bim"])
    CollectableFactory(description="y", tags=["bar"])
    res = Collectable.objects.all().advanced_search("NOT #ba*")
    assert list(res) == [a]


def test_collectable_search_refuses_too_many_terms():
    # Every term adds a join to the SQL query: an arbitrarily long query would
    # otherwise be an easy way to keep the database busy.
    query = " AND ".join(f"#tag{i}" for i in range(settings.MAX_SEARCH_TERMS + 1))

    with pytest.raises(ValueError, match="more than"):
        QBuilder().compile(query)


def test_collectable_search_accepts_the_maximum_number_of_terms():
    query = " AND ".join(f"#tag{i}" for i in range(settings.MAX_SEARCH_TERMS))

    include_q, _exclude_q = QBuilder().compile(query)

    assert include_q


def test_collectable_search_refuses_long_queries():
    with pytest.raises(ValueError, match="longer than"):
        QBuilder().compile("a" * (settings.MAX_SEARCH_QUERY_LENGTH + 1))


def test_collectable_search_falls_back_to_basic_search_when_refused(client):
    # The view turns a refused query into a basic search rather than an error.
    match = CollectableFactory(description="needle")
    CollectableFactory(description="haystack")
    query = " ".join(["needle"] * (settings.MAX_SEARCH_TERMS + 1))

    resp = client.get(reverse("collectable:search"), {"q": query})

    assert resp.status_code == 200
    assert resp.context["advanced_search"] is False
    assert list(resp.context["collectable_list"]) == [match]


def fallback_notice(keywords):
    """
    The notice shown when the query could not be compiled, as the page shows
    it: tests run in French, and only what is interpolated is escaped.
    """
    return gettext(
        '"%(keywords)s" could not be read as a query, so its words were '
        "searched as they are."
    ) % {"keywords": escape(keywords)}


def test_search_results_explain_a_query_that_could_not_be_read(client):
    CollectableFactory(description="sticker", tags=["bug"])

    response = client.get(reverse("collectable:search"), {"q": "#bug AND"})

    assert response.context["advanced_search"] is False
    content = response.content.decode()
    assert fallback_notice("#bug AND") in content
    # And the syntax is right there, under the results.
    assert 'id="how-to-search"' in content


def test_search_results_of_a_valid_query_only_show_the_syntax(client):
    CollectableFactory(description="sticker", tags=["bug"])

    response = client.get(reverse("collectable:search"), {"q": "#bug"})

    assert response.context["advanced_search"] is True
    content = response.content.decode()
    assert fallback_notice("#bug") not in content
    assert 'id="how-to-search"' in content


def test_other_lists_do_not_show_the_search_syntax(client):
    response = client.get(reverse("collectable:latest"))

    assert response.context["is_search"] is False
    assert 'id="how-to-search"' not in response.content.decode()


def test_collectable_search_parses_concurrently():
    # The `ply` lexer and parser are shared between threads, and keep the state
    # of the parse (input position, state and symbol stacks) on the instance:
    # without serialization, concurrent searches corrupt each other's results.
    queries = [f"#tag{i} AND description:value{i}" for i in range(30)]
    results = {}
    errors = []

    def compile_repeatedly(query):
        for _ in range(40):
            try:
                results[query] = QBuilder().compile(query)
            except Exception as exc:
                errors.append(exc)
                return

    threads = [
        threading.Thread(target=compile_repeatedly, args=(query,)) for query in queries
    ]
    # Switch between threads as often as possible, to make the interleaving
    # happen reliably rather than once in a while.
    previous_interval = sys.getswitchinterval()
    sys.setswitchinterval(1e-9)
    try:
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()
    finally:
        sys.setswitchinterval(previous_interval)

    assert errors == []
    assert len(results) == len(queries)
    # Each thread must get the terms of its own query, not of another one.
    for i, query in enumerate(queries):
        include_q, _exclude_q = results[query]
        assert f"value{i}" in str(include_q)
        assert f"tag{i}" in str(include_q)
