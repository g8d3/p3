const { chromium } = require('playwright');
const readline = require('readline');

async function scrapeTweets(num = 10) {
  let browser;
  try {
    // Connect to existing browser on CDP port 9222
    browser = await chromium.connectOverCDP('http://localhost:9222');

    // Get existing contexts and pages
    const existingContexts = browser.contexts();
    const options = [];
    let optionIndex = 1;

    console.log('Available tabs:');
    for (const ctx of existingContexts) {
      const pages = ctx.pages();
      for (const p of pages) {
        const url = await p.url();
        console.log(`${optionIndex}. Existing tab: ${url}`);
        options.push({ type: 'existing', page: p, url });
        optionIndex++;
      }
    }
    console.log(`${optionIndex}. New tab`);
    options.push({ type: 'new' });

    // Prompt user to choose
    const rl = readline.createInterface({
      input: process.stdin,
      output: process.stdout
    });

    const choice = await new Promise((resolve) => {
      rl.question('Choose a tab (number): ', (answer) => {
        rl.close();
        resolve(parseInt(answer));
      });
    });

    let page;
    if (choice >= 1 && choice < optionIndex) {
      const selected = options[choice - 1];
      page = selected.page;
      console.log('Using existing page:', selected.url);
      if (!selected.url.includes('/home')) {
        console.log('Navigating to home...');
        await page.goto('https://x.com/home', { waitUntil: 'domcontentloaded', timeout: 15000 });
      }
    } else if (choice === optionIndex) {
      console.log('Creating new tab...');
      const context = await browser.newContext();
      page = await context.newPage();
      await page.goto('https://x.com/home', { waitUntil: 'domcontentloaded', timeout: 15000 });
    } else {
      throw new Error('Invalid choice');
    }

    console.log('URL after navigation:', await page.url());
    if (!page.url().includes('/home')) {
      throw new Error('Not navigated to home page');
    }

    // Wait for tweets to load
    await page.waitForSelector('article[data-testid="tweet"]', { timeout: 10000 });

    // Add persistent ID display using MutationObserver
    await page.evaluate(() => {
      if (window.tweetIdObserverInjected) return;

      const addIdToTweet = (tweet) => {
        if (tweet.querySelector('.tweet-id-display')) return;
        const link = tweet.querySelector('a[href*="/status/"]');
        if (link) {
          const href = link.getAttribute('href');
          const id = href.split('/status/')[1]?.split('/')[0];
          if (id) {
            const idDiv = document.createElement('div');
            idDiv.textContent = `ID: ${id}`;
            idDiv.style.color = 'red';
            idDiv.style.fontSize = '12px';
            idDiv.style.fontWeight = 'bold';
            idDiv.className = 'tweet-id-display';
            tweet.appendChild(idDiv);
          }
        }
      };

      // Add to existing tweets
      document.querySelectorAll('article[data-testid="tweet"]').forEach(addIdToTweet);

      // Observe for new tweets
      const observer = new MutationObserver((mutations) => {
        mutations.forEach((mutation) => {
          mutation.addedNodes.forEach((node) => {
            if (node.nodeType === 1 && node.matches('article[data-testid="tweet"]')) {
              addIdToTweet(node);
            }
            if (node.nodeType === 1) {
              node.querySelectorAll('article[data-testid="tweet"]').forEach(addIdToTweet);
            }
          });
        });
      });
      observer.observe(document.body, { childList: true, subtree: true });

      window.tweetIdObserverInjected = true;
    });

    let scrapedIds = new Set();
    let tweets = [];
    let scrollCount = 0;
    const maxScrolls = 50; // Increased for more attempts
    let lastScrapedId = null;

    while (tweets.length < num && scrollCount < maxScrolls) {
      // Get current tweet elements
      const tweetElements = await page.$$('article[data-testid="tweet"]');

      // Extract data from unscraped tweets
      for (const el of tweetElements) {
        if (tweets.length >= num) break;
        const link = await el.$('a[href*="/status/"]');
        const href = link ? await link.getAttribute('href') : '';
        const id = href.split('/status/')[1]?.split('/')[0];
         if (id && !scrapedIds.has(id)) {
           const tweetData = await extractTweetData(el);
           if (tweetData) {
             scrapedIds.add(id);
             tweets.push(tweetData);
             lastScrapedId = id;
           }
         }
      }



      if (tweets.length >= num) break;

      // Scroll to load more tweets
      await page.evaluate(() => window.scrollBy(0, window.innerHeight));
      await page.waitForTimeout(3000);

      // If scrolled too much, scroll back once to keep last scraped tweet in view
      if (lastScrapedId) {
        const currentVisible = await page.$$('article[data-testid="tweet"]');
        const currentIds = [];
        for (const el of currentVisible) {
          const link = await el.$('a[href*="/status/"]');
          const href = link ? await link.getAttribute('href') : '';
          const id = href.split('/status/')[1]?.split('/')[0];
          if (id) currentIds.push(id);
        }
        if (!currentIds.includes(lastScrapedId)) {
          // Scroll back
          await page.evaluate(() => window.scrollBy(0, -window.innerHeight));
          await page.waitForTimeout(2000);
        }
      }

      scrollCount++;
    }

    console.log(`Extracted ${tweets.length} tweets`);

    const scrapedTweets = tweets.slice(0, num);

    // Output the scraped tweets
    console.log(JSON.stringify(scrapedTweets, null, 2));
    process.exit(0);

  } catch (error) {
    console.error('Error:', error.message);
    process.exit(1);
  }
}

