import re

from django.conf import settings
from django.core.paginator import Paginator
from taggit.utils import _parse_tags as parse_tags


def tags_splitter(s: str) -> list[str]:
    tags = parse_tags(s)
    # Matches pattern in `collectable.urls`:
    return [re.sub(r"[^0-9a-zA-Z_\-]", "", t) for t in tags]


def paginate(request, qs, limit=settings.DEFAULT_PAGE_SIZE):
    paginated_qs = Paginator(qs, limit)
    page_no = request.GET.get("page")
    return paginated_qs.get_page(page_no)
