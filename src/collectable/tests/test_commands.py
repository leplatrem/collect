from io import StringIO

from django.core.management import call_command

from collectable.models import Collectable
from collectable.tests.factories import (
    CollectableFactory,
    DuplicateReportFactory,
    PossessionFactory,
    UserFactory,
)


def merge():
    out = StringIO()
    call_command("mergeduplicates", stdout=out)
    return out.getvalue()


def test_merges_a_reported_duplicate(db, user):
    original = CollectableFactory(description="Original")
    duplicate = CollectableFactory(description="Duplicate", tags=["rare"])
    DuplicateReportFactory(original=original, duplicate=duplicate, reporter=user)

    output = merge()

    assert f"{duplicate.id} merged into {original.id}" in output
    assert "1 collectables merged." in output
    duplicate.refresh_from_db()
    original.refresh_from_db()
    assert duplicate.hidden
    assert "Duplicate" in original.description
    assert "rare" in original.tags.names()


def test_moves_possessions_over(db):
    owner = UserFactory()
    original = CollectableFactory()
    duplicate = CollectableFactory()
    DuplicateReportFactory(
        original=original, duplicate=duplicate, reporter=UserFactory()
    )
    PossessionFactory(
        user=owner, collectable=duplicate, owns=True, likes=True, wants=False
    )

    merge()

    possessed = Collectable.objects.with_counts_and_possessions(owner).get(
        id=original.id
    )
    assert possessed.nowns == 1
    assert possessed.nlikes == 1


def test_merges_a_duplicate_reported_twice_only_once(db):
    original = CollectableFactory(description="Original")
    duplicate = CollectableFactory(description="Duplicate")
    for _ in range(2):
        DuplicateReportFactory(
            original=original, duplicate=duplicate, reporter=UserFactory()
        )

    output = merge()

    assert "1 collectables merged." in output
    original.refresh_from_db()
    # The description of the duplicate was appended once, not twice.
    assert original.description.count("Duplicate") == 1


def test_leaves_already_merged_duplicates_alone(db, user):
    original = CollectableFactory()
    duplicate = CollectableFactory()
    # A report cannot be filed against a hidden collectable, so hide it after.
    DuplicateReportFactory(original=original, duplicate=duplicate, reporter=user)
    duplicate.hidden = True
    duplicate.save()

    assert "0 collectables merged." in merge()


def test_nothing_to_merge(db):
    CollectableFactory()

    assert "0 collectables merged." in merge()
