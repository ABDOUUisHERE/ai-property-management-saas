import { defineConfig } from '@playwright/test';

export default defineConfig({
  testDir: './e2e',
  timeout: 15000,
  workers: 1,
  use: {
    baseURL: 'http://127.0.0.1:18173',
    browserName: 'chromium',
    viewport: { width: 1360, height: 900 },
  },
});
