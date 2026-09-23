import pytest
from django.core.exceptions import ValidationError
from django.urls import reverse
from taggit.models import Tag

from collect.utils import tags_joiner
from collectable.models import (
    Collectable,
    DuplicateReport,
    Possession,
    visible_tag_names,
)
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


def test_tags_with_count_ignores_hidden(collectable):
    collectable.tags.add("foo")
    CollectableFactory(tags=["foo"], hidden=True)

    assert [t.ncollectable for t in collectable.tags_with_count()] == [1]


def test_visible_tag_names_are_ordered_by_usage(db):
    CollectableFactory(tags=["common", "rare"])
    CollectableFactory(tags=["common", "usual"])
    CollectableFactory(tags=["common", "usual"])

    # Most used first, so that completion and the chips both start with them.
    assert list(visible_tag_names()) == ["common", "usual", "rare"]


def test_visible_tag_names_ignore_hidden_and_unused(collectable):
    collectable.tags.add("shown")
    CollectableFactory(tags=["hidden-only"], hidden=True)
    Tag.objects.create(name="orphan", slug="orphan")

    assert list(visible_tag_names()) == ["shown"]


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
        [],
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
    assert Collectable.objects.count() == 0
    assert Collectable.all_objects.count() == 1


def test_duplicate_report_confirm(duplicate_report):
    duplicate_report.duplicate.tags.add("tag1", "tag2")
    duplicate_report.duplicate.description = "Coucou"
    duplicate_report.duplicate.save()
    PossessionFactory(
        user=duplicate_report.reporter,
        collectable=duplicate_report.duplicate,
        owns=True,
        likes=True,
        wants=False,
    )
    duplicate_report.original.tags.add("tag2", "tag4", "tag5")
    duplicate_report.original.description = "Hola"
    duplicate_report.original.save()

    assert len(duplicate_report.confirmations()) == 0
    dup = Collectable.objects.get(id=duplicate_report.duplicate.id)
    assert "duplicate" in dup.tags.names()

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
    assert set(duplicate_report.original.tags.names()) == {
        "tag1",
        "tag2",
        "tag4",
        "tag5",
    }
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


@pytest.mark.django_db
def test_merge_into_with_empty_original_description():
    original = CollectableFactory(description="")
    duplicate = CollectableFactory(description="duplicate description")

    duplicate.merge_into(original)

    original.refresh_from_db()
    # No leading "\n---\n" when the original description is empty.
    assert original.description == "duplicate description"


@pytest.mark.django_db
def test_duplicate_report_save_validates():
    c = CollectableFactory()
    with pytest.raises(ValidationError):
        DuplicateReport(reporter=UserFactory(), duplicate=c, original=c).save()


def test_swaps_is_cleared_when_not_owned(user, collectable):
    possession = PossessionFactory(user=user, collectable=collectable, owns=True)
    possession.swaps = True
    possession.save()
    assert possession.swaps is True

    possession.owns = False
    possession.save()
    possession.refresh_from_db()
    assert possession.swaps is False


def test_swaps_is_cleared_with_update_fields(user, collectable):
    possession = PossessionFactory(
        user=user, collectable=collectable, owns=True, swaps=True
    )
    possession.owns = False
    possession.save(update_fields=["owns"])
    possession.refresh_from_db()
    assert possession.swaps is False


def test_swapped_by(user, collectable, another_collectable):
    PossessionFactory(user=user, collectable=collectable, owns=True, swaps=True)
    PossessionFactory(user=user, collectable=another_collectable, owns=True)

    results = Collectable.objects.all().swapped_by(user)

    assert [c.id for c in results] == [collectable.id]


def test_swaps_count_annotation(user, collectable):
    PossessionFactory(user=user, collectable=collectable, owns=True, swaps=True)
    PossessionFactory(collectable=collectable, owns=True, swaps=True)
    PossessionFactory(collectable=collectable, owns=True, swaps=False)

    result = Collectable.objects.with_counts_and_possessions(user).get(
        id=collectable.id
    )

    assert result.nswaps == 2


def spare(user, collectable):
    """A collectable this user owns and offers for swap."""
    return PossessionFactory(
        user=user,
        collectable=collectable,
        likes=False,
        wants=False,
        owns=True,
        swaps=True,
    )


def want(user, collectable):
    """A collectable this user is looking for."""
    return PossessionFactory(
        user=user,
        collectable=collectable,
        likes=False,
        wants=True,
        owns=False,
        swaps=False,
    )


def test_trade_partners_one_way(user, collectable, another_collectable):
    wanter = UserFactory(username="wanter")
    offerer = UserFactory(username="offerer")
    # They want one of our spares.
    spare(user, collectable)
    want(wanter, collectable)
    # They offer a spare we are looking for.
    want(user, another_collectable)
    spare(offerer, another_collectable)

    partners = {
        p.username: (p.nwanted, p.noffered) for p in Possession.trade_partners(user)
    }

    assert partners == {"wanter": (1, 0), "offerer": (0, 1)}


def test_trade_partners_both_ways(user, collectable, another_collectable):
    mate = UserFactory(username="mate")
    spare(user, collectable)
    want(mate, collectable)
    want(user, another_collectable)
    spare(mate, another_collectable)

    (partner,) = Possession.trade_partners(user)

    assert partner.username == "mate"
    assert (partner.nwanted, partner.noffered) == (1, 1)


def test_trade_partners_excludes_self_and_non_matches(user, collectable):
    # Wanting our own spare does not make us our own partner.
    PossessionFactory(
        user=user,
        collectable=collectable,
        likes=False,
        wants=True,
        owns=True,
        swaps=True,
    )
    # Owning it without offering a spare is not offering anything.
    PossessionFactory(
        user=UserFactory(), collectable=collectable, likes=False, wants=False, owns=True
    )
    # Merely liking it either.
    PossessionFactory(
        user=UserFactory(), collectable=collectable, likes=True, wants=False, owns=False
    )

    assert list(Possession.trade_partners(user)) == []


def test_trade_partners_ignores_inactive_users(user, collectable):
    inactive = UserFactory(is_active=False)
    spare(user, collectable)
    want(inactive, collectable)

    assert list(Possession.trade_partners(user)) == []


def test_merge_into_keeps_swaps(user, collectable, another_collectable):
    PossessionFactory(user=user, collectable=collectable, owns=True, swaps=True)

    collectable.merge_into(another_collectable)

    merged = another_collectable.possession_set.get(user=user)
    assert merged.owns is True
    assert merged.swaps is True


def test_history_with_deltas_is_limited(collectable):
    for i in range(10):
        collectable.description = f"Update {i}"
        collectable.save()

    # The history of a collectable grows with every save, and the details page
    # loads and diffs it on every view.
    history = collectable.history_with_deltas(limit=3)

    assert len(history) == 3
    assert [c["new"] for r in history for c in r.history_delta_changes] == [
        "Update 9",
        "Update 8",
        "Update 7",
    ]


def test_history_with_deltas_limit_defaults_to_the_setting(collectable, settings):
    settings.HISTORY_LIST_COUNT = 2
    for i in range(6):
        collectable.description = f"Update {i}"
        collectable.save()

    assert len(collectable.history_with_deltas()) == 2


def test_history_with_deltas_shorter_than_the_limit(collectable):
    collectable.description = "Only update"
    collectable.save()

    # Every revision but the oldest one, which only serves as the reference
    # the next one is compared against.
    assert len(collectable.history_with_deltas(limit=10)) == (
        collectable.history.count() - 1
    )
