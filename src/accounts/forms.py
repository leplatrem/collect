from django import forms
from django.conf import settings
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import Group
from django.utils.translation import gettext_lazy as _


class SignUpForm(UserCreationForm):
    usable_password = None  # Remove this unused field.
    secret = forms.CharField(
        label=_("Invitation secret"),
        max_length=30,
        required=False,
        help_text=_(
            "If you have an invitation secret, enter it here to get full access."
        ),
    )

    def clean_secret(self):
        data = self.cleaned_data["secret"].strip()
        if data and data not in settings.SIGNUP_SECRETS_WORDS:
            raise forms.ValidationError(
                _("Invalid secret: %(value)s"),
                params={"value": data},
            )
        return data

    def save(self, commit=True):
        user = super().save(commit=commit)
        if commit and self.cleaned_data.get("secret"):
            try:
                group = Group.objects.get(name=settings.COLLECTORS_GROUP_NAME)
                user.groups.add(group)
            except Group.DoesNotExist:
                pass
        return user
