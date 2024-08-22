import hashlib
import os
import uuid
from pathlib import Path

from django.contrib.auth import get_user_model
from django.core.files import File
from django.core.management.base import BaseCommand, CommandError
from django.utils.translation import gettext_lazy as _
from PIL import ExifTags, Image

from collectable.models import Collectable, Possession


User = get_user_model()


class Command(BaseCommand):
    help = "Import collectables from folder"

    def add_arguments(self, parser):
        # Positional
        parser.add_argument(
            "creator", type=str, help=_("Username for creator of imported collectables")
        )
        parser.add_argument("folder", type=str)
        # Optional
        parser.add_argument(
            "--owner", type=str, help=_("Username for owner of imported collectables")
        )
        parser.add_argument("--tags", action="append")

    def handle(self, *args, **options):
        folder_path = Path(options["folder"])
        if not folder_path.exists():
            raise CommandError('Path "%s" does not exist' % folder_path)

        creator = User.objects.get(username=options["creator"])

        owner = None
        if options["owner"]:
            owner = User.objects.get(username=options["owner"])

        images = folder_path.glob("**/*.jpg")
        for image_path in images:
            # Consider subfolders as tags.
            parent_folder = image_path.parent
            relative_folder = parent_folder.relative_to(folder_path)
            folder_tags = list(relative_folder.parts)
            taglist = (options["tags"] or []) + folder_tags

            im = Image.open(image_path)
            width, height = im.size
            if width != height:
                self.stdout.write(
                    self.style.ERROR(
                        _('"%s" is not a square image, skipping.') % image_path
                    )
                )
                continue

            exif = im.getexif()
            try:
                # Use shot date time and camera model as identifier of collectable.
                # This way pictures can be renamed and still be identified.
                seed = (
                    exif[ExifTags.Base.DateTime.value]
                    + "-"
                    + exif[ExifTags.Base.Model.value]
                )
            except KeyError:
                self.stdout.write(
                    self.style.ERROR(
                        _('"%s" has no EXIF metadata, skipping.') % image_path
                    )
                )
                continue
            m = hashlib.md5()
            m.update(str(seed).encode("utf-8"))
            uuid_id = uuid.UUID(m.hexdigest())

            updated = False
            created = False
            try:
                collectable = Collectable.objects.get(id=uuid_id)

                if set(taglist) != set(collectable.tags.slugs()):
                    collectable.tags.add(*taglist)
                    updated = True

                if collectable.photo.size != os.path.getsize(image_path):
                    with image_path.open(mode="rb") as f:
                        collectable._history_user = creator
                        collectable.photo = File(file=f, name=image_path.name)
                        collectable.save()
                    collectable.thumbnail.generate()
                    updated = True

            except Collectable.DoesNotExist:
                with image_path.open(mode="rb") as f:
                    photo = File(file=f, name=image_path.name)
                    collectable = Collectable(id=uuid_id, photo=photo)
                    collectable._history_user = creator
                    collectable.save()
                collectable.tags.add(*taglist)
                collectable.thumbnail.generate()
                created = True

            if created:
                self.stdout.write(
                    self.style.SUCCESS(_("Successfully created %s") % collectable)
                )
            if updated:
                self.stdout.write(
                    self.style.SUCCESS(_("Successfully updated %s") % collectable)
                )

            if owner:
                possession, changed = Possession.objects.get_or_create(
                    collectable=collectable, user=owner
                )
                if not possession.owns:
                    possession.owns = True
                    possession.save()
                    changed = True
                if changed:
                    self.stdout.write(
                        self.style.SUCCESS(
                            _("Successfully assigned owner of %s") % collectable
                        )
                    )

        self.stdout.write(
            self.style.SUCCESS(
                _("%s collectables in database.") % Collectable.objects.count()
            )
        )
