import urllib

from django.forms import ModelForm, TextInput, ValidationError
from django.urls import Resolver404, resolve
from django.utils.translation import gettext_lazy as _

from collectable.models import UUID_REGEX, Collectable, DuplicateReport, Possession
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


class DuplicateReportForm(ModelForm):
    class Meta:
        model = DuplicateReport
        fields = ["original"]
        widgets = {
            "original": TextInput(attrs={"placeholder": "URL or ID of the original"}),
        }

    def clean(self):
        cleaned_data = super().clean()
        original_input = self.data.get("original", "").strip()

        if not original_input:
            raise ValidationError(_("This field is required."))

        # Possibly the user entered a URL instead of an ID
        if isinstance(original_input, str) and original_input.startswith("http"):
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
            original_obj = Collectable.objects.filter(id=original_id).first()
            if not original_obj:
                raise ValidationError(_("No collectable found at the given URL."))

        # Possibly the user entered an ID instead of a URL
        elif isinstance(original_input, str) and UUID_REGEX.match(original_input):
            original_obj = Collectable.objects.filter(id=original_input).first()
            if not original_obj:
                raise ValidationError(_("No collectable found with this ID."))
        else:
            raise ValidationError(_("Enter a valid URL or ID."))

        cleaned_data["original"] = original_obj
        return cleaned_data
