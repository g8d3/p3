/**
 * Monitor - Twitter/X.com feed monitoring, mentions, and bookmarks extraction
 * Uses Chrome DevTools Protocol for DOM scraping
 */

import { config } from '../../../config/defaults.js';

// X.com URLs
const URLS = {
  home: 'https://x.com/home',
  notifications: 'https://x.com/notifications',
  bookmarks: 'https://x.com/i/bookmarks',
  tweet: 'https://x.com/user/status'
};

/**
 * Navigate to a URL and wait for page load
 * @param {BrowserClient} browserClient - Connected browser client
 * @param {string} url - URL to navigate to
 * @param {number} waitTime - Additional wait time after load (ms)
 */
async function navigateAndWait(browserClient, url, waitTime = 2000) {
  await browserClient.sendCommand('Page.navigate', { url });
  
  // Wait for page load event
  await new Promise(resolve => {
    const handler = (message) => {
      if (message.method === 'Page.loadEventFired') {
        browserClient.removeListener('event', handler);
        resolve();
      }
    };
    browserClient.on('event', handler);
    
    // Timeout fallback
    setTimeout(() => {
      browserClient.removeListener('event', handler);
      resolve();
    }, 10000);
  });
  
  // Additional wait for dynamic content
  await new Promise(resolve => setTimeout(resolve, waitTime));
}

/**
 * Execute DOM query in the browser and return results
 * @param {BrowserClient} browserClient - Connected browser client
 * @param {string} selector - CSS selector
 * @param {Function} extractFn - Function to extract data from elements
 */
async function queryDOM(browserClient, selector, extractFn) {
  const document = await browserClient.sendCommand('DOM.getDocument');
  const nodeId = document.root.nodeId;
  
  // Find all matching elements
  const result = await browserClient.sendCommand('DOM.querySelectorAll', {
    nodeId,
    selector
  });
  
  if (!result.nodeIds || result.nodeIds.length === 0) {
    return [];
  }
  
  const extractedData = [];
  
  for (const nodeId of result.nodeIds) {
    try {
      // Get outer HTML for parsing
      const html = await browserClient.sendCommand('DOM.getOuterHTML', { nodeId });
      
      // Evaluate extraction function in browser context
      const evalResult = await browserClient.sendCommand('Runtime.evaluate', {
        expression: `(() => {
          const el = document.querySelector('[data-node-id="${nodeId}"]');
          if (!el) return null;
          return (${extractFn.toString()})(el);
        })()`,
        returnByValue: true
      });
      
      if (evalResult.result && evalResult.result.value) {
        extractedData.push(evalResult.result.value);
      }
    } catch (err) {
      // Skip elements that fail to extract
      continue;
    }
  }
  
  return extractedData;
}

/**
 * Extract a single tweet's data from an element
 * @param {Element} tweetEl - Tweet DOM element
 * @returns {object} Tweet data
 */
function extractTweetData(tweetEl) {
  // Extract tweet text
  const textEl = tweetEl.querySelector('[data-testid="tweetText"]');
  const text = textEl ? textEl.textContent : '';
  
  // Extract author info
  const authorLink = tweetEl.querySelector('a[href*="/status/"]');
  const authorHandle = authorLink ? 
    authorLink.href.match(/x\.com\/([^\/]+)/)?.[1] : '';
  
  const displayNameEl = tweetEl.querySelector('[data-testid="User-Name"]');
  const displayName = displayNameEl ? 
    displayNameEl.querySelector('span')?.textContent : '';
  
  // Extract tweet ID from link or time element
  const timeEl = tweetEl.querySelector('time');
  const tweetLink = tweetEl.querySelector('a[href*="/status/"]');
  const tweetId = tweetLink ? 
    tweetLink.href.match(/status\/(\d+)/)?.[1] : '';
  
  // Extract timestamp
  const timestamp = timeEl ? 
    timeEl.getAttribute('datetime') : new Date().toISOString();
  
  // Extract engagement counts
  const getMetric = (testId) => {
    const el = tweetEl.querySelector(`[data-testid="${testId}"]`);
    if (!el) return 0;
    const text = el.textContent || '0';
    return parseMetricCount(text);
  };
  
  return {
    tweetId,
    text,
    author: {
      handle: authorHandle,
      displayName
    },
    timestamp,
    engagement: {
      replies: getMetric('reply'),
      retweets: getMetric('retweet'),
      likes: getMetric('like'),
      views: getMetric('view'),
      bookmarks: getMetric('bookmark')
    },
    url: tweetId ? `https://x.com/${authorHandle}/status/${tweetId}` : null
  };
}

