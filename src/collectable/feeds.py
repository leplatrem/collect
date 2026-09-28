from urllib.parse import urlencode

from django.conf import settings
from django.contrib.syndication.views import Feed
from django.urls import reverse
from django.utils.feedgenerator import Atom1Feed
from django.utils.html import escape
from django.utils.translation import gettext_lazy as _
from taggit.models import Tag

from collect.utils import tags_joiner
from collectable.models import Collectable
from collectable.views import (
    LIST_DESCRIPTIONS,
    LIST_TITLES,
    list_of_kind,
    search_collectables,
)


class BaseCollectableFeed(Feed):
    """
    What every feed of the site has in common: how a collectable becomes an
    entry. Subclasses pick which collectables, and in which order.
    """

    feed_type = Atom1Feed
    description_template = "collectable/feed_item.html"

    def item_title(self, item):
        return escape(item.title())

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


class CollectableListAtomFeed(BaseCollectableFeed):
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

    def subtitle(self, obj):
        return LIST_DESCRIPTIONS[self.kind]

    def link(self, obj):
        page = reverse(f"collectable:{self.kind.replace('_', '-')}")
        return f"{page}{self._query_string(obj)}"

    def feed_url(self, obj):
        """
        The feed's own address. Spelled out rather than left to default to
        `request.path`, which drops the search query the feed is about.
        """
        url = reverse(f"collectable:{self.kind.replace('_', '-')}-feed")
        return f"{url}{self._query_string(obj)}"

    def items(self, obj):
        qs = list_of_kind(
            Collectable.objects.get_queryset().with_possession_counts().with_tags(),
            self.kind,
        )
        if self.kind == "search":
            qs, _advanced = search_collectables(qs, obj["keywords"])
        return qs[: settings.FEED_ITEM_COUNT]


class CollectionAtomFeed(BaseCollectableFeed):
    def get_object(self, request, slugs):
        # Read the URL the way `views.collection` does.
        slugs = slugs.split(",")
        # A slug is not its tag's name (`#Paris 2024` slugs to `paris-2024`),
        # and a slug nobody has used yet has no tag behind it at all.
        tags = list(Tag.objects.filter(slug__in=slugs))
        known = {tag.slug for tag in tags}
        tags += [Tag(name=slug, slug=slug) for slug in slugs if slug not in known]
        return {"slugs": slugs, "tags": tags}

    def title(self, obj):
        return _("Collect - Collection %(tags)s") % {"tags": tags_joiner(obj["tags"])}

    def subtitle(self, obj):
        return _("The collectables of this collection, most recent first.")

    def link(self, obj):
        return reverse("collectable:collection", args=[",".join(obj["slugs"])])

    def items(self, obj):
        qs = Collectable.objects.get_queryset().with_tags().order_by("-created_at")
        for slug in obj["slugs"]:
            qs = qs.filter(tags__slug=slug)
        return qs[: settings.FEED_ITEM_COUNT]
