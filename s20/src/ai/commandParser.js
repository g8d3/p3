/**
 * CommandParser - Parse natural language to structured commands using z.ai GLM-4
 * Handles intent detection, entity extraction, and action generation
 */

import { config } from '../../config/defaults.js';
import logger from '../infrastructure/logger.js';

/**
 * Supported intents for the AI command parser
 */
const INTENTS = {
  CREATE_CONTENT: 'create_content',
  SCHEDULE_TASK: 'schedule_task',
  EDIT_CONTENT: 'edit_content',
  DELETE_CONTENT: 'delete_content',
  PULL_BOOKMARKS: 'pull_bookmarks',
  ANALYZE_ENGAGEMENT: 'analyze_engagement',
  HELP: 'help'
};

/**
 * Action types that can be executed
 */
const ACTION_TYPES = {
  GENERATE_CONTENT: 'generate_content',
  CREATE_CONTENT_ITEM: 'create_content_item',
  SCHEDULE_CONTENT: 'schedule_content',
  PULL_BOOKMARKS: 'pull_bookmarks',
  ANALYZE_ENGAGEMENT: 'analyze_engagement',
  DELETE_CONTENT: 'delete_content',
  EDIT_CONTENT: 'edit_content'
};

/**
 * Content type mapping
 */
const CONTENT_TYPES = {
  tweet: 'tweet',
  thread: 'thread',
  blog: 'blog',
  post: 'tweet',
  article: 'blog'
};

/**
 * Simple date parser (basic chrono-node like functionality)
 * In production, you'd use the actual chrono-node package
 */
function parseDate(text) {
  const now = new Date();
  const lowerText = text.toLowerCase();
  
  // Relative dates
  if (lowerText.includes('now')) {
    return now.toISOString();
  }
  
  if (lowerText.includes('today')) {
    const today = new Date(now.getFullYear(), now.getMonth(), now.getDate());
    if (lowerText.includes('at')) {
      const timeMatch = text.match(/at\s+(\d{1,2})(?::(\d{2}))?\s*(am|pm)?/i);
      if (timeMatch) {
        let hours = parseInt(timeMatch[1]);
        const minutes = timeMatch[2] ? parseInt(timeMatch[2]) : 0;
        const meridiem = timeMatch[3]?.toLowerCase();
        
        if (meridiem === 'pm' && hours !== 12) hours += 12;
        if (meridiem === 'am' && hours === 12) hours = 0;
        
        today.setHours(hours, minutes, 0, 0);
      }
    }
    return today.toISOString();
  }
  
  if (lowerText.includes('tomorrow')) {
    const tomorrow = new Date(now.getFullYear(), now.getMonth(), now.getDate() + 1);
    if (lowerText.includes('at')) {
      const timeMatch = text.match(/at\s+(\d{1,2})(?::(\d{2}))?\s*(am|pm)?/i);
      if (timeMatch) {
        let hours = parseInt(timeMatch[1]);
        const minutes = timeMatch[2] ? parseInt(timeMatch[2]) : 0;
        const meridiem = timeMatch[3]?.toLowerCase();
        
        if (meridiem === 'pm' && hours !== 12) hours += 12;
        if (meridiem === 'am' && hours === 12) hours = 0;
        
        tomorrow.setHours(hours, minutes, 0, 0);
      }
    }
    return tomorrow.toISOString();
  }
  
  // Specific day names
  const days = ['sunday', 'monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday'];
  for (let i = 0; i < days.length; i++) {
    if (lowerText.includes(days[i])) {
      const targetDay = i;
      const currentDay = now.getDay();
      let daysUntil = targetDay - currentDay;
      if (daysUntil <= 0) daysUntil += 7;
      
      const target = new Date(now.getFullYear(), now.getMonth(), now.getDate() + daysUntil);
      if (lowerText.includes('at')) {
        const timeMatch = text.match(/at\s+(\d{1,2})(?::(\d{2}))?\s*(am|pm)?/i);
        if (timeMatch) {
          let hours = parseInt(timeMatch[1]);
          const minutes = timeMatch[2] ? parseInt(timeMatch[2]) : 0;
          const meridiem = timeMatch[3]?.toLowerCase();
          
          if (meridiem === 'pm' && hours !== 12) hours += 12;
          if (meridiem === 'am' && hours === 12) hours = 0;
          
          target.setHours(hours, minutes, 0, 0);
        }
      }
      return target.toISOString();
    }
  }
  
  // ISO date format
  const isoMatch = text.match(/\d{4}-\d{2}-\d{2}(?:T\d{2}:\d{2}:\d{2})?/);
  if (isoMatch) {
    return new Date(isoMatch[0]).toISOString();
  }
  
  // Time only (e.g., "at 3pm")
  const timeOnlyMatch = text.match(/at\s+(\d{1,2})(?::(\d{2}))?\s*(am|pm)?/i);
  if (timeOnlyMatch) {
    let hours = parseInt(timeOnlyMatch[1]);
    const minutes = timeOnlyMatch[2] ? parseInt(timeOnlyMatch[2]) : 0;
    const meridiem = timeOnlyMatch[3]?.toLowerCase();
    
    if (meridiem === 'pm' && hours !== 12) hours += 12;
    if (meridiem === 'am' && hours === 12) hours = 0;
    
    const target = new Date(now.getFullYear(), now.getMonth(), now.getDate(), hours, minutes, 0, 0);
    if (target <= now) {
      target.setDate(target.getDate() + 1);
    }
    return target.toISOString();
  }
  
  return null;
}

