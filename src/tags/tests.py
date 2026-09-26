import json
import re

from django.forms import Form
from taggit.forms import TagField

from tags.widgets import TagPillsWidget


def extract_data(rendered):
    """The JSON the script reads everything it builds from."""
    return json.loads(
        re.search(
            r'<script id="id_tags-data" type="application/json">(.*?)</script>',
            rendered,
            re.DOTALL,
        ).group(1)
    )


def render(vocabulary, initial=None):
    class TaggedForm(Form):
        tags = TagField(
            widget=TagPillsWidget(lambda: vocabulary, attrs={"autocapitalize": "none"}),
            initial=initial,
        )

    return TaggedForm()["tags"].as_widget()


def test_widget_ships_the_vocabulary_and_offers_its_head(settings):
    settings.POPULAR_TAG_LIST_COUNT = 2

    data = extract_data(render(["common", "usual", "rare"]))

    assert data["vocabulary"] == ["common", "usual", "rare"]
    assert data["popular"] == ["common", "usual"]


def test_widget_ships_its_labels():
    data = extract_data(render([]))

    assert "%(tag)s" in data["labels"]["remove"]
    assert set(data["labels"]) == {
        "remove",
        "added",
        "removed",
        "placeholder",
        "popular",
        "suggestions",
    }


def test_widget_renders_a_plain_text_input():
    """Test that plain text gets enhanced but still runs without JS."""
    rendered = render(["known"], initial="first, second")

    assert 'type="text"' in rendered
    assert 'name="tags"' in rendered
    assert "first, second" in rendered
    assert 'autocapitalize="none"' in rendered
