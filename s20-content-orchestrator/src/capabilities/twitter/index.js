/**
 * TwitterService - Main facade for X.com automation via Chrome CDP
 * 
 * Provides high-level methods for:
 * - Feed monitoring and mentions extraction
 * - Tweet composition, posting, and replying
 * - Engagement metrics collection
 * 
 * All actions respect rate limits and dry-run mode.
 * Posting actions require approval if configured.
 */

import { config } from '../../../config/defaults.js';
import { Logger } from '../../infrastructure/logger.js';
import {
  extractTweetsFromPage,
  extractMentions,
  extractBookmarks,
  getHomeFeed,
  scrollPage,
  URLS as MONITOR_URLS
} from './monitor.js';
import {
  composeTweet,
  submitTweet,
  postTweet as doPostTweet,
  replyToTweet,
  likeTweet as doLikeTweet,
  retweet as doRetweet,
  quoteTweet,
  TWEET_MAX_LENGTH
} from './post.js';
import {
  getTweetMetrics,
  getBatchMetrics,
  getTweetMetricsById,
  extractPageMetrics,
  calculateEngagementRate,
  compareMetrics
} from './engagement.js';

const logger = new Logger('twitter');

/**
 * TwitterService - Main service class for X.com automation
 */
export class TwitterService {
  /**
   * Create a TwitterService instance
   * @param {object} options - Configuration options
   * @param {BrowserClient} options.browserClient - Connected browser client
   * @param {StateManager} options.stateManager - State persistence manager
   * @param {RateLimiter} options.rateLimiter - Rate limiter instance
   * @param {DryRun} options.dryRun - Dry-run wrapper
   * @param {Approval} options.approval - Approval system
   */
  constructor(options = {}) {
    this.browserClient = options.browserClient;
    this.stateManager = options.stateManager;
    this.rateLimiter = options.rateLimiter;
    this.dryRun = options.dryRun;
    this.approval = options.approval;
    
    // Configuration
    this.requireApproval = config.safety.requireApproval;
    this.identity = config.identity;
    
    // State keys
    this.STATE_KEYS = {
      lastMentionId: 'twitter:lastMentionId',
      lastBookmarkSync: 'twitter:lastBookmarkSync',
      postedTweets: 'twitter:postedTweets'
    };
  }
  
  /**
   * Ensure browser is connected
   * @throws {Error} If browser is not connected
   */
  _ensureConnected() {
    if (!this.browserClient || !this.browserClient.isConnected()) {
      throw new Error('Browser client not connected');
    }
  }
  
  /**
   * Check rate limit for an action
   * @param {string} actionType - Type of action (tweet, reply, like, etc.)
   * @returns {Promise<{allowed: boolean, remaining: number}>}
   */
  async _checkRateLimit(actionType) {
    if (!this.rateLimiter) {
      return { allowed: true, remaining: Infinity };
    }
    
    return await this.rateLimiter.checkLimit(actionType);
  }
  
  /**
   * Record an action for rate limiting
   * @param {string} actionType - Type of action
   */
  async _recordAction(actionType) {
    if (this.rateLimiter) {
      await this.rateLimiter.recordAction(actionType);
    }
  }
  
  /**
   * Execute an action with dry-run check
   * @param {string} actionName - Name of the action
   * @param {object} actionData - Action data for logging
   * @param {Function} actionFn - Action function to execute
   * @returns {Promise<object>} Action result
   */
  async _executeWithDryRun(actionName, actionData, actionFn) {
    if (this.dryRun && this.dryRun.isEnabled()) {
      return await this.dryRun.wrapWithDetails(actionName, actionData, actionFn);
    }
    
    try {
      const result = await actionFn();
      return { simulated: false, success: true, result };
    } catch (error) {
      return { simulated: false, success: false, error: error.message };
    }
  }
  
  /**
   * Request approval for a posting action
   * @param {string} actionType - Type of action
   * @param {object} actionData - Action data
   * @returns {Promise<{approved: boolean, approvalId?: string}>}
   */
  async _requestApproval(actionType, actionData) {
    if (!this.requireApproval || !this.approval) {
      return { approved: true };
    }
    
    const result = await this.approval.requestApproval(actionType, actionData);
    
    if (!result.requiresApproval) {
      return { approved: true };
    }
    
    logger.info(`Approval requested for ${actionType}`, { approvalId: result.id });
    
    return {
      approved: false,
      approvalId: result.id,
      message: `Action requires approval. ID: ${result.id}`
    };
  }
  
  // ===========================================
  // Monitoring Methods
  // ===========================================
  
