from django.forms import ModelForm

from collectable.models import Possession


class PossessionForm(ModelForm):
    class Meta:
        model = Possession
        fields = ["likes", "wants", "owns"]