/**
 * Parse metric count string (e.g., "1.2K", "5M") to number
 * @param {string} text - Metric text
 * @returns {number} Parsed count
 */
function parseMetricCount(text) {
  if (!text) return 0;
  
  const cleanText = text.trim().toLowerCase();
  
  if (cleanText.includes('k')) {
    return Math.round(parseFloat(cleanText) * 1000);
  }
  if (cleanText.includes('m')) {
    return Math.round(parseFloat(cleanText) * 1000000);
  }
  if (cleanText.includes('b')) {
    return Math.round(parseFloat(cleanText) * 1000000000);
  }
  
  const num = parseInt(cleanText.replace(/[^0-9]/g, ''), 10);
  return isNaN(num) ? 0 : num;
}

/**
 * Extract tweets from current page
 * @param {BrowserClient} browserClient - Connected browser client
 * @param {number} limit - Maximum tweets to extract
 * @returns {Promise<Array>} Array of tweet objects
 */
export async function extractTweetsFromPage(browserClient, limit = 50) {
  if (!browserClient.isConnected()) {
    throw new Error('Browser client not connected');
  }
  
  // Use Runtime.evaluate to extract tweets directly
  const evalResult = await browserClient.sendCommand('Runtime.evaluate', {
    expression: `(() => {
      const tweets = [];
      const tweetEls = document.querySelectorAll('[data-testid="tweet"]');
      
      const parseCount = (text) => {
        if (!text) return 0;
        const clean = text.trim().toLowerCase();
        if (clean.includes('k')) return Math.round(parseFloat(clean) * 1000);
        if (clean.includes('m')) return Math.round(parseFloat(clean) * 1000000);
        if (clean.includes('b')) return Math.round(parseFloat(clean) * 1000000000);
        const num = parseInt(clean.replace(/[^0-9]/g, ''), 10);
        return isNaN(num) ? 0 : num;
      };
      
      tweetEls.forEach((el, index) => {
        if (index >= ${limit}) return;
        
        const textEl = el.querySelector('[data-testid="tweetText"]');
        const text = textEl ? textEl.textContent : '';
        
        const authorLink = el.querySelector('a[href*="/status/"]');
        const authorHandle = authorLink ? 
          authorLink.href.match(/x\\.com\\/([^\\/]+)/)?.[1] : '';
        
        const displayNameEl = el.querySelector('[data-testid="User-Name"]');
        const displayName = displayNameEl ? 
          displayNameEl.querySelector('span')?.textContent : '';
        
        const tweetLink = el.querySelector('a[href*="/status/"]');
        const tweetId = tweetLink ? 
          tweetLink.href.match(/status\\/(\\d+)/)?.[1] : '';
        
        const timeEl = el.querySelector('time');
        const timestamp = timeEl ? timeEl.getAttribute('datetime') : new Date().toISOString();
        
        const getMetric = (testId) => {
          const metricEl = el.querySelector('[data-testid="' + testId + '"]');
          if (!metricEl) return 0;
          return parseCount(metricEl.textContent);
        };
        
        if (tweetId) {
          tweets.push({
            tweetId,
            text,
            author: { handle: authorHandle, displayName },
            timestamp,
            engagement: {
              replies: getMetric('reply'),
              retweets: getMetric('retweet'),
              likes: getMetric('like'),
              views: getMetric('view'),
              bookmarks: getMetric('bookmark')
            },
            url: 'https://x.com/' + authorHandle + '/status/' + tweetId
          });
        }
      });
      
      return tweets;
    })()`,
    returnByValue: true
  });
  
  return evalResult.result?.value || [];
}

