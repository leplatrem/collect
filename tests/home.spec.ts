// @ts-check

import { test, expect } from '@playwright/test';

test('is alive', async ({ request }) => {
  const resp = await request.get('/health/');

  expect(resp.ok()).toBeTruthy();
  expect(await resp.json()).toEqual({ "status": "ok" });
});

test('is ready', async ({ request }) => {
  const resp = await request.get('/readiness/');

  expect(resp.ok()).toBeTruthy();
  expect(await resp.json()).toEqual({ "status": "ok" });
});

test('root redirects to collectables index', async ({ page }) => {
  await page.goto("/");
  await page.waitForURL("/en/collectable/");
});
