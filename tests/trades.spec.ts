// @ts-check

import { test, expect } from "@playwright/test";

import {
  USERS,
  collectionUrls,
  login,
  logout,
  markPossession,
} from "./helpers";

/** The count shown next to a tab of the profile page. */
function tabCount(page, label: string) {
  return page
    .locator(".tab-labels a")
    .filter({ hasText: label })
    .locator(".tab-count");
}

/** The thumbnails of the tab currently shown on the profile page. */
function tabThumbnails(page) {
  return page.locator(".tab-panel .collectable.thumbnail > a");
}

/** The number a counter of the possession form shows. */
async function counted(counters, pattern: RegExp): Promise<number> {
  const text = (await counters.textContent()) ?? "";
  return Number(text.match(pattern)?.[1] ?? NaN);
}

/**
 * The last of the rubik collection, ordered by creation date: the duplicate
 * tests report the first ones, and a reported collectable no longer shows a
 * possession form.
 */
async function tradableUrls(page) {
  const urls = await collectionUrls(page, "rubik");
  return urls.slice(-3);
}

test("shows the marked collectables under the profile tabs", async ({
  page,
}) => {
  const [owned, wanted, spare] = await tradableUrls(page);

  await login(page, USERS.alice);
  await markPossession(page, owned, { owns: true });
  await markPossession(page, wanted, { wants: true });
  // A spare is something you own twice, so the mark comes with `owns`.
  await markPossession(page, spare, { owns: true, swaps: true });

  await page.goto("/en/collectable/profile/");
  await page.waitForURL("/en/user/alice/");

  await expect(tabCount(page, "Owned")).toHaveText("2");
  await expect(tabCount(page, "Wanted")).toHaveText("1");
  await expect(tabCount(page, "Spares")).toHaveText("1");
  await expect(tabCount(page, "Liked")).toHaveText("0");

  // Each tab is served on its own, and lists what it says.
  await expect(tabThumbnails(page)).toHaveCount(2);
  await page.goto("/en/user/alice/?tab=wanted");
  await expect(tabThumbnails(page)).toHaveCount(1);
  await expect(tabThumbnails(page).first()).toHaveAttribute(
    "href",
    new URL(wanted).pathname,
  );
  await page.goto("/en/user/alice/?tab=swapped");
  await expect(tabThumbnails(page).first()).toHaveAttribute(
    "href",
    new URL(spare).pathname,
  );

  // The counters of the collectable count her marks, whoever else marked it.
  await page.goto(spare);
  const counters = page.locator("#possession .counters");
  expect(await counted(counters, /(\d+) owners?/)).toBeGreaterThan(0);
  expect(await counted(counters, /(\d+) spares?/)).toBeGreaterThan(0);
});

test("saves marks clicked one right after the other", async ({ page }) => {
  const [url] = await tradableUrls(page);
  await login(page, USERS.partner);
  await page.goto(url);

  const posted = page.waitForResponse(
    (response) =>
      response.request().method() === "POST" &&
      response.url().includes("/possession/"),
  );

  // No waiting in between the two clicks: they used to be posted twice, and
  // saved in whatever order they were handled.
  const likes = page.locator(
    '#possession .possession-form input[name="likes"]',
  );
  await likes.focus();
  await likes.press(" ");
  const wants = page.locator(
    '#possession .possession-form input[name="wants"]',
  );
  await wants.focus();
  await wants.press(" ");

  // Both marks in one post, so the answer is the state of both.
  const request = (await posted).request();
  expect(request.postData()).toContain("likes=on");
  expect(request.postData()).toContain("wants=on");

  await page.goto(url);
  await expect(likes).toBeChecked();
  await expect(wants).toBeChecked();
});

test("pairs two collectors on the trades page", async ({ page }) => {
  const [, wanted, spare] = await tradableUrls(page);

  // Bob is the mirror of alice: he has a spare of what she is looking for,
  // and is looking for the one she has a spare of.
  await login(page, USERS.bob);
  await markPossession(page, wanted, { owns: true, swaps: true });
  await markPossession(page, spare, { wants: true });

  await page.goto("/en/collectable/trades/");
  const twoWay = page.locator("section", { hasText: "Two-way trades" });
  await expect(twoWay.getByRole("link", { name: "alice" })).toBeVisible();
  await expect(twoWay).toContainText("2 collectables to trade");

  // The other two lists are the one-way halves of that same trade.
  await expect(
    page
      .locator("section", { hasText: "They want your spares" })
      .getByRole("link", { name: "alice" }),
  ).toBeVisible();
  await expect(
    page
      .locator("section", { hasText: "They have spares you want" })
      .getByRole("link", { name: "alice" }),
  ).toBeVisible();

  // Alice sees the same trade from her side.
  await logout(page);
  await login(page, USERS.alice);
  await page.goto("/en/collectable/trades/");
  await expect(
    page
      .locator("section", { hasText: "Two-way trades" })
      .getByRole("link", { name: "bob" }),
  ).toBeVisible();

  // Her link to his spares lands on the tab that shows them.
  await page
    .locator("section", { hasText: "They have spares you want" })
    .getByRole("link", { name: "bob" })
    .click();
  await expect(page).toHaveURL("/en/user/bob/?tab=swapped");
  await expect(tabThumbnails(page).first()).toHaveAttribute(
    "href",
    new URL(wanted).pathname,
  );
});

test("leaves the trades page empty for a collector without matches", async ({
  page,
}) => {
  await login(page, USERS.partner);

  await page.goto("/en/collectable/trades/");

  await expect(page.getByText("No two-way trade yet.")).toBeVisible();
  await expect(
    page.getByText("Nobody is looking for your spares yet."),
  ).toBeVisible();
});
