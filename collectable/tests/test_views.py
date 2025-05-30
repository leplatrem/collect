# Additions to your existing test_views.py file

import pytest
from django.urls import reverse
from django.utils import translation

from collectable.models import Collectable, Possession


@pytest.fixture(autouse=True, scope="module")
def set_language():
    translation.activate("en")
    yield
    translation.deactivate()


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
