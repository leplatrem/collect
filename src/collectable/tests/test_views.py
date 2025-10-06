# Additions to your existing test_views.py file

import pytest
from django.conf import settings
from django.urls import reverse

from collectable.models import Collectable, DuplicateReport, Possession
from collectable.tests.factories import (
    CollectableFactory,
    DuplicateReportFactory,
    UserFactory,
)


@pytest.mark.parametrize(
    "path_name",
    [
        "collectable:latest",
        "collectable:most-liked",
        "collectable:most-wanted",
        "collectable:most-owned",
    ],
)
def test_list_views(db, client, path_name):
    url = reverse(path_name)
    response = client.get(url)
    assert response.status_code == 200
    assert "object_list" in response.context


def test_index_view(db, client):
    url = reverse("collectable:index")
    response = client.get(url)
    assert response.status_code == 200
    assert "total_collectables" in response.context


def test_create_view_authenticated_get(db, logged_in_client, collectable):
    url = reverse("collectable:create")
    response = logged_in_client.get(url)
    assert response.status_code == 200
    assert "form" in response.context


def test_create_view_authenticated_post(db, logged_in_client, collectable):
    url = reverse("collectable:create")
    data = {
        "description": "Created via test",
        "tags": "tag1,tag2",
        "photo": collectable.photo,
        "photo_x": 0,
        "photo_y": 0,
        "photo_w": 400,
        "photo_h": 400,
    }
    response = logged_in_client.post(url, data)
    assert response.status_code == 302
    id = response.url.split("/")[-2]
    collectable = Collectable.objects.get(id=id)
    assert collectable.description == "Created via test"


def test_details_view_authenticated_post(db, logged_in_client, collectable):
    url = reverse("collectable:details", kwargs={"id": collectable.id})
    data = {
        "description": "Edited via test",
        "tags": "tag1,tag2",
        "photo": collectable.photo,
        "photo_x": 0,
        "photo_y": 0,
        "photo_w": 400,
        "photo_h": 400,
    }
    response = logged_in_client.post(url, data)
    assert response.status_code == 200
    assert response.context["form"].errors == {}
    collectable.refresh_from_db()
    assert collectable.description == "Edited via test"


def test_possession_view_post_creates(user, logged_in_client, collectable):
    url = reverse("collectable:possession", kwargs={"id": collectable.id})
    response = logged_in_client.post(url, {"likes": True, "wants": False, "owns": True})
    assert response.status_code == 200
    assert Possession.objects.filter(user=user, collectable=collectable).exists()


def test_collection_view_with_valid_tag(client, collectable):
    collectable.tags.add("tag1")
    url = reverse("collectable:collection", kwargs={"slugs": "tag1"})
    response = client.get(url)
    assert response.status_code == 200
    assert "collectable_list" in response.context
    assert "tag_list" in response.context
    assert "reltag_list" in response.context


def test_collection_view_with_multiple_tags(client, collectable):
    collectable.tags.add("tag1", "tag2")
    url = reverse("collectable:collection", kwargs={"slugs": "tag1,tag2"})
    response = client.get(url)
    assert response.status_code == 200


def test_invalid_tag_fallback(db, client):
    url = reverse("collectable:collection", kwargs={"slugs": "invalidtag"})
    response = client.get(url)
    assert response.status_code == 200
    assert "tag_list" in response.context
    # The tag_list should contain a Tag object with just a name
    assert any(t.name == "invalidtag" for t in response.context["tag_list"])


def test_profile_view(db, logged_in_client):
    url = reverse("collectable:profile")
    response = logged_in_client.get(url)
    assert response.status_code == 200
    assert "collectable_liked" in response.context


@pytest.mark.django_db
def test_duplicate_get_no_report(client, collectable):
    url = reverse("collectable:duplicate", kwargs={"id": collectable.id})
    response = client.get(url, follow_redirects=False)
    assert response.status_code == 302  # redirect
    assert reverse("collectable:details", kwargs={"id": collectable.id}) in response.url


