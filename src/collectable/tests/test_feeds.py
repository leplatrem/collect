from xml.etree import ElementTree

import pytest
from django.urls import reverse

from collectable.tests.factories import CollectableFactory, PossessionFactory
from collectable.views import LIST_DESCRIPTIONS


ATOM_NS = {"atom": "http://www.w3.org/2005/Atom"}


def parse(response):
    return ElementTree.fromstring(response.content)


@pytest.mark.parametrize(
    "path_name,content_type",
    [
        ("collectable:latest-feed", "application/atom+xml; charset=utf-8"),
        ("collectable:most-liked-feed", "application/atom+xml; charset=utf-8"),
        ("collectable:most-wanted-feed", "application/atom+xml; charset=utf-8"),
        ("collectable:most-owned-feed", "application/atom+xml; charset=utf-8"),
        ("collectable:most-spares-feed", "application/atom+xml; charset=utf-8"),
        ("collectable:search-feed", "application/atom+xml; charset=utf-8"),
    ],
)
def test_feeds_are_served(db, client, path_name, content_type):
    CollectableFactory()

    response = client.get(reverse(path_name))

    assert response.status_code == 200
    assert response["Content-Type"] == content_type
    parse(response)  # Well-formed XML.


def test_atom_feed_lists_the_collectables_of_its_page(client, db):
    older = CollectableFactory(description="older one")
    newer = CollectableFactory(description="newer one")

    response = client.get(reverse("collectable:latest-feed"))

    feed = parse(response)
    titles = [e.text for e in feed.findall("atom:entry/atom:title", ATOM_NS)]
    assert titles == [newer.description, older.description]


def test_atom_feed_only_keeps_the_kind_it_publishes(client, user):
    liked = CollectableFactory(description="liked one")
    CollectableFactory(description="unnoticed one")
    PossessionFactory(user=user, collectable=liked, likes=True)

    response = client.get(reverse("collectable:most-liked-feed"))

    feed = parse(response)
    titles = [e.text for e in feed.findall("atom:entry/atom:title", ATOM_NS)]
    assert titles == [liked.description]


def test_feed_leaves_out_hidden_collectables(client, db):
    CollectableFactory(description="shown one")
    CollectableFactory(description="hidden one", hidden=True)

    response = client.get(reverse("collectable:latest-feed"))

    feed = parse(response)
    titles = [e.text for e in feed.findall("atom:entry/atom:title", ATOM_NS)]
    assert titles == ["shown one"]


def test_feed_is_capped(client, db, settings):
    settings.FEED_ITEM_COUNT = 2
    for i in range(3):
        CollectableFactory(description=f"collectable {i}")

    response = client.get(reverse("collectable:latest-feed"))

    assert len(parse(response).findall("atom:entry", ATOM_NS)) == 2


def test_entries_carry_the_thumbnail_the_tags_and_the_license(client, db):
    collectable = CollectableFactory(description="a sticker", tags=["paris"])

    response = client.get(reverse("collectable:latest-feed"))

    feed = parse(response)
    (entry,) = feed.findall("atom:entry", ATOM_NS)
    assert entry.find("atom:id", ATOM_NS).text == f"urn:uuid:{collectable.id}"
    assert (
        entry.find("atom:link", ATOM_NS)
        .get("href")
        .endswith(collectable.get_absolute_url())
    )
    assert [c.get("term") for c in entry.findall("atom:category", ATOM_NS)] == ["paris"]
    assert entry.find("atom:rights", ATOM_NS).text == collectable.get_license_display()
    summary = entry.find("atom:summary", ATOM_NS).text
    assert "http://testserver" in summary
    assert collectable.thumbnail.url in summary
    assert "#paris" in summary


def test_entry_falls_back_on_the_photo_name_without_a_description(client, db):
    CollectableFactory(description="", filename="a-sticker.jpg")

    response = client.get(reverse("collectable:latest-feed"))

    feed = parse(response)
    (title,) = feed.findall("atom:entry/atom:title", ATOM_NS)
    assert title.text.startswith("a-sticker")


def test_search_feed_filters_and_keeps_its_query(client, db):
    CollectableFactory(description="a sticker", tags=["paris"])
    CollectableFactory(description="a badge", tags=["lyon"])

    url = reverse("collectable:search-feed")
    response = client.get(url, {"q": "#paris"})

    feed = parse(response)
    titles = [e.text for e in feed.findall("atom:entry/atom:title", ATOM_NS)]
    assert titles == ["a sticker"]
    # The feed points back at itself and at the page, query included.
    links = {
        link.get("rel"): link.get("href") for link in feed.findall("atom:link", ATOM_NS)
    }
    assert links["self"].endswith(f"{url}?q=%23paris")
    assert links["alternate"].endswith(f"{reverse('collectable:search')}?q=%23paris")


