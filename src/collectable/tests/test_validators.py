import io
from unittest.mock import Mock

import pytest
from django.conf import settings
from django.core.exceptions import ValidationError
from PIL import Image

from collectable.validators import MaxFileSizeValidator, MimetypeValidator


def _image_bytes(img_format):
    img = Image.new("RGB", (10, 10), color="white")
    buffer = io.BytesIO()
    img.save(buffer, format=img_format)
    return buffer.getvalue()


@pytest.mark.parametrize(
    "img_format, mime",
    [("JPEG", "image/jpeg"), ("PNG", "image/png")],
)
def test_mimetype_validator_accepts(img_format, mime):
    fieldfile = Mock()
    fieldfile.read.return_value = _image_bytes(img_format)
    # Should not raise for accepted types.
    MimetypeValidator(["image/jpeg", "image/png"])(fieldfile)


def test_mimetype_validator_rejects_unlisted_type():
    fieldfile = Mock()
    fieldfile.read.return_value = _image_bytes("GIF")
    fieldfile.__str__ = lambda self: "photo.gif"

    with pytest.raises(ValidationError) as exc:
        MimetypeValidator(["image/jpeg", "image/png"])(fieldfile)

    assert exc.value.code == "file-type"


def test_max_file_size_validator_message_format():
    fieldfile = Mock()
    fieldfile.size = settings.COLLECTABLE_MAX_UPLOAD_BYTES + 1
    fieldfile.__str__ = lambda self: "photo.jpg"

    with pytest.raises(ValidationError) as exc:
        MaxFileSizeValidator()(fieldfile)

    message = exc.value.messages[0]
    # Placeholders must be interpolated, not left as literal template syntax.
    assert "{{" not in message
    assert "photo.jpg" in message
    assert str(settings.COLLECTABLE_MAX_UPLOAD_BYTES) in message
