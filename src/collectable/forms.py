from django.forms import ModelForm, TextInput

from collectable.models import Collectable, Possession
from cropper.fields import CropImageField


class CollectableForm(ModelForm):
    photo = CropImageField()

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
