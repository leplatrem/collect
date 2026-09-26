from django.conf import settings
from django.utils.translation import gettext as _
from taggit.forms import TagWidget


class TagPillsWidget(TagWidget):
    """
    The comma-separated tags input, enhanced into removable pills, with
    completion and one-click chips for the most used tags.
    """

    template_name = "tags/widget.html"

    def __init__(self, get_vocabulary, attrs=None):
        """
        :param vocabulary: callable returning the tag names to complete from.
        """
        super().__init__(attrs)
        self.get_vocabulary = get_vocabulary

    def get_context(self, name, value, attrs):
        context = super().get_context(name, value, attrs)
        widget = context["widget"]
        vocabulary = list(self.get_vocabulary())
        popular = vocabulary[: settings.POPULAR_TAG_LIST_COUNT]
        widget["data"] = {
            "vocabulary": vocabulary,
            "popular": popular,
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
        js = ("tags/script.js",)
        css = {"all": ("tags/style.css",)}
