import pytest

from collectable.forms import DuplicateReportForm, PossessionForm
from collectable.models import Possession
from collectable.tests.factories import CollectableFactory, UserFactory


@pytest.mark.django_db
def test_duplicate_report_form_with_valid_id(collectable):
    form = DuplicateReportForm(data={"original_input": str(collectable.id)})
    form.instance.duplicate = CollectableFactory()
    form.instance.reporter = UserFactory()
    assert form.is_valid(), form.errors
    report = form.save()
    assert report.original == collectable


@pytest.mark.django_db
def test_duplicate_report_form_with_valid_url(collectable):
    url = f"http://testserver/fr/collectable/{collectable.id}/"
    form = DuplicateReportForm(data={"original_input": url})
    form.instance.duplicate = CollectableFactory()
    form.instance.reporter = UserFactory()
    assert form.is_valid(), form.errors
    report = form.save()
    assert report.original == collectable


@pytest.mark.django_db
@pytest.mark.parametrize(
    "input_data, error_msg",
    [
        ("", "Ce champ est obligatoire"),
        ("not-a-url-or-id", "Saisir une URL valide"),
        ("http://testserver/invalid/path/", "Saisir l'URL d'un objet"),
        (
            "http://testserver/fr/collectable/00000000-0000-0000-0000-000000000000/",
            "Related object not found.",
        ),
        (
            "http://testserver/fr/collectable/00000000-0000-0000-0000-000000000000/duplicate/",
            "Cette URL ne pointe pas vers la page détail d'un objet",
        ),
    ],
)
def test_duplicate_report_form_invalid(input_data, error_msg):
    form = DuplicateReportForm(data={"original_input": input_data})
    assert not form.is_valid()
    assert error_msg in str(form.errors["original_input"][0])


@pytest.mark.django_db
def test_possession_form_disables_swaps_when_not_owned(collectable):
    form = PossessionForm(instance=Possession(collectable=collectable, owns=False))
    assert form.fields["swaps"].disabled is True
    assert "disabled" in str(form["swaps"])


@pytest.mark.django_db
def test_possession_form_explains_why_swaps_is_disabled(collectable):
    # The tooltip is the only affordance: the icon alone cannot say why.
    disabled = PossessionForm(instance=Possession(collectable=collectable, owns=False))
    enabled = PossessionForm(instance=Possession(collectable=collectable, owns=True))
    assert "possédé" in str(disabled.fields["swaps"].help_text)
    assert disabled.fields["swaps"].help_text != enabled.fields["swaps"].help_text


@pytest.mark.django_db
def test_possession_form_enables_swaps_when_owned(collectable):
    form = PossessionForm(instance=Possession(collectable=collectable, owns=True))
    assert form.fields["swaps"].disabled is False
    assert "disabled" not in str(form["swaps"])


@pytest.mark.django_db
def test_possession_form_ignores_swaps_when_not_owned(user, collectable):
    possession = Possession(user=user, collectable=collectable, owns=False)
    form = PossessionForm({"owns": False, "swaps": True}, instance=possession)
    assert form.is_valid(), form.errors
    assert form.save().swaps is False
