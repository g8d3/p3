/**
 * Post - Twitter/X.com tweet composition, posting, and replying
 * Uses Chrome DevTools Protocol for browser automation
 */

import { config } from '../../../config/defaults.js';

// X.com selectors
const SELECTORS = {
  tweetComposer: '[data-testid="tweetTextarea_0"]',
  tweetButton: '[data-testid="tweetButtonInline"]',
  tweetButtonTimeline: '[data-testid="tweetButton"]',
  replyComposer: '[data-testid="tweetTextarea_0"]',
  replyButton: '[data-testid="reply"]',
  likeButton: '[data-testid="like"]',
  retweetButton: '[data-testid="retweet"]',
  unretweetButton: '[data-testid="unretweet"]',
  characterCount: '[data-testid="remainingChars"]',
  alertMessage: '[data-testid="toast"]',
  modal: '[data-testid="modal"]'
};

// Character limits
const TWEET_MAX_LENGTH = 280;

/**
 * Wait for an element to appear in the DOM
 * @param {BrowserClient} browserClient - Connected browser client
 * @param {string} selector - CSS selector
 * @param {number} timeout - Timeout in ms
 */
async function waitForElement(browserClient, selector, timeout = 10000) {
  const startTime = Date.now();
  
  while (Date.now() - startTime < timeout) {
    const result = await browserClient.sendCommand('Runtime.evaluate', {
      expression: `document.querySelector('${selector}') !== null`,
      returnByValue: true
    });
    
    if (result.result?.value) {
      return true;
    }
    
    await new Promise(resolve => setTimeout(resolve, 500));
  }
  
  throw new Error(`Element ${selector} not found within ${timeout}ms`);
}

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
    }, 15000);
  });
  
  await new Promise(resolve => setTimeout(resolve, waitTime));
}

/**
 * Type text into an element with human-like delays
 * @param {BrowserClient} browserClient - Connected browser client
 * @param {string} selector - CSS selector for input element
 * @param {string} text - Text to type
 * @param {number} delay - Delay between keystrokes (ms)
 */
async function typeText(browserClient, selector, text, delay = 30) {
  // Focus the element
  await browserClient.sendCommand('Runtime.evaluate', {
    expression: `
      const el = document.querySelector('${selector}');
      if (el) {
        el.focus();
        el.click();
      }
    `
  });
  
  await new Promise(resolve => setTimeout(resolve, 200));
  
  // Type character by character for more realistic input
  for (const char of text) {
    await browserClient.sendCommand('Runtime.evaluate', {
      expression: `
        const el = document.querySelector('${selector}');
        if (el) {
          // Dispatch input event for contenteditable
          const inputEvent = new InputEvent('input', {
            bubbles: true,
            cancelable: true,
            inputType: 'insertText',
            data: '${char.replace(/'/g, "\\'")}'
          });
          
          // For contenteditable, append to textContent
          if (el.isContentEditable) {
            const selection = window.getSelection();
            const range = selection.rangeCount > 0 ? selection.getRangeAt(0) : null;
            if (range) {
              const textNode = document.createTextNode('${char.replace(/'/g, "\\'")}');
              range.deleteContents();
              range.insertNode(textNode);
              range.setStartAfter(textNode);
              range.collapse(true);
              selection.removeAllRanges();
              selection.addRange(range);
            }
          }
          
          el.dispatchEvent(inputEvent);
        }
      `
    });
    
    await new Promise(resolve => setTimeout(resolve, delay + Math.random() * 20));
  }
}

/**
 * Click an element
 * @param {BrowserClient} browserClient - Connected browser client
 * @param {string} selector - CSS selector
 */
async function clickElement(browserClient, selector) {
  await browserClient.sendCommand('Runtime.evaluate', {
    expression: `
      const el = document.querySelector('${selector}');
      if (el) {
        el.scrollIntoView({ behavior: 'smooth', block: 'center' });
        el.click();
      }
    `
  });
  
  await new Promise(resolve => setTimeout(resolve, 500));
}

/**
 * Get the character count from the composer
 * @param {BrowserClient} browserClient - Connected browser client
 * @returns {Promise<number>} Remaining characters
 */
