// @ts-check

import { test, expect } from "@playwright/test";

import { USERS, collectionUrls, login, logout } from "./helpers";

test("reports a duplicate, and has it confirmed by another collector", async ({
  page,
}) => {
  await login(page, USERS.collector);
  const [duplicateUrl, originalUrl] = await collectionUrls(page, "rubik");

  await page.goto(duplicateUrl);
  await page.fill(
    '#report-duplicate input[name="original_input"]',
    originalUrl,
  );
  await page
    .locator("#report-duplicate")
    .getByRole("button", { name: "Report" })
    .click();

  // The report swaps the duplicate page in, in place of the details.
  await expect(page.getByRole("heading", { name: "Duplicate" })).toBeVisible();
  await expect(page.getByText(/duplicate reported/i)).toBeVisible();

  // From now on, the collectable opens on its duplicate page.
  await page.goto(duplicateUrl);
  await expect(page.getByRole("heading", { name: "Duplicate" })).toBeVisible();
  await expect(
    page.getByText(/has been reported as a duplicate of/),
  ).toBeVisible();
  await expect(page.locator("#attributes")).toContainText("collector");
  // The threshold counts the collectors other than the reporter.
  await expect(
    page.getByText(/2 more confirmations before merging/),
  ).toBeVisible();
  // Its own reporter has nothing to confirm, only a report to cancel.
  await expect(page.getByRole("button", { name: "Cancel" })).toBeVisible();
  await expect(page.getByRole("button", { name: "Confirm" })).toHaveCount(0);

  await logout(page);
  await login(page, USERS.partner);
  await page.goto(duplicateUrl);

  await page.getByRole("button", { name: "Confirm" }).click();

  await expect(page.getByText(/duplicate reported/i)).toBeVisible();
  await expect(
    page.getByText(/1 more confirmation before merging/),
  ).toBeVisible();
  // Both reports are listed, and this one is now the confirming collector's.
  await expect(page.locator("#attributes")).toContainText("collector");
  await expect(page.locator("#attributes")).toContainText("partner");
  await expect(page.getByRole("button", { name: "Cancel" })).toBeVisible();

  // The original is untouched, and still reachable on its own.
  await page.goto(originalUrl);
  await expect(page.getByRole("heading", { name: "Details" })).toBeVisible();
});

test("merges the duplicate into the original once the threshold is reached", async ({
  page,
}) => {
  // A pair of its own, so that the report count does not depend on the
  // other tests.
  const urls = await collectionUrls(page, "stickers");
  const [duplicateUrl, originalUrl] = [urls[0], urls[1]];

  for (const user of [USERS.collector, USERS.partner, USERS.admin]) {
    await login(page, user);
    await page.goto(duplicateUrl);
    const report = page.locator("#report-duplicate");
    if (await report.count()) {
      await page.fill(
        '#report-duplicate input[name="original_input"]',
        originalUrl,
      );
      await report.getByRole("button", { name: "Report" }).click();
    } else {
      await page.getByRole("button", { name: "Confirm" }).click();
    }
    // Reported, so this collector is offered to cancel from now on.
    await expect(page.getByRole("button", { name: "Cancel" })).toBeVisible();
    await logout(page);
  }

  // Merged: the duplicate is hidden, so its details are gone for good.
  const response = await page.goto(duplicateUrl);
  expect(response?.status()).toBe(404);

  // Its duplicate page says where it went, and sends the visitor there.
  await page.goto(`${duplicateUrl}duplicate/`);
  await expect(
    page.getByText(/has been hidden as it was reported/),
  ).toBeVisible();
  await expect(page).toHaveURL(originalUrl);

  // And a hidden collectable is out of the collection it was in.
  const remaining = await collectionUrls(page, "stickers");
  expect(remaining).not.toContain(duplicateUrl);
  expect(remaining).toContain(originalUrl);
  expect(remaining).toHaveLength(urls.length - 1);
});
