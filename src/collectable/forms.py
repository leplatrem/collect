from django.forms import ModelForm, TextInput

from collectable.models import Collectable, Possession
from cropper.fields import CropImageField


class CollectableForm(ModelForm):
    photo = CropImageField()

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["photo"].widget.attrs.update({"accept": "image/jpeg"})

    class Meta:
        model = Collectable
        fields = ["photo", "description", "tags"]
        widgets = {
            "description": TextInput(),
        }


class PossessionForm(ModelForm):
    class Meta:
        model = Possession
        fields = ["likes", "wants", "owns"]
