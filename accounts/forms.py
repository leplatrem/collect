from django import forms
from django.conf import settings
from django.contrib.auth.forms import UserCreationForm

from django.utils.translation import gettext_lazy as _


class SignUpForm(UserCreationForm):
    secret = forms.CharField(label=_("Invitation secret"), max_length=30, required=True)

    def clean_secret(self):
        data = self.cleaned_data["secret"]
        if data not in settings.SIGNUP_SECRETS_WORDS:
            raise forms.ValidationError(
                _("Invalid secret: %(value)s"),
                params={"value": data},
            )
        return data
