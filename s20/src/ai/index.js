/**
 * AI Module - Natural language command processing for the autonomous agent
 * Provides parsing, execution, and API routes for AI-powered operations
 */

import { CommandParser, INTENTS, ACTION_TYPES } from './commandParser.js';
import { ActionExecutor } from './actionExecutor.js';
import { createAiRouter } from './routes.js';

// Re-export all components
export {
  CommandParser,
  ActionExecutor,
  createAiRouter,
  INTENTS,
  ACTION_TYPES
};

// Default export
export default {
  CommandParser,
  ActionExecutor,
  createAiRouter,
  INTENTS,
  ACTION_TYPES
};
