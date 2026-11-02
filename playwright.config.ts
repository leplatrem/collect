import { defineConfig, devices } from '@playwright/test';

export default defineConfig({
  testDir: 'tests',
  use: {
    baseURL: 'http://127.0.0.1:8000',
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
