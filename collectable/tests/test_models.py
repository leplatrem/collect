from django.urls import reverse
from taggit.models import Tag

from collect.utils import tags_joiner
from collectable.models import Collectable
from collectable.tests.factories import CollectableFactory, PossessionFactory


def test_get_absolute_url(collectable):
    url = collectable.get_absolute_url()
    assert str(collectable.id) in url
    assert url == reverse("collectable:details", kwargs={"id": collectable.id})


def test_tags_with_count(collectable):
    collectable.tags.add("foo", "bar")
    tags = collectable.tags_with_count()
    assert tags.count() == 2
    assert all(isinstance(t, Tag) for t in tags)
    assert tags[0].ncollectable > 0 or tags[1].ncollectable > 0


def test_possession_of_authenticated(user, collectable):
    PossessionFactory(user=user, collectable=collectable, likes=True)
    collectable = Collectable.objects.with_counts_and_possessions(user).get(
        id=collectable.id
    )
    possession = collectable.possession_of(user)
    assert possession.likes is True


def test_possession_of_anonymous(collectable):
    class DummyUser:
        is_authenticated = False

    possession = collectable.possession_of(DummyUser())
    assert possession.likes is False
    assert not possession.pk  # Not saved


def test_history_with_deltas(collectable):
    collectable.description = "Update 1"
    collectable.save()
    collectable.description = "Update 2"
    collectable.save()
    history = collectable.history_with_deltas()
    assert isinstance(history, list)
    assert len(history) > 0


def test_manager_with_counts_and_possessions(user):
    # Create 2 collectables with user possession
    c1 = CollectableFactory()
    c2 = CollectableFactory()
    PossessionFactory(user=user, collectable=c1, likes=True, wants=False, owns=False)
    PossessionFactory(user=user, collectable=c2, owns=True, likes=False, wants=False)

    results = Collectable.objects.with_counts_and_possessions(user).order_by(
        "created_at"
    )

    assert results.count() == 2

    assert results[0].id == c1.id
    assert results[0].nlikes == 1
    assert results[0].nowns == 0
    assert results[0].nwants == 0

    assert results[1].id == c2.id
    assert results[1].nlikes == 0
    assert results[1].nowns == 1
    assert results[1].nwants == 0


def test_computed_tags_signal(collectable):
    collectable.tags.add("a", "b")
    collectable.refresh_from_db()
    assert collectable._computed_tags == tags_joiner(collectable.tags.all())
