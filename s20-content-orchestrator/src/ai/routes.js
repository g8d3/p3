/**
 * AI Command Routes - REST API endpoints for AI command processing
 * Provides natural language interface for agent operations
 */

import { Router } from 'express';
import { v4 as uuidv4 } from 'uuid';
import logger from '../infrastructure/logger.js';
import { CommandParser, INTENTS } from './commandParser.js';
import { ActionExecutor } from './actionExecutor.js';

const log = logger.module('ai-routes');

/**
 * Create AI command router
 * @param {Object} options - Configuration options
 * @param {Object} options.stateManager - StateManager instance
 * @param {Object} options.contentFactory - ContentFactory instance
 * @param {Object} options.wsManager - WebSocket manager for broadcasting
 * @returns {Router}
 */
export function createAiRouter(options = {}) {
  const router = Router();
  const { stateManager, contentFactory, wsManager } = options;
  
  // Initialize parser and executor
  const commandParser = new CommandParser().init();
  const actionExecutor = new ActionExecutor({ 
    stateManager, 
    contentFactory 
  }).init();
  
  // Store pending commands (in production, use Redis or database)
  const pendingCommands = new Map();
  
  // ===========================================
  // POST /ai/command - Process natural language command
  // ===========================================
  
  router.post('/command', async (req, res) => {
    try {
      const { input, autoConfirm = false, userId = 'default' } = req.body;
      
      if (!input || typeof input !== 'string') {
        return res.status(400).json({
          success: false,
          error: 'Input is required and must be a string'
        });
      }
      
      log.info('Processing AI command', { input: input.slice(0, 100), autoConfirm });
      
      // Parse the command
      const parsed = await commandParser.parse(input, { userId });
      
      // Generate command ID
      const commandId = uuidv4();
      
      // Store command in database
      storeCommand(stateManager, {
        id: commandId,
        userId,
        input,
        parsedIntent: JSON.stringify(parsed)
      });
      
      // Check if clarification is needed
      if (parsed.status === 'needs_clarification') {
        return res.json({
          success: true,
          status: 'clarification_needed',
          commandId,
          clarification: parsed.clarification,
          parsed: {
            intent: parsed.intent,
            confidence: parsed.confidence,
            entities: parsed.entities
          }
        });
      }
      
      // Check if this is a help request
      if (parsed.intent === INTENTS.HELP) {
        return res.json({
          success: true,
          status: 'help',
          commandId,
          summary: parsed.summary,
          help: getHelpContent()
        });
      }
      
      // If autoConfirm is true, execute immediately
      if (autoConfirm) {
        const executionResult = await actionExecutor.execute(parsed.actions, { userId });
        
        // Update command with executed actions
        updateCommandExecuted(stateManager, commandId, JSON.stringify(executionResult.results));
        
        // Broadcast event
        wsManager?.broadcast('ai:command:executed', { 
          commandId, 
          intent: parsed.intent,
          success: executionResult.success 
        });
        
        return res.json({
          success: executionResult.success,
          status: 'executed',
          commandId,
          summary: parsed.summary,
          results: executionResult.results,
          executedActions: executionResult.executedActions
        });
      }
      
      // Otherwise, store as pending and return plan for confirmation
      pendingCommands.set(commandId, {
        parsed,
        userId,
        createdAt: new Date().toISOString()
      });
      
      return res.json({
        success: true,
        status: 'pending_confirmation',
        commandId,
        plan: {
          intent: parsed.intent,
          entities: parsed.entities,
          actions: parsed.actions.map(a => ({
            type: a.type,
            description: describeAction(a)
          }))
        },
        summary: parsed.summary,
        expiresIn: 300 // 5 minutes
      });
      
    } catch (error) {
      log.error(`Command processing error: ${error.message}`);
      res.status(500).json({ success: false, error: error.message });
    }
  });
  
  // ===========================================
  // POST /ai/command/:id/confirm - Confirm and execute pending command
  // ===========================================
  
  router.post('/command/:id/confirm', async (req, res) => {
    try {
      const { id } = req.params;
      const { userId = 'default' } = req.body;
      
      // Check pending commands first (in-memory)
      let pendingCommand = pendingCommands.get(id);
      
      // If not in memory, try to get from database (for resumed sessions)
      if (!pendingCommand && stateManager) {
        const storedCommand = stateManager.queryOne(
          'SELECT * FROM ai_commands WHERE id = ?',
          [id]
        );
        
        if (storedCommand) {
          pendingCommand = {
            parsed: JSON.parse(storedCommand.parsed_intent),
            userId: storedCommand.user_id,
            createdAt: storedCommand.created_at
          };
        }
      }
      
      if (!pendingCommand) {
        return res.status(404).json({
          success: false,
          error: 'Command not found or expired'
        });
      }
      
      const { parsed } = pendingCommand;
      
      // Execute the actions
      const executionResult = await actionExecutor.execute(parsed.actions, { userId });
      
      // Update command with executed actions
      updateCommandExecuted(stateManager, id, JSON.stringify(executionResult.results));
      
      // Remove from pending
      pendingCommands.delete(id);
      
      // Broadcast event
      wsManager?.broadcast('ai:command:executed', { 
        commandId: id, 
        intent: parsed.intent,
        success: executionResult.success 
      });
      
      return res.json({
        success: executionResult.success,
        status: 'executed',
        commandId: id,
        summary: parsed.summary,
        results: executionResult.results,
        executedActions: executionResult.executedActions
      });
      
    } catch (error) {
      log.error(`Command confirmation error: ${error.message}`);
      res.status(500).json({ success: false, error: error.message });
    }
  });
  
  // ===========================================
  // POST /ai/command/:id/feedback - Submit feedback for executed command
  // ===========================================
  
  router.post('/command/:id/feedback', async (req, res) => {
    try {
      const { id } = req.params;
      const { feedback, comment } = req.body;
      
      if (!['positive', 'negative'].includes(feedback)) {
        return res.status(400).json({
          success: false,
          error: 'Feedback must be "positive" or "negative"'
        });
      }
      
      // Update command with feedback
      if (stateManager) {
        const result = stateManager.query(
          `UPDATE ai_commands SET user_feedback = ? WHERE id = ?`,
          [JSON.stringify({ feedback, comment, submittedAt: new Date().toISOString() }), id]
        );
        
        if (result.changes === 0) {
          return res.status(404).json({
            success: false,
            error: 'Command not found'
          });
        }
      }
      
      // Broadcast event
      wsManager?.broadcast('ai:command:feedback', { commandId: id, feedback });
      
      return res.json({
        success: true,
        message: 'Feedback recorded',
        commandId: id
      });
      
    } catch (error) {
      log.error(`Feedback error: ${error.message}`);
      res.status(500).json({ success: false, error: error.message });
    }
  });
  
  // ===========================================
  // GET /ai/commands - List recent commands
  // ===========================================
  
  router.get('/commands', (req, res) => {
    try {
      const { limit = 20, userId } = req.query;
      
      if (!stateManager) {
        return res.json({
          success: true,
          data: []
        });
      }
      
      let query = 'SELECT * FROM ai_commands ORDER BY created_at DESC LIMIT ?';
      const params = [parseInt(limit)];
      
      if (userId) {
        query = 'SELECT * FROM ai_commands WHERE user_id = ? ORDER BY created_at DESC LIMIT ?';
        params.unshift(userId);
      }
      
      const commands = stateManager.query(query, params);
      
      return res.json({
        success: true,
        data: commands.map(cmd => ({
          id: cmd.id,
          userId: cmd.user_id,
          input: cmd.input,
          parsedIntent: cmd.parsed_intent ? JSON.parse(cmd.parsed_intent) : null,
          executedActions: cmd.executed_actions ? JSON.parse(cmd.executed_actions) : null,
          userFeedback: cmd.user_feedback ? JSON.parse(cmd.user_feedback) : null,
          createdAt: cmd.created_at
        }))
      });
      
    } catch (error) {
      log.error(`Commands list error: ${error.message}`);
      res.status(500).json({ success: false, error: error.message });
    }
  });
  
  // ===========================================
  // GET /ai/help - Get available commands help
  // ===========================================
  
  router.get('/help', (req, res) => {
    return res.json({
      success: true,
      data: getHelpContent()
    });
  });
  
  return router;
}

