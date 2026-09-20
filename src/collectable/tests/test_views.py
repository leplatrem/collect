# Additions to your existing test_views.py file

import io
from unittest.mock import patch

import pytest
from django.conf import settings
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import IntegrityError, connection
from django.test.utils import CaptureQueriesContext
from django.urls import reverse
from PIL import Image

from collectable.models import Collectable, DuplicateReport, Possession
from collectable.tests.factories import (
    CollectableFactory,
    DuplicateReportFactory,
    PossessionFactory,
    UserFactory,
    image_upload,
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
        "license": "CC-BY-SA-4.0",
        "photo": image_upload(),
        "photo_x": 0,
        "photo_y": 0,
        "photo_w": 400,
        "photo_h": 400,
        "rights_confirmed": True,
    }
    response = logged_in_client.post(url, data)
    assert response.status_code == 302
    id = response.url.split("/")[-2]
    collectable = Collectable.objects.get(id=id)
    assert collectable.description == "Created via test"


def test_create_view_accepts_png_upload(db, logged_in_client):
    # Build a transparent PNG upload.
    img = Image.new("RGBA", (400, 400), color=(255, 0, 0, 0))
    buffer = io.BytesIO()
    img.save(buffer, format="PNG")
    buffer.seek(0)
    png = SimpleUploadedFile("sticker.png", buffer.read(), content_type="image/png")

    url = reverse("collectable:create")
    data = {
        "description": "PNG upload",
        "tags": "tag1",
        "license": "CC-BY-SA-4.0",
        "photo": png,
        "photo_x": 0,
        "photo_y": 0,
        "photo_w": 400,
        "photo_h": 400,
        "rights_confirmed": True,
    }
    response = logged_in_client.post(url, data)
    assert response.status_code == 302
    id = response.url.split("/")[-2]
    collectable = Collectable.objects.get(id=id)
    # Original is preserved as PNG.
    assert collectable.photo.name.endswith(".png")
    # JPEG thumbnail is generated without error (transparency flattened onto white).
    thumb = Image.open(collectable.thumbnail.file)
    assert thumb.format == "JPEG"
    assert thumb.convert("RGB").getpixel((0, 0)) == (255, 255, 255)


