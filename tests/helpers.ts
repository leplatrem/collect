// @ts-check

import { expect, type Page } from "@playwright/test";

/**
 * The accounts seeded by `make browser-test-server`.
 * `collector` and `partner` belong to the collectors group, so they can create
 * collectables and report duplicates. `alice` and `bob` are plain collectors
 * of the site: marking possessions needs no permission.
 */
export const USERS = {
  admin: { username: "admin", password: "s3cr3t" },
  collector: { username: "collector", password: "collectorpass" },
  partner: { username: "partner", password: "partnerpass" },
  alice: { username: "alice", password: "alicepass" },
  bob: { username: "bob", password: "bobpass" },
};

/** Any square image: the form rejects the ones that are not. */
const SQUARE_IMAGE = "demo/rubik/IMG_3270.jpg";

export async function login(
  page: Page,
  user: { username: string; password: string },
) {
  await page.goto("/en/accounts/login/");
  await page.fill('input[name="username"]', user.username);
  await page.fill('input[name="password"]', user.password);
  await page.getByRole("button", { name: /log in/i }).click();
  await page.waitForURL("/en/collectable/");
}

export async function logout(page: Page) {
  await page.goto("/en/collectable/");
  await page.getByRole("button", { name: /log out/i }).click();
  await expect(page.getByRole("link", { name: "Log In" })).toBeVisible();
}

/**
 * Create a collectable through the form, and return the URL of its details
 * page. The photo goes through the cropper, which computes its coordinates
 * from the file itself, so nothing else has to be filled in.
 */
export async function createCollectable(
  page: Page,
  { description, tags }: { description: string; tags: string[] },
): Promise<string> {
  await page.goto("/en/collectable/create/");
  await page.setInputFiles('input[name="photo"]', SQUARE_IMAGE);
  await page.fill('textarea[name="description"]', description);
  await page.fill('input[name="tags"]', tags.join(","));
  await page.check('input[name="rights_confirmed"]');
  await page.getByRole("button", { name: "Create" }).click();
  await page.waitForURL(/\/en\/collectable\/[0-9a-f-]{36}\//);
  return page.url();
}

/** The details URLs of the collectables of a collection, in page order. */
export async function collectionUrls(
  page: Page,
  slug: string,
): Promise<string[]> {
  await page.goto(`/en/collectable/collection/${slug}/`);
  const links = page.locator(".collectable.thumbnail > a");
  await expect(links.first()).toBeVisible();
  return links.evaluateAll((nodes) =>
    nodes.map((node) => (node as HTMLAnchorElement).href),
  );
}

/**
 * Tick the possession marks of the collectable shown on `url`. Each change is
 * posted on its own, so they are checked one at a time.
 *
 * Only the form of the `#possession` section: the related collectables shown
 * further down the details page carry one of their own.
 */
export async function markPossession(
  page: Page,
  url: string,
  marks: { likes?: boolean; wants?: boolean; owns?: boolean; swaps?: boolean },
) {
  for (const [name, wanted] of Object.entries(marks)) {
    // One mark per page load: the form swaps itself in after each post, and a
    // swap still on its way would detach the checkbox about to be pressed.
    await page.goto(url);
    const selector = `#possession .possession-form input[name="${name}"]`;
    // Toggled with the keyboard: the marks are icons with a tooltip, and the
    // tooltip of the one being pointed at covers it.
    const checkbox = page.locator(selector);
    await checkbox.focus();
    if ((await checkbox.isChecked()) === wanted) {
      continue; // Already marked, nothing to post.
    }
    // Every checkbox posts the whole form, so the next mark has to wait for
    // the answer to the previous one: two posts in flight at once would be
    // saved in whatever order they are handled.
    const posted = page.waitForResponse(
      (response) =>
        response.request().method() === "POST" &&
        response.url().includes("/possession/"),
    );
    await checkbox.press(" ");
    await posted;
    // The form swaps itself back in, as saved.
    await expect(page.locator(selector)).toBeChecked({ checked: wanted });
  }
}
