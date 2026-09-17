import { defineConfig } from '@playwright/test'

// Drives the Chrome already installed on the machine rather than a downloaded bundle, so the
// suite runs without reaching cdn.playwright.dev. Swap to 'msedge' if Chrome isn't present.
const CHANNEL = 'chrome'

export default defineConfig({
  testDir: './e2e',
  timeout: 30_000,
  expect: { timeout: 7_000 },
  // One worker: every test signs up its own business, but they share one API process.
  workers: 1,
  reporter: [['list']],
  use: {
    baseURL: 'http://localhost:5173',
    channel: CHANNEL,
    trace: 'retain-on-failure',
    screenshot: 'only-on-failure',
  },
  projects: [
    { name: 'desktop', use: { channel: CHANNEL, viewport: { width: 1280, height: 900 } } },
    // The narrowest phone the design targets; the layout must not scroll sideways here.
    { name: 'phone', use: { channel: CHANNEL, viewport: { width: 390, height: 844 } } },
  ],
})
