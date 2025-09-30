from django import template
from django.conf import settings

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


@register.filter(name="next_page_reveal_index")
def next_page_reveal_index(value):
    # Start loading the next page when second half of current page is revealed.
    return int(len(value) * settings.PAGE_REVEAL_LOAD_NEXT)


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
