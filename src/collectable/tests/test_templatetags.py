from django.template import Context, Template
from django.urls import reverse

from collectable.models import get_unknown_user
from collectable.tests.factories import UserFactory


def render(template_string, **context):
    return Template("{% load collectable_extras %}" + template_string).render(
        Context(context)
    )


def test_user_link_points_at_the_public_profile(db):
    user = UserFactory(username="collectomane")

    output = render("{% user_link user %}", user=user)

    url = reverse("user-profile", kwargs={"username": "collectomane"})
    assert output == f'<a href="{url}" class="user-link">collectomane</a>'


def test_user_link_opens_a_given_tab(db):
    user = UserFactory(username="collectomane")

    output = render('{% user_link user tab="swapped" %}', user=user)

    url = reverse("user-profile", kwargs={"username": "collectomane"})
    assert f'href="{url}?tab=swapped"' in output


def test_user_link_of_inactive_user_is_plain_text(db):
    # eg. the placeholder that owns the reports of deleted accounts.
    output = render("{% user_link user %}", user=get_unknown_user())

    assert output == "unknown"


def test_user_link_of_missing_user_is_empty():
    assert render("{% user_link user %}", user=None) == ""


def test_user_link_escapes_the_username(db):
    user = UserFactory(username="a<b>c")

    output = render("{% user_link user %}", user=user)

    assert ">a&lt;b&gt;c<" in output


def test_user_link_can_be_interpolated_in_a_translation(db):
    user = UserFactory(username="collectomane")

    output = render(
        "{% load i18n %}{% user_link user as link %}"
        "{% blocktranslate with who=link %}by {{ who }}{% endblocktranslate %}",
        user=user,
    )

    assert '<a href="' in output
    assert "collectomane</a>" in output
