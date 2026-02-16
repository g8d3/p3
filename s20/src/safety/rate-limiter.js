import config from '../../config/defaults.js';

/**
 * RateLimiter - Token bucket algorithm with configurable windows
 * Uses StateManager to persist counts across restarts
 */
export class RateLimiter {
  constructor(stateManager) {
    this.stateManager = stateManager;
    this.rateLimits = config.safety.rateLimits;
    this.limits = {};
    this.initialized = false;
  }

  /**
   * Initialize rate limiter and load persisted state
   */
  async init() {
    if (this.initialized) return;
    
    // Load persisted rate limit state from StateManager
    for (const [actionType, limitConfig] of Object.entries(this.rateLimits)) {
      const stored = await this.stateManager.get(`ratelimit:${actionType}`);
      if (stored) {
        this.limits[actionType] = stored;
      } else {
        this.limits[actionType] = {
          tokens: limitConfig.max,
          lastRefill: Date.now(),
          max: limitConfig.max,
          windowMs: limitConfig.windowMinutes * 60 * 1000
        };
      }
    }
    this.initialized = true;
  }

  /**
   * Refill tokens based on elapsed time (token bucket algorithm)
   * @param {string} actionType - The type of action
   */
  async refillTokens(actionType) {
    const limit = this.limits[actionType];
    if (!limit) return;

    const now = Date.now();
    const elapsed = now - limit.lastRefill;
    
    // Calculate tokens to add based on elapsed time
    const tokensPerMs = limit.max / limit.windowMs;
    const tokensToAdd = Math.floor(elapsed * tokensPerMs);
    
    if (tokensToAdd > 0) {
      limit.tokens = Math.min(limit.max, limit.tokens + tokensToAdd);
      limit.lastRefill = now;
      await this.persistState(actionType);
    }
  }

  /**
   * Persist rate limit state to StateManager
   * @param {string} actionType - The type of action
   */
  async persistState(actionType) {
    await this.stateManager.set(`ratelimit:${actionType}`, this.limits[actionType]);
  }

  /**
   * Check if an action is allowed under rate limits
   * @param {string} actionType - The type of action to check
   * @returns {Promise<{allowed: boolean, remaining: number, resetIn: number}>}
   */
  async checkLimit(actionType) {
    await this.init();
    
    const limitConfig = this.rateLimits[actionType];
    if (!limitConfig) {
      // No rate limit configured for this action type
      return { allowed: true, remaining: Infinity, resetIn: 0 };
    }

    await this.refillTokens(actionType);
    
    const limit = this.limits[actionType];
    const allowed = limit.tokens >= 1;
    const remaining = Math.floor(limit.tokens);
    
    // Calculate time until full refill
    const tokensNeeded = limit.max - limit.tokens;
    const tokensPerMs = limit.max / limit.windowMs;
    const resetIn = Math.ceil((tokensNeeded / tokensPerMs) / 1000);

    return {
      allowed,
      remaining,
      resetIn: allowed ? 0 : resetIn,
      limit: limit.max,
      windowMs: limit.windowMs
    };
  }

  /**
   * Record that an action was taken (consume a token)
   * @param {string} actionType - The type of action recorded
   * @returns {Promise<boolean>} - Whether the recording was successful
   */
  async recordAction(actionType) {
    await this.init();
    
    const limitConfig = this.rateLimits[actionType];
    if (!limitConfig) {
      // No rate limit configured, always allow
      return true;
    }

    await this.refillTokens(actionType);
    
    const limit = this.limits[actionType];
    if (limit.tokens < 1) {
      return false;
    }

    limit.tokens -= 1;
    await this.persistState(actionType);
    return true;
  }

  /**
   * Get remaining tokens for an action type
   * @param {string} actionType - The type of action
   * @returns {Promise<number>} - Number of remaining tokens
   */
  async getRemaining(actionType) {
    await this.init();
    
    const limitConfig = this.rateLimits[actionType];
    if (!limitConfig) {
      return Infinity;
    }

    await this.refillTokens(actionType);
    return Math.floor(this.limits[actionType].tokens);
  }

  /**
   * Reset rate limit for an action type (admin function)
   * @param {string} actionType - The type of action to reset
   */
  async reset(actionType) {
    await this.init();
    
    const limitConfig = this.rateLimits[actionType];
    if (!limitConfig) return;

    this.limits[actionType] = {
      tokens: limitConfig.max,
      lastRefill: Date.now(),
      max: limitConfig.max,
      windowMs: limitConfig.windowMinutes * 60 * 1000
    };
    await this.persistState(actionType);
  }
}

export default RateLimiter;
