import puppeteer from 'puppeteer-core';
const browser = await puppeteer.connect({ browserURL: 'http://localhost:9222' });
const page = await browser.newPage();
await page.goto('https://x.com/home', { waitUntil: 'networkidle2' });
await page.waitForSelector('[data-testid="SideNav_NewTweet_Button"]');
await page.click('[data-testid="SideNav_NewTweet_Button"]');
await page.waitForSelector('[data-testid="tweetTextarea_0_label"]');
await page.focus('[data-testid="tweetTextarea_0_label"]');
await page.keyboard.type(process.argv[2] || 'Hello!', { delay: 50 });
if (process.argv.includes('--post')) { await page.click('[data-testid="tweetButton"]'); await new Promise(r => setTimeout(r, 3000)); console.log('Posted!'); }
else { await page.screenshot({ path: 'x-min.png' }); console.log('Dry run. Screenshot saved. Add --post to tweet.'); }
await browser.disconnect();
