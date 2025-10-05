from django.conf import settings
from django.core.management.base import BaseCommand
from django.utils.translation import gettext_lazy as _
from PIL import Image

from collectable.models import Collectable


class Command(BaseCommand):
    help = "Check collectables uploads"

    def handle(self, *args, **options):
        excs = []
        count = 0
        for collectable in Collectable.objects.all():
            try:
                img = Image.open(collectable.photo.path)
            except Exception as exc:
                excs.append(exc)
            w, h = img.size
            if diff := abs(w - h) > 0:
                style_klass = (
                    self.style.ERROR
                    if diff > settings.COLLECTABLE_SQUARE_IMAGE_TOLERANCE_PX
                    else self.style.WARNING
                )
                self.stdout.write(
                    style_klass(
                        f"{collectable.photo.path} is not a square image (is {w}x{h})"
                    )
                )
            try:
                Image.open(collectable.thumbnail.path)
            except Exception as exc:
                excs.append(exc)
            count += 1
        if excs:
            self.stdout.write(self.style.ERROR("\n".join(str(e) for e in excs)))
        self.stdout.write(self.style.SUCCESS(_("%s collectables verified.") % count))
