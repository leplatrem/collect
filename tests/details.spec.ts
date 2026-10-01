// @ts-check

import { test, expect } from "@playwright/test";

test.beforeEach(async ({ page }) => {
  await page.goto("/en/accounts/login/");
  await page.fill('input[name="username"]', "collector");
  await page.fill('input[name="password"]', "collectorpass");
  await page.getByRole("button", { name: /log in/i }).click();
  await page.waitForURL("/en/collectable/");
  await page.locator(".collectable.thumbnail a").first().click();
  await page.waitForURL(/collectable\/[0-9a-f-]+\//);
});

test("saves on ctrl/cmd + enter from a text field", async ({ page }) => {
  await page.locator('textarea[name="description"]').fill("Saved by shortcut");

  await page
    .locator('textarea[name="description"]')
    .press("ControlOrMeta+Enter");

  await expect(page.getByText(/updated successfully/i)).toBeVisible();
  await expect(page.locator('textarea[name="description"]')).toHaveValue(
    "Saved by shortcut",
  );
});

test("saves on ctrl/cmd + enter from any other field", async ({ page }) => {
  // The shortcut is bound to the form, which every field's keyup reaches,
  // rather than to the text inputs only.
  const select = page.locator('select[name="license"]');
  await select.focus();

  await select.press("ControlOrMeta+Enter");

  await expect(page.getByText(/updated successfully/i)).toBeVisible();
});

test("does not save on enter alone", async ({ page }) => {
  // Enter in a single-line input would submit the form natively, which the
  // page has to prevent: nothing must reach the server here.
  let posted = false;
  page.on("request", (request) => {
    posted = posted || request.method() === "POST";
  });
  await page.locator('input[name="copies_count"]').fill("3");

  await page.locator('input[name="copies_count"]').press("Enter");
  await page.waitForTimeout(500);

  expect(posted).toBe(false);
  await expect(page.getByText(/updated successfully/i)).toHaveCount(0);
});