  /**
   * Check for new mentions
   * Navigates to notifications and extracts new mentions since last check
   * @returns {Promise<{mentions: Array, count: number}>}
   */
  async checkMentions() {
    this._ensureConnected();
    
    logger.info('Checking for new mentions');
    
    try {
      // Get last checked mention ID
      const lastCheckedId = this.stateManager ?
        await this.stateManager.get(this.STATE_KEYS.lastMentionId) : null;
      
      // Extract mentions from notifications page
      const mentions = await extractMentions(this.browserClient, lastCheckedId);
      
      // Update last checked ID
      if (mentions.length > 0 && this.stateManager) {
        await this.stateManager.set(this.STATE_KEYS.lastMentionId, mentions[0].tweetId);
      }
      
      logger.info(`Found ${mentions.length} new mentions`);
      
      return {
        mentions,
        count: mentions.length,
        lastCheckedId
      };
      
    } catch (error) {
      logger.error('Failed to check mentions', { error: error.message });
      throw error;
    }
  }
  
  /**
   * Sync bookmarks from X.com
   * Navigates to bookmarks and extracts bookmarked tweets
   * @param {number} limit - Maximum bookmarks to extract
   * @returns {Promise<{bookmarks: Array, count: number}>}
   */
  async syncBookmarks(limit = 100) {
    this._ensureConnected();
    
    logger.info('Syncing bookmarks', { limit });
    
    try {
      const bookmarks = await extractBookmarks(this.browserClient, limit);
      
      // Update last sync time
      if (this.stateManager) {
        await this.stateManager.set(this.STATE_KEYS.lastBookmarkSync, new Date().toISOString());
      }
      
      logger.info(`Synced ${bookmarks.length} bookmarks`);
      
      return {
        bookmarks,
        count: bookmarks.length,
        syncedAt: new Date().toISOString()
      };
      
    } catch (error) {
      logger.error('Failed to sync bookmarks', { error: error.message });
      throw error;
    }
  }
  
  /**
   * Get tweets from home feed
   * @param {number} count - Number of tweets to fetch
   * @returns {Promise<{tweets: Array, count: number}>}
   */
  async getFeed(count = 50) {
    this._ensureConnected();
    
    logger.info('Fetching home feed', { count });
    
    try {
      const tweets = await getHomeFeed(this.browserClient, count);
      
      return {
        tweets,
        count: tweets.length
      };
      
    } catch (error) {
      logger.error('Failed to get feed', { error: error.message });
      throw error;
    }
  }
  
  // ===========================================
  // Posting Methods
  // ===========================================
  
  /**
   * Post a tweet
   * @param {string} content - Tweet content
   * @param {object} options - Additional options
   * @param {Array} options.media - Media attachments (not implemented)
   * @returns {Promise<{success: boolean, tweetId?: string, error?: string}>}
   */
  async postTweet(content, options = {}) {
    this._ensureConnected();
    
    // Check character limit
    if (content.length > TWEET_MAX_LENGTH) {
      return {
        success: false,
        error: `Tweet exceeds ${TWEET_MAX_LENGTH} character limit`
      };
    }
    
    // Check rate limit
    const rateCheck = await this._checkRateLimit('tweet');
    if (!rateCheck.allowed) {
      return {
        success: false,
        error: 'Rate limit exceeded for tweets',
        retryIn: rateCheck.resetIn
      };
    }
    
    // Request approval if required
    const approval = await this._requestApproval('tweet', { content, options });
    if (!approval.approved) {
      return {
        success: false,
        requiresApproval: true,
        approvalId: approval.approvalId,
        message: approval.message
      };
    }
    
    // Execute with dry-run check
    const result = await this._executeWithDryRun(
      'postTweet',
      { content, options },
      async () => {
        return await doPostTweet(this.browserClient, content);
      }
    );
    
    // Record action and save to state if successful
    if (result.success || result.simulated) {
      await this._recordAction('tweet');
      
      if (this.stateManager && result.result?.tweetId) {
        const postedTweets = await this.stateManager.get(this.STATE_KEYS.postedTweets) || [];
        postedTweets.unshift({
          tweetId: result.result.tweetId,
          content,
          postedAt: new Date().toISOString()
        });
        await this.stateManager.set(this.STATE_KEYS.postedTweets, postedTweets.slice(0, 100));
      }
      
      logger.info('Tweet posted successfully', { 
        content: content.substring(0, 50) + '...',
        simulated: result.simulated 
      });
    }
    
    return result;
  }
  
