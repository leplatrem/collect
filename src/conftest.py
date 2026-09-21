import pytest
from django.core.cache import cache
from django.utils import translation


@pytest.fixture(autouse=True, scope="session")
def set_language():
    # `LANGUAGE_CODE` is not one of the `LANGUAGES` the URLs are prefixed with,
    # so a language has to be activated for URLs to reverse to existing paths.
    translation.activate("fr")
    yield
    translation.deactivate()


@pytest.fixture(autouse=True)
def clear_cache():
    """
    Start every test with an empty cache.

    Rate limit counters and thumbnail states live in the cache, which outlives
    a single test: without this, tests would influence each other depending on
    the order they run in.
    """
    cache.clear()
    yield
    cache.clear()
