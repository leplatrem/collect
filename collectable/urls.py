from django.urls import path, re_path

from . import views


urlpatterns = [
    path("", views.index, name="index"),
    path("detail/<uuid:id>/", views.details, name="details"),
    re_path(
        r"^tags/(?P<slugs>[a-zA-Z]+(,[a-zA-Z]+)*)/$", views.by_tags, name="by_tags"
    ),
]