async function extractTweetData(tweetEl) {
  try {
    // Get tweet ID for tracking
    const tweetLink = await tweetEl.$('a[href*="/status/"]');
    const href = tweetLink ? await tweetLink.getAttribute('href') : '';
    const tweetId = href.split('/status/')[1]?.split('/')[0];

    // Extract user info
    const userText = await tweetEl.$eval('[data-testid="User-Name"]', el => el.textContent.trim()).catch(() => '');
    const [nameHandle, relativeTime] = userText.split('·');
    const [displayName, handleWithAt] = (nameHandle || '').trim().split('@');
    const handle = (handleWithAt || '').trim();
    const timeEl = await tweetEl.$('time');
    const datetime = timeEl ? await timeEl.getAttribute('datetime') : '';

    // Extract tweet content, click show more if needed (only for main tweet)
    let content = await tweetEl.$eval('[data-testid="tweetText"]', el => el.textContent.trim()).catch(() => '');
    const showMoreBtn = await tweetEl.$('button:has-text("Show more")');
    if (showMoreBtn) {
      await showMoreBtn.click();
      await tweetEl.page().waitForTimeout(500); // wait for expansion
      content = await tweetEl.$eval('[data-testid="tweetText"]', el => el.textContent.trim()).catch(() => content);
    }

    // Extract stats: replies, reposts, likes, views
    const statElements = await tweetEl.$$('[role="group"] [dir="ltr"]');
    const replies = statElements[0] ? await statElements[0].textContent().then(t => t.trim()) : '0';
    const reposts = statElements[1] ? await statElements[1].textContent().then(t => t.trim()) : '0';
    const likes = statElements[2] ? await statElements[2].textContent().then(t => t.trim()) : '0';
    const views = statElements[3] ? await statElements[3].textContent().then(t => t.trim()) : '0';

    // Skip replies
    const replyingTo = await tweetEl.$('text=Replying to').catch(() => null);
    if (replyingTo) return null;

    // Check if it's a thread - look for thread indicators
    const threadIndicator = await tweetEl.$('text=Show this thread').catch(() => null);
    const isThread = !!threadIndicator;

    console.log(`Scraping tweet ID: ${tweetId}`);
    return { tweetId, displayName, handle, datetime, content, replies, likes, reposts, views, isThread };
  } catch (e) {
    return null;
  }
}

const args = process.argv.slice(2);
const numArg = args.find(arg => !isNaN(parseInt(arg)));
const num = numArg ? parseInt(numArg) : 10;
scrapeTweets(num);