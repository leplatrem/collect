from django.forms import ModelForm, TextInput

from collectable.models import Collectable, Possession


class CollectableForm(ModelForm):
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
