import pytest
from django.core.exceptions import ValidationError
from django.urls import reverse
from taggit.models import Tag

from collect.utils import tags_joiner
from collectable.models import Collectable, DuplicateReport
from collectable.tests.factories import (
    CollectableFactory,
    DuplicateReportFactory,
    PossessionFactory,
    UserFactory,
)


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


def test_history_with_tags_deltas(collectable):
    collectable.tags.add("tag1")
    collectable.save()
    collectable.tags.add("tag2")
    collectable.save()

    history = collectable.history_with_deltas()
    assert [r.history_delta_changes for r in history] == [
        [{"field": "tags", "old": "#tag1, #tag2", "new": ""}],
        [{"field": "tags", "old": "", "new": "#tag1, #tag2"}],
        [{"field": "tags", "old": "#tag1", "new": ""}],
        [{"field": "tags", "old": "", "new": "#tag1"}],
    ]


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


def test_hidden_collectable_is_not_in_default_manager(db, user):
    CollectableFactory(hidden=True)
    assert Collectable.objects.count() == 1
    assert Collectable.objects.with_counts_and_possessions(user).count() == 0


def test_duplicate_report_confirm(duplicate_report):
    duplicate_report.duplicate.tags.add("tag1", "tag2")
    duplicate_report.duplicate.description = "Coucou"
    duplicate_report.duplicate.save()
    PossessionFactory(
        user=duplicate_report.reporter,
        collectable=duplicate_report.duplicate,
        owns=True,
        likes=True,
    )
    duplicate_report.original.tags.add("tag2", "tag4", "tag5")
    duplicate_report.original.description = "Hola"
    duplicate_report.original.save()

    assert len(duplicate_report.confirmations()) == 0
    assert "duplicate" in duplicate_report.duplicate.tags.names()

    # Create a report from another user.
    DuplicateReportFactory(
        reporter=UserFactory(),
        duplicate=duplicate_report.duplicate,
        original=duplicate_report.original,
    )

    assert len(duplicate_report.confirmations()) == 1
    assert not duplicate_report.duplicate.hidden

    # Create a report from another user. Second confirmation.
    DuplicateReportFactory(
        reporter=UserFactory(),
        duplicate=duplicate_report.duplicate,
        original=duplicate_report.original,
    )

    assert len(duplicate_report.confirmations()) == 2
    # Now the duplicate should be hidden.
    assert duplicate_report.duplicate.hidden
    # And original merged.
    assert duplicate_report.original.tags.count() == 5
    assert "Hola\n---\nCoucou" in duplicate_report.original.description
    # The reporter should now own and like the original.
    possessed = Collectable.objects.with_counts_and_possessions(
        duplicate_report.reporter
    )
    assert possessed.count() == 1
    assert possessed[0].id == duplicate_report.original.id
    assert possessed[0].nlikes == 1
    assert possessed[0].nowns == 1
    assert possessed[0].nwants == 0


@pytest.mark.django_db
def test_duplicate_report_loops():
    c0 = CollectableFactory()
    with pytest.raises(ValidationError) as exc:
        DuplicateReport(reporter=UserFactory(), duplicate=c0, original=c0).full_clean()
    assert "itself" in str(exc.value).lower()

    c1 = CollectableFactory()
    c2 = CollectableFactory()
    c3 = CollectableFactory()

    # c1 -> c2
    r1 = DuplicateReportFactory(reporter=UserFactory(), duplicate=c1, original=c2)
    assert len(r1.confirmations()) == 0

    # c2 -> c3
    r2 = DuplicateReportFactory(reporter=UserFactory(), duplicate=c2, original=c3)
    assert len(r2.confirmations()) == 0

    # Now creating a report c3 -> c1 should raise an error
    with pytest.raises(ValidationError) as exc:
        DuplicateReport(reporter=UserFactory(), duplicate=c3, original=c1).full_clean()
    assert "create a loop" in str(exc.value).lower()


@pytest.mark.django_db
def test_duplicate_not_deleted_on_user_delete(duplicate_report):
    user = duplicate_report.reporter

    user.delete()

    duplicate_report.refresh_from_db()
    assert duplicate_report.reporter.username == "unknown"
