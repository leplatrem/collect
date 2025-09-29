from django import forms


class SquareImageCropper(forms.ClearableFileInput):
    template_name = "cropper/widget.html"

    class Media:
        js = ("cropper/script.js",)
        css = {"all": ("cropper/style.css",)}
