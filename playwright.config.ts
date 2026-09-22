import { defineConfig, devices } from '@playwright/test';

export default defineConfig({
  testDir: 'tests',
  // The specs share the database of the app they run against: they create
  // collectables, report duplicates and mark possessions, which a spec
  // running beside them would see appear under its feet.
  workers: 1,
  use: {
    baseURL: 'http://localhost:8000',
    screenshot: 'on',
    viewport: { width: 1280, height: 720 },
    locale: 'en-US',
  },
  projects: [
    {
      name: 'firefox',
      use: { ...devices['Desktop Firefox'] },
    },
  ]
});