  /**
   * Reply to a tweet
   * @param {string} tweetId - ID of tweet to reply to
   * @param {string} content - Reply content
   * @returns {Promise<{success: boolean, error?: string}>}
   */
  async replyTo(tweetId, content, options = {}) {
    this._ensureConnected();
    
    if (!tweetId) {
      return { success: false, error: 'Tweet ID is required' };
    }
    
    if (content.length > TWEET_MAX_LENGTH) {
      return {
        success: false,
        error: `Reply exceeds ${TWEET_MAX_LENGTH} character limit`
      };
    }
    
    // Check rate limit
    const rateCheck = await this._checkRateLimit('reply');
    if (!rateCheck.allowed) {
      return {
        success: false,
        error: 'Rate limit exceeded for replies',
        retryIn: rateCheck.resetIn
      };
    }
    
    // Request approval if required
    const approval = await this._requestApproval('reply', { tweetId, content });
    if (!approval.approved) {
      return {
        success: false,
        requiresApproval: true,
        approvalId: approval.approvalId
      };
    }
    
    // Execute with dry-run check
    const result = await this._executeWithDryRun(
      'replyToTweet',
      { tweetId, content },
      async () => {
        return await replyToTweet(this.browserClient, tweetId, content);
      }
    );
    
    if (result.success || result.simulated) {
      await this._recordAction('reply');
      logger.info('Reply posted', { tweetId, simulated: result.simulated });
    }
    
    return result;
  }
  
  /**
   * Like a tweet
   * @param {string} tweetId - ID of tweet to like
   * @returns {Promise<{success: boolean, error?: string}>}
   */
  async likeTweet(tweetId) {
    this._ensureConnected();
    
    if (!tweetId) {
      return { success: false, error: 'Tweet ID is required' };
    }
    
    // Check rate limit
    const rateCheck = await this._checkRateLimit('like');
    if (!rateCheck.allowed) {
      return {
        success: false,
        error: 'Rate limit exceeded for likes',
        retryIn: rateCheck.resetIn
      };
    }
    
    // Likes typically don't require approval, but check anyway
    const approval = await this._requestApproval('like', { tweetId });
    if (!approval.approved) {
      return {
        success: false,
        requiresApproval: true,
        approvalId: approval.approvalId
      };
    }
    
    // Execute with dry-run check
    const result = await this._executeWithDryRun(
      'likeTweet',
      { tweetId },
      async () => {
        return await doLikeTweet(this.browserClient, tweetId);
      }
    );
    
    if (result.success || result.simulated) {
      await this._recordAction('like');
      logger.info('Tweet liked', { tweetId, simulated: result.simulated });
    }
    
    return result;
  }
  
  /**
   * Retweet a tweet
   * @param {string} tweetId - ID of tweet to retweet
   * @returns {Promise<{success: boolean, error?: string}>}
   */
  async retweet(tweetId) {
    this._ensureConnected();
    
    if (!tweetId) {
      return { success: false, error: 'Tweet ID is required' };
    }
    
    // Check rate limit (use tweet limit for retweets)
    const rateCheck = await this._checkRateLimit('tweet');
    if (!rateCheck.allowed) {
      return {
        success: false,
        error: 'Rate limit exceeded',
        retryIn: rateCheck.resetIn
      };
    }
    
    // Request approval if required
    const approval = await this._requestApproval('retweet', { tweetId });
    if (!approval.approved) {
      return {
        success: false,
        requiresApproval: true,
        approvalId: approval.approvalId
      };
    }
    
    // Execute with dry-run check
    const result = await this._executeWithDryRun(
      'retweet',
      { tweetId },
      async () => {
        return await doRetweet(this.browserClient, tweetId);
      }
    );
    
    if (result.success || result.simulated) {
      await this._recordAction('tweet');
      logger.info('Tweet retweeted', { tweetId, simulated: result.simulated });
    }
    
    return result;
  }
  
  /**
   * Quote tweet (retweet with comment)
   * @param {string} tweetId - ID of tweet to quote
   * @param {string} content - Quote comment
   * @returns {Promise<{success: boolean, error?: string}>}
   */
  async quoteTweet(tweetId, content) {
    this._ensureConnected();
    
    if (!tweetId) {
      return { success: false, error: 'Tweet ID is required' };
    }
    
    if (content.length > TWEET_MAX_LENGTH) {
      return {
        success: false,
        error: `Quote exceeds ${TWEET_MAX_LENGTH} character limit`
      };
    }
    
    // Check rate limit
    const rateCheck = await this._checkRateLimit('tweet');
    if (!rateCheck.allowed) {
      return {
        success: false,
        error: 'Rate limit exceeded',
        retryIn: rateCheck.resetIn
      };
    }
    
    // Request approval if required
    const approval = await this._requestApproval('quoteTweet', { tweetId, content });
    if (!approval.approved) {
      return {
        success: false,
        requiresApproval: true,
        approvalId: approval.approvalId
      };
    }
    
    // Execute with dry-run check
    const result = await this._executeWithDryRun(
      'quoteTweet',
      { tweetId, content },
      async () => {
        return await quoteTweet(this.browserClient, tweetId, content);
      }
    );
    
    if (result.success || result.simulated) {
      await this._recordAction('tweet');
      logger.info('Quote tweet posted', { tweetId, simulated: result.simulated });
    }
    
    return result;
  }
  
