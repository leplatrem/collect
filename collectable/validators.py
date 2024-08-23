import pylibmagic  # noqa: F401, I001
import magic
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
            mime = magic.from_buffer(fieldfile.read(2048), mime=True)
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
        if image.width != image.height:
            raise ValidationError(
                _("%s is not a square image") % image, code="square-image"
            )
