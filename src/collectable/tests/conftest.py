import shutil
import tempfile

import pytest
from django.conf import settings
from django.core.management import call_command
from django.utils import translation

from collectable.tests.factories import (
    CollectableFactory,
    DuplicateReportFactory,
    PossessionFactory,
    UserFactory,
)


@pytest.fixture(scope="session", autouse=True)
def staticfiles():
    static_root = tempfile.mkdtemp(prefix="test_static")
    settings.STATIC_ROOT = static_root
    try:
        call_command("collectstatic", "--noinput")
        yield
    finally:
        shutil.rmtree(static_root)


@pytest.fixture(autouse=True, scope="session")
def set_language():
    translation.activate("fr")
    yield
    translation.deactivate()


@pytest.fixture
def user(db):
    return UserFactory()


@pytest.fixture
def collectable(db):
    return CollectableFactory()


@pytest.fixture
def duplicate_report(db):
    return DuplicateReportFactory()


@pytest.fixture
def possession(user, collectable):
    return PossessionFactory(user=user, collectable=collectable)


@pytest.fixture
def logged_in_client(client, user):
    client.force_login(user)
    client.user = user
    return client