async function getCharacterCount(browserClient) {
  const result = await browserClient.sendCommand('Runtime.evaluate', {
    expression: `
      (() => {
        const counterEl = document.querySelector('${SELECTORS.characterCount}');
        if (!counterEl) return 280;
        
        const text = counterEl.textContent || '';
        const count = parseInt(text, 10);
        return isNaN(count) ? 280 : count;
      })()
    `,
    returnByValue: true
  });
  
  return result.result?.value ?? 280;
}

/**
 * Compose a tweet in the text area
 * @param {BrowserClient} browserClient - Connected browser client
 * @param {string} text - Tweet text content
 * @returns {Promise<{success: boolean, remainingChars: number, error?: string}>}
 */
export async function composeTweet(browserClient, text) {
  if (!browserClient.isConnected()) {
    throw new Error('Browser client not connected');
  }
  
  // Check character limit
  if (text.length > TWEET_MAX_LENGTH) {
    return {
      success: false,
      error: `Tweet exceeds ${TWEET_MAX_LENGTH} character limit (${text.length} chars)`,
      remainingChars: TWEET_MAX_LENGTH - text.length
    };
  }
  
  try {
    // Navigate to home to ensure composer is available
    await navigateAndWait(browserClient, 'https://x.com/home', 2000);
    
    // Wait for tweet composer
    await waitForElement(browserClient, SELECTORS.tweetComposer, 10000);
    
    // Click to focus composer
    await clickElement(browserClient, SELECTORS.tweetComposer);
    
    await new Promise(resolve => setTimeout(resolve, 500));
    
    // Type the tweet text
    await typeText(browserClient, SELECTORS.tweetComposer, text);
    
    // Get remaining character count
    const remainingChars = await getCharacterCount(browserClient);
    
    return {
      success: true,
      remainingChars,
      text
    };
    
  } catch (error) {
    return {
      success: false,
      error: error.message,
      remainingChars: TWEET_MAX_LENGTH - text.length
    };
  }
}

/**
 * Submit the composed tweet
 * @param {BrowserClient} browserClient - Connected browser client
 * @returns {Promise<{success: boolean, tweetId?: string, error?: string}>}
 */
export async function submitTweet(browserClient) {
  if (!browserClient.isConnected()) {
    throw new Error('Browser client not connected');
  }
  
  try {
    // Try timeline tweet button first, then inline button
    let buttonFound = false;
    
    try {
      await waitForElement(browserClient, SELECTORS.tweetButtonTimeline, 3000);
      buttonFound = true;
    } catch {
      try {
        await waitForElement(browserClient, SELECTORS.tweetButton, 3000);
        buttonFound = true;
      } catch {
        // Try inline button as last resort
        await waitForElement(browserClient, SELECTORS.tweetButtonInline, 2000);
        buttonFound = true;
      }
    }
    
    if (!buttonFound) {
      throw new Error('Tweet button not found');
    }
    
    // Click the tweet button
    const buttonSelector = buttonFound ? 
      (await browserClient.sendCommand('Runtime.evaluate', {
        expression: `
          document.querySelector('${SELECTORS.tweetButtonTimeline}') ? 
            '${SELECTORS.tweetButtonTimeline}' : 
          document.querySelector('${SELECTORS.tweetButton}') ? 
            '${SELECTORS.tweetButton}' : 
            '${SELECTORS.tweetButtonInline}'
        `,
        returnByValue: true
      })).result.value : SELECTORS.tweetButtonInline;
    
    await clickElement(browserClient, buttonSelector);
    
    // Wait for tweet to be posted
    await new Promise(resolve => setTimeout(resolve, 2000));
    
    // Check for success (URL change or success toast)
    const result = await browserClient.sendCommand('Runtime.evaluate', {
      expression: `
        (() => {
          // Check for success indicators
          const toast = document.querySelector('[data-testid="toast"]');
          if (toast && toast.textContent.includes('posted')) {
            return { success: true };
          }
          
          // Check if modal closed (tweet posted)
          const modal = document.querySelector('[data-testid="modal"]');
          if (!modal) {
            return { success: true };
          }
          
          // Check for error messages
          const errorEl = document.querySelector('[data-testid="error"]');
          if (errorEl) {
            return { success: false, error: errorEl.textContent };
          }
          
          return { success: true }; // Assume success if no errors
        })()
      `,
      returnByValue: true
    });
    
    const response = result.result?.value || { success: true };
    
    return response;
    
  } catch (error) {
    return {
      success: false,
      error: error.message
    };
  }
}

