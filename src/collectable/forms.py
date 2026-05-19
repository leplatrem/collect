import urllib

from django.forms import (
    BooleanField,
    CharField,
    ModelForm,
    Textarea,
    TextInput,
    ValidationError,
)
from django.urls import Resolver404, resolve
from django.utils.translation import gettext_lazy as _

from collectable.models import UUID_REGEX, Collectable, DuplicateReport, Possession
from cropper.fields import CropImageField


class CollectableForm(ModelForm):
    photo = CropImageField()
    rights_confirmed = BooleanField(
        required=True,
        label=_("Rights confirmation"),
        help_text=_(
            "I confirm that I am the author of this photo, or that it is in the public "
            "domain, and that I have the right to submit it under the selected license."
        ),
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["photo"].widget.attrs.update({"accept": "image/jpeg"})
        self.fields["description"].widget.attrs.update(
            {"placeholder": _("Description, author, history, links to source, ...")}
        )
        # On edit, rights were already confirmed at creation time.
        if self.instance and self.instance.pk:
            del self.fields["rights_confirmed"]

    class Meta:
        model = Collectable
        fields = ["photo", "description", "tags", "license"]
        widgets = {
            "description": Textarea(attrs={"rows": "5"}),
        }


class PossessionForm(ModelForm):
    class Meta:
        model = Possession
        fields = ["likes", "wants", "owns"]


class DuplicateReportForm(ModelForm):
    original_input = CharField(
        label=_("Original"),
        widget=TextInput(attrs={"placeholder": _("ID or URL of the original")}),
    )

    class Meta:
        model = DuplicateReport
        fields = ["original_input"]

    def save(self, commit=True):
        instance = super().save(commit=False)
        if commit:
            instance.save()
        return instance

    def clean(self):
        cleaned_data = super().clean()
        if original := self.cleaned_data.get("original_input"):
            self.instance.original = original
        return cleaned_data

    def clean_original_input(self):
        original_input = self.cleaned_data["original_input"].strip()

        if not original_input:
            raise ValidationError(_("This field is required."))

        # Possibly the user entered a URL instead of an ID
        if UUID_REGEX.match(original_input):
            original_id = original_input

        # Possibly the user entered an ID instead of a URL
        elif original_input.startswith("http"):
            try:
                parsed = urllib.parse.urlparse(original_input)
            except ValueError:
                raise ValidationError(_("Enter a valid URL"))
            try:
                endpoint = resolve(parsed.path)
            except Resolver404:
                raise ValidationError(_("Enter a collectable URL"))
            if (
                "collectable" not in endpoint.namespaces
                or endpoint.url_name != "details"
            ):
                raise ValidationError(
                    _("The URL does not point to a collectable details page.")
                )
            original_id = endpoint.kwargs["id"]

        else:
            raise ValidationError(_("Enter a valid URL or ID."))

        # Check if RelatedModel exists
        try:
            original_obj = Collectable.objects.get(id=original_id)
        except Collectable.DoesNotExist:
            raise ValidationError("Related object not found.")

        return original_obj