def test_details_view_authenticated_post(db, logged_in_client, collectable):
    url = reverse("collectable:details", kwargs={"id": collectable.id})
    data = {
        "description": "Edited via test",
        "tags": "tag1,tag2",
        "license": "CC-BY-SA-4.0",
        "photo": image_upload(),
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


@pytest.mark.django_db(transaction=True)
def test_collectable_advanced_search(client, collectable, another_collectable):
    another_collectable.hidden = True
    another_collectable.save()
    resp = client.get(reverse("collectable:search"), {"q": "NOT #nonexistent"})
    assert resp.status_code == 200
    assert resp.context["collectable_list"].count() == 1


@pytest.mark.django_db(transaction=True)
def test_collectable_basic_search_on_error(client, collectable, another_collectable):
    resp = client.get(reverse("collectable:search"), {"q": "AN( "})
    assert resp.status_code == 200
    assert resp.context["advanced_search"] is False
    assert resp.context["collectable_list"].count() == 0


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


@pytest.mark.django_db
def test_index_view_tag_list_excludes_hidden_collectables(client):
    visible1 = CollectableFactory()
    visible2 = CollectableFactory()
    visible1.tags.add("shared")
    visible2.tags.add("shared")

    hidden1 = CollectableFactory(hidden=True)
    hidden2 = CollectableFactory(hidden=True)
    hidden1.tags.add("ghost")
    hidden2.tags.add("ghost")

    response = client.get(reverse("collectable:index"))

    tag_names = {t.name for t in response.context["tag_list"]}
    assert "shared" in tag_names
    assert "ghost" not in tag_names


@pytest.mark.django_db
def test_list_view_extra_context_not_shared_across_requests(client, collectable):
    # Trigger a search request that sets `advanced_search` in extra_context.
    client.get(reverse("collectable:search"), {"q": "anything"})

    # A subsequent unrelated list request must not inherit `advanced_search`.
    response = client.get(reverse("collectable:latest"))

    assert "advanced_search" not in response.context


def test_collection_view_paginates_in_the_database(db, client):
    for _ in range(3):
        CollectableFactory(tags=["big"])
    url = reverse("collectable:collection", kwargs={"slugs": "big"})

    with CaptureQueriesContext(connection) as small:
        client.get(url)

    for _ in range(9):
        CollectableFactory(tags=["big"])

    with CaptureQueriesContext(connection) as large:
        response = client.get(url)

    # Whatever the size of the collection, the page costs the same: the view
    # used to load every collectable of the tag in memory to show 20 of them.
    assert len(large.captured_queries) == len(small.captured_queries)
    assert response.context["total_collectables"] == 12


def test_collection_view_page_size(db, client, settings):
    settings.DEFAULT_PAGE_SIZE = 5
    for _ in range(8):
        CollectableFactory(tags=["big"])
    url = reverse("collectable:collection", kwargs={"slugs": "big"})

    response = client.get(url)

    assert len(response.context["page_obj"].object_list) == 5
    assert response.context["page_obj"].paginator.count == 8
    assert response.context["page_obj"].has_next()

    response = client.get(url, {"page": 2})
    assert len(response.context["page_obj"].object_list) == 3


def test_collection_view_counts_what_the_user_owns(logged_in_client, user):
    owned = CollectableFactory(tags=["big"])
    CollectableFactory(tags=["big"])
    PossessionFactory(user=user, collectable=owned, owns=True, likes=False, wants=False)

    url = reverse("collectable:collection", kwargs={"slugs": "big"})
    response = logged_in_client.get(url)

    assert response.context["total_owned"] == 1
    assert response.context["total_collectables"] == 2
    assert response.context["percent_owned"] == 50


def test_collection_view_of_anonymous_user_owns_nothing(client, user):
    owned = CollectableFactory(tags=["big"])
    PossessionFactory(user=user, collectable=owned, owns=True, likes=False, wants=False)

    url = reverse("collectable:collection", kwargs={"slugs": "big"})
    response = client.get(url)

    assert response.context["total_owned"] == 0
    assert response.context["percent_owned"] == 0


def test_list_view_stores_a_bounded_list_in_session(db, client, settings):
    settings.SESSION_LIST_MAX_SIZE = 3
    for _ in range(5):
        CollectableFactory()

    client.get(reverse("collectable:latest"))

    # The list is written on every list view and read back on every request of
    # the session afterwards.
    assert len(client.session["collectable_list"]) == 3


def test_collection_view_stores_a_bounded_list_in_session(db, client, settings):
    settings.SESSION_LIST_MAX_SIZE = 2
    for _ in range(5):
        CollectableFactory(tags=["big"])

    client.get(reverse("collectable:collection", kwargs={"slugs": "big"}))

    assert len(client.session["collectable_list"]) == 2


def test_list_view_session_list_follows_the_displayed_order(db, client):
    oldest = CollectableFactory()
    newest = CollectableFactory()

    client.get(reverse("collectable:latest"))

    assert client.session["collectable_list"] == [str(newest.id), str(oldest.id)]


@pytest.mark.parametrize(
    "path_name, counter",
    [
        ("collectable:most-liked", "likes"),
        ("collectable:most-wanted", "wants"),
        ("collectable:most-owned", "owns"),
    ],
)
def test_count_sorted_lists_still_filter_on_their_counter(
    client, user, path_name, counter
):
    listed = CollectableFactory()
    CollectableFactory()  # No possession at all.
    PossessionFactory(
        user=user,
        collectable=listed,
        **{"likes": False, "wants": False, "owns": False, counter: True},
    )

    response = client.get(reverse(path_name))

    assert list(response.context["object_list"]) == [listed]


def test_index_view_tag_list_is_bounded(db, client, settings):
    settings.INDEX_TAG_LIST_COUNT = 2
    for i in range(4):
        CollectableFactory(tags=[f"tag{i}"])
        CollectableFactory(tags=[f"tag{i}"])

    response = client.get(reverse("collectable:index"))

    assert len(response.context["tag_list"]) == 2


def test_profile_view_is_bounded(logged_in_client, user, settings):
    settings.PROFILE_LIST_COUNT = 2
    for _ in range(4):
        PossessionFactory(
            user=user,
            collectable=CollectableFactory(),
            owns=True,
            likes=True,
            wants=False,
        )

    response = logged_in_client.get(reverse("collectable:profile"))

    assert len(response.context["collectable_owned"]) == 2
    assert len(response.context["collectable_liked"]) == 2
    # The totals are still exact.
    assert response.context["total_owned"] == 4
    assert response.context["total_liked"] == 4
    assert response.context["total_wanted"] == 0


def test_possession_view_survives_a_concurrent_creation(
    user, logged_in_client, collectable
):
    # Another request of the same user inserted the row between our lookup and
    # our insert: `unique_possession` rejects ours.
    existing = Possession.objects.create(
        user=user, collectable=collectable, likes=False, owns=False
    )
    url = reverse("collectable:possession", kwargs={"id": collectable.id})

    with patch.object(Possession.objects, "get_or_create", side_effect=IntegrityError):
        response = logged_in_client.post(url, {"likes": True, "owns": True})

    # The request is served with the row the other one created, instead of
    # failing with a server error.
    assert response.status_code == 200
    existing.refresh_from_db()
    assert existing.likes is True
    assert existing.owns is True


def test_details_view_shows_a_bounded_history(logged_in_client, collectable, settings):
    settings.HISTORY_LIST_COUNT = 2
    for i in range(6):
        collectable.description = f"Update {i}"
        collectable.save()

    url = reverse("collectable:details", kwargs={"id": collectable.id})
    response = logged_in_client.get(url)

    assert response.status_code == 200
    assert len(response.context["collectable"].history_with_deltas()) == 2


def test_create_view_rejects_a_renderable_source_file(db, logged_in_client):
    url = reverse("collectable:create")
    data = {
        "description": "With a source file",
        "tags": "tag1",
        "license": "CC-BY-SA-4.0",
        "photo": image_upload(),
        "photo_x": 0,
        "photo_y": 0,
        "photo_w": 400,
        "photo_h": 400,
        "rights_confirmed": True,
        "source_file": SimpleUploadedFile(
            "payload.html", b"<script>alert(document.cookie)</script>"
        ),
    }

    response = logged_in_client.post(url, data)

    # Source files are downloadable from the same origin as the site.
    assert response.status_code == 200
    assert "source_file" in response.context["form"].errors
    assert not Collectable.objects.filter(description="With a source file").exists()


def test_create_view_accepts_a_source_file(db, logged_in_client):
    url = reverse("collectable:create")
    data = {
        "description": "With a source file",
        "tags": "tag1",
        "license": "CC-BY-SA-4.0",
        "photo": image_upload(),
        "photo_x": 0,
        "photo_y": 0,
        "photo_w": 400,
        "photo_h": 400,
        "rights_confirmed": True,
        "source_file": SimpleUploadedFile("original.svg", b"<svg></svg>"),
    }

    response = logged_in_client.post(url, data)

    assert response.status_code == 302
    created = Collectable.objects.get(description="With a source file")
    assert created.source_filename().endswith(".svg")


def test_collection_view_related_tags(db, client):
    # Related tags are the tags of the collection members, which the view now
    # looks up with a subquery instead of a list of IDs.
    CollectableFactory(tags=["big", "shared"])
    CollectableFactory(tags=["big", "shared"])
    CollectableFactory(tags=["big", "alone"])
    CollectableFactory(tags=["elsewhere", "shared"])

    url = reverse("collectable:collection", kwargs={"slugs": "big"})
    response = client.get(url)

    related = {t.name: t.ncollectable for t in response.context["reltag_list"]}
    # "shared" is on two members of the collection, "alone" on only one (below
    # the threshold), "big" is the collection itself, "elsewhere" is outside.
    assert related == {"shared": 2}
