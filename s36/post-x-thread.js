import puppeteer from 'puppeteer-core';
import fs from 'fs';
import path from 'path';

const browser = await puppeteer.connect({ browserURL: 'http://localhost:9222' });
const page = await browser.newPage();
await page.goto('https://x.com/home', { waitUntil: 'networkidle2' });
await page.waitForSelector('[data-testid="SideNav_NewTweet_Button"]');
await page.click('[data-testid="SideNav_NewTweet_Button"]');
await page.waitForSelector('[data-testid="tweetTextarea_0_label"]');

// Parse args: files are media, rest are text
const isMedia = (arg) => fs.existsSync(arg) && /\.(jpg|jpeg|png|gif|webp|mp4|mov|webm)$/i.test(arg);
const args = process.argv.slice(2);
const mediaFiles = args.filter(isMedia);
const tweetTexts = args.filter(a => !isMedia(a));
if (tweetTexts.length === 0) tweetTexts.push('');

// Type text into tweet textarea
async function typeTweet(index, text) {
  await page.focus(`[data-testid="tweetTextarea_${index}_label"]`);
  if (text) await page.keyboard.type(text, { delay: 50 });
}

// Upload media files to current tweet
async function uploadMedia(files) {
  if (!files.length) return;
  const btn = await page.evaluateHandle(() => document.querySelector('button[aria-label="Add photos or video"]'));
  await btn.click();
  await new Promise(r => setTimeout(r, 500));
  const input = await page.$('input[type="file"]');
  if (input) {
    await input.uploadFile(...files.map(f => path.resolve(f)));
    console.log(`Uploaded ${files.length} media file(s)`);
    await new Promise(r => setTimeout(r, 2000));
  }
}

// Build thread
for (let i = 0; i < tweetTexts.length; i++) {
  console.log(`Tweet ${i + 1}/${tweetTexts.length}...`);
  await typeTweet(i, tweetTexts[i]);
  await new Promise(r => setTimeout(r, 300));
  
  // Attach media to first tweet only
  if (i === 0 && mediaFiles.length) await uploadMedia(mediaFiles);
  
  // Add next tweet in thread
  if (i < tweetTexts.length - 1) {
    await page.waitForSelector('[data-testid="addButton"]', { timeout: 5000 });
    await page.click('[data-testid="addButton"]');
    await new Promise(r => setTimeout(r, 500));
  }
}

// Post or screenshot
if (process.argv.includes('--post')) {
  await page.click('[data-testid="tweetButton"]');
  await new Promise(r => setTimeout(r, 3000));
  console.log(`Posted${mediaFiles.length ? ' with media' : ''}!`);
} else {
  await page.screenshot({ path: 'x-thread.png' });
  console.log(`Dry run: ${tweetTexts.length} tweet(s)${mediaFiles.length ? ` + ${mediaFiles.length} media` : ''}`);
}
await browser.disconnect();
