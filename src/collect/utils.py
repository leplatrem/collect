import re

from django.conf import settings
from django.core.paginator import Paginator
from taggit.utils import _parse_tags as parse_tags


def tags_splitter(s: str) -> list[str]:
    tags = parse_tags(s)
    # Matches pattern in `collectable.urls`:
    return [re.sub(r"[^0-9a-zA-Z_\-]", "", t) for t in tags]


def tags_joiner(tags: list) -> str:
    return ", ".join(sorted(f"#{tag.name}" for tag in tags))


class CountedPaginator(Paginator):
    """
    Paginator that is given the total number of objects.

    `Paginator` counts the objects itself, which runs the paginated query a
    second time just to count its rows. When the caller already knows the
    total, or can obtain it with a cheaper query, it can pass it along.
    """

    def __init__(self, object_list, per_page, *, count, **kwargs):
        super().__init__(object_list, per_page, **kwargs)
        # Shadows the `count` cached property of `Paginator`.
        self.count = count


def paginate(request, qs, limit=None, count=None):
    # Read at call time, not when this module is imported, so that the setting
    # is what it says it is.
    limit = limit if limit is not None else settings.DEFAULT_PAGE_SIZE
    if count is None:
        paginated_qs = Paginator(qs, limit)
    else:
        paginated_qs = CountedPaginator(qs, limit, count=count)
    page_no = request.GET.get("page")
    return paginated_qs.get_page(page_no)
