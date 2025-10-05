import re
import uuid

import taggit.models
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Count, Prefetch, Q
from django.db.models.functions import Coalesce
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.urls import reverse_lazy
from django.utils.translation import gettext_lazy as _
from imagekit.models import ImageSpecField
from imagekit.processors import Thumbnail
from simple_history.models import HistoricalRecords
from taggit.managers import TaggableManager
from taggit.models import Tag

from collect.utils import tags_joiner
from collectable.validators import (
    MaxFileSizeValidator,
    MimetypeValidator,
    SquareImageValidator,
)


UUID_REGEX = re.compile(
    r"^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$"
)


class UUIDTaggedItem(
    taggit.models.GenericUUIDTaggedItemBase, taggit.models.TaggedItemBase
):
    """
    Since our Collectable model uses UUIDs, we need to override the default TaggedItem
    model to use UUIDs instead of integers.
    """

    class Meta:
        verbose_name = _("Tag")
        verbose_name_plural = _("Tags")


class CollectableQuerySet(models.QuerySet):
    """
    Custom QuerySet for Collectable model to include methods for prefetching.
    """

    def visible(self):
        return self.filter(hidden=False)

    def with_tags(self):
        return self.prefetch_related(Prefetch("tags", to_attr="tags_list"))

    def for_user(self, user):
        if user.is_authenticated:
            return self.prefetch_related(
                Prefetch(
                    "possession_set",
                    queryset=Possession.objects.filter(user=user),
                    # This will cache the possessions for the user
                    # so we can access them without hitting the database again.
                    to_attr="possession_set_list",
                )
            )
        return self

    def liked_by(self, user):
        return self.filter(possession__user=user, possession__likes=True)

    def wanted_by(self, user):
        return self.filter(possession__user=user, possession__wants=True)

    def owned_by(self, user):
        return self.filter(possession__user=user, possession__owns=True)

    def with_possession_counts(self):
        """
        Annotate the queryset with counts of likes, wants, and owns for each collectable.
        This uses the related field from the Possession model to count the number of
        possessions that have likes, wants, and owns set to True.
        """
        return self.annotate(
            nlikes=Coalesce(
                Count(
                    "possessions",
                    filter=Q(**{"possession__likes": True}),
                    distinct=True,
                ),
                0,
            ),
            nwants=Coalesce(
                Count(
                    "possessions",
                    filter=Q(**{"possession__wants": True}),
                    distinct=True,
                ),
                0,
            ),
            nowns=Coalesce(
                Count(
                    "possessions", filter=Q(**{"possession__owns": True}), distinct=True
                ),
                0,
            ),
        )

    def prefetch_tags_and_possessions(self, user):
        return self.with_tags().for_user(user)

    def search_keywords(self, keywords):
        """
        Filter the queryset by searching for keywords in the description and tags.
        """
        if not keywords:
            return self

        query = Q()
        for keyword in keywords:
            word_filter = (
                Q(description__icontains=keyword)
                | Q(id__icontains=keyword)
                | Q(photo__icontains=keyword)
                | Q(tags__name__iexact=keyword)
            )
            query |= word_filter  # any word match (OR)

        return self.filter(query).distinct()


class CollectableManager(models.Manager):
    """
    Custom manager for Collectable model to return a custom QuerySet.
    This allows us to chain methods and keep as much logics close
    to models definitions.
    """

    def __init__(self, *args, with_hidden=False, **kwargs):
        super().__init__(*args, **kwargs)
        self.with_hidden = with_hidden

    def get_queryset(self):
        qs = CollectableQuerySet(self.model, using=self._db)
        if not self.with_hidden:
            qs = qs.visible()
        return qs

    def with_counts_and_possessions(self, user):
        return self.get_queryset().with_possession_counts().with_tags().for_user(user)


