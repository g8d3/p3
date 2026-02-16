/**
 * ActionExecutor - Execute parsed AI commands
 * Handles sequential execution of action plans
 */

import { config } from '../../config/defaults.js';
import logger from '../infrastructure/logger.js';
import { ACTION_TYPES } from './commandParser.js';

/**
 * ActionExecutor class
 * Executes parsed actions from CommandParser
 */
class ActionExecutor {
  /**
   * Create an ActionExecutor instance
   * @param {Object} options - Configuration options
   * @param {Object} options.contentFactory - ContentFactory instance
   * @param {Object} options.stateManager - StateManager instance
   */
  constructor(options = {}) {
    this.contentFactory = options.contentFactory;
    this.stateManager = options.stateManager;
    this.logger = logger.module('ActionExecutor');
    this.initialized = false;
  }

  /**
   * Initialize the executor
   * @returns {ActionExecutor} this instance for chaining
   */
  init() {
    if (this.initialized) return this;
    
    this.logger.info('ActionExecutor initialized');
    this.initialized = true;
    
    return this;
  }

  /**
   * Execute a list of actions sequentially
   * @param {Array} actions - Array of action objects
   * @param {Object} context - Execution context
   * @returns {Promise<Object>} Execution results
   */
  async execute(actions, context = {}) {
    this._ensureInitialized();
    
    if (!Array.isArray(actions) || actions.length === 0) {
      return {
        success: true,
        executedActions: 0,
        results: [],
        message: 'No actions to execute'
      };
    }
    
    const results = [];
    let hasError = false;
    
    for (let i = 0; i < actions.length; i++) {
      const action = actions[i];
      
      this.logger.info('Executing action', { 
        type: action.type, 
        index: i + 1, 
        total: actions.length 
      });
      
      try {
        const result = await this._executeAction(action, context, results);
        
        results.push({
          action: action.type,
          success: true,
          result,
          index: i
        });
        
      } catch (error) {
        this.logger.error('Action failed', { 
          type: action.type, 
          error: error.message 
        });
        
        results.push({
          action: action.type,
          success: false,
          error: error.message,
          index: i
        });
        
        hasError = true;
        
        // Stop execution on critical errors
        if (this._isCriticalError(error)) {
          break;
        }
      }
    }
    
    return {
      success: !hasError,
      executedActions: results.length,
      totalActions: actions.length,
      results,
      completedAt: new Date().toISOString()
    };
  }

  /**
   * Execute a single action
   * @param {Object} action - Action object with type and params
   * @param {Object} context - Execution context
   * @param {Array} previousResults - Results from previous actions
   * @returns {Promise<*>} Action result
   */
  async _executeAction(action, context, previousResults) {
    const { type, params } = action;
    
    switch (type) {
      case ACTION_TYPES.GENERATE_CONTENT:
        return await this._generateContent(params, context, previousResults);
        
      case ACTION_TYPES.CREATE_CONTENT_ITEM:
        return await this._createContentItem(params, context, previousResults);
        
      case ACTION_TYPES.SCHEDULE_CONTENT:
        return await this._scheduleContent(params, context, previousResults);
        
      case ACTION_TYPES.PULL_BOOKMARKS:
        return await this._pullBookmarks(params, context);
        
      case ACTION_TYPES.ANALYZE_ENGAGEMENT:
        return await this._analyzeEngagement(params, context);
        
      case ACTION_TYPES.DELETE_CONTENT:
        return await this._deleteContent(params, context);
        
      case ACTION_TYPES.EDIT_CONTENT:
        return await this._editContent(params, context);
        
      default:
        throw new Error(`Unknown action type: ${type}`);
    }
  }

  /**
   * Generate content using ContentFactory
   * @param {Object} params - Generation parameters
   * @param {Object} context - Execution context
   * @param {Array} previousResults - Previous action results
   * @returns {Promise<Object>} Generated content
   */
  async _generateContent(params, context, previousResults) {
    if (!this.contentFactory) {
      throw new Error('ContentFactory not configured');
    }
    
    const { contentType, topic, tone } = params;
    
    this.logger.info('Generating content', { contentType, topic });
    
    let result;
    
    switch (contentType) {
      case 'tweet':
        result = await this.contentFactory.generateTweet(topic);
        break;
        
      case 'thread':
        result = await this.contentFactory.generateThread(topic, params.numTweets || 5);
        break;
        
      case 'blog':
        result = await this.contentFactory.generateBlogPost(topic);
        break;
        
      default:
        result = await this.contentFactory.generateTweet(topic);
    }
    
    return {
      contentType,
      topic,
      content: result.content || result.tweets || result,
      metadata: {
        characterCount: result.characterCount,
        wordCount: result.wordCount,
        totalTweets: result.totalTweets
      }
    };
  }

