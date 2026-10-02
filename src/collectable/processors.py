from PIL import Image, ImageOps


class ExifTranspose:
    """Rotate/flip the image according to its EXIF orientation tag."""

    def process(self, image):
        return ImageOps.exif_transpose(image)


class FlattenOnWhite:
    """Composite images that have transparency onto a white background.

    JPEG has no alpha channel, so PNG uploads with transparency would otherwise
    be flattened onto black when the thumbnail is saved as JPEG.
    """

    def __init__(self, color=(255, 255, 255)):
        self.color = color

    def process(self, image):
        has_alpha = image.mode in ("RGBA", "LA") or (
            image.mode == "P" and "transparency" in image.info
        )
        if has_alpha:
            rgba = image.convert("RGBA")
            background = Image.new("RGB", rgba.size, self.color)
            background.paste(rgba, mask=rgba.split()[-1])
            return background
        return image.convert("RGB")
