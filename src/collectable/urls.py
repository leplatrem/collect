from django.urls import path, re_path

from collect.throttle import throttle
from collectable.feeds import CollectableListFeed, CollectableListRssFeed

from . import views


urlpatterns = [
    path("", views.index, name="index"),
    path("profile/", views.profile, name="profile"),
    path("trades/", views.trades, name="trades"),
    path(
        "latest/",
        views.CollectableListView.as_view(kind="latest"),
        name="latest",
    ),
    path(
        "most-liked/",
        views.CollectableListView.as_view(kind="most_liked"),
        name="most-liked",
    ),
    path(
        "most-wanted/",
        views.CollectableListView.as_view(kind="most_wanted"),
        name="most-wanted",
    ),
    path(
        "most-owned/",
        views.CollectableListView.as_view(kind="most_owned"),
        name="most-owned",
    ),
    path(
        "most-spares/",
        views.CollectableListView.as_view(kind="most_spares"),
        name="most-spares",
    ),
    # Searching is the most expensive read of the site (it scans descriptions
    # and tags), and the search box queries it as the visitor types.
    path(
        "search/",
        throttle("search", "THROTTLE_SEARCH", methods=("GET",))(
            views.CollectableListView.as_view(kind="search")
        ),
        name="search",
    ),
    path("create/", views.create, name="create"),
    path("<uuid:id>/", views.details, name="details"),
    path("<uuid:id>/duplicate/", views.DuplicateView.as_view(), name="duplicate"),
    path("<uuid:id>/possession/", views.possession, name="possession"),
    re_path(
        r"^collection/(?P<slugs>[0-9a-zA-Z_\-]+(,[0-9a-zA-Z_\-]+)*)/$",
        views.collection,
        name="collection",
    ),
]


def feed_urlpatterns():
    """
    Every list is also published as a feed, in both formats, eg.
    `latest/feed.atom` and `latest/feed.rss`. Search feeds carry their query
    in `?q=`, and are throttled like the page they mirror.
    """
    for kind in views.LIST_ORDERING:
        slug = kind.replace("_", "-")
        for feed_class in (CollectableListFeed, CollectableListRssFeed):
            feed_view = feed_class(kind=kind)
            if kind == "search":
                feed_view = throttle("search", "THROTTLE_SEARCH", methods=("GET",))(
                    feed_view
                )
            yield path(
                f"{slug}/feed.{feed_class.format}",
                feed_view,
                name=f"{slug}-{feed_class.format}",
            )


urlpatterns += list(feed_urlpatterns())
