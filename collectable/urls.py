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
    path("<uuid:id>/", views.details, name="details"),
    path("<uuid:id>/possession/", views.possession, name="possession"),
    re_path(
        r"^tags/(?P<slugs>[a-zA-Z]+(,[a-zA-Z]+)*)/$", views.by_tags, name="by_tags"
    ),
]
