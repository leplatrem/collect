import io

import factory
from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core.files.uploadedfile import SimpleUploadedFile
from factory import Faker, SubFactory
from factory.django import DjangoModelFactory
from factory.fuzzy import FuzzyChoice
from PIL import Image

from collectable.models import Collectable, DuplicateReport, Possession


class UserFactory(DjangoModelFactory):
    class Meta:
        model = get_user_model()

    username = Faker("user_name")
    email = Faker("email")

    @factory.post_generation
    def collector(self, create, extracted, **kwargs):
        if not create:
            return
        if extracted is False:
            return
        group, _ = Group.objects.get_or_create(name=settings.COLLECTORS_GROUP_NAME)
        self.groups.add(group)


class CollectableFactory(DjangoModelFactory):
    class Meta:
        model = Collectable

    description = Faker("sentence")

    @classmethod
    def _create(cls, model_class, *args, **kwargs):
        # Add a fake image, JPEG by default, PNG (with transparency) on request.
        img_format = kwargs.pop("img_format", "JPEG")
        if img_format == "PNG":
            img = Image.new("RGBA", (100, 100), color=(255, 0, 0, 0))
            default_filename = "sticker-filename.png"
            content_type = "image/png"
        else:
            img = Image.new("RGB", (100, 100), color="white")
            default_filename = "sticker-filename.jpg"
            content_type = "image/jpeg"
        buffer = io.BytesIO()
        img.save(buffer, format=img_format)
        buffer.seek(0)
        file = SimpleUploadedFile(
            kwargs.pop("filename", default_filename),
            buffer.read(),
            content_type=content_type,
        )
        kwargs["photo"] = file
        return super()._create(model_class, *args, **kwargs)

    @factory.post_generation
    def tags(self, create, extracted, **kwargs):
        if not create:
            # Object not saved yet — skip
            return
        if extracted:
            self.tags.add(*extracted)


class PossessionFactory(DjangoModelFactory):
    class Meta:
        model = Possession

    user = SubFactory(UserFactory)
    collectable = SubFactory(CollectableFactory)
    likes = FuzzyChoice([True, False])
    wants = FuzzyChoice([True, False])
    owns = FuzzyChoice([True, False])


class DuplicateReportFactory(DjangoModelFactory):
    class Meta:
        model = DuplicateReport

    reporter = SubFactory(UserFactory)
    duplicate = SubFactory(CollectableFactory)
    original = SubFactory(CollectableFactory)
