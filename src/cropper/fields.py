from io import BytesIO

from django import forms
from django.conf import settings
from django.core.files.uploadedfile import InMemoryUploadedFile
from django.utils.translation import gettext_lazy as _
from PIL import Image

from .widgets import CropImageWidget


class CropImageField(forms.ImageField):
    widget = CropImageWidget

    def clean(self, data, initial=None):
        if not data or not data.get("file"):
            return None

        # Run checks before the image is decoded
        self.check_file_size(data["file"])

        uploaded_file = super().clean(data["file"], initial)
        x, y, w, h = data["x"], data["y"], data["w"], data["h"]

        # `Image.open()` only reads the header, it does not decode pixels.
        image = Image.open(uploaded_file)
        self.check_pixel_count(image)

        width, height = image.size

        # Clamp coordinates
        x = max(0, min(x, width))
        y = max(0, min(y, height))
        w = min(w, width - x)
        h = min(h, height - y)

        if w <= 0 or h <= 0:
            raise forms.ValidationError(
                _("Invalid crop dimensions."), code="invalid-crop"
            )

        # Force crop to square.
        size = min(w, h)
        cropped = image.crop((x, y, x + size, y + size))

        buf = BytesIO()
        cropped.save(buf, format=image.format or "JPEG")
        buf.seek(0)

        return InMemoryUploadedFile(
            buf,  # file
            field_name=getattr(uploaded_file, "field_name", None),
            name=uploaded_file.name,
            content_type=uploaded_file.content_type,
            size=buf.getbuffer().nbytes,
            charset=None,
        )

    def check_file_size(self, uploaded_file):
        max_bytes = settings.COLLECTABLE_MAX_UPLOAD_BYTES
        if uploaded_file.size > max_bytes:
            raise forms.ValidationError(
                _("The file exceeds the maximum size of %(max_size)s bytes.")
                % {"max_size": max_bytes},
                code="max-file-size",
            )

    def check_pixel_count(self, image):
        max_pixels = settings.COLLECTABLE_MAX_IMAGE_PIXELS
        width, height = image.size
        if width * height > max_pixels:
            raise forms.ValidationError(
                _("The image is too large to be processed (max %(max)s pixels).")
                % {"max": max_pixels},
                code="max-image-pixels",
            )
