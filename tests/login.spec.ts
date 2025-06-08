// @ts-check

import { test, expect } from '@playwright/test';

test('redirects to collectables index on success', async ({ page }) => {
  await page.goto("/");
  await page.getByRole('link', { name: 'Log In' }).click();
  await page.waitForURL("/en/accounts/login/");

  await page.fill('input[name="username"]', "testuser");
  await page.fill('input[name="password"]', "testpass");
  await page.getByRole('button', { name: /log in/i }).click();

  await page.waitForURL("/en/collectable/");
  await expect(page.getByRole('heading', { name: 'Explore' })).toBeVisible();
});
