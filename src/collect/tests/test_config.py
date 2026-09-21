from pathlib import Path

import pytest
from django.core.exceptions import ImproperlyConfigured

from collect.config import (
    DEVELOPMENT_SECRET_KEY,
    PUBLIC_SECRET_KEYS,
    checked_secret_key,
)


REPOSITORY_ROOT = Path(__file__).resolve().parents[3]


def test_secret_key_is_returned_as_is():
    assert checked_secret_key("a-private-value", debug=False) == "a-private-value"


def test_missing_secret_key_falls_back_in_debug():
    assert checked_secret_key("", debug=True) == DEVELOPMENT_SECRET_KEY


def test_published_secret_key_is_tolerated_in_debug():
    assert checked_secret_key("not-secret-yet", debug=True) == "not-secret-yet"


def test_missing_secret_key_is_refused():
    with pytest.raises(ImproperlyConfigured) as exc:
        checked_secret_key("", debug=False)

    assert "DJANGO_SECRET_KEY must be set" in str(exc.value)


@pytest.mark.parametrize("secret_key", sorted(PUBLIC_SECRET_KEYS))
def test_published_secret_key_is_refused(secret_key):
    with pytest.raises(ImproperlyConfigured) as exc:
        checked_secret_key(secret_key, debug=False)

    assert "published in the sources" in str(exc.value)


def test_secret_key_of_env_local_is_listed_as_published():
    content = (REPOSITORY_ROOT / "env.local").read_text()
    lines = [line.strip() for line in content.splitlines() if line.strip()]

    suggested = [
        line.split("=", 1)[1]
        for line in lines
        if line.startswith("DJANGO_SECRET_KEY=")  # Commented out lines excluded.
    ]
    assert all(key in PUBLIC_SECRET_KEYS for key in suggested), suggested
