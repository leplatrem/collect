from django.urls import path, re_path

from . import views


urlpatterns = [
    path("", views.index, name="index"),
    path("profile/", views.profile, name="profile"),
    path("<uuid:id>/", views.details, name="details"),
    path("<uuid:id>/possession/", views.possession, name="possession"),
    re_path(
        r"^tags/(?P<slugs>[a-zA-Z]+(,[a-zA-Z]+)*)/$", views.by_tags, name="by_tags"
    ),
]
