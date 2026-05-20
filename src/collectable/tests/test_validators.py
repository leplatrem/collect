from unittest.mock import Mock

import pytest
from django.conf import settings
from django.core.exceptions import ValidationError

from collectable.validators import MaxFileSizeValidator


def test_max_file_size_validator_message_format():
    fieldfile = Mock()
    fieldfile.size = settings.COLLECTABLE_MAX_UPLOAD_BYTES + 1
    fieldfile.__str__ = lambda self: "photo.jpg"

    with pytest.raises(ValidationError) as exc:
        MaxFileSizeValidator()(fieldfile)

    message = exc.value.messages[0]
    # Placeholders must be interpolated, not left as literal template syntax.
    assert "{{" not in message
    assert "photo.jpg" in message
    assert str(settings.COLLECTABLE_MAX_UPLOAD_BYTES) in message
