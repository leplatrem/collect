import hashlib
import os
import re
import uuid
from pathlib import Path

from django.contrib.auth import get_user_model
from django.core.files import File
from django.core.management.base import BaseCommand, CommandError
from django.utils.translation import gettext_lazy as _
from PIL import ExifTags, Image, ImageOps

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
            "--prepend-description",
            type=str,
            help=_("Text to prepend to description"),
            default="",
        )
        parser.add_argument(
            "--append-description",
            type=str,
            help=_("Text to append to description"),
            default="",
        )
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

        images = folder_path.glob("**/*.*")
        count_created = 0
        count_updated = 0
        for image_path in images:
            if image_path.suffix.lower() not in [".jpg", ".jpeg", ".png"]:
                continue  # skip non-image files
            # Consider subfolders as tags.
            parent_folder = image_path.parent
            relative_folder = parent_folder.relative_to(folder_path)
            folder_tags = list(relative_folder.parts)
            taglist = (options["tags"] or []) + folder_tags

            im = Image.open(image_path)
            im = ImageOps.exif_transpose(im)

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
                    + exif.get(ExifTags.Base.Model.value, "unknown")
                )
            except KeyError:
                self.stdout.write(
                    self.style.WARNING(
                        _(
                            '"%s" has no DateTime EXIF metadata, using filename as ID seed.'
                        )
                        % image_path
                    )
                )
                seed = image_path.name
            m = hashlib.md5()
            m.update(str(seed).encode("utf-8"))
            uuid_id = uuid.UUID(m.hexdigest())

            # Extract EXIF description
            # Extract tags from description (eg. `This is a caption with some hashtags #fun #2025`)
            exif_description = (
                exif.get(ExifTags.Base.ImageDescription, "")
                .encode("latin1")
                .decode("utf-8", errors="replace")
            )
            if match := re.match(
                r"^(.*?)(?:\s+(#[\w\d]+(?:\s+#[\w\d]+)*))?$", exif_description.strip()
            ):
                exif_description = match.group(1).strip()
                tags_str = match.group(2)
                taglist += [
                    t.replace("#", "")
                    for t in (tags_str.strip().split() if tags_str else [])
                ]

            description = (
                options["prepend_description"]
                + exif_description
                + options["append_description"]
            )

            updated = False
            created = False
            try:
                collectable = Collectable.objects.get(id=uuid_id)

                if not collectable.description:
                    collectable.description = description
                    updated = True

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

                if updated:
                    collectable._history_user = creator
                    collectable.save()

            except Collectable.DoesNotExist:
                with image_path.open(mode="rb") as f:
                    photo = File(file=f, name=image_path.name)
                    collectable = Collectable(
                        id=uuid_id, photo=photo, description=description
                    )
                    collectable._history_user = creator
                    collectable.save()
                collectable.tags.add(*taglist)
                collectable.thumbnail.generate()
                created = True

            if created:
                self.stdout.write(
                    self.style.SUCCESS(_("Successfully created %s") % collectable)
                )
                count_created += 1
            if updated:
                self.stdout.write(
                    self.style.SUCCESS(_("Successfully updated %s") % collectable)
                )
                count_updated += 1

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
                _("%(num_created)s collectables created, %(num_updated)s updated.")
                % {"num_created": count_created, "num_updated": count_updated}
            )
        )

        self.stdout.write(
            self.style.SUCCESS(
                _("%(total)s collectables in database.")
                % {"total": Collectable.objects.count()}
            )
        )
