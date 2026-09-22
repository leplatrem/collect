// @ts-check

import { test, expect } from "@playwright/test";

import { USERS, createCollectable, login } from "./helpers";

// A vocabulary of this run only, so that neither the demo data nor what an
// earlier run left behind can match by accident.
const STAMP = Date.now();
const NEEDLE = `e2eneedle${STAMP}`;
const HAYSTACK = `e2ehaystack${STAMP}`;
const DESCRIPTION = `A needle in a haystack of stickers ${STAMP}`;

let created: string;

test.beforeAll(async ({ browser }) => {
  const page = await browser.newPage();
  await login(page, USERS.collector);
  created = await createCollectable(page, {
    description: DESCRIPTION,
    tags: [NEEDLE, HAYSTACK],
  });
  await page.close();
});

/** Run a query straight on the search page, and return the results found. */
async function search(page, query: string) {
  await page.goto(`/en/collectable/search/?q=${encodeURIComponent(query)}`);
  const links = page.locator(".collectable.thumbnail > a");
  return {
    title: await page.locator("h1").textContent(),
    count: await links.count(),
    paths: await links.evaluateAll((nodes) =>
      nodes.map((node) => new URL((node as HTMLAnchorElement).href).pathname),
    ),
  };
}

test("finds a collectable by tag, by field and by phrase", async ({ page }) => {
  const path = new URL(created).pathname;

  for (const query of [
    `#${NEEDLE}`,
    `#e2eneedle${STAMP.toString().slice(0, -1)}*`,
    `description:"needle in a haystack of stickers ${STAMP}"`,
    // `tags:` is how a query asks for several tags at once.
    `tags:#${NEEDLE},#${HAYSTACK}`,
    `"in a haystack of stickers ${STAMP}"`,
    `#${NEEDLE} AND description:haystack`,
    `(#${NEEDLE} OR #nothinglikethis) AND NOT #duplicate`,
  ]) {
    const { title, paths } = await search(page, query);
    expect(title, `query: ${query}`).toContain(`Search results for '${query}'`);
    expect(paths, `query: ${query}`).toEqual([path]);
  }
});

test("excludes what the query says to exclude", async ({ page }) => {
  const path = new URL(created).pathname;

  // The two tags are on the same collectable, so asking for one without the
  // other matches nothing.
  const excluded = await search(page, `#${NEEDLE} AND NOT #${HAYSTACK}`);
  expect(excluded.count).toBe(0);
  await expect(page.getByText("0 collectables.")).toBeVisible();

  // `-` is the shorthand for NOT.
  const others = await search(page, `#rubik AND -#${NEEDLE}`);
  expect(others.count).toBeGreaterThan(0);
  expect(others.paths).not.toContain(path);

  // Every collectable of the demo data has tags, so this one finds none.
  const untagged = await search(page, "NOT #*");
  expect(untagged.count).toBe(0);
});

test("widens the results with OR", async ({ page }) => {
  const alone = await search(page, `#${NEEDLE}`);
  const wider = await search(page, `#${NEEDLE} OR #rubik`);

  expect(wider.count).toBeGreaterThan(alone.count);
  expect(wider.paths).toContain(new URL(created).pathname);
});

test("falls back to a basic search on an invalid query", async ({ page }) => {
  // A dangling operator is not a query the parser can compile, so the words
  // are searched for as they are typed.
  const { title } = await search(page, `${NEEDLE} AND`);

  expect(title).toContain("Basic search results");
});

test("searches from the box in the header", async ({ page }) => {
  await page.goto("/en/collectable/");

  // The box queries on a pause in the typing, so the keys have to be pressed
  // one by one for it to react at all.
  await page.locator('input[type="search"]').pressSequentially(`#${NEEDLE}`);

  await expect(page.locator("h1")).toContainText("Search results");
  await expect(page.locator(".collectable.thumbnail > a")).toHaveCount(1);
  // And the query lands in the address bar, so the results can be shared.
  await expect(page).toHaveURL(
    `/en/collectable/search/?q=${encodeURIComponent(`#${NEEDLE}`)}`,
  );
});