  // ===========================================
  // Engagement Methods
  // ===========================================
  
  /**
   * Collect engagement metrics for posted tweets
   * @returns {Promise<{tweets: Array, summary: object}>}
   */
  async collectEngagement() {
    this._ensureConnected();
    
    logger.info('Collecting engagement metrics');
    
    try {
      // Get posted tweets from state
      const postedTweets = this.stateManager ?
        await this.stateManager.get(this.STATE_KEYS.postedTweets) || [] : [];
      
      if (postedTweets.length === 0) {
        return {
          tweets: [],
          summary: {
            totalTweets: 0,
            totalEngagements: 0
          }
        };
      }
      
      // Collect metrics for each tweet
      const tweetMetrics = [];
      let totalLikes = 0;
      let totalRetweets = 0;
      let totalReplies = 0;
      let totalViews = 0;
      
      for (const tweet of postedTweets.slice(0, 20)) { // Limit to 20 most recent
        try {
          const tweetUrl = `https://x.com/${this.identity.handle}/status/${tweet.tweetId}`;
          const metrics = await getTweetMetrics(this.browserClient, tweetUrl);
          
          if (metrics.success) {
            tweetMetrics.push({
              ...tweet,
              metrics: metrics.metrics
            });
            
            totalLikes += metrics.metrics.likes || 0;
            totalRetweets += metrics.metrics.retweets || 0;
            totalReplies += metrics.metrics.replies || 0;
            totalViews += metrics.metrics.views || 0;
          }
          
          // Delay between requests
          await new Promise(resolve => setTimeout(resolve, 2000));
          
        } catch (error) {
          logger.warn('Failed to get metrics for tweet', { 
            tweetId: tweet.tweetId, 
            error: error.message 
          });
        }
      }
      
      // Update stored metrics
      if (this.stateManager) {
        await this.stateManager.set(this.STATE_KEYS.postedTweets, postedTweets);
      }
      
      const summary = {
        totalTweets: tweetMetrics.length,
        totalEngagements: totalLikes + totalRetweets + totalReplies,
        totalLikes,
        totalRetweets,
        totalReplies,
        totalViews,
        averageEngagementRate: totalViews > 0 ? 
          ((totalLikes + totalRetweets + totalReplies) / totalViews * 100).toFixed(2) : 0
      };
      
      logger.info('Engagement metrics collected', summary);
      
      return {
        tweets: tweetMetrics,
        summary,
        collectedAt: new Date().toISOString()
      };
      
    } catch (error) {
      logger.error('Failed to collect engagement', { error: error.message });
      throw error;
    }
  }
  
  /**
   * Get metrics for a specific tweet
   * @param {string} tweetUrl - Full URL to the tweet
   * @returns {Promise<object>} Tweet metrics
   */
  async getTweetMetrics(tweetUrl) {
    this._ensureConnected();
    return await getTweetMetrics(this.browserClient, tweetUrl);
  }
  
  /**
   * Get engagement analytics for tweets
   * @param {Array<string>} tweetUrls - Array of tweet URLs
   * @returns {Promise<Array>} Array of tweet metrics
   */
  async getBatchMetrics(tweetUrls) {
    this._ensureConnected();
    return await getBatchMetrics(this.browserClient, tweetUrls);
  }
  
  // ===========================================
  // Utility Methods
  // ===========================================
  
  /**
   * Get service status
   * @returns {object} Service status
   */
  getStatus() {
    return {
      connected: this.browserClient?.isConnected() || false,
      dryRunEnabled: this.dryRun?.isEnabled() || false,
      requireApproval: this.requireApproval,
      identity: this.identity
    };
  }
  
  /**
   * Get remaining rate limits
   * @returns {Promise<object>} Rate limit status
   */
  async getRateLimitStatus() {
    if (!this.rateLimiter) {
      return { available: false };
    }
    
    return {
      available: true,
      tweet: await this.rateLimiter.getRemaining('tweet'),
      reply: await this.rateLimiter.getRemaining('reply'),
      like: await this.rateLimiter.getRemaining('like')
    };
  }
}

// Export for module usage
export default TwitterService;

// Also export submodules for direct access
export {
  // Monitor functions
  extractTweetsFromPage,
  extractMentions,
  extractBookmarks,
  getHomeFeed,
  
  // Post functions
  composeTweet,
  submitTweet,
  replyToTweet,
  quoteTweet,
  TWEET_MAX_LENGTH,
  
  // Engagement functions
  getTweetMetrics,
  getBatchMetrics,
  calculateEngagementRate,
  compareMetrics
};