/**
 * Store command in database
 */
function storeCommand(stateManager, { id, userId, input, parsedIntent }) {
  if (!stateManager) return;
  
  stateManager.query(
    `INSERT INTO ai_commands (id, user_id, input, parsed_intent) VALUES (?, ?, ?, ?)`,
    [id, userId, input, parsedIntent]
  );
}

/**
 * Update command with executed actions
 */
function updateCommandExecuted(stateManager, id, executedActions) {
  if (!stateManager) return;
  
  stateManager.query(
    `UPDATE ai_commands SET executed_actions = ? WHERE id = ?`,
    [executedActions, id]
  );
}

/**
 * Get human-readable description for an action
 */
function describeAction(action) {
  const descriptions = {
    generate_content: `Generate ${action.params?.contentType || 'content'} about "${action.params?.topic || 'the specified topic'}"`,
    create_content_item: `Save the generated content as a draft`,
    schedule_content: `Schedule for ${action.params?.scheduledFor ? new Date(action.params.scheduledFor).toLocaleString() : 'later'}`,
    pull_bookmarks: `Retrieve saved bookmarks`,
    analyze_engagement: `Analyze engagement metrics`,
    delete_content: `Delete content item ${action.params?.contentId || ''}`,
    edit_content: `Edit content item ${action.params?.contentId || ''}`
  };
  
  return descriptions[action.type] || `Execute ${action.type}`;
}

/**
 * Get help content
 */
function getHelpContent() {
  return {
    title: 'AI Command Interface',
    description: 'Use natural language to control your content agent',
    examples: [
      {
        command: 'Post a thread about AI agents tomorrow at 9am',
        description: 'Creates a thread about AI agents and schedules it for tomorrow at 9:00 AM'
      },
      {
        command: 'Write a tweet about building in public',
        description: 'Generates a single tweet about building in public'
      },
      {
        command: 'Show me my bookmarks',
        description: 'Retrieves your saved/bookmarked content items'
      },
      {
        command: 'Analyze my engagement this week',
        description: 'Shows engagement metrics for your recent posts'
      },
      {
        command: 'Create a blog post about automation',
        description: 'Generates a full blog post about automation'
      }
    ],
    intents: [
      { name: 'create_content', description: 'Create new content (tweets, threads, blogs)' },
      { name: 'schedule_task', description: 'Schedule content for future posting' },
      { name: 'pull_bookmarks', description: 'Retrieve saved content items' },
      { name: 'analyze_engagement', description: 'View engagement analytics' },
      { name: 'edit_content', description: 'Modify existing content' },
      { name: 'delete_content', description: 'Remove content' },
      { name: 'help', description: 'Show this help message' }
    ],
    tips: [
      'Be specific about topics for better content generation',
      'Use natural time expressions like "tomorrow at 3pm" or "next Monday"',
      'Specify content type: tweet, thread, or blog',
      'Use autoConfirm=true to skip confirmation step'
    ]
  };
}

export default createAiRouter;
