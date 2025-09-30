from io import BytesIO

from django import forms
from django.core.files.uploadedfile import InMemoryUploadedFile
from PIL import Image

from .widgets import CropImageWidget


class CropImageField(forms.ImageField):
    widget = CropImageWidget

    def clean(self, data, initial=None):
        if not data or not data.get("file"):
            return None

        uploaded_file = super().clean(data["file"], initial)
        x, y, w, h = data["x"], data["y"], data["w"], data["h"]

        image = Image.open(uploaded_file)
        width, height = image.size

        # Clamp coordinates
        x = max(0, min(x, width))
        y = max(0, min(y, height))
        w = min(w, width - x)
        h = min(h, height - y)

        if w <= 0 or h <= 0:
            raise forms.ValidationError("Invalid crop dimensions.")

        cropped = image.crop((x, y, x + w, y + h))

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
