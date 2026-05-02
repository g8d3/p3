/**
 * ContentFactory - Main module for content generation using z.ai API
 * Provides methods to generate tweets, threads, blog posts, and replies
 * Also handles content scheduling and posting
 */

import { config } from '../../../config/defaults.js';
import logger from '../../infrastructure/logger.js';
import {
  tweetGenerator,
  threadGenerator,
  blogGenerator,
  replyGenerator
} from './generators.js';

/**
 * ContentFactory class
 * Main interface for content generation and scheduling
 */
class ContentFactory {
  /**
   * Create a ContentFactory instance
   * @param {Object} stateManager - StateManager instance for persistence
   * @param {Object} customConfig - Optional config overrides
   */
  constructor(stateManager, customConfig = {}) {
    this.stateManager = stateManager;
    this.config = {
      llm: {
        ...config.llm,
        ...(customConfig.llm || {})
      },
      identity: {
        ...config.identity,
        ...(customConfig.identity || {})
      }
    };
    this.logger = logger.module('ContentFactory');
    this.initialized = false;
  }

  /**
   * Initialize the content factory
   * @returns {ContentFactory} this instance for chaining
   */
  init() {
    if (this.initialized) return this;
    
    // Validate API key
    if (!this.config.llm.apiKey) {
      this.logger.warn('No API key configured. Set GLM_API_KEY environment variable.');
    }
    
    this.initialized = true;
    this.logger.info('ContentFactory initialized', {
      model: this.config.llm.model,
      identity: this.config.identity.handle
    });
    
    return this;
  }