/**
 * Extract mentions from notifications page
 * @param {BrowserClient} browserClient - Connected browser client
 * @param {string} lastCheckedId - Last checked tweet ID for filtering new mentions
 * @returns {Promise<Array>} Array of mention objects
 */
export async function extractMentions(browserClient, lastCheckedId = null) {
  if (!browserClient.isConnected()) {
    throw new Error('Browser client not connected');
  }
  
  // Navigate to notifications
  await navigateAndWait(browserClient, URLS.notifications, 3000);
  
  // Wait for mentions tab to potentially be needed
  const evalResult = await browserClient.sendCommand('Runtime.evaluate', {
    expression: `(() => {
      const mentions = [];
      const tweetEls = document.querySelectorAll('[data-testid="tweet"]');
      
      const parseCount = (text) => {
        if (!text) return 0;
        const clean = text.trim().toLowerCase();
        if (clean.includes('k')) return Math.round(parseFloat(clean) * 1000);
        if (clean.includes('m')) return Math.round(parseFloat(clean) * 1000000);
        const num = parseInt(clean.replace(/[^0-9]/g, ''), 10);
        return isNaN(num) ? 0 : num;
      };
      
      tweetEls.forEach(el => {
        const textEl = el.querySelector('[data-testid="tweetText"]');
        const text = textEl ? textEl.textContent : '';
        
        // Check if this is a mention (contains @handle)
        if (!text.includes('@')) return;
        
        const authorLink = el.querySelector('a[href*="/status/"]');
        const authorHandle = authorLink ? 
          authorLink.href.match(/x\\.com\\/([^\\/]+)/)?.[1] : '';
        
        const displayNameEl = el.querySelector('[data-testid="User-Name"]');
        const displayName = displayNameEl ? 
          displayNameEl.querySelector('span')?.textContent : '';
        
        const tweetLink = el.querySelector('a[href*="/status/"]');
        const tweetId = tweetLink ? 
          tweetLink.href.match(/status\\/(\\d+)/)?.[1] : '';
        
        const timeEl = el.querySelector('time');
        const timestamp = timeEl ? timeEl.getAttribute('datetime') : '';
        
        const getMetric = (testId) => {
          const metricEl = el.querySelector('[data-testid="' + testId + '"]');
          return metricEl ? parseCount(metricEl.textContent) : 0;
        };
        
        if (tweetId) {
          mentions.push({
            tweetId,
            text,
            author: { handle: authorHandle, displayName },
            timestamp,
            type: 'mention',
            engagement: {
              replies: getMetric('reply'),
              retweets: getMetric('retweet'),
              likes: getMetric('like')
            },
            url: 'https://x.com/' + authorHandle + '/status/' + tweetId
          });
        }
      });
      
      return mentions;
    })()`,
    returnByValue: true
  });
  
  let mentions = evalResult.result?.value || [];
  
  // Filter out already checked mentions
  if (lastCheckedId) {
    mentions = mentions.filter(m => m.tweetId !== lastCheckedId);
  }
  
  return mentions;
}

/**
 * Extract bookmarks from bookmarks page
 * @param {BrowserClient} browserClient - Connected browser client
 * @param {number} limit - Maximum bookmarks to extract
 * @returns {Promise<Array>} Array of bookmarked tweet objects
 */
