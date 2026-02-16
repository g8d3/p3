import config from '../../config/defaults.js';

/**
 * DryRun - Wrapper that logs instead of executing when dryRun mode is enabled
 */
export class DryRun {
  constructor(stateManager, logger = console) {
    this.stateManager = stateManager;
    this.logger = logger;
    this.dryRunEnabled = config.safety.dryRun;
  }

  /**
   * Check if dry-run mode is enabled
   * @returns {boolean}
   */
  isEnabled() {
    return this.dryRunEnabled;
  }

  /**
   * Enable or disable dry-run mode
   * @param {boolean} enabled
   */
  setEnabled(enabled) {
    this.dryRunEnabled = enabled;
  }

  /**
   * Wrap an action function - executes or simulates based on dry-run mode
   * @param {string} actionName - Name/description of the action
   * @param {Function} actionFn - Async function to execute
   * @returns {Promise<{simulated: boolean, result?: any, error?: Error}>}
   */
  async wrap(actionName, actionFn) {
    if (!this.dryRunEnabled) {
      // Dry-run disabled, execute the action
      try {
        const result = await actionFn();
        return {
          simulated: false,
          result
        };
      } catch (error) {
        return {
          simulated: false,
          error
        };
      }
    }

    // Dry-run mode enabled - log and return simulated response
    this.logger.log(`[DRY-RUN] Action: ${actionName}`);
    this.logger.log(`[DRY-RUN] Would execute: ${actionFn.name || 'anonymous function'}`);
    
    // Try to extract parameters/preview from function if possible
    const fnString = actionFn.toString().slice(0, 200);
    this.logger.debug?.(`[DRY-RUN] Function preview: ${fnString}...`);

    return {
      simulated: true,
      actionName,
      timestamp: new Date().toISOString()
    };
  }

  /**
   * Wrap an action with detailed logging
   * @param {string} actionName - Name of the action
   * @param {object} actionData - Data/parameters for the action
   * @param {Function} actionFn - Async function to execute
   * @returns {Promise<{simulated: boolean, result?: any, error?: Error}>}
   */
  async wrapWithDetails(actionName, actionData, actionFn) {
    if (!this.dryRunEnabled) {
      try {
        const result = await actionFn();
        return {
          simulated: false,
          result
        };
      } catch (error) {
        return {
          simulated: false,
          error
        };
      }
    }

    // Dry-run mode - log detailed information
    this.logger.log(`[DRY-RUN] ========== SIMULATED ACTION ==========`);
    this.logger.log(`[DRY-RUN] Action: ${actionName}`);
    this.logger.log(`[DRY-RUN] Timestamp: ${new Date().toISOString()}`);
    this.logger.log(`[DRY-RUN] Data:`, JSON.stringify(actionData, null, 2));
    this.logger.log(`[DRY-RUN] ======================================`);

    return {
      simulated: true,
      actionName,
      actionData,
      timestamp: new Date().toISOString()
    };
  }

  /**
   * Create a wrapped version of a function that respects dry-run mode
   * @param {string} actionName - Name of the action
   * @param {Function} actionFn - Function to wrap
   * @returns {Function} - Wrapped function
   */
  createWrapper(actionName, actionFn) {
    return async (...args) => {
      return this.wrapWithDetails(actionName, { args }, () => actionFn(...args));
    };
  }
}

export default DryRun;
