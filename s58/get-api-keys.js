#!/usr/bin/env node
/**
 * API Key Retrieval Script
 * 
 * Opens Pexels and Pixabay API pages in your real Chrome browser,
 * helps you sign up if needed, and saves your API keys to .env
 * 
 * Usage:
 *   1. Make sure Chrome is running with remote debugging:
 *      google-chrome --remote-debugging-port=9222
 *      (or use the cdp.sh script)
 *   2. Run this script:
 *      node get-api-keys.js
 * 
 * What it does:
 *   - Opens Pexels API page → helps you get your API key
 *   - Opens Pixabay API page → helps you get your API key
 *   - Saves both keys to .env file
 */

import puppeteer from 'puppeteer-core';
import { writeFileSync, existsSync, readFileSync, appendFileSync } from 'fs';
import { resolve } from 'path';

const BROWSER_URL = 'http://localhost:9222';
const ENV_PATH = resolve(import.meta.dirname, '.env');

// ── Helpers ────────────────────────────────────────────────────────────────

async function connect() {
  const browser = await puppeteer.connect({ browserURL: BROWSER_URL });
  console.log('✓ Connected to Chrome on', BROWSER_URL);
  return browser;
}

async function newPage(browser) {
  const page = await browser.newPage();
  // Use a real viewport to look more human
  await page.setViewport({ width: 1280, height: 800 });
  return page;
}

function saveToEnv(key, value) {
  const entry = `${key}=${value}\n`;
  if (!existsSync(ENV_PATH)) {
    writeFileSync(ENV_PATH, entry);
    console.log(`  ✓ Saved ${key} to .env`);
    return;
  }
  const existing = readFileSync(ENV_PATH, 'utf-8');
  if (existing.includes(`${key}=`)) {
    // Replace existing value
    const updated = existing.replace(new RegExp(`${key}=.*`), `${key}=${value}`);
    writeFileSync(ENV_PATH, updated);
    console.log(`  ✓ Updated ${key} in .env`);
  } else {
    appendFileSync(ENV_PATH, entry);
    console.log(`  ✓ Appended ${key} to .env`);
  }
}

async function waitForLogin(page, name, url, apiKeyPattern) {
  console.log(`\n  ┌──────────────────────────────────────────────────┐`);
  console.log(`  │  ${name.padEnd(46)}│`);
  console.log(`  ├──────────────────────────────────────────────────┤`);
  console.log(`  │  Navigated to: ${url.padEnd(25)}│`);
  console.log(`  │                                                  │`);
  console.log(`  │  If you're NOT logged in:                       │`);
  console.log(`  │  1. Look at your Chrome browser window          │`);
  console.log(`  │  2. Click "Log in" or "Sign up"                 │`);
  console.log(`  │  3. Create an account (or log in)               │`);
  console.log(`  │  4. Come back to this terminal                  │`);
  console.log(`  │                                                  │`);
  console.log(`  └──────────────────────────────────────────────────┘`);

  // Wait for user to log in (check every 3 seconds for up to 5 minutes)
  for (let attempt = 0; attempt < 100; attempt++) {
    await new Promise(r => setTimeout(r, 3000));
    try {
      const html = await page.content();
      const match = html.match(apiKeyPattern);
      if (match) {
        const key = match[1] || match[0];
        console.log(`\n  ✅ Found ${name} API key!`);
        return key;
      }
      // Check if we're on a page that shows the key
      const url = page.url();
      if (url.includes('dashboard') || url.includes('api') || url.includes('account')) {
        // Try to find the key more carefully
        const text = await page.evaluate(() => document.body.innerText);
        const textMatch = text.match(apiKeyPattern);
        if (textMatch) {
          console.log(`\n  ✅ Found ${name} API key in page text!`);
          return textMatch[1] || textMatch[0];
        }
      }
      if (attempt % 10 === 0) {
        console.log(`  ⏳ Waiting for you to log in to ${name}... (${Math.round(attempt * 3)}s)`);
      }
    } catch (e) {
      // Page might be loading, just continue
    }
  }
  console.log(`  ⏰ Timed out waiting for ${name} login.`);
  return null;
}

// ── Pexels ─────────────────────────────────────────────────────────────────

