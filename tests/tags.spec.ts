// @ts-check

import { test, expect } from "@playwright/test";

test.beforeEach(async ({ page }) => {
  await page.goto("/en/accounts/login/");
  await page.fill('input[name="username"]', "collector");
  await page.fill('input[name="password"]', "collectorpass");
  await page.getByRole("button", { name: /log in/i }).click();
  await page.waitForURL("/en/collectable/");
  await page.goto("/en/collectable/create/");
});

test("shows the prefilled tags as pills", async ({ page }) => {
  const pills = page.locator(".tags-pill");

  await expect(pills).not.toHaveCount(0);
  // The field itself is what gets submitted, and keeps holding every tag.
  await expect(page.locator('input[name="tags"]')).toHaveAttribute(
    "type",
    "hidden",
  );
});

test("removes a tag by clicking its cross", async ({ page }) => {
  const first = page.locator(".tags-pill").first();
  const name = (await first.textContent())!.replace("×", "").trim();

  await first.getByRole("button").click();

  await expect(page.locator(".tags-pill", { hasText: name })).toHaveCount(0);
  const value = await page.locator('input[name="tags"]').inputValue();
  expect(value.split(", ")).not.toContain(name);
});

test("adds the highlighted suggestion", async ({ page }) => {
  await page.locator(".tags-entry").fill("stick");

  await expect(page.getByRole("option", { name: "stickers" })).toBeVisible();
  await page.locator(".tags-entry").press("ArrowDown");
  await page.locator(".tags-entry").press("Enter");

  await expect(page.locator(".tags-pill", { hasText: "stickers" })).toHaveCount(
    1,
  );
  expect(await page.locator('input[name="tags"]').inputValue()).toContain(
    "stickers",
  );
});

test("adds what was typed when no suggestion is highlighted", async ({
  page,
}) => {
  // Completion suggests, it never decides: a new tag that happens to be the
  // prefix of an existing one stays what it is.
  await page.locator(".tags-entry").fill("stick");
  await page.locator(".tags-entry").press("Enter");

  await expect(
    page.locator(".tags-pill", { hasText: /^stick×?$/ }),
  ).toHaveCount(1);
});

test("adds and removes a popular tag with one click", async ({ page }) => {
  const chip = page.locator(".tags-chip").first();
  const name = (await chip.textContent())!.trim();

  await chip.click();
  await expect(chip).toHaveAttribute("aria-pressed", "true");
  await expect(page.locator(".tags-pill", { hasText: name })).toHaveCount(1);

  await chip.click();
  await expect(chip).toHaveAttribute("aria-pressed", "false");
  await expect(page.locator(".tags-pill", { hasText: name })).toHaveCount(0);
});

test("keeps only what the server would keep of a typed tag", async ({
  page,
}) => {
  await page.locator(".tags-entry").fill("Hé! deux mots");
  await page.locator(".tags-entry").press("Enter");

  // `tags_splitter` splits on spaces and drops the rest.
  await expect(page.locator(".tags-pill", { hasText: /^H×?$/ })).toHaveCount(1);
  await expect(page.locator(".tags-pill", { hasText: "deux" })).toHaveCount(1);
  await expect(page.locator(".tags-pill", { hasText: "mots" })).toHaveCount(1);
});

test("works as a plain text field without javascript", async ({ browser }) => {
  const context = await browser.newContext({ javaScriptEnabled: false });
  const page = await context.newPage();
  await page.goto("/en/accounts/login/");
  await page.fill('input[name="username"]', "collector");
  await page.fill('input[name="password"]', "collectorpass");
  await page.getByRole("button", { name: /log in/i }).click();
  await page.goto("/en/collectable/create/");

  const input = page.locator('input[name="tags"]');
  await expect(input).toHaveAttribute("type", "text");
  await expect(page.locator(".tags-pill")).toHaveCount(0);

  await context.close();
});

test("commits a tag on Enter instead of saving the collectable", async ({
  page,
}) => {
  // The details form saves on Enter from any of its inputs, which would be a
  // trap for a field where Enter means "this tag is done".
  await page.goto("/en/collectable/");
  await page.locator(".collectable.thumbnail a").first().click();
  await page.waitForURL(/collectable\/[0-9a-f-]+\//);

  await page.locator(".tags-entry").fill("entered-tag");
  await page.locator(".tags-entry").press("Enter");

  await expect(
    page.locator(".tags-pill", { hasText: "entered-tag" }),
  ).toHaveCount(1);
  await expect(page.getByText(/updated successfully/i)).toHaveCount(0);
});
