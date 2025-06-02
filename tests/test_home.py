import pytest
from playwright.sync_api import Page


@pytest.mark.parametrize("username,password", [("testuser", "testpass")])
def test_login_and_check_version(page: Page, username, password):
    page.goto("/fr/accounts/login/")
    page.fill('input[name="username"]', username)
    page.fill('input[name="password"]', password)
    page.click('button[type="submit"]')

    # Successful login redirects to 'home', which redirects to 'collection:index'
    page.wait_for_url("/fr/collectable/")

    assert "Explorer" in (page.text_content("h1") or "")
