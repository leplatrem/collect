import io
from unittest.mock import patch

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.forms import ValidationError
from django.test import override_settings
from PIL import Image

from cropper.fields import CropImageField


def upload(size=(100, 100), img_format="JPEG", name="sticker.jpg"):
    img = Image.new("RGB", size, color="white")
    buffer = io.BytesIO()
    img.save(buffer, format=img_format)
    buffer.seek(0)
    return SimpleUploadedFile(name, buffer.read(), content_type="image/jpeg")


def data_for(uploaded_file, x=0, y=0, w=50, h=50):
    return {"file": uploaded_file, "x": x, "y": y, "w": w, "h": h}


def test_returns_none_without_file():
    assert CropImageField(required=False).clean(None) is None
    assert CropImageField(required=False).clean(data_for(None)) is None


def test_crops_to_a_square():
    cleaned = CropImageField().clean(data_for(upload(), w=60, h=40))

    assert Image.open(cleaned).size == (40, 40)


def test_crop_coordinates_are_clamped_to_the_image():
    # A client can send anything: the crop box must be brought back inside.
    cleaned = CropImageField().clean(data_for(upload(), x=90, y=90, w=500, h=500))

    assert Image.open(cleaned).size == (10, 10)


def test_rejects_empty_crop():
    with pytest.raises(ValidationError) as exc:
        CropImageField().clean(data_for(upload(), x=100, y=100, w=10, h=10))

    assert exc.value.code == "invalid-crop"


@override_settings(COLLECTABLE_MAX_UPLOAD_BYTES=10)
def test_rejects_oversized_file_without_decoding_it():
    # Decoding is what costs memory, so the size has to be checked first: the
    # model validators only run once the form field is done cropping.
    with patch.object(Image, "open", side_effect=AssertionError("decoded!")):
        with pytest.raises(ValidationError) as exc:
            CropImageField().clean(data_for(upload()))

    assert exc.value.code == "max-file-size"


@override_settings(COLLECTABLE_MAX_IMAGE_PIXELS=100)
def test_rejects_too_many_pixels():
    # 100x100 pixels of white noise compress to almost nothing, but decoding
    # them allocates width * height * 4 bytes.
    with pytest.raises(ValidationError) as exc:
        CropImageField().clean(data_for(upload(size=(100, 100))))

    assert exc.value.code == "max-image-pixels"


@override_settings(COLLECTABLE_MAX_IMAGE_PIXELS=100)
def test_accepts_images_within_the_pixel_limit():
    cleaned = CropImageField().clean(data_for(upload(size=(10, 10)), w=5, h=5))

    assert Image.open(cleaned).size == (5, 5)