  /**
   * Create a content item in the database
   * @param {Object} params - Content item parameters
   * @param {Object} context - Execution context
   * @param {Array} previousResults - Previous action results (to get generated content)
   * @returns {Promise<Object>} Created content item
   */
  async _createContentItem(params, context, previousResults) {
    if (!this.stateManager) {
      throw new Error('StateManager not configured');
    }
    
    // Get content from previous generate action if available
    let content = params.content;
    const generateResult = previousResults.find(r => r.action === ACTION_TYPES.GENERATE_CONTENT);
    
    if (generateResult?.result?.content) {
      content = typeof generateResult.result.content === 'string' 
        ? generateResult.result.content 
        : JSON.stringify(generateResult.result.content);
    }
    
    if (!content) {
      throw new Error('No content to create item for');
    }
    
    const result = this.stateManager.createContentItem({
      type: params.contentType || 'tweet',
      content,
      status: params.status || 'draft',
      platform: params.platform || 'twitter'
    });
    
    return {
      id: result.lastInsertRowid,
      type: params.contentType,
      status: params.status || 'draft',
      message: 'Content item created'
    };
  }

  /**
   * Schedule content for future posting
   * @param {Object} params - Schedule parameters
   * @param {Object} context - Execution context
   * @param {Array} previousResults - Previous action results
   * @returns {Promise<Object>} Scheduled content info
   */
  async _scheduleContent(params, context, previousResults) {
    if (!this.stateManager) {
      throw new Error('StateManager not configured');
    }
    
    const { scheduledFor, contentType } = params;
    
    if (!scheduledFor) {
      throw new Error('scheduled_for is required for scheduling content');
    }
    
    // Get content from previous generate action if available
    let content = params.content;
    const generateResult = previousResults.find(r => r.action === ACTION_TYPES.GENERATE_CONTENT);
    
    if (generateResult?.result?.content) {
      content = generateResult.result.content;
    }
    
    const postDate = new Date(scheduledFor);
    
    if (postDate <= new Date()) {
      throw new Error('Scheduled time must be in the future');
    }
    
    // Create scheduled task
    const result = this.stateManager.query(
      `INSERT INTO scheduled_tasks (module, action, cron_expr, next_run, config, enabled)
       VALUES (?, ?, ?, ?, ?, ?)`,
      [
        'content',
        'post',
        '', // Not a cron job, one-time
        postDate.toISOString(),
        JSON.stringify({ content, contentType }),
        1
      ]
    );
    
    this.logger.info('Content scheduled', { 
      id: result.lastInsertRowid,
      scheduledFor: postDate.toISOString()
    });
    
    return {
      id: result.lastInsertRowid,
      scheduledFor: postDate.toISOString(),
      contentType,
      status: 'scheduled',
      message: `Content scheduled for ${postDate.toLocaleString()}`
    };
  }

  /**
   * Pull bookmarks from storage
   * @param {Object} params - Pull parameters
   * @param {Object} context - Execution context
   * @returns {Promise<Object>} Bookmarks
   */
  async _pullBookmarks(params, context) {
    if (!this.stateManager) {
      throw new Error('StateManager not configured');
    }
    
    const { limit = 10 } = params;
    
    // For now, return saved content items (could be extended to actual bookmarks)
    const bookmarks = this.stateManager.query(
      `SELECT * FROM content_items 
       WHERE status IN ('draft', 'generated') 
       ORDER BY created_at DESC 
       LIMIT ?`,
      [limit]
    );
    
    return {
      bookmarks: bookmarks.map(item => ({
        id: item.id,
        type: item.type,
        content: item.content,
        createdAt: item.created_at,
        platform: item.platform
      })),
      count: bookmarks.length,
      message: `Found ${bookmarks.length} saved items`
    };
  }

