from django.urls import path, re_path

from . import views


urlpatterns = [
    path("", views.index, name="index"),
    path("profile/", views.profile, name="profile"),
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
    path("search/", views.CollectableListView.as_view(kind="search"), name="search"),
    path("create/", views.create, name="create"),
    path("<uuid:id>/", views.details, name="details"),
    path("<uuid:id>/duplicate/", views.duplicate, name="duplicate"),
    path("<uuid:id>/possession/", views.possession, name="possession"),
    re_path(
        r"^collection/(?P<slugs>[0-9a-zA-Z_\-]+(,[0-9a-zA-Z_\-]+)*)/$",
        views.collection,
        name="collection",
    ),
]
