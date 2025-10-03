import pytest

from collectable.forms import DuplicateReportForm
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
