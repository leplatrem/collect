// @ts-check

import { test, expect } from "@playwright/test";

import { USERS, createCollectable, login } from "./helpers";

test("creates a collectable and lands on its details page", async ({
  page,
}) => {
  // A tag of this run only, so that the collection below holds this one
  // collectable whatever the database already had in it.
  const tag = `e2ecreate${Date.now()}`;
  const description = `Created by the browser tests ${tag}`;
  await login(page, USERS.collector);

  const url = await createCollectable(page, {
    description,
    tags: [tag, "rubik"],
  });

  await expect(page.getByText(/created successfully/i)).toBeVisible();
  await expect(page.locator("#photo img")).toBeVisible();
  // The details page of a collector opens on the edit form, filled in with
  // what was just submitted.
  await expect(page.locator('textarea[name="description"]')).toHaveValue(
    description,
  );
  await expect(page.locator('input[name="tags"]')).toHaveValue(
    new RegExp(`#${tag}.*#rubik|#rubik.*#${tag}`),
  );
  // Creating one counts as owning it. The related collectables further down
  // the page carry a possession form of their own, hence the section.
  await expect(
    page.locator('#possession .possession-form input[name="owns"]'),
  ).toBeChecked();

  // It is the newest one, so it comes first of the latest ones.
  const path = new URL(url).pathname;
  await page.goto("/en/collectable/latest/");
  await expect(
    page.locator(".collectable.thumbnail > a").first(),
  ).toHaveAttribute("href", path);

  // The home page shows it among them. Its sections pick the newest, the most
  // liked, and so on, but do not order what they show, so the position there
  // is not part of the contract.
  await page.goto("/en/collectable/");
  // Once under the latest ones, and once under the most owned.
  await expect(
    page.locator(`.collectable.thumbnail > a[href="${path}"]`),
  ).toHaveCount(2);

  // And it shows up in the collection of both of its tags.
  await page.goto(`/en/collectable/collection/${tag},rubik/`);
  await expect(page.locator(".collectable.thumbnail")).toHaveCount(1);
});

test("refuses a collectable whose rights are not confirmed", async ({
  page,
}) => {
  await login(page, USERS.collector);
  await page.goto("/en/collectable/create/");

  await page.setInputFiles('input[name="photo"]', "demo/rubik/IMG_3271.jpg");
  await page.fill('textarea[name="description"]', "Not mine to submit");
  const confirmation = page.locator('input[name="rights_confirmed"]');
  await expect(confirmation).toHaveAttribute("required", "");

  // The browser stops the submission on its own, so nothing is posted.
  await page.getByRole("button", { name: "Create" }).click();
  await expect(page).toHaveURL("/en/collectable/create/");
  await expect(page.getByText(/created successfully/i)).toHaveCount(0);

  // And the server refuses it too, for a client that skips that check.
  await confirmation.evaluate((field) => field.removeAttribute("required"));
  await page.getByRole("button", { name: "Create" }).click();

  await expect(page.getByText(/invalid fields/i)).toBeVisible();
  await expect(page).toHaveURL("/en/collectable/create/");
});

test("keeps the create page for collectors only", async ({ page }) => {
  await login(page, { username: "testuser", password: "testpass" });

  await expect(
    page.getByRole("link", { name: /create collectable/i }),
  ).toHaveCount(0);

  const response = await page.goto("/en/collectable/create/");
  expect(response?.status()).toBe(403);
});