class Collectable(models.Model):
    """
    Main model representing a collectable item.
    """

    id = models.UUIDField(
        _("Identifier"), primary_key=True, default=uuid.uuid4, editable=False
    )
    created_at = models.DateTimeField(
        _("Created at"), auto_now_add=True, editable=False
    )
    modified_at = models.DateTimeField(_("Modified at"), auto_now=True, editable=False)
    description = models.TextField(_("Description"), blank=True)
    photo = models.ImageField(
        _("Photo"),
        upload_to="collectables/%Y/",
        help_text=_("Please provide a square JPEG image (.jpg, .jpeg)"),
        validators=[
            MimetypeValidator(["image/jpg", "image/jpeg"]),
            SquareImageValidator(),
            MaxFileSizeValidator(),
        ],
    )
    tags = TaggableManager(_("Tags"), through=UUIDTaggedItem)
    possessions = models.ManyToManyField(settings.AUTH_USER_MODEL, through="Possession")

    history = HistoricalRecords(_("History"), excluded_fields=["modified_at"])
    # Because of https://github.com/jazzband/django-taggit/issues/918
    # we use a computed field to track tags changes, with the `post_save` signal
    # defined below.
    _computed_tags = models.TextField(
        _("Tags"), editable=False, db_comment="Read only field to track tags history"
    )

    thumbnail = ImageSpecField(
        source="photo",
        processors=[
            Thumbnail(
                settings.COLLECTABLE_THUMBNAIL_SIZE,
                settings.COLLECTABLE_THUMBNAIL_SIZE,
            )
        ],
        format="JPEG",
        options={"quality": settings.COLLECTABLE_THUMBNAIL_QUALITY},
    )
    hidden = models.BooleanField(_("Hidden"), default=False)

    objects = CollectableManager()
    all_objects = CollectableManager(with_hidden=True)

    @receiver(post_save, sender=UUIDTaggedItem, dispatch_uid="update_computed_tags")
    def on_tag_changed(sender, instance, created, **kwargs):
        """Workaround for the issue with history not able to track tags changes correctly.
        See https://github.com/jazzband/django-taggit/issues/918
        """
        item = instance.content_object
        if not isinstance(item, Collectable):  # pragma: no cover
            # This signal can be triggered by other models, we only care about Collectable
            return
        item._computed_tags = tags_joiner(item.tags.all())
        item.save(update_fields=["_computed_tags"])

    def tags_with_count(self):
        """
        Return the tags associated with this collectable, annotated with the count of
        collectables that have this tag, ordered by the count in descending order.

        :param min_count: Minimum count of collectables for the tag to be included.
        :return: QuerySet of `Tag` objects with an annotation for the count of collectables.
        """
        return (
            Tag.objects.filter(slug__in=self.tags.slugs())
            .annotate(ncollectable=Count("collectable"))
            .order_by("-ncollectable")
        )

    def related_tags(self, min_count=2):
        return self.tags_with_count().filter(ncollectable__gte=min_count)

    def related_collectables(self, user):
        related_tags = self.related_tags()
        return (
            Collectable.objects.with_counts_and_possessions(user)
            .exclude(id=self.id)
            .filter(tags__in=related_tags)
            .distinct()
        )

    def get_absolute_url(self):
        return reverse_lazy("collectable:details", kwargs={"id": self.id})

    def possession_of(self, user):
        """
        Return the `Possession` object for the given user.
        If the user is not authenticated or does not have a possession, return a new
        Possession instance with default values.
        """
        possession = None
        if user.is_authenticated:
            if cached_possessions := getattr(self, "possession_set_list", []):
                possession = cached_possessions[0]
        if possession is None:
            possession = Possession(
                collectable=self, likes=False, wants=False, owns=False
            )  # Don't save.
        return possession

    def history_with_deltas(self):
        """
        Return the history entries with delta information.

        We wish this was built-in to simple_history, but it is not.
        """
        history_records = (
            self.history.select_related("history_user").all().order_by("history_date")
        )
        filtered = []

        previous = None
        for record in history_records:
            if previous is None:
                previous = record
                continue

            changes = []

            # Explicitly include tag changes from _computed_tags
            if previous._computed_tags != record._computed_tags:
                changes.append(
                    {
                        "field": "tags",
                        "old": previous._computed_tags,
                        "new": record._computed_tags,
                    }
                )

            delta = record.diff_against(previous)

            # Add field-level changes from simple_history
            for change in delta.changes:
                changes.append(
                    {
                        "field": change.field,
                        "old": change.old,
                        "new": change.new,
                    }
                )

            previous.history_delta_changes = changes
            filtered.append(previous)

            previous = record

        return list(reversed(filtered))

    def merge_into(self, original):
        """Merge this collectable into the original one."""
        if not self.hidden:
            self.hidden = True
            self.save(update_fields=["hidden"])
        # Merge tags
        original.tags.add(*self.tags.all())
        # Merge descriptions
        original.description = original.description + "\n---\n" + self.description
        original.save(update_fields=["description"])
        # Reassign possessions
        for possession in self.possession_set.all():
            poss, _ = Possession.objects.get_or_create(
                user=possession.user, collectable=original
            )
            if possession.likes:
                poss.likes = True
            if possession.wants:
                poss.wants = True
            if possession.owns:
                poss.owns = True
            poss.save()

    def is_duplicate(self) -> bool:
        """
        Return True if this collectable has been reported as a duplicate of another one.
        """
        return self.reports_as_duplicate.exists()

    def duplicates(self, user):
        """
        Return the list of collectables that have been reported as duplicates of this one.
        """
        duplicate_reports = self.reports_as_original.values_list(
            "duplicate_id", flat=True
        )
        duplicates = Collectable.objects.with_counts_and_possessions(user).filter(
            id__in=duplicate_reports
        )
        return duplicates

    class Meta:
        verbose_name = _("Collectable")
        verbose_name_plural = _("Collectables")


