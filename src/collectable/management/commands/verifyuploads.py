from django.core.management.base import BaseCommand
from django.utils.translation import gettext_lazy as _
from PIL import Image

from collectable.models import Collectable


class Command(BaseCommand):
    help = "Check collectables uploads"

    def handle(self, *args, **options):
        excs = []
        for collectable in Collectable.objects.all():
            self.stdout.write(collectable.photo.path)
            try:
                Image.open(collectable.photo.path)
            except Exception as exc:
                excs.append(exc)
            self.stdout.write(collectable.thumbnail.path)
            try:
                Image.open(collectable.thumbnail.path)
            except Exception as exc:
                excs.append(exc)
        if excs:
            self.stdout.write(self.style.ERROR("\n".join(str(e) for e in excs)))
        self.stdout.write(
            self.style.SUCCESS(
                _("%s collectables verified.") % Collectable.objects.count()
            )
        )
