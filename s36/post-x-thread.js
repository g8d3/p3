import puppeteer from 'puppeteer-core';
const browser = await puppeteer.connect({ browserURL: 'http://localhost:9222' });
const page = await browser.newPage();
await page.goto('https://x.com/home', { waitUntil: 'networkidle2' });
await page.waitForSelector('[data-testid="SideNav_NewTweet_Button"]');
await page.click('[data-testid="SideNav_NewTweet_Button"]');
await page.waitForSelector('[data-testid="tweetTextarea_0_label"]');

const tweets = process.argv.slice(2);
if (tweets.length === 0) tweets.push('Hello!');

for (let i = 0; i < tweets.length; i++) {
  const textarea = `[data-testid="tweetTextarea_${i}_label"]`;
  console.log(`Typing tweet ${i + 1}/${tweets.length}...`);
  await page.focus(textarea);
  await page.keyboard.type(tweets[i], { delay: 50 });
  if (i < tweets.length - 1) {
    await page.waitForSelector('[data-testid="addButton"]', { timeout: 5000 });
    await page.click('[data-testid="addButton"]');
    await new Promise(r => setTimeout(r, 500));
  }
}

if (process.argv.includes('--post')) { await page.click('[data-testid="tweetButton"]'); await new Promise(r => setTimeout(r, 3000)); console.log(`Posted thread with ${tweets.length} tweets!`); }
else { await page.screenshot({ path: 'x-thread.png' }); console.log(`Dry run: ${tweets.length} tweet(s). Screenshot saved.`); }
await browser.disconnect();
