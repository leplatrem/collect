import re

from taggit.utils import _parse_tags as parse_tags


def tags_splitter(s: str) -> list[str]:
    tags = parse_tags(s)
    # Matches pattern in `collectable.urls`:
    return [re.sub(r"[^0-9a-zA-Z_\-]", "", t) for t in tags]
