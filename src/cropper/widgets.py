from django import forms


class CropImageWidget(forms.ClearableFileInput):
    template_name = "cropper/widget.html"

    def value_from_datadict(self, data, files, name):
        """
        Collect both the file and cropping coordinates.
        """
        file = super().value_from_datadict(data, files, name)
        try:
            x = int(data[f"{name}_x"])
            y = int(data[f"{name}_y"])
            w = int(data[f"{name}_w"])
            h = int(data[f"{name}_h"])
        except (KeyError, ValueError):
            x = y = w = h = 0
        return {"file": file, "x": x, "y": y, "w": w, "h": h}

    class Media:
        js = ("cropper/script.js",)
        css = {"all": ("cropper/style.css",)}