export async function extractBookmarks(browserClient, limit = 100) {
  if (!browserClient.isConnected()) {
    throw new Error('Browser client not connected');
  }
  
  // Navigate to bookmarks
  await navigateAndWait(browserClient, URLS.bookmarks, 3000);
  
  // Extract bookmarks using the same tweet extraction logic
  const evalResult = await browserClient.sendCommand('Runtime.evaluate', {
    expression: `(() => {
      const bookmarks = [];
      const tweetEls = document.querySelectorAll('[data-testid="tweet"]');
      
      const parseCount = (text) => {
        if (!text) return 0;
        const clean = text.trim().toLowerCase();
        if (clean.includes('k')) return Math.round(parseFloat(clean) * 1000);
        if (clean.includes('m')) return Math.round(parseFloat(clean) * 1000000);
        const num = parseInt(clean.replace(/[^0-9]/g, ''), 10);
        return isNaN(num) ? 0 : num;
      };
      
      tweetEls.forEach((el, index) => {
        if (index >= ${limit}) return;
        
        const textEl = el.querySelector('[data-testid="tweetText"]');
        const text = textEl ? textEl.textContent : '';
        
        const authorLink = el.querySelector('a[href*="/status/"]');
        const authorHandle = authorLink ? 
          authorLink.href.match(/x\\.com\\/([^\\/]+)/)?.[1] : '';
        
        const displayNameEl = el.querySelector('[data-testid="User-Name"]');
        const displayName = displayNameEl ? 
          displayNameEl.querySelector('span')?.textContent : '';
        
        const tweetLink = el.querySelector('a[href*="/status/"]');
        const tweetId = tweetLink ? 
          tweetLink.href.match(/status\\/(\\d+)/)?.[1] : '';
        
        const timeEl = el.querySelector('time');
        const timestamp = timeEl ? timeEl.getAttribute('datetime') : '';
        
        const getMetric = (testId) => {
          const metricEl = el.querySelector('[data-testid="' + testId + '"]');
          return metricEl ? parseCount(metricEl.textContent) : 0;
        };
        
        if (tweetId) {
          bookmarks.push({
            tweetId,
            text,
            author: { handle: authorHandle, displayName },
            timestamp,
            bookmarkedAt: new Date().toISOString(),
            engagement: {
              replies: getMetric('reply'),
              retweets: getMetric('retweet'),
              likes: getMetric('like'),
              views: getMetric('view'),
              bookmarks: getMetric('bookmark')
            },
            url: 'https://x.com/' + authorHandle + '/status/' + tweetId
          });
        }
      });
      
      return bookmarks;
    })()`,
    returnByValue: true
  });
  
  return evalResult.result?.value || [];
}

/**
 * Scroll down the page to load more content
 * @param {BrowserClient} browserClient - Connected browser client
 * @param {number} pixels - Pixels to scroll
 */
export async function scrollPage(browserClient, pixels = 1000) {
  await browserClient.sendCommand('Runtime.evaluate', {
    expression: `window.scrollBy(0, ${pixels})`
  });
  
  // Wait for new content to load
  await new Promise(resolve => setTimeout(resolve, 1500));
}

/**
 * Get home feed tweets
 * @param {BrowserClient} browserClient - Connected browser client
 * @param {number} count - Number of tweets to fetch
 * @returns {Promise<Array>} Array of tweet objects
 */
export async function getHomeFeed(browserClient, count = 50) {
  if (!browserClient.isConnected()) {
    throw new Error('Browser client not connected');
  }
  
  // Navigate to home
  await navigateAndWait(browserClient, URLS.home, 3000);
  
  // Extract initial tweets
  let tweets = await extractTweetsFromPage(browserClient, count);
  
  // Scroll to load more if needed
  while (tweets.length < count) {
    await scrollPage(browserClient, 1000);
    const newTweets = await extractTweetsFromPage(browserClient, count);
    
    // Check if we got new tweets
    if (newTweets.length <= tweets.length) {
      break; // No more tweets loading
    }
    
    tweets = newTweets;
  }
  
  return tweets.slice(0, count);
}

// Export URLS as named export
export { URLS };

export default {
  extractTweetsFromPage,
  extractMentions,
  extractBookmarks,
  scrollPage,
  getHomeFeed,
  URLS
};
