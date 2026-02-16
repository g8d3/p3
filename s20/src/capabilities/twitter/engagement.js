/**
 * Engagement - Twitter/X.com metrics collection
 * Extracts likes, retweets, replies, views, and bookmarks from tweets
 */

import { config } from '../../../config/defaults.js';

// X.com URLs
const URLS = {
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
  
  await new Promise(resolve => setTimeout(resolve, waitTime));
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
 * Extract engagement metrics from a tweet page
 * @param {BrowserClient} browserClient - Connected browser client
 * @param {string} tweetUrl - Full URL to the tweet
 * @returns {Promise<object>} Metrics object
 */
export async function getTweetMetrics(browserClient, tweetUrl) {
  if (!browserClient.isConnected()) {
    throw new Error('Browser client not connected');
  }
  
  try {
    // Navigate to the tweet
    await navigateAndWait(browserClient, tweetUrl, 3000);
    
    // Extract metrics from the tweet page
    const evalResult = await browserClient.sendCommand('Runtime.evaluate', {
      expression: `(() => {
        const parseCount = (text) => {
          if (!text) return 0;
          const clean = text.trim().toLowerCase();
          if (clean.includes('k')) return Math.round(parseFloat(clean) * 1000);
          if (clean.includes('m')) return Math.round(parseFloat(clean) * 1000000);
          if (clean.includes('b')) return Math.round(parseFloat(clean) * 1000000000);
          const num = parseInt(clean.replace(/[^0-9]/g, ''), 10);
          return isNaN(num) ? 0 : num;
        };
        
        // Get the main tweet (first one on the page)
        const mainTweet = document.querySelector('article[data-testid="tweet"]');
        if (!mainTweet) return null;
        
        // Extract tweet ID from URL
        const tweetId = window.location.href.match(/status\\/(\\d+)/)?.[1] || '';
        
        // Extract author
        const authorLink = mainTweet.querySelector('a[href*="/status/"]');
        const authorHandle = authorLink ? 
          authorLink.href.match(/x\\.com\\/([^\\/]+)/)?.[1] : '';
        
        // Extract text
        const textEl = mainTweet.querySelector('[data-testid="tweetText"]');
        const text = textEl ? textEl.textContent : '';
        
        // Extract engagement metrics from buttons
        const getButtonCount = (testId) => {
          const btn = mainTweet.querySelector('[data-testid="' + testId + '"]');
          if (!btn) return 0;
          
          // Try to find the count in aria-label or visible text
          const ariaLabel = btn.getAttribute('aria-label') || '';
          const countMatch = ariaLabel.match(/[\\d,]+/);
          if (countMatch) {
            return parseCount(countMatch[0]);
          }
          
          // Try to get from visible text
          const countEl = btn.querySelector('[data-testid="app-text-transition-container"]');
          if (countEl) {
            return parseCount(countEl.textContent);
          }
          
          return 0;
        };
        
        // Get view count (usually in a separate section)
        let views = 0;
        const viewEl = document.querySelector('[data-testid="views"]');
        if (viewEl) {
          views = parseCount(viewEl.textContent);
        } else {
          // Views might be in the analytics section
          const analyticsLink = mainTweet.querySelector('a[href*="/analytics"]');
          if (analyticsLink) {
            const viewText = analyticsLink.textContent;
            const viewMatch = viewText.match(/[\\d,.]+[KkMmBb]?/);
            if (viewMatch) {
              views = parseCount(viewMatch[0]);
            }
          }
        }
        
        // Get bookmark count
        const bookmarkBtn = mainTweet.querySelector('[data-testid="bookmark"]');
        let bookmarks = 0;
        if (bookmarkBtn) {
          const ariaLabel = bookmarkBtn.getAttribute('aria-label') || '';
          const countMatch = ariaLabel.match(/[\\d,]+/);
          if (countMatch) {
            bookmarks = parseCount(countMatch[0]);
          }
        }
        
        return {
          tweetId,
          url: window.location.href,
          author: authorHandle,
          text: text.substring(0, 280), // Truncate for storage
          metrics: {
            replies: getButtonCount('reply'),
            retweets: getButtonCount('retweet'),
            likes: getButtonCount('like'),
            views,
            bookmarks
          },
          scrapedAt: new Date().toISOString()
        };
      })()`,
      returnByValue: true
    });
    
    const data = evalResult.result?.value;
    
    if (!data) {
      return {
        success: false,
        error: 'Could not extract tweet metrics',
        url: tweetUrl
      };
    }
    
    return {
      success: true,
      ...data
    };
    
  } catch (error) {
    return {
      success: false,
      error: error.message,
      url: tweetUrl
    };
  }
}

/**
 * Get metrics for multiple tweets
 * @param {BrowserClient} browserClient - Connected browser client
 * @param {Array<string>} tweetUrls - Array of tweet URLs
 * @param {number} delay - Delay between requests (ms) to avoid rate limiting
 * @returns {Promise<Array>} Array of metric objects
 */
export async function getBatchMetrics(browserClient, tweetUrls, delay = 2000) {
  const results = [];
  
  for (const url of tweetUrls) {
    const metrics = await getTweetMetrics(browserClient, url);
    results.push(metrics);
    
    // Delay between requests
    if (tweetUrls.indexOf(url) < tweetUrls.length - 1) {
      await new Promise(resolve => setTimeout(resolve, delay));
    }
  }
  
  return results;
}

/**
 * Get engagement metrics for a tweet by ID
 * @param {BrowserClient} browserClient - Connected browser client
 * @param {string} tweetId - Tweet ID
 * @param {string} authorHandle - Author's handle (required to construct URL)
 * @returns {Promise<object>} Metrics object
 */
export async function getTweetMetricsById(browserClient, tweetId, authorHandle) {
  const tweetUrl = `https://x.com/${authorHandle}/status/${tweetId}`;
  return await getTweetMetrics(browserClient, tweetUrl);
}

/**
 * Extract engagement metrics from the current page (without navigation)
 * @param {BrowserClient} browserClient - Connected browser client
 * @returns {Promise<Array>} Array of tweet metrics from current page
 */
export async function extractPageMetrics(browserClient) {
  if (!browserClient.isConnected()) {
    throw new Error('Browser client not connected');
  }
  
  const evalResult = await browserClient.sendCommand('Runtime.evaluate', {
    expression: `(() => {
      const parseCount = (text) => {
        if (!text) return 0;
        const clean = text.trim().toLowerCase();
        if (clean.includes('k')) return Math.round(parseFloat(clean) * 1000);
        if (clean.includes('m')) return Math.round(parseFloat(clean) * 1000000);
        if (clean.includes('b')) return Math.round(parseFloat(clean) * 1000000000);
        const num = parseInt(clean.replace(/[^0-9]/g, ''), 10);
        return isNaN(num) ? 0 : num;
      };
      
      const tweets = [];
      const tweetEls = document.querySelectorAll('[data-testid="tweet"]');
      
      tweetEls.forEach(el => {
        const getButtonCount = (testId) => {
          const btn = el.querySelector('[data-testid="' + testId + '"]');
          if (!btn) return 0;
          const ariaLabel = btn.getAttribute('aria-label') || '';
          const countMatch = ariaLabel.match(/[\\d,]+/);
          return countMatch ? parseCount(countMatch[0]) : 0;
        };
        
        const tweetLink = el.querySelector('a[href*="/status/"]');
        const tweetId = tweetLink ? 
          tweetLink.href.match(/status\\/(\\d+)/)?.[1] : '';
        
        const authorLink = el.querySelector('a[href*="/status/"]');
        const authorHandle = authorLink ? 
          authorLink.href.match(/x\\.com\\/([^\\/]+)/)?.[1] : '';
        
        if (tweetId) {
          tweets.push({
            tweetId,
            author: authorHandle,
            metrics: {
              replies: getButtonCount('reply'),
              retweets: getButtonCount('retweet'),
              likes: getButtonCount('like'),
              views: getButtonCount('view'),
              bookmarks: getButtonCount('bookmark')
            }
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
 * Calculate engagement rate
 * @param {object} metrics - Tweet metrics
 * @param {number} followersCount - Author's follower count
 * @returns {object} Engagement analysis
 */
export function calculateEngagementRate(metrics, followersCount) {
  const { likes, retweets, replies, views, bookmarks } = metrics;
  
  const totalEngagements = likes + retweets + replies + bookmarks;
  
  // Engagement rate based on impressions (views)
  const engagementRateByViews = views > 0 ? 
    ((totalEngagements / views) * 100).toFixed(2) : 0;
  
  // Engagement rate based on followers
  const engagementRateByFollowers = followersCount > 0 ?
    ((totalEngagements / followersCount) * 100).toFixed(2) : 0;
  
  // Virality score (ratio of retweets to likes)
  const viralityScore = likes > 0 ? 
    ((retweets / likes) * 100).toFixed(2) : 0;
  
  return {
    totalEngagements,
    engagementRateByViews: parseFloat(engagementRateByViews),
    engagementRateByFollowers: parseFloat(engagementRateByFollowers),
    viralityScore: parseFloat(viralityScore),
    breakdown: {
      likes: (likes / totalEngagements * 100).toFixed(1) + '%',
      retweets: (retweets / totalEngagements * 100).toFixed(1) + '%',
      replies: (replies / totalEngagements * 100).toFixed(1) + '%',
      bookmarks: (bookmarks / totalEngagements * 100).toFixed(1) + '%'
    }
  };
}

/**
 * Compare metrics between two time points
 * @param {object} previous - Previous metrics
 * @param {object} current - Current metrics
 * @returns {object} Metric changes
 */
export function compareMetrics(previous, current) {
  const calcChange = (prev, curr) => {
    if (prev === 0) return curr > 0 ? 100 : 0;
    return ((curr - prev) / prev * 100).toFixed(2);
  };
  
  return {
    likes: {
      previous: previous.likes,
      current: current.likes,
      change: current.likes - previous.likes,
      changePercent: parseFloat(calcChange(previous.likes, current.likes))
    },
    retweets: {
      previous: previous.retweets,
      current: current.retweets,
      change: current.retweets - previous.retweets,
      changePercent: parseFloat(calcChange(previous.retweets, current.retweets))
    },
    replies: {
      previous: previous.replies,
      current: current.replies,
      change: current.replies - previous.replies,
      changePercent: parseFloat(calcChange(previous.replies, current.replies))
    },
    views: {
      previous: previous.views,
      current: current.views,
      change: current.views - previous.views,
      changePercent: parseFloat(calcChange(previous.views, current.views))
    },
    bookmarks: {
      previous: previous.bookmarks,
      current: current.bookmarks,
      change: current.bookmarks - previous.bookmarks,
      changePercent: parseFloat(calcChange(previous.bookmarks, current.bookmarks))
    }
  };
}

export default {
  getTweetMetrics,
  getBatchMetrics,
  getTweetMetricsById,
  extractPageMetrics,
  calculateEngagementRate,
  compareMetrics
};
