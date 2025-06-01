import pytest
from playwright.sync_api import Page


@pytest.mark.parametrize("username,password", [("testuser", "testpass")])
def test_login_and_check_version(page: Page, username, password):
    page.goto("/login/")
    page.fill('input[name="username"]', username)
    page.fill('input[name="password"]', password)
    page.click('button[type="submit"]')

    # Assumes successful login redirects to home
    page.wait_for_url("/")

    # Dummy assertion: check for version text on homepage
    assert "Version 1.0" in page.text_content("body")
