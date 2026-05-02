import puppeteer from 'puppeteer-core';

const dryRun = process.argv.includes('--dry-run');
const browser = await puppeteer.connect({ browserURL: 'http://localhost:9222' });
const page = await browser.newPage();
await page.goto('https://x.com/home', { waitUntil: 'networkidle2' });
await new Promise(r => setTimeout(r, 1000));

// Click compose button to open modal
await page.waitForSelector('[data-testid="SideNav_NewTweet_Button"]', { timeout: 10000 });
await page.click('[data-testid="SideNav_NewTweet_Button"]');

// Wait for textarea in modal
await page.waitForSelector('[data-testid="tweetTextarea_0_label"]', { timeout: 10000 });
await new Promise(r => setTimeout(r, 500));

// Type using keyboard (X uses contenteditable div)
const tweetText = process.argv[2] || 'Hello from CDP!';
await page.focus('[data-testid="tweetTextarea_0_label"]');
await page.keyboard.type(tweetText, { delay: 100 });
await new Promise(r => setTimeout(r, 1000));

if (dryRun) {
  await page.screenshot({ path: 'x-dry-run.png', fullPage: false });
  console.log('Dry run: Text filled. Screenshot saved to x-dry-run.png');
} else {
  await page.click('[data-testid="tweetButton"]');
  await page.waitForSelector('[data-testid="tweetTextarea_0_label"]', { timeout: 10000 });
  console.log('Posted!');
}
await browser.disconnect();
