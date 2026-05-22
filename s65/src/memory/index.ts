/**
 * Memory module - context management + persistent storage.
 * 
 * Three layers:
 *   1. Context Window (in-memory, manages LLM context limits)
 *   2. Episodic Memory (SQLite, task/session history)
 *   3. Semantic Memory (vector store, knowledge retrieval)
 */

export { ContextWindowManager } from './context-window.js';
export { EpisodicMemory } from './episodic.js';
export type { ContextMessage, ContextWindowConfig, ContextCompressionResult } from './context-window.js';
export type { SessionRecord, EventRecord } from './episodic.js';
