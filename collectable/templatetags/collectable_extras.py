from django import template

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
