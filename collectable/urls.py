from django.urls import path, re_path

from . import views


urlpatterns = [
    path("", views.index, name="index"),
    path("profile/", views.profile, name="profile"),
    path(
        "latest/",
        views.CollectableListView.as_view(sort_by="-created_at"),
        name="latest",
    ),
    path(
        "most-liked/",
        views.CollectableListView.as_view(sort_by="-nlikes"),
        name="most-liked",
    ),
    path(
        "most-wanted/",
        views.CollectableListView.as_view(sort_by="-nwants"),
        name="most-wanted",
    ),
    path(
        "most-owned/",
        views.CollectableListView.as_view(sort_by="-nowns"),
        name="most-owned",
    ),
    path("create/", views.create, name="create"),
    path("<uuid:id>/", views.details, name="details"),
    path("<uuid:id>/possession/", views.possession, name="possession"),
    re_path(
        r"^collection/(?P<slugs>[0-9a-zA-Z]+(,[0-9a-zA-Z]+)*)/$",
        views.collection,
        name="collection",
    ),
]
