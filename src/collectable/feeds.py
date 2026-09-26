import os
from urllib.parse import urlencode

from django.conf import settings
from django.contrib.syndication.views import Feed
from django.urls import reverse
from django.utils.feedgenerator import Atom1Feed, Rss201rev2Feed
from django.utils.translation import gettext_lazy as _

from collectable.models import Collectable
from collectable.views import (
    LIST_DESCRIPTIONS,
    LIST_TITLES,
    list_of_kind,
    search_collectables,
)


class CollectableListFeed(Feed):
    """
    A list page, published as a feed: the same collectables, in the same
    order, for the collectors who follow the collection from a reader rather
    than by coming back to the site.

    Unlike a view, a single instance serves every request of its URL, so
    nothing about the request may be kept on `self`: what the feed methods
    need of it travels in the object built by `get_object()`.
    """

    feed_type = Atom1Feed
    format = "atom"
    description_template = "collectable/feed_item.html"

    def __init__(self, kind="latest"):
        # One of the `kind` of `CollectableListView`, set by the URLconf.
        self.kind = kind

    def get_object(self, request):
        # The feed is the same for everybody: it carries no possession mark,
        # so it can be cached and shared like any other public page.
        return {"keywords": request.GET.get("q", "").strip()}

    def _query_string(self, obj):
        return f"?{urlencode({'q': obj['keywords']})}" if obj["keywords"] else ""

    def title(self, obj):
        if self.kind == "search":
            return _("Collect - Search results for '%(q)s'") % {"q": obj["keywords"]}
        return _("Collect - %(list)s") % {"list": LIST_TITLES[self.kind]}

    def description(self, obj):
        return LIST_DESCRIPTIONS[self.kind]

    # RSS calls it a description, Atom a subtitle. Same sentence either way.
    subtitle = description

    def link(self, obj):
        """The page this feed mirrors."""
        page = reverse(f"collectable:{self.kind.replace('_', '-')}")
        return f"{page}{self._query_string(obj)}"

    def feed_url(self, obj):
        """
        The feed's own address. Spelled out rather than left to default to
        `request.path`, which drops the search query the feed is about.
        """
        url = reverse(f"collectable:{self.kind.replace('_', '-')}-{self.format}")
        return f"{url}{self._query_string(obj)}"

    def items(self, obj):
        qs = list_of_kind(
            Collectable.objects.get_queryset().with_possession_counts().with_tags(),
            self.kind,
        )
        if self.kind == "search":
            qs, _advanced = search_collectables(qs, obj["keywords"])
        return qs[: settings.FEED_ITEM_COUNT]

    def item_title(self, item):
        # Collectables have no title of their own: the description is what
        # the site shows with them, and the name of the photo is the best
        # there is without one.
        return item.description or os.path.basename(item.photo.name) or str(item.id)

    def item_link(self, item):
        return item.get_absolute_url()

    def item_guid(self, item):
        # The identifier of a collectable outlives the URL it is served at.
        return f"urn:uuid:{item.id}"

    item_guid_is_permalink = False

    def item_pubdate(self, item):
        return item.created_at

    def item_updateddate(self, item):
        return item.modified_at

    def item_categories(self, item):
        return [tag.name for tag in item.tags_list]

    def item_copyright(self, item):
        return item.get_license_display()


class CollectableListRssFeed(CollectableListFeed):
    feed_type = Rss201rev2Feed
    format = "rss"
