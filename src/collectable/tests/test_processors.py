from PIL import Image

from collectable.processors import FlattenOnWhite


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
