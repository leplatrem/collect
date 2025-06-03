import pytest
from playwright.sync_api import Page


def test_health_check(page: Page):
    page.goto("/health/")
    assert "ok" in (page.text_content("body") or "")


def test_readiness_check(page: Page):
    page.goto("/readiness/")
    assert "ok" in (page.text_content("body") or "")


def test_home_redirect(page: Page):
    page.goto("/")
    # Redirects to 'collection:index'
    page.wait_for_url("/en/collectable/")


@pytest.mark.parametrize("username,password", [("testuser", "testpass")])
def test_login_and_check_version(page: Page, username, password):
    page.goto("/en/accounts/login/")
    page.fill('input[name="username"]', username)
    page.fill('input[name="password"]', password)
    page.click('button[type="submit"]')

    # Successful login redirects to 'home', which redirects to 'collection:index'
    page.wait_for_url("/en/collectable/")

    assert "Explore" in (page.text_content("h1") or "")