/**
 * Post a tweet (compose and submit)
 * @param {BrowserClient} browserClient - Connected browser client
 * @param {string} text - Tweet text content
 * @returns {Promise<{success: boolean, tweetId?: string, error?: string}>}
 */
export async function postTweet(browserClient, text) {
  const composeResult = await composeTweet(browserClient, text);
  
  if (!composeResult.success) {
    return composeResult;
  }
  
  return await submitTweet(browserClient);
}

/**
 * Compose a reply to a specific tweet
 * @param {BrowserClient} browserClient - Connected browser client
 * @param {string} tweetId - ID of tweet to reply to
 * @param {string} text - Reply text content
 * @returns {Promise<{success: boolean, error?: string}>}
 */
export async function composeReply(browserClient, tweetId, text) {
  if (!browserClient.isConnected()) {
    throw new Error('Browser client not connected');
  }
  
  // Check character limit
  if (text.length > TWEET_MAX_LENGTH) {
    return {
      success: false,
      error: `Reply exceeds ${TWEET_MAX_LENGTH} character limit (${text.length} chars)`
    };
  }
  
  try {
    // Navigate to the tweet
    const tweetUrl = `https://x.com/user/status/${tweetId}`;
    await navigateAndWait(browserClient, tweetUrl, 3000);
    
    // Click reply button
    await clickElement(browserClient, SELECTORS.replyButton);
    
    await new Promise(resolve => setTimeout(resolve, 1000));
    
    // Wait for reply composer
    await waitForElement(browserClient, SELECTORS.replyComposer, 5000);
    
    // Type the reply text
    await typeText(browserClient, SELECTORS.replyComposer, text);
    
    return {
      success: true,
      text,
      inReplyTo: tweetId
    };
    
  } catch (error) {
    return {
      success: false,
      error: error.message
    };
  }
}

/**
 * Submit a reply
 * @param {BrowserClient} browserClient - Connected browser client
 * @returns {Promise<{success: boolean, error?: string}>}
 */
export async function submitReply(browserClient) {
  // Reply uses the same tweet button
  return await submitTweet(browserClient);
}

/**
 * Reply to a tweet
 * @param {BrowserClient} browserClient - Connected browser client
 * @param {string} tweetId - ID of tweet to reply to
 * @param {string} text - Reply text content
 * @returns {Promise<{success: boolean, error?: string}>}
 */
export async function replyToTweet(browserClient, tweetId, text) {
  const composeResult = await composeReply(browserClient, tweetId, text);
  
  if (!composeResult.success) {
    return composeResult;
  }
  
  return await submitReply(browserClient);
}

/**
 * Like a tweet
 * @param {BrowserClient} browserClient - Connected browser client
 * @param {string} tweetId - ID of tweet to like
 * @returns {Promise<{success: boolean, error?: string}>}
 */
export async function likeTweet(browserClient, tweetId) {
  if (!browserClient.isConnected()) {
    throw new Error('Browser client not connected');
  }
  
  try {
    // Navigate to the tweet
    const tweetUrl = `https://x.com/user/status/${tweetId}`;
    await navigateAndWait(browserClient, tweetUrl, 2000);
    
    // Check if already liked
    const checkResult = await browserClient.sendCommand('Runtime.evaluate', {
      expression: `
        (() => {
          const likeBtn = document.querySelector('[data-testid="like"]');
          const unlikeBtn = document.querySelector('[data-testid="unlike"]');
          return {
            hasLikeBtn: !!likeBtn,
            hasUnlikeBtn: !!unlikeBtn,
            isLiked: !!unlikeBtn
          };
        })()
      `,
      returnByValue: true
    });
    
    const state = checkResult.result?.value || {};
    
    if (state.isLiked) {
      return {
        success: true,
        alreadyLiked: true,
        message: 'Tweet already liked'
      };
    }
    
    // Click like button
    await clickElement(browserClient, '[data-testid="like"]');
    
    await new Promise(resolve => setTimeout(resolve, 1000));
    
    // Verify like was successful
    const verifyResult = await browserClient.sendCommand('Runtime.evaluate', {
      expression: `
        document.querySelector('[data-testid="unlike"]') !== null
      `,
      returnByValue: true
    });
    
    return {
      success: verifyResult.result?.value ?? true,
      tweetId
    };
    
  } catch (error) {
    return {
      success: false,
      error: error.message
    };
  }
}