class Possession(models.Model):
    """
    Link between a user and a collectable item, representing the user's
    possession status of the collectable.
    """

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    collectable = models.ForeignKey(Collectable, on_delete=models.CASCADE)
    likes = models.BooleanField(_("Likes"), default=False)
    wants = models.BooleanField(_("Wants"), default=False)
    owns = models.BooleanField(_("Owns"), default=True)

    class Meta:
        verbose_name = _("Possession")
        verbose_name_plural = _("Possessions")
        unique_together = ("user", "collectable")


def get_unknown_user():
    """
    Returns the system 'unknown' user. Creates it if not already present.
    Prevents reports to be deleted in cascade when user is deleted.
    """
    User = get_user_model()
    user, _ = User.objects.get_or_create(
        username="unknown",
        defaults={
            "email": "unknown@example.com",
            "is_active": False,  # prevents login
        },
    )
    return user


class DuplicateReport(models.Model):
    original = models.ForeignKey(
        Collectable,
        on_delete=models.CASCADE,
        related_name="reports_as_original",
    )
    duplicate = models.ForeignKey(
        Collectable,
        on_delete=models.CASCADE,
        related_name="reports_as_duplicate",
    )
    reporter = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET(get_unknown_user),
        related_name="duplicate_reports",
    )
    created_at = models.DateTimeField(_("Reported at"), auto_now_add=True)

    class Meta:
        constraints = [
            models.CheckConstraint(
                check=~models.Q(original=models.F("duplicate")),
                name="prevent_self_duplicate",
            ),
            models.UniqueConstraint(
                fields=["original", "duplicate", "reporter"],
                name="unique_duplicate_report",
            ),
        ]

    def save(self, *args, **kwargs):
        # Tag the duplicate as such.
        self.duplicate.tags.add("duplicate")
        # If the threshold is reached, merge the duplicate with the original.
        if len(self.confirmations()) >= settings.DUPLICATE_CONFIRMATION_THRESHOLD:
            self.duplicate.merge_into(self.original)
        super().save(*args, **kwargs)

    def confirmations(self):
        return (
            DuplicateReport.objects.filter(
                original=self.original, duplicate=self.duplicate
            )
            .exclude(reporter=self.reporter)
            .values_list("reporter__username", flat=True)
        )

    def clean(self):
        # If the model instance is not fully initialized, skip validation.
        if not all([self.original_id, self.duplicate_id, self.reporter_id]):
            return  # Skip validation if any ID is missing

        # Prevent self-links
        if self.original == self.duplicate:
            raise ValidationError("A collectable cannot be a duplicate of itself.")

        # Prevent reporting hidden collectables
        if self.duplicate.hidden or self.original.hidden:
            raise ValidationError("Cannot report a hidden collectable.")

        # Prevent duplicate reports by the same user
        if DuplicateReport.objects.filter(
            original=self.original, duplicate=self.duplicate, reporter=self.reporter
        ).exists():
            raise ValidationError("You have already reported this duplicate.")
        # Prevent loops
        if self._creates_cycle():
            raise ValidationError("Adding this duplicate would create a loop.")

    def _creates_cycle(self):
        """
        Detect if adding this duplicate would create a cycle in the duplicates graph.
        Multiple reports of the same edge do NOT count as a loop.
        """
        visited = set()
        queue = [self.duplicate.id]

        # Build a graph of all edges as (original -> duplicate)
        edges = DuplicateReport.objects.exclude(
            original=self.original, duplicate=self.duplicate
        ).values_list("original_id", "duplicate_id")

        graph = {}
        for orig, dup in edges:
            graph.setdefault(orig, set()).add(dup)

        # Include the new edge
        graph.setdefault(self.original.id, set()).add(self.duplicate.id)

        while queue:
            current = queue.pop(0)
            if current == self.original.id and current != self.duplicate.id:
                return True  # cycle detected

            visited.add(current)
            for neighbor in graph.get(current, []):
                if neighbor not in visited:
                    queue.append(neighbor)

        return False