async function getPexelsKey(page) {
  console.log('\n' + '='.repeat(60));
  console.log('  PEXELS API KEY');
  console.log('='.repeat(60));

  await page.goto('https://www.pexels.com/api/', { waitUntil: 'networkidle2', timeout: 30000 });
  await new Promise(r => setTimeout(r, 2000));

  // Check if already on the API page (logged in)
  let html = await page.content();
  
  // Pattern for Pexels API key (looks like a long alphanumeric string)
  // Pexels shows the key in an input field or as text on the /api/ page when logged in
  let pexelsKey = null;

  // Method 1: Look for the API key in the page
  const keyMatch = html.match(/[A-Za-z0-9]{20,40}/);
  const text = await page.evaluate(() => document.body.innerText);

  if (text.includes('API Key') || text.includes('api key') || text.includes('Your API')) {
    // Extract the key
    const lines = text.split('\n');
    for (const line of lines) {
      if (line.includes('api') || line.includes('API')) {
        const words = line.split(/\s+/);
        for (const word of words) {
          if (word.length > 20 && /^[A-Za-z0-9]+$/.test(word)) {
            pexelsKey = word;
            break;
          }
        }
      }
    }
  }

  if (pexelsKey) {
    console.log(`\n  ✅ Found Pexels API key: ${pexelsKey.slice(0, 8)}...${pexelsKey.slice(-4)}`);
  } else {
    console.log(`\n  ℹ️  Not logged in yet. Let's navigate to the signup/login page.`);
    
    // Try clicking the "Get Started" or "Login" button
    try {
      const loginLink = await page.$('a[href*="login"], a[href*="sign"], a[href*="register"], button:has-text("Get Started")');
      if (loginLink) {
        await loginLink.click();
        await new Promise(r => setTimeout(r, 2000));
      }
    } catch (e) {
      // Try navigating directly to login
      await page.goto('https://www.pexels.com/login/', { waitUntil: 'networkidle2', timeout: 30000 });
      await new Promise(r => setTimeout(r, 2000));
    }

    console.log(`  ℹ️  Please log in or sign up in the Chrome window.`);
    console.log(`  ℹ️  After logging in, you'll be redirected to the API page with your key.`);

    // Wait for login and API key (Pexels keys are 40-char hex: [a-f0-9]{40})
    const key = await waitForLogin(page, 'Pexels', 'https://www.pexels.com/api/', /[a-f0-9]{40}/);
    if (key) pexelsKey = key;
  }

  return pexelsKey;
}

// ── Pixabay ────────────────────────────────────────────────────────────────

async function getPixabayKey(page) {
  console.log('\n' + '='.repeat(60));
  console.log('  PIXABAY API KEY');
  console.log('='.repeat(60));

  await page.goto('https://pixabay.com/api/docs/', { waitUntil: 'networkidle2', timeout: 30000 });
  await new Promise(r => setTimeout(r, 2000));

  let pixabayKey = null;

  // Check if logged in: the page says "Please login to see your API key here"
  // When logged in, the key appears where that text was
  const loginPrompt = await page.evaluate(() => {
    const body = document.body.innerText;
    return body.includes('Please login to see your API key');
  });

  if (!loginPrompt) {
    // Might be logged in — find the key in the key/input field area
    // Pixabay shows the key as text in the "key (required)" row
    pixabayKey = await page.evaluate(() => {
      // Look for the API key in the parameter table
      const rows = document.querySelectorAll('tr');
      for (const row of rows) {
        const text = row.textContent || '';
        if (text.includes('key') && text.includes('required')) {
          const cells = row.querySelectorAll('td, th');
          for (const cell of cells) {
            const content = cell.textContent || '';
            // A real key is 10+ alphanumeric chars and doesn't contain 'login' or 'signup'
            const match = content.match(/([A-Za-z0-9]{10,50})/);
            if (match && !content.toLowerCase().includes('login') && !content.toLowerCase().includes('sign')) {
              return match[1];
            }
          }
        }
      }
      return null;
    });
  }

  if (pixabayKey) {
    console.log(`\n  ✅ Found Pixabay API key: ${pixabayKey.slice(0, 8)}...${pixabayKey.slice(-4)}`);
  } else {
    console.log(`\n  ℹ️  Not logged in to Pixabay. Opening signup...`);
    
    await page.goto('https://pixabay.com/accounts/register/', { waitUntil: 'networkidle2', timeout: 30000 })
      .catch(() => page.goto('https://pixabay.com/accounts/join/', { waitUntil: 'networkidle2', timeout: 30000 }));
    await new Promise(r => setTimeout(r, 2000));

    console.log(`  ℹ️  Please sign up or log in in the Chrome window.`);
    console.log(`  ℹ️  After logging in, return here.`);

    // Wait for login by checking the prompt disappears
    const loggedIn = await waitForLogin(page, 'Pixabay', 'https://pixabay.com/api/docs/',
      /Please login to see your API key/);

    // Navigate to API docs to see the key
    await page.goto('https://pixabay.com/api/docs/', { waitUntil: 'networkidle2', timeout: 30000 });
    await new Promise(r => setTimeout(r, 2000));

    // Extract key from the specific location
    pixabayKey = await page.evaluate(() => {
      const rows = document.querySelectorAll('tr');
      for (const row of rows) {
        const text = row.textContent || '';
        if (text.includes('key') && text.includes('required')) {
          const cells = row.querySelectorAll('td, th');
          for (const cell of cells) {
            const content = cell.textContent || '';
            const match = content.match(/([A-Za-z0-9]{10,50})/);
            if (match && !content.toLowerCase().includes('login') && !content.toLowerCase().includes('sign')) {
              return match[1];
            }
          }
        }
      }
      return null;
    });
  }

  return pixabayKey;
}

