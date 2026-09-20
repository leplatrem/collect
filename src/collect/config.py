"""
Helpers to validate the configuration, called from `collect.settings`.

Kept free of any import.
"""

from django.core.exceptions import ImproperlyConfigured


# Secret keys that ship with the sources (``env.local``)
PUBLIC_SECRET_KEYS = frozenset(
    [
        "not-secret",
        "not-secret-yet",
        "insecure-development-key",
    ]
)

DEVELOPMENT_SECRET_KEY = "insecure-development-key"


def checked_secret_key(secret_key, debug, published=PUBLIC_SECRET_KEYS):
    """
    Return the secret key to use, refusing to run unsafely.
    """
    if debug:
        return secret_key or DEVELOPMENT_SECRET_KEY

    if not secret_key:
        raise ImproperlyConfigured(
            "DJANGO_SECRET_KEY must be set when DJANGO_DEBUG is off. "
            "Generate one with: "
            "python -c 'import secrets; print(secrets.token_urlsafe(64))'"
        )
    if secret_key in published:
        raise ImproperlyConfigured(
            "DJANGO_SECRET_KEY is set to a value published in the sources of "
            "this project, which would let anyone forge session cookies and "
            "password reset tokens. Set a private random value instead: "
            "python -c 'import secrets; print(secrets.token_urlsafe(64))'"
        )
    return secret_key
