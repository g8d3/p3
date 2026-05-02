import puppeteer from 'puppeteer-core';
import fs from 'fs';
import path from 'path';

const args = process.argv.slice(2);
const reuse = args.includes('--reuse');
const post = args.includes('--post');

// Parse --tweet and --media flags for per-tweet media
const tweets = [];
let current = { text: '', media: [] };
for (let i = 0; i < args.length; i++) {
  if (args[i] === '--tweet' && args[i + 1]) {
    if (current.text || current.media.length) tweets.push(current);
    current = { text: args[++i], media: [] };
  } else if (args[i] === '--media' && args[i + 1]) {
    while (args[i + 1] && !args[i + 1].startsWith('--')) current.media.push(args[++i]);
  }
}
if (current.text || current.media.length) tweets.push(current);
if (tweets.length === 0) tweets.push({ text: 'Hello!', media: [] });

const browser = await puppeteer.connect({ browserURL: 'http://localhost:9222' });
let page;

if (reuse) {
  const pages = await browser.pages();
  page = pages.find(p => p.url().includes('x.com')) || pages[0] || await browser.newPage();
} else {
  page = await browser.newPage();
}

await page.setViewport({ width: 1280, height: 800 });
await page.goto('https://x.com/home', { waitUntil: 'networkidle2' });
await page.waitForSelector('[data-testid="SideNav_NewTweet_Button"]');
await page.click('[data-testid="SideNav_NewTweet_Button"]');
await page.waitForSelector('[data-testid="tweetTextarea_0_label"]');

async function typeTweet(index, text) {
  await page.focus(`[data-testid="tweetTextarea_${index}_label"]`);
  if (text) await page.keyboard.type(text, { delay: 50 });
}

async function uploadMedia(files) {
  if (!files.length) return;
  const resolved = files.map(f => path.resolve(f));
  // Listen for file chooser event (prevents native dialog from opening)
  const [fileChooser] = await Promise.all([
    page.waitForFileChooser({ timeout: 5000 }),
    (async () => {
      const btn = await page.evaluateHandle(() => document.querySelector('button[aria-label="Add photos or video"]'));
      await btn.click();
    })()
  ]);
  await fileChooser.accept(resolved);
  console.log(`  Uploaded ${files.length} media`);
  await new Promise(r => setTimeout(r, 1500));
}

for (let i = 0; i < tweets.length; i++) {
  const { text, media } = tweets[i];
  console.log(`Tweet ${i + 1}/${tweets.length}: "${text.slice(0, 40)}${text.length > 40 ? '...' : ''}"${media.length ? ` + ${media.length} media` : ''}`);
  await typeTweet(i, text);
  await new Promise(r => setTimeout(r, 300));
  if (media.length) await uploadMedia(media);
  if (i < tweets.length - 1) {
    await page.waitForSelector('[data-testid="addButton"]', { timeout: 5000 });
    await page.click('[data-testid="addButton"]');
    await new Promise(r => setTimeout(r, 500));
  }
}

if (post) {
  await page.click('[data-testid="tweetButton"]');
  await new Promise(r => setTimeout(r, 3000));
  console.log('Posted!');
} else {
  await page.screenshot({ path: 'x-thread.png' });
  console.log(`Dry run: ${tweets.length} tweet(s). Screenshot saved.`);
}

if (!reuse) await browser.disconnect();
else console.log('Browser kept open (--reuse).');