def test_search_feed_falls_back_on_plain_words(client, db):
    CollectableFactory(description="a sticker")

    response = client.get(reverse("collectable:search-feed"), {"q": "sticker AND"})

    feed = parse(response)
    titles = [e.text for e in feed.findall("atom:entry/atom:title", ATOM_NS)]
    assert titles == ["a sticker"]


def test_search_feed_is_throttled(client, db, settings):
    settings.THROTTLE_SEARCH = "1/60"

    assert client.get(reverse("collectable:search-feed")).status_code == 200
    assert client.get(reverse("collectable:search-feed")).status_code == 429


def test_list_pages_carry_the_same_description_as_their_feed(db, client):
    page = client.get(reverse("collectable:most-wanted"))
    feed = client.get(reverse("collectable:most-wanted-feed"))

    description = str(LIST_DESCRIPTIONS["most_wanted"])
    assert f'<p class="list-description">{description}</p>' in page.content.decode()
    assert parse(feed).find("atom:subtitle", ATOM_NS).text == description


def test_search_page_advertises_a_feed_of_that_search(db, client):
    response = client.get(reverse("collectable:search"), {"q": "#paris"})

    url = reverse("collectable:search-feed")
    assert f'href="{url}?q=%23paris"' in response.content.decode()


def test_collection_feed_lists_the_collectables_of_every_tag(client, db):
    both = CollectableFactory(description="both tags", tags=["paris", "2024"])
    CollectableFactory(description="one tag", tags=["paris"])

    url = reverse("collectable:collection-feed", args=["paris,2024"])
    response = client.get(url)

    assert response.status_code == 200
    assert response["Content-Type"] == "application/atom+xml; charset=utf-8"
    feed = parse(response)
    titles = [e.text for e in feed.findall("atom:entry/atom:title", ATOM_NS)]
    assert titles == [both.description]


def test_collection_feed_is_named_after_its_tags(client, db):
    CollectableFactory(tags=["paris"])

    response = client.get(reverse("collectable:collection-feed", args=["paris"]))

    feed = parse(response)
    assert feed.find("atom:title", ATOM_NS).text == "Collect - Collection #paris"


def test_collection_feed_names_a_tag_nobody_used_yet(client, db):
    response = client.get(reverse("collectable:collection-feed", args=["nothing"]))

    feed = parse(response)
    assert feed.find("atom:title", ATOM_NS).text == "Collect - Collection #nothing"
    assert feed.findall("atom:entry", ATOM_NS) == []


def test_collection_feed_points_back_at_its_page(client, db):
    CollectableFactory(tags=["paris", "2024"])

    url = reverse("collectable:collection-feed", args=["paris,2024"])
    response = client.get(url)

    feed = parse(response)
    links = {
        link.get("rel"): link.get("href") for link in feed.findall("atom:link", ATOM_NS)
    }
    page = reverse("collectable:collection", args=["paris,2024"])
    assert links["alternate"].endswith(page)
    assert links["self"].endswith(url)


def test_collection_feed_entries_carry_their_tags(client, db):
    CollectableFactory(description="a sticker", tags=["paris"])

    response = client.get(reverse("collectable:collection-feed", args=["paris"]))

    (entry,) = parse(response).findall("atom:entry", ATOM_NS)
    assert [c.get("term") for c in entry.findall("atom:category", ATOM_NS)] == ["paris"]
    assert "#paris" in entry.find("atom:summary", ATOM_NS).text


def test_collection_feed_leaves_out_hidden_collectables(client, db):
    CollectableFactory(description="shown one", tags=["paris"])
    CollectableFactory(description="hidden one", tags=["paris"], hidden=True)

    response = client.get(reverse("collectable:collection-feed", args=["paris"]))

    feed = parse(response)
    titles = [e.text for e in feed.findall("atom:entry/atom:title", ATOM_NS)]
    assert titles == ["shown one"]


def test_collection_page_advertises_its_feed(client, db):
    CollectableFactory(tags=["paris"])

    response = client.get(reverse("collectable:collection", args=["paris"]))

    url = reverse("collectable:collection-feed", args=["paris"])
    assert f'href="{url}"' in response.content.decode()


def test_home_page_advertises_the_latest_feed(client, db):
    response = client.get(reverse("collectable:index"))

    url = reverse("collectable:latest-feed")
    assert f'href="{url}"' in response.content.decode()
