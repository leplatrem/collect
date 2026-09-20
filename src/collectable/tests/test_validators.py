import io
from unittest.mock import Mock

import pytest
from django.conf import settings
from django.core.exceptions import ValidationError
from django.test import override_settings
from PIL import Image

from collectable.validators import (
    FileExtensionValidator,
    MaxFileSizeValidator,
    MaxImagePixelsValidator,
    MimetypeValidator,
)


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


def test_mimetype_validator_rewinds_the_file():
    fieldfile = Mock()
    fieldfile.read.return_value = _image_bytes("JPEG")

    MimetypeValidator(["image/jpeg"])(fieldfile)

    # Whoever reads the file next (another validator, the storage backend)
    # expects to find it at the beginning.
    fieldfile.seek.assert_called_once_with(0)


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


@override_settings(COLLECTABLE_SOURCE_FILE_MAX_UPLOAD_BYTES=10)
def test_max_file_size_validator_reads_the_given_setting():
    fieldfile = Mock()
    fieldfile.size = 11
    fieldfile.__str__ = lambda self: "source.pdf"

    with pytest.raises(ValidationError) as exc:
        MaxFileSizeValidator("COLLECTABLE_SOURCE_FILE_MAX_UPLOAD_BYTES")(fieldfile)

    assert exc.value.code == "max-file-size"
    # The limit is read when validating, not frozen when the field is declared.
    assert "10 bytes" in exc.value.messages[0]


def test_max_file_size_validators_compare_by_setting():
    assert MaxFileSizeValidator() == MaxFileSizeValidator()
    assert MaxFileSizeValidator() != MaxFileSizeValidator("OTHER_SETTING")
    assert MaxFileSizeValidator() != "not a validator"


@pytest.mark.parametrize("filename", ["source.pdf", "SOURCE.PDF", "source.svg"])
def test_file_extension_validator_accepts_listed_extensions(filename):
    fieldfile = Mock()
    fieldfile.name = filename
    # Should not raise.
    FileExtensionValidator()(fieldfile)


@pytest.mark.parametrize(
    "filename",
    [
        "payload.html",
        "payload.htm",
        "payload.xhtml",
        "payload.js",
        "payload.svg.html",
        "payload",
    ],
)
def test_file_extension_validator_rejects_renderable_files(filename):
    # Source files are served from the same origin as the site: a file the
    # browser renders as a document could read the visitor's session.
    fieldfile = Mock()
    fieldfile.name = filename

    with pytest.raises(ValidationError) as exc:
        FileExtensionValidator()(fieldfile)

    assert exc.value.code == "file-extension"


@override_settings(COLLECTABLE_SOURCE_FILE_EXTENSIONS=["odt"])
def test_file_extension_validator_reads_the_given_setting():
    fieldfile = Mock()
    fieldfile.name = "source.odt"
    FileExtensionValidator()(fieldfile)

    fieldfile.name = "source.pdf"
    with pytest.raises(ValidationError):
        FileExtensionValidator()(fieldfile)


def test_file_extension_validators_compare_by_setting():
    assert FileExtensionValidator() == FileExtensionValidator()
    assert FileExtensionValidator() != FileExtensionValidator("OTHER_SETTING")
    assert FileExtensionValidator() != "not a validator"


@override_settings(COLLECTABLE_MAX_IMAGE_PIXELS=100)
def test_max_image_pixels_validator():
    image = Mock()
    image.width = image.height = 10
    # Exactly at the limit.
    MaxImagePixelsValidator()(image)

    image.width = 11
    with pytest.raises(ValidationError) as exc:
        MaxImagePixelsValidator()(image)

    assert exc.value.code == "max-image-pixels"


def test_max_image_pixels_validators_compare_by_setting():
    assert MaxImagePixelsValidator() == MaxImagePixelsValidator()
    assert MaxImagePixelsValidator() != MaxImagePixelsValidator("OTHER")
    assert MaxImagePixelsValidator() != "not a validator"
