from django.forms import ModelForm, TextInput

from collectable.models import Collectable, Possession
from cropper.widget import SquareImageCropper


class CollectableForm(ModelForm):
    class Meta:
        model = Collectable
        fields = ["photo", "description", "tags"]
        widgets = {
            "photo": SquareImageCropper(),
            "description": TextInput(),
        }


class PossessionForm(ModelForm):
    class Meta:
        model = Possession
        fields = ["likes", "wants", "owns"]
