import { test, expect } from '@playwright/test';

test('capture browser console logs and test app functionality', async ({ page }) => {
  // Listen to console messages
  page.on('console', (msg) => {
    console.log(`Browser console: ${msg.type()}: ${msg.text()}`);
  });

  // Listen to page errors
  page.on('pageerror', (error) => {
    console.log(`Browser page error: ${error.message}`);
  });

  // Navigate to the app
  await page.goto('/');

  // Wait for the app to load
  await page.waitForSelector('input[placeholder="Enter contract address"]');

  // Check title
  await expect(page).toHaveTitle(/React App/);

  // Test fetching contract info
  await page.fill('input[placeholder="Enter contract address"]', '0x1234567890123456789012345678901234567890'); // Dummy address
  await page.click('button:has-text("Fetch Contract Info")');

  // Wait for potential response
  await page.waitForTimeout(2000);

  // If contract info appears, test audit
  const contractInfoVisible = await page.locator('h2:has-text("Contract Info")').isVisible();
  if (contractInfoVisible) {
    await page.click('button:has-text("Run Audit")');
    await page.waitForTimeout(2000);

    // Then start protection
    await page.click('button:has-text("Start Protection")');
    await page.waitForTimeout(2000);
  }

  // Wait a bit more for all logs
  await page.waitForTimeout(3000);
});