// ── Main ────────────────────────────────────────────────────────────────────

async function main() {
  console.log(`
  ╔══════════════════════════════════════════════════╗
  ║        API Key Retrieval Tool                    ║
  ║                                                  ║
  ║  This script helps you get API keys for:         ║
  ║    • Pexels  (free stock videos)                 ║
  ║    • Pixabay (free stock videos + music)         ║
  ║                                                  ║
  ║  Make sure Chrome is running on port 9222:       ║
  ║    source ../cdp.sh                              ║
  ╚══════════════════════════════════════════════════╝`);

  // Check if Chrome is running
  try {
    const resp = await fetch('http://localhost:9222/json/version');
    const info = await resp.json();
    console.log(`\n✓ Chrome ${info.Browser} running on port 9222`);
  } catch (e) {
    console.error(`\n✗ Chrome is NOT running on port 9222.`);
    console.error(`  Run: google-chrome --remote-debugging-port=9222`);
    console.error(`  Or:  source /home/vuos/code/cdp.sh`);
    process.exit(1);
  }

  const browser = await connect();
  
  let savedPexels = null, savedPixabay = null;
  
  try {
    // Get Pexels key
    const pexelsPage = await newPage(browser);
    const pexelsKey = await getPexelsKey(pexelsPage);
    if (pexelsKey) {
      saveToEnv('PEXELS_API_KEY', pexelsKey);
      savedPexels = pexelsKey;
    } else {
      console.log(`\n  ⚠ Could not get Pexels API key.`);
      console.log(`  ℹ  After signing up, get your key at:`);
      console.log(`     https://www.pexels.com/api/`);
    }
    await pexelsPage.close();

    // Get Pixabay key
    const pixabayPage = await newPage(browser);
    const pixabayKey = await getPixabayKey(pixabayPage);
    if (pixabayKey) {
      saveToEnv('PIXABAY_API_KEY', pixabayKey);
      savedPixabay = pixabayKey;
    } else {
      console.log(`\n  ⚠ Could not get Pixabay API key.`);
      console.log(`  ℹ  After signing up, get your key at:`);
      console.log(`     https://pixabay.com/api/docs/`);
    }
    await pixabayPage.close();

  } finally {
    await browser.disconnect();
  }

  // Summary
  console.log('\n' + '='.repeat(60));
  const k1 = savedPexels;
  const k2 = savedPixabay;
  if (k1 || k2) {
    console.log('  ✅ Summary:');
    if (k1) console.log(`  ✅ PEXELS_API_KEY=${k1.slice(0, 8)}...${k1.slice(-4)}`);
    if (k2) console.log(`  ✅ PIXABAY_API_KEY=${k2.slice(0, 8)}...${k2.slice(-4)}`);
    console.log(`\n  Keys saved to: ${ENV_PATH}`);
    console.log(`  To load: source ${ENV_PATH}`);
  } else {
    console.log('  ⚠ No API keys were retrieved.');
    console.log('  ℹ  Manually sign up and get your keys:');
    console.log('     Pexels:  https://www.pexels.com/api/');
    console.log('     Pixabay: https://pixabay.com/api/docs/');
  }
  console.log('='.repeat(60));
}

main().catch(console.error);
