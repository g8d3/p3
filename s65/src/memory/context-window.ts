/**
 * Context window manager.
 * 
 * Manages the context window for LLM conversations.
 * Automatically compresses/prunes when approaching limits.
 * 
 * Context structure:
 *   - System prompt (always kept)
 *   - Conversation history (messages)
 *   - Working context (current task files, state)
 *   - Knowledge base (retrieved from memory)
 * 
 * Compression strategies:
 *   1. Summarize oldest messages
 *   2. Prune tool call results
 *   3. Drop redundant context
 *   4. Full summary of conversation so far
 */

export interface ContextMessage {
  role: 'system' | 'user' | 'assistant' | 'tool';
  content: string;
  timestamp: number;
  tokenCount?: number;
  metadata?: Record<string, unknown>;
}

export interface ContextWindowConfig {
  /** Maximum token limit before compression */
  maxTokens: number;
  /** Compression threshold (% of maxTokens) */
  compressionThreshold: number;
  /** Strategy for compression */
  strategy: 'summarize_oldest' | 'prune_tool_results' | 'drop_redundant' | 'full_summary';
  /** Keep at least this many recent messages */
  keepRecentMessages: number;
}

export interface ContextCompressionResult {
  messagesRemoved: number;
  tokensSaved: number;
  summary: string;
}

export class ContextWindowManager {
  private messages: ContextMessage[] = [];
  private config: ContextWindowConfig;
  private accessLog: Map<number, number> = new Map(); // message index -> access count

  constructor(config: Partial<ContextWindowConfig> = {}) {
    this.config = {
      maxTokens: config.maxTokens ?? 128_000,
      compressionThreshold: config.compressionThreshold ?? 0.85,
      strategy: config.strategy ?? 'summarize_oldest',
      keepRecentMessages: config.keepRecentMessages ?? 10,
    };
  }

  /**
   * Add a message to the context window.
   */
  add(message: Omit<ContextMessage, 'timestamp'>): void {
    this.messages.push({
      ...message,
      timestamp: Date.now(),
      tokenCount: this.estimateTokens(message.content),
    });
    this.accessLog.set(this.messages.length - 1, 0);
  }

  /**
   * Get all messages.
   */
  getMessages(): ContextMessage[] {
    // Update access log for importance tracking
    this.messages.forEach((_, i) => {
      if (this.accessLog.has(i)) {
        this.accessLog.set(i, (this.accessLog.get(i) ?? 0) + 1);
      }
    });
    return [...this.messages];
  }

  /**
   * Estimate token count for a string (rough: ~4 chars per token).
   */
  estimateTokens(text: string): number {
    return Math.ceil(text.length / 4);
  }

  /**
   * Get current total token count.
   */
  getTotalTokens(): number {
    return this.messages.reduce((sum, m) => sum + (m.tokenCount ?? this.estimateTokens(m.content)), 0);
  }

  /**
   * Check if compression is needed.
   */
  needsCompression(): boolean {
    return this.getTotalTokens() >= this.config.maxTokens * this.config.compressionThreshold;
  }

  /**
   * Compress the context window using the configured strategy.
   */
  compress(): ContextCompressionResult | null {
    if (!this.needsCompression()) return null;
    
    const beforeTokens = this.getTotalTokens();
    let result: ContextCompressionResult;
    
    switch (this.config.strategy) {
      case 'summarize_oldest':
        result = this.summarizeOldest();
        break;
      case 'prune_tool_results':
        result = this.pruneToolResults();
        break;
      case 'drop_redundant':
        result = this.dropRedundant();
        break;
      case 'full_summary':
        result = this.fullSummary();
        break;
      default:
        result = this.summarizeOldest();
    }
    
    return result;
  }

