import uuid

import simple_history
import taggit.models
from django.conf import settings
from django.db import models
from django.db.models import Prefetch
from django.db.models.functions import Coalesce
from django.urls import reverse_lazy
from django.utils.translation import gettext_lazy as _
from imagekit.models import ImageSpecField
from imagekit.processors import Thumbnail
from simple_history.models import HistoricalRecords
from taggit.managers import TaggableManager

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
        qs = self.prefetch_related("tags")
        # If user is logged in, prefetch their possessions.
        if user.is_authenticated:
            qs = qs.prefetch_related(
                Prefetch(
                    "possession_set", queryset=Possession.objects.filter(user=user)
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


# Track changes of tags
# simple_history.register(taggit.models.Tag)
# simple_history.register(UUIDTaggedItem)


class Collectable(models.Model):
    id = models.UUIDField(
        _("Identifier"), primary_key=True, default=uuid.uuid4, editable=False
    )
    created_at = models.DateTimeField(
        _("Created at"), auto_now_add=True, editable=False
    )
    modified_at = models.DateTimeField(_("Modified at"), auto_now=True, editable=False)
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
    history = HistoricalRecords(
        _("History"), excluded_fields=["modified_at"]
    )  # m2m_fields=[tags]
    possessions = models.ManyToManyField(settings.AUTH_USER_MODEL, through="Possession")

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

    def get_absolute_url(self):
        return reverse_lazy("collectable:details", kwargs={"id": self.id})

    def possession_of(self, user):
        possession = None
        if user.is_authenticated:
            possessions = self.possession_set.all()
            possession = possessions[0] if possessions else None
        if possession is None:
            possession = Possession(
                collectable=self, likes=False, wants=False, owns=False
            )  # Don't save.
        return possession

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
