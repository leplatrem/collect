from django.urls import path, re_path

from collect.throttle import throttle

from . import feeds, views


urlpatterns = [
    path("", views.index, name="index"),
    path("profile/", views.profile, name="profile"),
    path("trades/", views.trades, name="trades"),
    path("create/", views.create, name="create"),
    path("<uuid:id>/", views.details, name="details"),
    path("<uuid:id>/duplicate/", views.DuplicateView.as_view(), name="duplicate"),
    path("<uuid:id>/possession/", views.possession, name="possession"),
    re_path(
        r"^collection/(?P<slugs>[0-9a-zA-Z_\-]+(,[0-9a-zA-Z_\-]+)*)/$",
        views.collection,
        name="collection",
    ),
    re_path(
        r"^collection/(?P<slugs>[0-9a-zA-Z_\-]+(,[0-9a-zA-Z_\-]+)*)/feed.atom$",
        feeds.CollectionAtomFeed(),
        name="collection-feed",
    ),
]


def lists_urlpatterns():
    for kind in views.LIST_ORDERING:
        slug = kind.replace("_", "-")

        list_view = views.CollectableListView.as_view(kind=kind)
        feed_view = feeds.CollectableListAtomFeed(kind=kind)

        if kind == "search":
            throttle_dec = throttle("search", "THROTTLE_SEARCH", methods=("GET",))
            list_view = throttle_dec(list_view)
            feed_view = throttle_dec(feed_view)

        yield path(f"{slug}/", list_view, name=slug)
        yield path(f"{slug}/feed.atom", feed_view, name=f"{slug}-feed")


urlpatterns += list(lists_urlpatterns())
