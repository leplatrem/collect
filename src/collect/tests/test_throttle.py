import pytest
from django.contrib.auth.models import AnonymousUser
from django.http import HttpResponse
from django.test import RequestFactory, override_settings
from django.urls import reverse

from collect.throttle import client_ip, client_key, is_throttled, parse_rate, throttle


def request_from(path="/", method="get", remote_addr="10.0.0.1", **meta):
    request = getattr(RequestFactory(), method)(path, REMOTE_ADDR=remote_addr, **meta)
    request.user = AnonymousUser()
    return request


def test_parse_rate():
    assert parse_rate("20/300") == (20, 300)


@override_settings(THROTTLE_NUM_PROXIES=0)
def test_client_ip_without_proxy_is_the_peer_address():
    request = request_from(HTTP_X_FORWARDED_FOR="1.2.3.4")
    # No proxy configured, so the header is not ours and means nothing.
    assert client_ip(request) == "10.0.0.1"


@override_settings(THROTTLE_NUM_PROXIES=1)
def test_client_ip_behind_one_proxy():
    request = request_from(HTTP_X_FORWARDED_FOR="1.2.3.4")
    assert client_ip(request) == "1.2.3.4"


@override_settings(THROTTLE_NUM_PROXIES=1)
def test_client_ip_ignores_addresses_forged_by_the_client():
    # The client sent "9.9.9.9" itself; our proxy appended the address it saw.
    request = request_from(HTTP_X_FORWARDED_FOR="9.9.9.9, 1.2.3.4")
    assert client_ip(request) == "1.2.3.4"


@override_settings(THROTTLE_NUM_PROXIES=2)
def test_client_ip_falls_back_when_there_are_fewer_hops_than_expected():
    request = request_from(HTTP_X_FORWARDED_FOR="9.9.9.9")
    assert client_ip(request) == "10.0.0.1"


@override_settings(THROTTLE_NUM_PROXIES=1)
def test_client_ip_without_header():
    assert client_ip(request_from()) == "10.0.0.1"


def test_client_key_of_anonymous_user():
    assert client_key(request_from()) == "ip:10.0.0.1"


def test_client_key_of_logged_in_user(db, django_user_model):
    user = django_user_model.objects.create(username="someone")
    request = request_from()
    request.user = user
    # Logged in users are counted individually.
    assert client_key(request) == f"user:{user.pk}"


def test_is_throttled_counts_requests():
    request = request_from()
    assert [is_throttled(request, "scope", "3/60") for _ in range(5)] == [
        False,
        False,
        False,
        True,
        True,
    ]


def test_is_throttled_counts_callers_separately():
    for _ in range(3):
        assert not is_throttled(request_from(remote_addr="10.0.0.1"), "s", "3/60")

    assert is_throttled(request_from(remote_addr="10.0.0.1"), "s", "3/60")
    assert not is_throttled(request_from(remote_addr="10.0.0.2"), "s", "3/60")


def test_is_throttled_counts_scopes_separately():
    for _ in range(3):
        is_throttled(request_from(), "one", "3/60")

    assert is_throttled(request_from(), "one", "3/60")
    assert not is_throttled(request_from(), "two", "3/60")


@pytest.mark.parametrize("rate", ["0/60", "10/0"])
def test_is_throttled_disabled(rate):
    assert not any(is_throttled(request_from(), "scope", rate) for _ in range(20))


def test_throttle_decorator_lets_requests_through():
    view = throttle("scope", "THROTTLE_LOGIN")(lambda request: HttpResponse(b"ok"))

    with override_settings(THROTTLE_LOGIN="2/60"):
        assert view(request_from(method="post")).status_code == 200
        assert view(request_from(method="post")).status_code == 200
        response = view(request_from(method="post"))

    assert response.status_code == 429
    assert response["Retry-After"] == "60"


def test_throttle_decorator_ignores_other_methods():
    view = throttle("scope", "THROTTLE_LOGIN", methods=("POST",))(
        lambda request: HttpResponse(b"ok")
    )

    with override_settings(THROTTLE_LOGIN="1/60"):
        statuses = [view(request_from(method="get")).status_code for _ in range(5)]

    assert statuses == [200] * 5


@override_settings(THROTTLE_LOGIN="2/60")
def test_login_is_throttled(db, client):
    url = reverse("auth:login")
    credentials = {"username": "someone", "password": "guessing"}

    statuses = [client.post(url, credentials).status_code for _ in range(3)]

    # Password guessing stops being practical.
    assert statuses[-1] == 429
    assert statuses[:-1] == [200, 200]


@override_settings(THROTTLE_LOGIN="2/60")
def test_login_page_can_still_be_displayed_when_throttled(db, client):
    url = reverse("auth:login")
    for _ in range(3):
        client.post(url, {"username": "someone", "password": "guessing"})

    assert client.get(url).status_code == 200


@override_settings(THROTTLE_SIGNUP="1/3600")
def test_signup_is_throttled(db, client):
    url = reverse("accounts:signup")
    data = {
        "username": "newcomer",
        "password1": "a-long-enough-password",
        "password2": "a-long-enough-password",
    }

    assert client.post(url, data).status_code == 302
    assert client.post(url, {**data, "username": "another"}).status_code == 429


@override_settings(THROTTLE_SEARCH="2/60")
def test_search_is_throttled(db, client):
    url = reverse("collectable:search")

    statuses = [client.get(url, {"q": "anything"}).status_code for _ in range(3)]

    assert statuses == [200, 200, 429]
