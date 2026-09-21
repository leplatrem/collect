from django.test import RequestFactory

from collect.utils import paginate, tags_joiner, tags_splitter


class FakeTag:
    def __init__(self, name):
        self.name = name


def test_tags_splitter_keeps_url_safe_characters():
    assert tags_splitter("#foo, bar-baz, héllo!") == ["foo", "bar-baz", "hllo"]


def test_tags_joiner_sorts_and_prefixes():
    assert tags_joiner([FakeTag("beta"), FakeTag("alpha")]) == "#alpha, #beta"


def test_paginate_reads_the_page_size_from_the_settings(settings):
    settings.DEFAULT_PAGE_SIZE = 3
    request = RequestFactory().get("/")

    page = paginate(request, qs=list(range(10)))

    assert list(page.object_list) == [0, 1, 2]
    assert page.paginator.num_pages == 4


def test_paginate_accepts_an_explicit_page_size():
    request = RequestFactory().get("/", {"page": "2"})

    page = paginate(request, qs=list(range(10)), limit=4)

    assert list(page.object_list) == [4, 5, 6, 7]


def test_paginate_falls_back_to_the_first_page():
    request = RequestFactory().get("/", {"page": "not-a-number"})

    assert paginate(request, qs=list(range(10)), limit=4).number == 1
