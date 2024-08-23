from django.forms import ModelForm

from collectable.models import Collectable, Possession


class CollectableForm(ModelForm):
    class Meta:
        model = Collectable
        fields = ["photo", "tags"]


class PossessionForm(ModelForm):
    class Meta:
        model = Possession
        fields = ["likes", "wants", "owns"]