/**
 * CommandParser class
 * Parses natural language into structured commands using GLM-4
 */
class CommandParser {
  /**
   * Create a CommandParser instance
   * @param {Object} options - Configuration options
   */
  constructor(options = {}) {
    this.config = {
      llm: {
        ...config.llm,
        ...(options.llm || {})
      }
    };
    this.confidenceThreshold = options.confidenceThreshold || 0.7;
    this.logger = logger.module('CommandParser');
    this.initialized = false;
  }

  /**
   * Initialize the parser
   * @returns {CommandParser} this instance for chaining
   */
  init() {
    if (this.initialized) return this;
    
    if (!this.config.llm.apiKey) {
      this.logger.warn('No API key configured. Set GLM_API_KEY environment variable.');
    }
    
    this.initialized = true;
    this.logger.info('CommandParser initialized', {
      model: this.config.llm.model,
      confidenceThreshold: this.confidenceThreshold
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
  async callLLM(systemPrompt, userPrompt, maxTokens = 1500) {
    if (!this.config.llm.apiKey) {
      throw new Error('API key not configured. Set GLM_API_KEY environment variable.');
    }

    const requestBody = {
      model: this.config.llm.model,
      messages: [
        { role: 'system', content: systemPrompt },
        { role: 'user', content: userPrompt }
      ],
      max_tokens: maxTokens
    };

    const url = `${this.config.llm.baseUrl}/chat/completions`;
    
    this.logger.debug('Calling LLM API for command parsing');

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
    return data.choices?.[0]?.message?.content || '';
  }

  /**
   * Build the system prompt for intent parsing
   * @returns {string} System prompt
   */
  _buildSystemPrompt() {
    return `You are an AI command parser for a content management system. Your job is to parse natural language commands into structured JSON.

Analyze the user's input and return a JSON object with:
1. "intent": One of these intents:
   - "create_content": User wants to create new content (tweet, thread, blog)
   - "schedule_task": User wants to schedule something for later
   - "edit_content": User wants to modify existing content
   - "delete_content": User wants to remove content
   - "pull_bookmarks": User wants to retrieve saved/bookmarked items
   - "analyze_engagement": User wants analytics or engagement data
   - "help": User is asking for help or instructions

2. "confidence": A number from 0 to 1 indicating how confident you are in the intent detection

3. "entities": Extract relevant entities like:
   - "content_type": "tweet", "thread", or "blog"
   - "topic": The subject matter
   - "scheduled_for": ISO date string if scheduling
   - "content_id": ID if referencing specific content
   - "tone": "helpful", "curious", "opinionated", "excited"

4. "actions": Array of action objects with "type" and "params"
   - generate_content: Generate new content
   - create_content_item: Store content in database
   - schedule_content: Schedule for future posting
   - pull_bookmarks: Retrieve bookmarked items
   - analyze_engagement: Get engagement metrics

5. "summary": A friendly one-sentence summary of what you'll do

6. "clarification": If confidence < 0.7, provide a clarifying question

Return ONLY valid JSON, no markdown formatting.`;
  }

  /**
   * Parse natural language input into a structured command
   * @param {string} input - Natural language input
   * @param {Object} context - Additional context (user info, etc.)
   * @returns {Promise<Object>} Parsed command object
   */
  async parse(input, context = {}) {
    this._ensureInitialized();
    
    this.logger.info('Parsing command', { input: input.slice(0, 100) });
    
    const systemPrompt = this._buildSystemPrompt();
    const userPrompt = `Parse this command: "${input}"

Context: ${JSON.stringify(context)}
Current date/time: ${new Date().toISOString()}

Return the parsed command as JSON.`;

    try {
      const response = await this.callLLM(systemPrompt, userPrompt);
      let parsed = this._parseJsonResponse(response);
      
      // Apply local date parsing as backup/enhancement
      if (!parsed.entities?.scheduled_for && input.toLowerCase().match(/tomorrow|today|at \d|monday|tuesday|wednesday|thursday|friday|saturday|sunday/)) {
        const dateResult = parseDate(input);
        if (dateResult) {
          if (!parsed.entities) parsed.entities = {};
          parsed.entities.scheduled_for = dateResult;
        }
      }
      
      // Normalize content type
      if (parsed.entities?.content_type) {
        parsed.entities.content_type = CONTENT_TYPES[parsed.entities.content_type.toLowerCase()] || parsed.entities.content_type;
      }
      
      // Add clarification if confidence is low
      if (parsed.confidence < this.confidenceThreshold && !parsed.clarification) {
        parsed.clarification = this._generateClarification(parsed);
        parsed.status = 'needs_clarification';
      } else {
        parsed.status = 'ready';
      }
      
      // Ensure required fields
      parsed = this._normalizeCommand(parsed, input);
      
      this.logger.debug('Command parsed', { intent: parsed.intent, confidence: parsed.confidence });
      
      return parsed;
      
    } catch (error) {
      this.logger.error('Failed to parse command', { error: error.message });
      
      // Return a fallback parsed command
      return this._fallbackParse(input, error);
    }
  }

  /**
   * Parse JSON response from LLM
   * @param {string} text - Raw response text
   * @returns {Object} Parsed JSON
   */
  _parseJsonResponse(text) {
    try {
      return JSON.parse(text);
    } catch {
      // Try extracting JSON from markdown code blocks
      const jsonMatch = text.match(/```(?:json)?\s*([\s\S]*?)```/);
      if (jsonMatch) {
        try {
          return JSON.parse(jsonMatch[1].trim());
        } catch {
          // Fall through
        }
      }
      
      // Try finding JSON object in text
      const objectMatch = text.match(/\{[\s\S]*\}/);
      if (objectMatch) {
        try {
          return JSON.parse(objectMatch[0]);
        } catch {
          // Fall through
        }
      }
    }
    
    // Return default structure
    return {
      intent: 'help',
      confidence: 0.3,
      entities: {},
      actions: [],
      summary: 'I couldn\'t understand that command. Type "help" for available commands.'
    };
  }

  /**
   * Normalize and validate the parsed command
   * @param {Object} parsed - Parsed command
   * @param {string} input - Original input
   * @returns {Object} Normalized command
   */
  _normalizeCommand(parsed, input) {
    // Ensure intent is valid
    if (!Object.values(INTENTS).includes(parsed.intent)) {
      parsed.intent = INTENTS.HELP;
      parsed.confidence = Math.min(parsed.confidence, 0.5);
    }
    
    // Ensure entities object exists
    if (!parsed.entities) {
      parsed.entities = {};
    }
    
    // Ensure actions array exists
    if (!Array.isArray(parsed.actions)) {
      parsed.actions = [];
    }
    
    // Generate actions if missing
    if (parsed.actions.length === 0) {
      parsed.actions = this._generateActions(parsed);
    }
    
    // Ensure summary exists
    if (!parsed.summary) {
      parsed.summary = this._generateSummary(parsed);
    }
    
    // Store original input
    parsed.originalInput = input;
    parsed.parsedAt = new Date().toISOString();
    
    return parsed;
  }

  /**
   * Generate actions based on intent
   * @param {Object} parsed - Parsed command
   * @returns {Array} Generated actions
   */
  _generateActions(parsed) {
    const actions = [];
    const { intent, entities } = parsed;
    
    switch (intent) {
      case INTENTS.CREATE_CONTENT:
        actions.push({
          type: ACTION_TYPES.GENERATE_CONTENT,
          params: {
            contentType: entities.content_type || 'tweet',
            topic: entities.topic || '',
            tone: entities.tone || 'helpful'
          }
        });
        actions.push({
          type: ACTION_TYPES.CREATE_CONTENT_ITEM,
          params: {
            contentType: entities.content_type || 'tweet',
            status: 'draft'
          }
        });
        break;
        
      case INTENTS.SCHEDULE_TASK:
        if (entities.topic) {
          actions.push({
            type: ACTION_TYPES.GENERATE_CONTENT,
            params: {
              contentType: entities.content_type || 'thread',
              topic: entities.topic
            }
          });
        }
        actions.push({
          type: ACTION_TYPES.SCHEDULE_CONTENT,
          params: {
            scheduledFor: entities.scheduled_for,
            contentType: entities.content_type || 'thread'
          }
        });
        break;
        
      case INTENTS.PULL_BOOKMARKS:
        actions.push({
          type: ACTION_TYPES.PULL_BOOKMARKS,
          params: {
            limit: entities.limit || 10
          }
        });
        break;
        
      case INTENTS.ANALYZE_ENGAGEMENT:
        actions.push({
          type: ACTION_TYPES.ANALYZE_ENGAGEMENT,
          params: {
            timeframe: entities.timeframe || '7d',
            contentType: entities.content_type
          }
        });
        break;
        
      case INTENTS.DELETE_CONTENT:
        actions.push({
          type: ACTION_TYPES.DELETE_CONTENT,
          params: {
            contentId: entities.content_id
          }
        });
        break;
        
      case INTENTS.EDIT_CONTENT:
        actions.push({
          type: ACTION_TYPES.EDIT_CONTENT,
          params: {
            contentId: entities.content_id,
            changes: entities.changes || {}
          }
        });
        break;
        
      case INTENTS.HELP:
      default:
        // No actions for help
        break;
    }
    
    return actions;
  }

  /**
   * Generate a summary for the command
   * @param {Object} parsed - Parsed command
   * @returns {string} Summary text
   */
  _generateSummary(parsed) {
    const { intent, entities } = parsed;
    
    switch (intent) {
      case INTENTS.CREATE_CONTENT:
        return `I'll create a ${entities.content_type || 'post'} about "${entities.topic || 'the topic you specified'}"`;
        
      case INTENTS.SCHEDULE_TASK:
        const dateStr = entities.scheduled_for 
          ? new Date(entities.scheduled_for).toLocaleString('en-US', { 
              weekday: 'long', 
              hour: 'numeric', 
              minute: '2-digit',
              hour12: true 
            })
          : 'later';
        return `I'll create a ${entities.content_type || 'post'} about "${entities.topic || 'that'}" and schedule it for ${dateStr}`;
        
      case INTENTS.PULL_BOOKMARKS:
        return `I'll retrieve your saved bookmarks`;
        
      case INTENTS.ANALYZE_ENGAGEMENT:
        return `I'll analyze your engagement metrics`;
        
      case INTENTS.DELETE_CONTENT:
        return `I'll delete the specified content`;
        
      case INTENTS.EDIT_CONTENT:
        return `I'll edit the content as requested`;
        
      case INTENTS.HELP:
      default:
        return `Here are the available commands and how to use them`;
    }
  }

  /**
   * Generate a clarification question
   * @param {Object} parsed - Parsed command
   * @returns {string} Clarification question
   */
  _generateClarification(parsed) {
    const { intent, entities, confidence } = parsed;
    
    if (!entities.topic && [INTENTS.CREATE_CONTENT, INTENTS.SCHEDULE_TASK].includes(intent)) {
      return 'What topic would you like me to write about?';
    }
    
    if (!entities.content_type) {
      return 'Would you like a tweet, thread, or blog post?';
    }
    
    if (!entities.scheduled_for && intent === INTENTS.SCHEDULE_TASK) {
      return 'When would you like me to schedule this for?';
    }
    
    return `I'm not quite sure what you mean. Could you rephrase that? (confidence: ${Math.round(confidence * 100)}%)`;
  }

  /**
   * Fallback parser for when LLM fails
   * @param {string} input - Original input
   * @param {Error} error - The error that occurred
   * @returns {Object} Basic parsed command
   */
  _fallbackParse(input, error) {
    const lowerInput = input.toLowerCase();
    let intent = INTENTS.HELP;
    let entities = {};
    
    // Simple keyword matching
    if (lowerInput.includes('post') || lowerInput.includes('tweet') || lowerInput.includes('write') || lowerInput.includes('create')) {
      intent = INTENTS.CREATE_CONTENT;
      
      if (lowerInput.includes('thread')) {
        entities.content_type = 'thread';
      } else if (lowerInput.includes('blog')) {
        entities.content_type = 'blog';
      } else {
        entities.content_type = 'tweet';
      }
    }
    
    if (lowerInput.includes('schedule') || lowerInput.includes('later') || lowerInput.includes('tomorrow')) {
      intent = INTENTS.SCHEDULE_TASK;
      entities.scheduled_for = parseDate(input);
    }
    
    if (lowerInput.includes('bookmark') || lowerInput.includes('saved')) {
      intent = INTENTS.PULL_BOOKMARKS;
    }
    
    if (lowerInput.includes('analytic') || lowerInput.includes('engagement') || lowerInput.includes('stats')) {
      intent = INTENTS.ANALYZE_ENGAGEMENT;
    }
    
    if (lowerInput.includes('help') || lowerInput.includes('how')) {
      intent = INTENTS.HELP;
    }
    
    const parsed = {
      intent,
      confidence: 0.5,
      entities,
      actions: [],
      error: error?.message
    };
    
    parsed.actions = this._generateActions(parsed);
    parsed.summary = this._generateSummary(parsed);
    parsed.status = 'ready';
    parsed.originalInput = input;
    parsed.parsedAt = new Date().toISOString();
    
    return parsed;
  }

  /**
   * Ensure parser is initialized
   * @private
   */
  _ensureInitialized() {
    if (!this.initialized) {
      throw new Error('CommandParser not initialized. Call init() first.');
    }
  }
}

// Export class and intents
export { CommandParser, INTENTS, ACTION_TYPES };
export default CommandParser;