  /**
   * Strategy 1: Summarize oldest non-system messages.
   */
  private summarizeOldest(): ContextCompressionResult {
    const messagesToKeep = Math.max(this.config.keepRecentMessages, 5);
    const compressible = this.messages.slice(1, -messagesToKeep); // skip system prompt and recent
    const systemPrompt = this.messages[0];
    
    if (compressible.length === 0) {
      return { messagesRemoved: 0, tokensSaved: 0, summary: 'No messages to compress' };
    }
    
    const tokensSaved = compressible.reduce((sum, m) => sum + (m.tokenCount ?? this.estimateTokens(m.content)), 0);
    const summaryContent = compressible.map(m => `[${m.role}]: ${m.content.slice(0, 100)}...`).join('\n');
    const summary = `[Compressed summary of ${compressible.length} previous messages]\n${summaryContent}`;
    
    // Replace compressed messages with summary
    const recentMessages = this.messages.slice(-messagesToKeep);
    this.messages = [systemPrompt, {
      role: 'assistant',
      content: summary,
      timestamp: Date.now(),
      tokenCount: this.estimateTokens(summary),
    }, ...recentMessages];
    
    // Reset access log for new indices
    this.accessLog.clear();
    
    return {
      messagesRemoved: compressible.length - 1, // -1 for the summary message we added
      tokensSaved,
      summary,
    };
  }

  /**
   * Strategy 2: Prune verbose tool call results.
   */
  private pruneToolResults(): ContextCompressionResult {
    let tokensSaved = 0;
    let removed = 0;
    
    this.messages = this.messages.filter((m) => {
      if (m.role === 'tool') {
        const tokens = m.tokenCount ?? this.estimateTokens(m.content);
        if (tokens > 500) { // prune large tool results
          tokensSaved += tokens;
          removed++;
          return false;
        }
      }
      return true;
    });
    
    return {
      messagesRemoved: removed,
      tokensSaved,
      summary: `Pruned ${removed} large tool result messages`,
    };
  }

  /**
   * Strategy 3: Drop redundant information.
   */
  private dropRedundant(): ContextCompressionResult {
    // Track content hashes to find duplicates
    const seen = new Set<string>();
    let tokensSaved = 0;
    let removed = 0;
    
    this.messages = this.messages.filter((m, i) => {
      // Always keep system prompt and recent messages
      if (i === 0 || i >= this.messages.length - this.config.keepRecentMessages) return true;
      
      const hash = m.content.slice(0, 200); // hash by first 200 chars
      if (seen.has(hash)) {
        tokensSaved += m.tokenCount ?? this.estimateTokens(m.content);
        removed++;
        return false;
      }
      seen.add(hash);
      return true;
    });
    
    return {
      messagesRemoved: removed,
      tokensSaved,
      summary: `Removed ${removed} redundant messages`,
    };
  }

  /**
   * Strategy 4: Full conversation summary (most aggressive).
   */
  private fullSummary(): ContextCompressionResult {
    const systemPrompt = this.messages[0];
    const recentMessages = this.messages.slice(-this.config.keepRecentMessages);
    const compressible = this.messages.slice(1, -this.config.keepRecentMessages);
    
    if (compressible.length === 0) {
      return { messagesRemoved: 0, tokensSaved: 0, summary: 'No messages to compress' };
    }
    
    const tokensSaved = compressible.reduce((sum, m) => sum + (m.tokenCount ?? this.estimateTokens(m.content)), 0);
    const conversationSummary = compressible
      .filter(m => m.role !== 'tool')
      .map(m => `[${m.role}]: ${m.content.slice(0, 200)}`)
      .join('\n');
    
    const summary = `[Full conversation summary]\n${conversationSummary}\n[End summary - ${compressible.length} messages compressed]`;
    
    this.messages = [systemPrompt, {
      role: 'user',
      content: summary,
      timestamp: Date.now(),
      tokenCount: this.estimateTokens(summary),
    }, ...recentMessages];
    
    this.accessLog.clear();
    
    return {
      messagesRemoved: compressible.length - 1,
      tokensSaved,
      summary,
    };
  }

  /**
   * Reset the context window.
   */
  reset(systemPrompt?: string): void {
    this.messages = systemPrompt 
      ? [{ role: 'system', content: systemPrompt, timestamp: Date.now() }]
      : [];
    this.accessLog.clear();
  }
}
