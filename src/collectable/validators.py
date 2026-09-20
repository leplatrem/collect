import os  # noqa: I001

# `pylibmagic` must be imported before `magic`, which looks up the library it
# installs, so this import block is left unsorted.
import pylibmagic  # noqa: F401
import magic
from django.conf import settings
from django.core.exceptions import ValidationError
from django.utils.deconstruct import deconstructible
from django.utils.translation import gettext_lazy as _


@deconstructible
class MimetypeValidator(object):
    def __init__(self, mimetypes, code="file-type"):
        self.mimetypes = mimetypes
        self.code = code

    def __call__(self, fieldfile):
        try:
            # A file already stored may have been closed by whoever read it
            # last (generating the thumbnail, for instance).
            if getattr(fieldfile, "closed", False):
                fieldfile.open("rb")
            header = fieldfile.read(2048)
            # Leave the file where we found it.
            fieldfile.seek(0)
            mime = magic.from_buffer(header, mime=True)
            if mime not in self.mimetypes:
                raise ValidationError(
                    _("%s is not an acceptable file type.") % fieldfile, code=self.code
                )
        except AttributeError:
            raise ValidationError(
                "Value could not be validated for file type %s." % fieldfile,
                code="file-type",
            )


@deconstructible
class SquareImageValidator(object):
    def __call__(self, image):
        if (
            abs(image.width - image.height)
            > settings.COLLECTABLE_SQUARE_IMAGE_TOLERANCE_PX
        ):
            raise ValidationError(
                _("%s is not a square image") % image, code="square-image"
            )


@deconstructible
class MaxFileSizeValidator(object):
    """
    Refuse files bigger than the value of the given setting.
    """

    def __init__(self, setting="COLLECTABLE_MAX_UPLOAD_BYTES"):
        self.setting = setting

    def __call__(self, fieldfile):
        max_bytes = getattr(settings, self.setting)
        if fieldfile.size > max_bytes:
            raise ValidationError(
                _("%(file)s exceeds the maximum file size of %(max_size)s bytes.")
                % {
                    "file": fieldfile,
                    "max_size": max_bytes,
                },
                code="max-file-size",
            )

    def __eq__(self, other):
        return isinstance(other, MaxFileSizeValidator) and (
            self.setting == other.setting
        )


@deconstructible
class FileExtensionValidator(object):
    """
    Refuse files whose extension is not listed in the given setting.
    """

    def __init__(self, setting="COLLECTABLE_SOURCE_FILE_EXTENSIONS"):
        self.setting = setting

    def __call__(self, fieldfile):
        allowed = getattr(settings, self.setting)
        extension = os.path.splitext(fieldfile.name)[1].lstrip(".").lower()
        if extension not in allowed:
            raise ValidationError(
                _("%(extension)s files are not accepted. Allowed formats: %(allowed)s.")
                % {
                    "extension": f".{extension}" if extension else _("Extension-less"),
                    "allowed": ", ".join(f".{e}" for e in allowed),
                },
                code="file-extension",
            )

    def __eq__(self, other):
        return isinstance(other, FileExtensionValidator) and (
            self.setting == other.setting
        )


@deconstructible
class MaxImagePixelsValidator(object):
    """
    Refuse images with too many pixels, whatever the size of the file.

    Decoding allocates about ``width * height * 4`` bytes, so a small
    compressed file can exhaust the memory of the whole worker process.
    """

    def __init__(self, setting="COLLECTABLE_MAX_IMAGE_PIXELS"):
        self.setting = setting

    def __call__(self, image):
        max_pixels = getattr(settings, self.setting)
        if image.width * image.height > max_pixels:
            raise ValidationError(
                _("%(file)s is too large to be processed (max %(max)s pixels).")
                % {"file": image, "max": max_pixels},
                code="max-image-pixels",
            )

    def __eq__(self, other):
        return isinstance(other, MaxImagePixelsValidator) and (
            self.setting == other.setting
        )