/**
 * Retweet a tweet
 * @param {BrowserClient} browserClient - Connected browser client
 * @param {string} tweetId - ID of tweet to retweet
 * @returns {Promise<{success: boolean, error?: string}>}
 */
export async function retweet(browserClient, tweetId) {
  if (!browserClient.isConnected()) {
    throw new Error('Browser client not connected');
  }
  
  try {
    // Navigate to the tweet
    const tweetUrl = `https://x.com/user/status/${tweetId}`;
    await navigateAndWait(browserClient, tweetUrl, 2000);
    
    // Check if already retweeted
    const checkResult = await browserClient.sendCommand('Runtime.evaluate', {
      expression: `
        (() => {
          const retweetBtn = document.querySelector('[data-testid="retweet"]');
          const unretweetBtn = document.querySelector('[data-testid="unretweet"]');
          return {
            hasRetweetBtn: !!retweetBtn,
            hasUnretweetBtn: !!unretweetBtn,
            isRetweeted: !!unretweetBtn
          };
        })()
      `,
      returnByValue: true
    });
    
    const state = checkResult.result?.value || {};
    
    if (state.isRetweeted) {
      return {
        success: true,
        alreadyRetweeted: true,
        message: 'Tweet already retweeted'
      };
    }
    
    // Click retweet button to open menu
    await clickElement(browserClient, '[data-testid="retweet"]');
    
    await new Promise(resolve => setTimeout(resolve, 500));
    
    // Click "Repost" or "Retweet" in the dropdown
    await browserClient.sendCommand('Runtime.evaluate', {
      expression: `
        (() => {
          const menuItems = document.querySelectorAll('[role="menuitem"]');
          for (const item of menuItems) {
            if (item.textContent.includes('Repost') || 
                item.textContent.includes('Retweet')) {
              item.click();
              return true;
            }
          }
          return false;
        })()
      `,
      returnByValue: true
    });
    
    await new Promise(resolve => setTimeout(resolve, 1000));
    
    // Verify retweet was successful
    const verifyResult = await browserClient.sendCommand('Runtime.evaluate', {
      expression: `
        document.querySelector('[data-testid="unretweet"]') !== null
      `,
      returnByValue: true
    });
    
    return {
      success: verifyResult.result?.value ?? true,
      tweetId
    };
    
  } catch (error) {
    return {
      success: false,
      error: error.message
    };
  }
}

/**
 * Quote tweet (retweet with comment)
 * @param {BrowserClient} browserClient - Connected browser client
 * @param {string} tweetId - ID of tweet to quote
 * @param {string} text - Quote tweet text
 * @returns {Promise<{success: boolean, error?: string}>}
 */
export async function quoteTweet(browserClient, tweetId, text) {
  if (!browserClient.isConnected()) {
    throw new Error('Browser client not connected');
  }
  
  try {
    // Navigate to the tweet
    const tweetUrl = `https://x.com/user/status/${tweetId}`;
    await navigateAndWait(browserClient, tweetUrl, 2000);
    
    // Click retweet button to open menu
    await clickElement(browserClient, '[data-testid="retweet"]');
    
    await new Promise(resolve => setTimeout(resolve, 500));
    
    // Click "Quote" in the dropdown
    await browserClient.sendCommand('Runtime.evaluate', {
      expression: `
        (() => {
          const menuItems = document.querySelectorAll('[role="menuitem"]');
          for (const item of menuItems) {
            if (item.textContent.includes('Quote')) {
              item.click();
              return true;
            }
          }
          return false;
        })()
      `,
      returnByValue: true
    });
    
    await new Promise(resolve => setTimeout(resolve, 1000));
    
    // Wait for quote composer
    await waitForElement(browserClient, SELECTORS.tweetComposer, 5000);
    
    // Type the quote text
    await typeText(browserClient, SELECTORS.tweetComposer, text);
    
    // Submit the quote tweet
    return await submitTweet(browserClient);
    
  } catch (error) {
    return {
      success: false,
      error: error.message
    };
  }
}

export default {
  composeTweet,
  submitTweet,
  postTweet,
  composeReply,
  submitReply,
  replyToTweet,
  likeTweet,
  retweet,
  quoteTweet,
  TWEET_MAX_LENGTH
};

// Export constant as named export
export { TWEET_MAX_LENGTH };
