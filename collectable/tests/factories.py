import io

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from factory import Faker, SubFactory
from factory.django import DjangoModelFactory
from factory.fuzzy import FuzzyChoice
from PIL import Image

from collectable.models import Collectable, Possession


class UserFactory(DjangoModelFactory):
    class Meta:
        model = get_user_model()

    username = Faker("user_name")
    email = Faker("email")


class CollectableFactory(DjangoModelFactory):
    class Meta:
        model = Collectable

    description = Faker("sentence")

    @classmethod
    def _create(cls, model_class, *args, **kwargs):
        # Add a fake image
        img = Image.new("RGB", (100, 100), color="white")
        buffer = io.BytesIO()
        img.save(buffer, format="JPEG")
        buffer.seek(0)
        file = SimpleUploadedFile("test.jpg", buffer.read(), content_type="image/jpeg")
        kwargs["photo"] = file
        return super()._create(model_class, *args, **kwargs)


class PossessionFactory(DjangoModelFactory):
    class Meta:
        model = Possession

    user = SubFactory(UserFactory)
    collectable = SubFactory(CollectableFactory)
    likes = FuzzyChoice([True, False])
    wants = FuzzyChoice([True, False])
    owns = FuzzyChoice([True, False])
