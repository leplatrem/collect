from urllib.parse import urlencode

from django import template
from django.conf import settings
from django.urls import reverse
from django.utils.html import format_html

from collectable.forms import PossessionForm


register = template.Library()


@register.inclusion_tag("collectable/possession_form.html", takes_context=True)
def user_possession_form(context, collectable):
    user = context["user"]
    possession = collectable.possession_of(user)
    form = PossessionForm(instance=possession)
    return {
        "user": user,
        "form": form,
    }


@register.simple_tag
def user_link(user, tab=None):
    """
    A username, linking to the collector's public profile.

    `tab` opens the profile on one of its tabs, eg. `{% user_link partner
    tab="swapped" %}` lands on the spares of a collector you could trade with.
    Unknown tab names fall back to the default one, like a hand-typed URL.

    Can be assigned with `as` to be interpolated in a `{% blocktranslate %}`.
    """
    if not user:
        return ""
    if not user.is_active:
        # eg. the placeholder that owns the reports of deleted accounts: it has
        # no profile page to link to.
        return str(user)
    url = reverse("user-profile", kwargs={"username": user.username})
    if tab:
        url = f"{url}?{urlencode({'tab': tab})}"
    return format_html('<a href="{}" class="user-link">{}</a>', url, str(user))


@register.filter(name="next_page_reveal_index")
def next_page_reveal_index(value):
    # Start loading the next page when second half of current page is revealed.
    return int(len(value) * settings.PAGE_REVEAL_LOAD_NEXT)


@register.simple_tag(takes_context=True)
def page_url(context, page_number):
    """
    URL of the given page, leaving the other query string parameters untouched
    (eg. search keywords, profile tab).
    """
    # requires 'django.template.context_processors.request' context processor
    params = context["request"].GET.copy()
    params["page"] = page_number
    return f"?{params.urlencode()}"


@register.simple_tag(takes_context=True)
def fullurl(context, path=""):
    """
    Returns the full absolute URL.
    """
    # requires 'django.template.context_processors.request' context processor
    request = context["request"]
    # Ensure path starts with '/'
    if not path.startswith("/"):
        path = "/" + path
    return request.build_absolute_uri(path)


@register.filter
def date_only(value):
    """Return only the date part of a datetime."""
    if not value:
        return ""
    return value.date() if hasattr(value, "date") else value
