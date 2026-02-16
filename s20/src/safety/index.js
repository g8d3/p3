/**
 * Safety Layer - Rate limiting, dry-run mode, and approval queue
 */
export { RateLimiter } from './rate-limiter.js';
export { DryRun } from './dry-run.js';
export { Approval } from './approval.js';

/**
 * Initialize all safety components
 * @param {object} stateManager - State manager instance
 * @param {object} logger - Logger instance
 * @returns {object} - All safety components
 */
export function initSafetyLayer(stateManager, logger = console) {
  const rateLimiter = new RateLimiter(stateManager);
  const dryRun = new DryRun(stateManager, logger);
  const approval = new Approval(stateManager, logger);

  return {
    rateLimiter,
    dryRun,
    approval
  };
}

// Re-export classes for default import
import { RateLimiter } from './rate-limiter.js';
import { DryRun } from './dry-run.js';
import { Approval } from './approval.js';

export default {
  RateLimiter,
  DryRun,
  Approval,
  initSafetyLayer
};
