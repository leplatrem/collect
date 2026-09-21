# Additions to your existing test_views.py file

import io

import pytest
from django.conf import settings
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse
from django.utils.translation import gettext
from PIL import Image

from collectable.models import (
    Collectable,
    DuplicateReport,
    Possession,
    get_unknown_user,
)
from collectable.tests.factories import (
    CollectableFactory,
    DuplicateReportFactory,
    PossessionFactory,
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
        "license": "CC-BY-SA-4.0",
        "photo": collectable.photo,
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


def test_possession_view_enables_swaps_once_owned(user, logged_in_client, collectable):
    url = reverse("collectable:possession", kwargs={"id": collectable.id})
    # Not owned yet: the checkbox is there, but inert.
    response = logged_in_client.post(url, {"owns": False})
    assert response.context["form"].fields["swaps"].disabled is True
    assert "id_swaps" in response.content.decode()
    # It becomes usable in the very response that marks the collectable as owned.
    response = logged_in_client.post(url, {"owns": True})
    assert response.context["form"].fields["swaps"].disabled is False


def test_possession_view_ignores_swaps_when_not_owned(
    user, logged_in_client, collectable
):
    url = reverse("collectable:possession", kwargs={"id": collectable.id})
    # A crafted POST cannot offer a spare of something the user does not own.
    logged_in_client.post(url, {"owns": False, "swaps": True})
    assert Possession.objects.get(user=user, collectable=collectable).swaps is False


def test_possession_view_post_swaps(user, logged_in_client, collectable):
    url = reverse("collectable:possession", kwargs={"id": collectable.id})
    logged_in_client.post(url, {"owns": True})
    logged_in_client.post(url, {"owns": True, "swaps": True})
    assert Possession.objects.get(user=user, collectable=collectable).swaps is True
    # Un-owning drops the spare offer along with it.
    logged_in_client.post(url, {"owns": False, "swaps": True})
    possession = Possession.objects.get(user=user, collectable=collectable)
    assert possession.owns is False
    assert possession.swaps is False


def test_collection_view_with_valid_tag(client, collectable):
    collectable.tags.add("tag1")
    url = reverse("collectable:collection", kwargs={"slugs": "tag1"})
    response = client.get(url)
    assert response.status_code == 200
    assert "collectable_list" in response.context
    assert "tag_list" in response.context
    assert "reltag_list" in response.context


def test_collection_view_hide_owned_toggle(possession, logged_in_client, collectable):
    collectable.tags.add("tag1")
    url = reverse("collectable:collection", kwargs={"slugs": "tag1"})

    response = logged_in_client.get(url)

    content = response.content.decode()
    # The toggle, and the checkbox it hides the owned thumbnails with (CSS only).
    assert 'id="hide-owned"' in content
    assert 'for="hide-owned"' in content
    assert 'name="owns"' in content


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


def test_profile_view_redirects_to_public_page(user, logged_in_client):
    response = logged_in_client.get(reverse("collectable:profile"))
    assert response.status_code == 302
    assert response.url == reverse("user-profile", kwargs={"username": user.username})


def test_profile_view_requires_login(db, client):
    response = client.get(reverse("collectable:profile"))
    assert response.status_code == 302
    assert response.url.startswith(settings.LOGIN_URL)


def test_user_profile_view(user, logged_in_client):
    url = reverse("user-profile", kwargs={"username": user.username})
    response = logged_in_client.get(url)
    assert response.status_code == 200
    assert response.context["profile_user"] == user
    assert response.context["is_own_profile"]
    assert response.context["active_tab"] == "owned"
    assert [t["name"] for t in response.context["tabs"]] == [
        "owned",
        "liked",
        "wanted",
        "swapped",
    ]
    assert "page_obj" in response.context
    content = response.content.decode()
    # Visitors looking at their own page are told so, and trades are on their
    # own page now, linked from the top menu.
    assert gettext("You") in content
    assert reverse("collectable:trades") in content


def test_user_profile_view_is_public(client, user, collectable):
    PossessionFactory(user=user, collectable=collectable, owns=True)
    url = reverse("user-profile", kwargs={"username": user.username})

    response = client.get(url)

    assert response.status_code == 200
    assert not response.context["is_own_profile"]
    assert list(response.context["page_obj"]) == [collectable]
    content = response.content.decode()
    assert gettext("User %(username)s") % {"username": user.username} in content
    # Trades are personal: the menu does not offer them to a visitor.
    assert reverse("collectable:trades") not in content


def test_user_profile_view_shows_member_since(client, user):
    url = reverse("user-profile", kwargs={"username": user.username})

    content = client.get(url).content.decode()

    assert 'class="profile-meta"' in content
    assert str(user.date_joined.year) in content


def test_user_profile_view_of_someone_else(logged_in_client, collectable):
    other = UserFactory(username="othercollector")
    PossessionFactory(user=other, collectable=collectable, owns=True)

    response = logged_in_client.get(
        reverse("user-profile", kwargs={"username": "othercollector"})
    )

    assert response.status_code == 200
    assert response.context["profile_user"] == other
    assert not response.context["is_own_profile"]
    assert list(response.context["page_obj"]) == [collectable]


@pytest.mark.parametrize("username", ["ghost", "unknown"])
def test_user_profile_view_unknown_or_inactive_user(db, client, username):
    # The `unknown` placeholder user is inactive: it has no public profile.
    get_unknown_user()

    response = client.get(reverse("user-profile", kwargs={"username": username}))

    assert response.status_code == 404


@pytest.mark.parametrize(
    "tab,expected",
    [
        ("liked", "liked"),
        ("swapped", "swapped"),
        # Unknown tabs fall back to the default one.
        ("matched", "owned"),
        ("unknown", "owned"),
        ("", "owned"),
    ],
)
def test_user_profile_view_tabs(user, logged_in_client, tab, expected):
    url = reverse("user-profile", kwargs={"username": user.username})
    response = logged_in_client.get(url, {"tab": tab})
    assert response.status_code == 200
    assert response.context["active_tab"] == expected


def test_profile_view_paginates_tab(user, logged_in_client, collectable, settings):
    settings.DEFAULT_PAGE_SIZE = 1
    another = CollectableFactory()
    for c in (collectable, another):
        PossessionFactory(user=user, collectable=c, likes=True, wants=False, owns=False)

    url = reverse("user-profile", kwargs={"username": user.username})
    page1 = logged_in_client.get(url, {"tab": "liked"})
    page2 = logged_in_client.get(url, {"tab": "liked", "page": 2})

    assert page1.context["tabs"][1]["count"] == 2
    assert len(page1.context["page_obj"]) == 1
    assert len(page2.context["page_obj"]) == 1
    assert set(page1.context["page_obj"]) | set(page2.context["page_obj"]) == {
        collectable,
        another,
    }
    # The next page is fetched when the visitor scrolls down.
    assert "?tab=liked&amp;page=2" in page1.content.decode()


def test_trades_view_requires_login(db, client):
    response = client.get(reverse("collectable:trades"))
    assert response.status_code == 302
    assert response.url.startswith(settings.LOGIN_URL)


def test_trades_view_trade_lists(
    user, logged_in_client, collectable, another_collectable
):
    wanter = UserFactory(username="wanter")
    mate = UserFactory(username="mate")
    url = reverse("collectable:trades")

    # One of our spares, nobody after it yet.
    PossessionFactory(
        user=user,
        collectable=collectable,
        likes=False,
        wants=False,
        owns=True,
        swaps=True,
    )
    response = logged_in_client.get(url)
    assert response.context["trade_partners"] == []

    # Somebody wants it: one-way only.
    PossessionFactory(
        user=wanter, collectable=collectable, likes=False, wants=True, owns=False
    )
    response = logged_in_client.get(url)
    assert [u.username for u in response.context["trade_wanting_our_spares"]] == [
        "wanter"
    ]
    assert response.context["trade_offering_our_wants"] == []
    assert response.context["trade_both_ways"] == []

    # Somebody offers a spare we want, and wants one of ours: two-way.
    PossessionFactory(
        user=user, collectable=another_collectable, likes=False, wants=True, owns=False
    )
    PossessionFactory(
        user=mate,
        collectable=another_collectable,
        likes=False,
        wants=False,
        owns=True,
        swaps=True,
    )
    PossessionFactory(
        user=mate, collectable=collectable, likes=False, wants=True, owns=False
    )
    response = logged_in_client.get(url)
    assert [u.username for u in response.context["trade_both_ways"]] == ["mate"]
    assert sorted(u.username for u in response.context["trade_wanting_our_spares"]) == [
        "mate",
        "wanter",
    ]
    assert [u.username for u in response.context["trade_offering_our_wants"]] == [
        "mate"
    ]


def test_trades_view_renders_trade_names(user, logged_in_client, collectable):
    PossessionFactory(
        user=user,
        collectable=collectable,
        likes=False,
        wants=False,
        owns=True,
        swaps=True,
    )
    PossessionFactory(
        user=UserFactory(username="collectomane"),
        collectable=collectable,
        likes=False,
        wants=True,
        owns=False,
    )

    response = logged_in_client.get(reverse("collectable:trades"))
    content = response.content.decode()

    assert "collectomane" in content
    assert "1 double recherch" in content
    # Partner names link to the list that matters for that direction: here,
    # what they are looking for.
    url = reverse("user-profile", kwargs={"username": "collectomane"})
    assert f'href="{url}?tab=wanted"' in content


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


def test_trades_view_trade_lists_hit_the_database_once(
    user, logged_in_client, collectable, django_assert_num_queries
):
    # The three lists are sliced from one annotated query, not three.
    PossessionFactory(
        user=user,
        collectable=collectable,
        likes=False,
        wants=False,
        owns=True,
        swaps=True,
    )
    PossessionFactory(
        user=UserFactory(), collectable=collectable, likes=False, wants=True, owns=False
    )
    url = reverse("collectable:trades")
    logged_in_client.get(url)  # warm up sessions/auth queries

    with django_assert_num_queries(1):
        list(Possession.trade_partners(user))


def test_duplicate_page_links_the_reporter(
    logged_in_client, collectable, another_collectable, user
):
    DuplicateReportFactory(
        original=another_collectable, duplicate=collectable, reporter=user
    )
    url = reverse("collectable:duplicate", kwargs={"id": collectable.id})

    response = logged_in_client.get(url)

    assert (
        reverse("user-profile", kwargs={"username": user.username})
        in response.content.decode()
    )


def test_details_page_links_the_history_user(logged_in_client, collectable, user):
    url = reverse("collectable:details", kwargs={"id": collectable.id})
    logged_in_client.post(
        url,
        {
            "description": "Edited via test",
            "tags": "tag1",
            "license": "CC-BY-SA-4.0",
            "photo": collectable.photo,
            "photo_x": 0,
            "photo_y": 0,
            "photo_w": 400,
            "photo_h": 400,
        },
    )

    content = logged_in_client.get(url).content.decode()

    assert (
        f'<a href="{reverse("user-profile", kwargs={"username": user.username})}"'
        in content
    )
