from django.conf import settings
from django.db.models import Count, Q
from django.utils.translation import gettext as _
from taggit.forms import TagWidget
from taggit.models import Tag


class TagPillsWidget(TagWidget):
    """
    The comma-separated tags input, enhanced into removable pills, with
    completion and one-click chips for the most used tags.

    The vocabulary is small enough to be shipped with the page, so completion
    needs no endpoint of its own. The text input remains the only thing that
    gets submitted, so the field still works, as a plain comma-separated one,
    when the script does not run.
    """

    template_name = "collectable/tags_widget.html"

    def get_context(self, name, value, attrs):
        context = super().get_context(name, value, attrs)
        widget = context["widget"]
        # Most used first: completion offers the whole vocabulary, in that
        # order, and the chips only its head.
        vocabulary = list(
            Tag.objects.annotate(
                ncollectable=Count("collectable", filter=Q(collectable__hidden=False))
            )
            .filter(ncollectable__gt=0)
            .order_by("-ncollectable", "name")
            .values_list("name", flat=True)[: settings.TAG_COMPLETION_LIST_COUNT]
        )
        # The script builds every control it needs from this payload, rather
        # than from markup that would be dead weight without it. Labels are
        # translated here, where gettext knows the active language.
        widget["data"] = {
            "vocabulary": vocabulary,
            "popular": vocabulary[: settings.POPULAR_TAG_LIST_COUNT],
            "labels": {
                "remove": _("Remove tag %(tag)s"),
                "added": _("Added tag %(tag)s"),
                "removed": _("Removed tag %(tag)s"),
                "placeholder": _("Add a tag..."),
                "popular": _("Most used tags:"),
                "suggestions": _("Tag suggestions"),
            },
        }
        widget["data_id"] = f"{widget['attrs'].get('id', name)}-data"
        return context

    class Media:
        js = ("collectable/tags.js",)
        css = {"all": ("collectable/tags.css",)}
