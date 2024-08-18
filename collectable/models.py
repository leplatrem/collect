import uuid

from django.contrib.auth.models import User
from django.db import models
from django.utils.translation import gettext_lazy as _
from simple_history.models import HistoricalRecords
from taggit.managers import TaggableManager
from taggit.models import GenericUUIDTaggedItemBase, TaggedItemBase


class UUIDTaggedItem(GenericUUIDTaggedItemBase, TaggedItemBase):
    class Meta:
        verbose_name = _("Tag")
        verbose_name_plural = _("Tags")


class Collectable(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    created_at = models.DateTimeField(auto_now_add=True, editable=False)
    modified_at = models.DateTimeField(auto_now=True, editable=False)
    photo = models.ImageField(upload_to="collectables/%Y/")
    tags = TaggableManager(through=UUIDTaggedItem)
    history = HistoricalRecords()
    possessions = models.ManyToManyField(User, through="Possession")


class Possession(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    collectable = models.ForeignKey(Collectable, on_delete=models.CASCADE)
    owns = models.BooleanField(default=True)
    wants = models.BooleanField(default=False)
    likes = models.BooleanField(default=False)