  /**
   * Analyze engagement metrics
   * @param {Object} params - Analysis parameters
   * @param {Object} context - Execution context
   * @returns {Promise<Object>} Engagement analysis
   */
  async _analyzeEngagement(params, context) {
    if (!this.stateManager) {
      throw new Error('StateManager not configured');
    }
    
    const { timeframe = '7d', contentType } = params;
    
    // Calculate date range
    const days = parseInt(timeframe) || 7;
    const startDate = new Date();
    startDate.setDate(startDate.getDate() - days);
    
    // Get posted content with engagement metrics
    let query = `SELECT * FROM content_items 
                 WHERE status = 'posted' 
                 AND posted_at >= ?`;
    const queryParams = [startDate.toISOString()];
    
    if (contentType) {
      query += ` AND type = ?`;
      queryParams.push(contentType);
    }
    
    query += ` ORDER BY posted_at DESC`;
    
    const items = this.stateManager.query(query, queryParams);
    
    // Aggregate metrics
    let totalLikes = 0;
    let totalRetweets = 0;
    let totalReplies = 0;
    let totalImpressions = 0;
    
    const analyzedItems = items.map(item => {
      const metrics = item.engagement_metrics ? JSON.parse(item.engagement_metrics) : {};
      totalLikes += metrics.likes || 0;
      totalRetweets += metrics.retweets || 0;
      totalReplies += metrics.replies || 0;
      totalImpressions += metrics.impressions || 0;
      
      return {
        id: item.id,
        type: item.type,
        postedAt: item.posted_at,
        metrics
      };
    });
    
    return {
      timeframe: `${days} days`,
      summary: {
        totalPosts: items.length,
        totalLikes,
        totalRetweets,
        totalReplies,
        totalImpressions,
        averageEngagement: items.length > 0 
          ? Math.round((totalLikes + totalRetweets + totalReplies) / items.length) 
          : 0
      },
      topContent: analyzedItems.slice(0, 5),
      message: `Analyzed ${items.length} posts from the last ${days} days`
    };
  }

  /**
   * Delete content
   * @param {Object} params - Delete parameters
   * @param {Object} context - Execution context
   * @returns {Promise<Object>} Delete result
   */
  async _deleteContent(params, context) {
    if (!this.stateManager) {
      throw new Error('StateManager not configured');
    }
    
    const { contentId } = params;
    
    if (!contentId) {
      throw new Error('contentId is required for deletion');
    }
    
    // Get the item first to confirm it exists
    const item = this.stateManager.queryOne(
      'SELECT * FROM content_items WHERE id = ?',
      [contentId]
    );
    
    if (!item) {
      throw new Error(`Content item not found: ${contentId}`);
    }
    
    // Delete the item
    this.stateManager.query(
      'DELETE FROM content_items WHERE id = ?',
      [contentId]
    );
    
    return {
      id: contentId,
      deleted: true,
      message: `Content item ${contentId} deleted`
    };
  }

  /**
   * Edit content
   * @param {Object} params - Edit parameters
   * @param {Object} context - Execution context
   * @returns {Promise<Object>} Edit result
   */
  async _editContent(params, context) {
    if (!this.stateManager) {
      throw new Error('StateManager not configured');
    }
    
    const { contentId, changes } = params;
    
    if (!contentId) {
      throw new Error('contentId is required for editing');
    }
    
    // Get the item first
    const item = this.stateManager.queryOne(
      'SELECT * FROM content_items WHERE id = ?',
      [contentId]
    );
    
    if (!item) {
      throw new Error(`Content item not found: ${contentId}`);
    }
    
    // Apply changes
    const updates = [];
    const values = [];
    
    if (changes.content) {
      updates.push('content = ?');
      values.push(changes.content);
    }
    
    if (changes.status) {
      updates.push('status = ?');
      values.push(changes.status);
    }
    
    if (updates.length === 0) {
      return {
        id: contentId,
        updated: false,
        message: 'No changes to apply'
      };
    }
    
    values.push(contentId);
    
    this.stateManager.query(
      `UPDATE content_items SET ${updates.join(', ')} WHERE id = ?`,
      values
    );
    
    return {
      id: contentId,
      updated: true,
      changes,
      message: `Content item ${contentId} updated`
    };
  }

  /**
   * Check if an error should stop execution
   * @param {Error} error - The error
   * @returns {boolean} True if critical
   */
  _isCriticalError(error) {
    const criticalMessages = [
      'API key not configured',
      'StateManager not configured',
      'ContentFactory not configured',
      'not initialized'
    ];
    
    return criticalMessages.some(msg => 
      error.message.toLowerCase().includes(msg.toLowerCase())
    );
  }

  /**
   * Ensure executor is initialized
   * @private
   */
  _ensureInitialized() {
    if (!this.initialized) {
      throw new Error('ActionExecutor not initialized. Call init() first.');
    }
  }
}

export { ActionExecutor };
export default ActionExecutor;
