import uuid

import simple_history
import taggit.models
from django.conf import settings
from django.db import models
from django.db.models.functions import Coalesce
from django.utils.translation import gettext_lazy as _
from imagekit.models import ImageSpecField
from imagekit.processors import Thumbnail
from simple_history.models import HistoricalRecords
from taggit.managers import TaggableManager


class UUIDTaggedItem(
    taggit.models.GenericUUIDTaggedItemBase, taggit.models.TaggedItemBase
):
    class Meta:
        verbose_name = _("Tag")
        verbose_name_plural = _("Tags")


class CollectableManager(models.Manager):
    def with_counts(self):
        return (
            self.annotate(
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
            # Since all views show tags, prefetch them.
            .prefetch_related("tags")
        )


# Track changes of tags
simple_history.register(taggit.models.Tag)
simple_history.register(UUIDTaggedItem)


class Collectable(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    created_at = models.DateTimeField(auto_now_add=True, editable=False)
    modified_at = models.DateTimeField(auto_now=True, editable=False)
    photo = models.ImageField(upload_to="collectables/%Y/")
    tags = TaggableManager(through=UUIDTaggedItem)
    history = HistoricalRecords(excluded_fields=["modified_at"])  # m2m_fields=[tags]
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


class Possession(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    collectable = models.ForeignKey(Collectable, on_delete=models.CASCADE)
    likes = models.BooleanField(default=False)
    wants = models.BooleanField(default=False)
    owns = models.BooleanField(default=True)