@pytest.mark.django_db
def test_duplicate_get_with_report_not_hidden(
    client, collectable, another_collectable, user
):
    DuplicateReportFactory(
        original=another_collectable, duplicate=collectable, reporter=user
    )
    url = reverse("collectable:duplicate", kwargs={"id": collectable.id})
    response = client.get(url)
    assert response.status_code == 200
    assert response.context["collectable"] == collectable
    assert response.context["original"] == another_collectable


@pytest.mark.django_db
def test_duplicate_delete(logged_in_client, collectable, another_collectable, user):
    DuplicateReportFactory(
        original=another_collectable, duplicate=collectable, reporter=user
    )
    url = reverse("collectable:duplicate", kwargs={"id": collectable.id})
    response = logged_in_client.delete(url)
    assert response.status_code == 204


@pytest.mark.django_db
def test_duplicate_delete_with_multiple(
    logged_in_client, collectable, another_collectable, user
):
    DuplicateReportFactory(
        original=another_collectable, duplicate=collectable, reporter=user
    )
    DuplicateReportFactory(
        original=CollectableFactory(), duplicate=collectable, reporter=user
    )
    url = reverse("collectable:duplicate", kwargs={"id": collectable.id})
    response = logged_in_client.delete(url)
    assert response.status_code == 204


@pytest.mark.django_db
def test_duplicate_get_with_report_hidden_redirects_to_original(
    client, collectable, another_collectable, user
):
    for _ in range(settings.DUPLICATE_CONFIRMATION_THRESHOLD + 1):
        DuplicateReportFactory(
            original=another_collectable, duplicate=collectable, reporter=UserFactory()
        )
    collectable.refresh_from_db()
    assert collectable.hidden

    url = reverse("collectable:duplicate", kwargs={"id": collectable.id})
    response = client.get(url, follow_redirects=False)
    assert response.status_code == 302
    assert (
        reverse("collectable:details", kwargs={"id": another_collectable.id})
        in response.url
    )


@pytest.mark.django_db
def test_duplicate_get_with_report_hidden_redirects_to_original_in_chain(
    client, collectable, another_collectable, user
):
    c0 = CollectableFactory()
    c1 = CollectableFactory()
    c2 = CollectableFactory()
    c3 = CollectableFactory()
    DuplicateReportFactory(original=c0, duplicate=c1, reporter=user)
    DuplicateReportFactory(original=c0, duplicate=c2, reporter=user)
    DuplicateReportFactory(original=c2, duplicate=c3, reporter=user)
    c2.hidden = True
    c2.save()
    c3.hidden = True
    c3.save()

    url = reverse("collectable:duplicate", kwargs={"id": c3.id})
    response = client.get(url, follow=True)
    assert response.status_code == 200
    assert response.context["collectable"] == c0
    # c1 is also a duplicate of c0, but not hidden.
    assert list(response.context["duplicates"]) == [c1]


@pytest.mark.django_db
def test_duplicate_post_invalid_form(logged_in_client, collectable):
    url = reverse("collectable:duplicate", kwargs={"id": collectable.id})
    response = logged_in_client.post(url, {"original_input": ""})  # invalid
    assert response.status_code == 200
    assert "form" in response.context
    assert "Ce champ est obligatoire" in str(response.context["form"].errors)
    assert response.context["collectable"] == collectable


@pytest.mark.django_db
def test_duplicate_post_valid_form(logged_in_client, collectable, another_collectable):
    url = reverse("collectable:duplicate", kwargs={"id": collectable.id})
    response = logged_in_client.post(url, {"original_input": another_collectable.id})
    assert response.status_code == 200
    assert DuplicateReport.objects.filter(
        original=another_collectable, duplicate=collectable
    ).exists()
    assert response.context["original"] == another_collectable
    assert "reports" in response.context
    assert response.headers["HX-Retarget"] == "main"
    assert response.headers["HX-Reselect"] == "main"
