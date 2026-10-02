import io

from PIL import ExifTags, Image

from collectable.processors import ExifTranspose, FlattenOnWhite


def test_exif_transpose_applies_orientation():
    # Red on top, blue at bottom, tagged as rotated 180°.
    img = Image.new("RGB", (10, 10), color=(255, 0, 0))
    img.paste((0, 0, 255), (0, 5, 10, 10))
    exif = Image.Exif()
    exif[ExifTags.Base.Orientation] = 3
    buf = io.BytesIO()
    img.save(buf, format="JPEG", exif=exif)
    buf.seek(0)

    result = ExifTranspose().process(Image.open(buf))
    assert result.getpixel((5, 0))[2] > 200
    assert result.getpixel((5, 9))[0] > 200


def test_exif_transpose_without_exif_is_passthrough():
    img = Image.new("RGB", (10, 10), color=(10, 20, 30))
    result = ExifTranspose().process(img)
    assert result.getpixel((0, 0)) == (10, 20, 30)


def test_flatten_rgba_composites_onto_white():
    # Fully transparent pixels should become white, not black.
    img = Image.new("RGBA", (10, 10), color=(0, 0, 0, 0))
    result = FlattenOnWhite().process(img)
    assert result.mode == "RGB"
    assert result.getpixel((0, 0)) == (255, 255, 255)


def test_flatten_keeps_opaque_pixels():
    img = Image.new("RGBA", (10, 10), color=(10, 20, 30, 255))
    result = FlattenOnWhite().process(img)
    assert result.mode == "RGB"
    assert result.getpixel((0, 0)) == (10, 20, 30)


def test_flatten_rgb_is_passthrough():
    img = Image.new("RGB", (10, 10), color=(10, 20, 30))
    result = FlattenOnWhite().process(img)
    assert result.mode == "RGB"
    assert result.getpixel((0, 0)) == (10, 20, 30)


def test_flatten_palette_with_transparency():
    img = Image.new("P", (10, 10))
    img.info["transparency"] = 0
    result = FlattenOnWhite().process(img)
    assert result.mode == "RGB"