  /**
   * Call the z.ai LLM API
   * @param {string} systemPrompt - System prompt
   * @param {string} userPrompt - User prompt
   * @param {number} maxTokens - Maximum tokens to generate
   * @returns {Promise<string>} Generated text
   */
  async callLLM(systemPrompt, userPrompt, maxTokens = null) {
    if (!this.config.llm.apiKey) {
      throw new Error('API key not configured. Set GLM_API_KEY environment variable.');
    }

    const tokens = maxTokens || this.config.llm.maxTokens;
    
    const requestBody = {
      model: this.config.llm.model,
      messages: [
        { role: 'system', content: systemPrompt },
        { role: 'user', content: userPrompt }
      ],
      max_tokens: tokens
    };

    const url = `${this.config.llm.baseUrl}/chat/completions`;
    
    this.logger.debug('Calling LLM API', { 
      model: this.config.llm.model,
      maxTokens: tokens 
    });

    const startTime = Date.now();
    
    try {
      const response = await fetch(url, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${this.config.llm.apiKey}`
        },
        body: JSON.stringify(requestBody)
      });

      if (!response.ok) {
        const errorText = await response.text();
        throw new Error(`LLM API error: ${response.status} - ${errorText}`);
      }

      const data = await response.json();
      const content = data.choices?.[0]?.message?.content || '';
      
      const duration = Date.now() - startTime;
      this.logger.debug('LLM API response received', { 
        duration: `${duration}ms`,
        responseLength: content.length 
      });

      // Log the action if stateManager is available
      if (this.stateManager) {
        this.stateManager.logAction({
          module: 'ContentFactory',
          action: 'callLLM',
          params: { model: this.config.llm.model },
          result: { success: true, responseLength: content.length },
          durationMs: duration
        });
      }

      return content;
    } catch (error) {
      const duration = Date.now() - startTime;
      this.logger.error('LLM API call failed', { 
        error: error.message,
        duration: `${duration}ms`
      });

      // Log the error
      if (this.stateManager) {
        this.stateManager.logAction({
          module: 'ContentFactory',
          action: 'callLLM',
          params: { model: this.config.llm.model },
          error: error.message,
          durationMs: duration
        });
      }

      throw error;
    }
  }

  /**
   * Generate a single tweet
   * @param {string} context - Topic or context for the tweet
   * @returns {Promise<Object>} Generated tweet object
   */
  async generateTweet(context) {
    this._ensureInitialized();
    
    this.logger.info('Generating tweet', { context });
    
    const result = await tweetGenerator(
      (system, user) => this.callLLM(system, user),
      context
    );
    
    // Store in state
    if (this.stateManager) {
      this.stateManager.createContentItem({
        type: 'tweet',
        content: result.content,
        status: 'generated',
        platform: 'twitter'
      });
    }
    
    return result;
  }

  /**
   * Generate a tweet thread
   * @param {string} topic - Topic for the thread
   * @param {number} numTweets - Number of tweets (default: 5)
   * @returns {Promise<Object>} Generated thread object
   */
  async generateThread(topic, numTweets = 5) {
    this._ensureInitialized();
    
    this.logger.info('Generating thread', { topic, numTweets });
    
    const result = await threadGenerator(
      (system, user, tokens) => this.callLLM(system, user, tokens),
      topic,
      numTweets
    );
    
    // Store in state
    if (this.stateManager) {
      this.stateManager.createContentItem({
        type: 'thread',
        content: JSON.stringify(result.tweets),
        status: 'generated',
        platform: 'twitter'
      });
    }
    
    return result;
  }

  /**
   * Generate a blog post
   * @param {string} topic - Topic for the blog post
   * @returns {Promise<Object>} Generated blog post object
   */
  async generateBlogPost(topic) {
    this._ensureInitialized();
    
    this.logger.info('Generating blog post', { topic });
    
    const result = await blogGenerator(
      (system, user, tokens) => this.callLLM(system, user, tokens),
      topic
    );
    
    // Store in state
    if (this.stateManager) {
      this.stateManager.createContentItem({
        type: 'blog',
        content: result.content,
        status: 'generated',
        platform: 'blog'
      });
    }
    
    return result;
  }

  /**
   * Generate a reply to a tweet
   * @param {string} originalTweet - The tweet to reply to
   * @param {string} tone - Tone of the reply (helpful, curious, opinionated, excited)
   * @returns {Promise<Object>} Generated reply object
   */
  async generateReply(originalTweet, tone = 'helpful') {
    this._ensureInitialized();
    
    this.logger.info('Generating reply', { tone, tweetLength: originalTweet.length });
    
    const result = await replyGenerator(
      (system, user) => this.callLLM(system, user),
      originalTweet,
      tone
    );
    
    // Store in state
    if (this.stateManager) {
      this.stateManager.createContentItem({
        type: 'reply',
        content: result.content,
        status: 'generated',
        platform: 'twitter'
      });
    }
    
    return result;
  }

  /**
   * Schedule content for future posting
   * @param {Object} content - Content to schedule
   * @param {Date|string} postAt - When to post the content
   * @returns {Promise<Object>} Scheduled content object with ID
   */
  async scheduleContent(content, postAt) {
    this._ensureInitialized();
    
    if (!this.stateManager) {
      throw new Error('StateManager required for scheduling');
    }
    
    const postDate = typeof postAt === 'string' ? new Date(postAt) : postAt;
    
    if (postDate <= new Date()) {
      throw new Error('postAt must be in the future');
    }
    
    // Create a scheduled task
    const result = this.stateManager.query(
      `INSERT INTO scheduled_tasks (module, action, cron_expr, next_run, config, enabled)
       VALUES (?, ?, ?, ?, ?, ?)`,
      [
        'content',
        'post',
        '', // Not a cron job, one-time
        postDate.toISOString(),
        JSON.stringify({ content }),
        1
      ]
    );
    
    this.logger.info('Content scheduled', { 
      id: result.lastInsertRowid,
      postAt: postDate.toISOString()
    });
    
    return {
      id: result.lastInsertRowid,
      content,
      scheduledFor: postDate.toISOString(),
      status: 'scheduled'
    };
  }

  /**
   * Get all scheduled content that's due for posting
   * @returns {Promise<Array>} Array of due content items
   */
  async getScheduledContent() {
    this._ensureInitialized();
    
    if (!this.stateManager) {
      return [];
    }
    
    const now = new Date().toISOString();
    
    const tasks = this.stateManager.query(
      `SELECT * FROM scheduled_tasks 
       WHERE module = 'content' 
       AND action = 'post' 
       AND enabled = 1 
       AND next_run IS NOT NULL 
       AND next_run <= ?
       ORDER BY next_run ASC`,
      [now]
    );
    
    return tasks.map(task => ({
      id: task.id,
      content: JSON.parse(task.config || '{}').content,
      scheduledFor: task.next_run,
      status: 'due'
    }));
  }

  /**
   * Post any scheduled content that's due
   * @param {Function} postFunction - Function to call to actually post content
   * @returns {Promise<Object>} Results of posting
   */
  async postScheduled(postFunction) {
    this._ensureInitialized();
    
    const dueContent = await this.getScheduledContent();
    
    if (dueContent.length === 0) {
      this.logger.debug('No scheduled content due');
      return { posted: 0, failed: 0, results: [] };
    }
    
    const results = [];
    let posted = 0;
    let failed = 0;
    
    for (const item of dueContent) {
      try {
        this.logger.info('Posting scheduled content', { id: item.id });
        
        const result = await postFunction(item.content);
        
        // Mark as completed
        this.stateManager.query(
          `UPDATE scheduled_tasks SET enabled = 0, last_run = ? WHERE id = ?`,
          [new Date().toISOString(), item.id]
        );
        
        results.push({ id: item.id, success: true, result });
        posted++;
        
      } catch (error) {
        this.logger.error('Failed to post scheduled content', { 
          id: item.id, 
          error: error.message 
        });
        
        results.push({ id: item.id, success: false, error: error.message });
        failed++;
      }
    }
    
    return { posted, failed, results };
  }

  /**
   * Cancel scheduled content
   * @param {number} scheduleId - ID of scheduled content to cancel
   * @returns {Promise<boolean>} True if cancelled
   */
  async cancelScheduled(scheduleId) {
    this._ensureInitialized();
    
    if (!this.stateManager) {
      throw new Error('StateManager required for canceling scheduled content');
    }
    
    const result = this.stateManager.query(
      `UPDATE scheduled_tasks SET enabled = 0 WHERE id = ? AND module = 'content'`,
      [scheduleId]
    );
    
    const cancelled = result.changes > 0;
    
    if (cancelled) {
      this.logger.info('Cancelled scheduled content', { id: scheduleId });
    }
    
    return cancelled;
  }

  /**
   * Get generation statistics
   * @returns {Promise<Object>} Statistics about generated content
   */
  async getStats() {
    this._ensureInitialized();
    
    if (!this.stateManager) {
      return { enabled: false };
    }
    
    const byType = this.stateManager.query(
      `SELECT type, status, COUNT(*) as count 
       FROM content_items 
       GROUP BY type, status`
    );
    
    const scheduled = this.stateManager.query(
      `SELECT COUNT(*) as count FROM scheduled_tasks 
       WHERE module = 'content' AND enabled = 1`
    )[0]?.count || 0;
    
    return {
      enabled: true,
      byType: byType.reduce((acc, row) => {
        if (!acc[row.type]) acc[row.type] = {};
        acc[row.type][row.status] = row.count;
        return acc;
      }, {}),
      scheduledCount: scheduled
    };
  }

  /**
   * Ensure the factory is initialized
   * @private
   */
  _ensureInitialized() {
    if (!this.initialized) {
      throw new Error('ContentFactory not initialized. Call init() first.');
    }
  }
}

// Export class and default instance factory
export { ContentFactory };

/**
 * Create a ContentFactory instance
 * @param {Object} stateManager - StateManager instance
 * @param {Object} config - Configuration options
 * @returns {ContentFactory} Initialized ContentFactory
 */
export function createContentFactory(stateManager, config = {}) {
  const factory = new ContentFactory(stateManager, config);
  return factory.init();
}

export default ContentFactory;
