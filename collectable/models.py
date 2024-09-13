import uuid

import taggit.models
from django.conf import settings
from django.db import models
from django.db.models import Count, Prefetch
from django.db.models.functions import Coalesce
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.urls import reverse_lazy
from django.utils.translation import gettext_lazy as _
from imagekit.models import ImageSpecField
from imagekit.processors import Thumbnail
from simple_history.models import HistoricalRecords
from simple_history.template_utils import HistoricalRecordContextHelper
from taggit.managers import TaggableManager
from taggit.models import Tag

from collect.utils import tags_joiner
from collectable.validators import MimetypeValidator, SquareImageValidator


class UUIDTaggedItem(
    taggit.models.GenericUUIDTaggedItemBase, taggit.models.TaggedItemBase
):
    class Meta:
        verbose_name = _("Tag")
        verbose_name_plural = _("Tags")


class CollectableManager(models.Manager):
    def with_counts_and_possessions(self, user):
        # Since all views show tags, prefetch them.
        qs = self.prefetch_related(Prefetch("tags", to_attr="tags_list"))
        # If user is logged in, prefetch their possessions.
        if user.is_authenticated:
            qs = qs.prefetch_related(
                Prefetch(
                    "possession_set",
                    queryset=Possession.objects.filter(user=user),
                    to_attr="possession_set_list",
                )
            )
        # Add counter aggregations for possessions
        return (
            qs.annotate(
                nlikes=Coalesce(
                    models.Count(
                        "possessions", filter=models.Q(possession__likes=True)
                    ),
                    0,
                )
            )
            .annotate(
                nwants=Coalesce(
                    models.Count(
                        "possessions", filter=models.Q(possession__wants=True)
                    ),
                    0,
                )
            )
            .annotate(
                nowns=Coalesce(
                    models.Count("possessions", filter=models.Q(possession__owns=True)),
                    0,
                )
            )
        )


class Collectable(models.Model):
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
        ],
    )
    tags = TaggableManager(_("Tags"), through=UUIDTaggedItem)
    possessions = models.ManyToManyField(settings.AUTH_USER_MODEL, through="Possession")

    history = HistoricalRecords(_("History"), excluded_fields=["modified_at"])
    # Because of https://github.com/jazzband/django-taggit/issues/918
    # we use a computed field to track tags changes, with the `post_save` signal
    # defined below.
    _computed_tags = models.TextField(_("Tags"))

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

    objects = CollectableManager()

    @receiver(post_save, sender=UUIDTaggedItem, dispatch_uid="update_computed_tags")
    def on_tag_changed(sender, instance, created, **kwargs):
        item = instance.content_object
        if not isinstance(item, Collectable):
            return
        item._computed_tags = tags_joiner(item.tags.all())
        item.save(update_fields=["_computed_tags"])

    def tags_with_count(self):
        return (
            Tag.objects.filter(slug__in=self.tags.slugs())
            .annotate(ncollectable=Count("collectable"))
            .order_by("-ncollectable")
        )

    def get_absolute_url(self):
        return reverse_lazy("collectable:details", kwargs={"id": self.id})

    def possession_of(self, user):
        possession = None
        if user.is_authenticated:
            if possessions := getattr(self, "possession_set_list", []):
                possession = possessions[0]
        if possession is None:
            possession = Possession(
                collectable=self, likes=False, wants=False, owns=False
            )  # Don't save.
        return possession

    def history_with_deltas(self):
        """
        Return the history entries with delta information.
        """
        previous = None
        history_records = self.history.select_related("history_user").all()
        filtered = []
        for current in history_records:
            if previous is None:
                previous = current
                continue

            delta = previous.diff_against(current)
            if len(delta.changes) == 0 or len(delta.changed_fields) == 0:
                previous = current
                continue

            helper = HistoricalRecordContextHelper(Collectable, previous)
            previous.history_delta_changes = helper.context_for_delta_changes(delta)
            filtered.append(previous)
            previous = current
        return filtered

    class Meta:
        verbose_name = _("Collectable")
        verbose_name_plural = _("Collectables")


class Possession(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    collectable = models.ForeignKey(Collectable, on_delete=models.CASCADE)
    likes = models.BooleanField(_("Likes"), default=False)
    wants = models.BooleanField(_("Wants"), default=False)
    owns = models.BooleanField(_("Owns"), default=True)

    class Meta:
        verbose_name = _("Possession")
        verbose_name_plural = _("Possessions")
        unique_together = ("user", "collectable")
