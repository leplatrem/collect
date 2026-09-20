from django.apps import AppConfig
from django.conf import settings
from PIL import Image


class CollectableConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "collectable"

    def ready(self) -> None:
        # Backstop for every code path that decodes an image (thumbnails,
        # imports, ...) and not just the upload form: above this many pixels,
        # Pillow refuses to decode instead of allocating the memory.
        Image.MAX_IMAGE_PIXELS = settings.COLLECTABLE_MAX_IMAGE_PIXELS
        print(f"{self.name} app started.")
