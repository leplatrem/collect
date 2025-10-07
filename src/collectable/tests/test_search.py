import pytest

from collectable.models import Collectable
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
