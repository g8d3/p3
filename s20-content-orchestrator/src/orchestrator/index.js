/**
 * Orchestrator - Main daemon that coordinates all modules
 * Handles initialization, lifecycle, and task execution
 */

import EventEmitter from 'events';
import { config } from '../../config/defaults.js';
import StateManager from '../infrastructure/state.js';
import logger from '../infrastructure/logger.js';
import BrowserClient from '../browser/client.js';
import { initSafetyLayer } from '../safety/index.js';
import { Scheduler } from '../infrastructure/scheduler.js';
import TwitterService from '../capabilities/twitter/index.js';
import { ContentFactory } from '../capabilities/content/index.js';
import ExperimentEngine from '../capabilities/experiments/index.js';
import { DashboardServer } from '../web/server.js';

/**
 * Orchestrator - Main coordinator class
 * @extends EventEmitter
 */
export class Orchestrator extends EventEmitter {
  constructor() {
    super();
    
    // Core components
    this.state = null;
    this.logger = null;
    this.browser = null;
    this.safety = null;
    this.scheduler = null;
    this.dashboard = null;
    this.wsManager = null;
    
    // Capabilities
    this.twitter = null;
    this.content = null;
    this.experiments = null;
    
    // Module failure tracking
    this.moduleFailures = new Map();
    this.maxFailures = 3;
    
    // Lifecycle state
    this.initialized = false;
    this.running = false;
    this.shuttingDown = false;
    this.startTime = null;
    
    // Bind signal handlers
    this._handleSignal = this._handleSignal.bind(this);
    this._handleException = this._handleException.bind(this);
  }

  /**
   * Initialize all components in order
   */
  async init() {
    if (this.initialized) {
      return this;
    }

    this.logger = logger.module('orchestrator');
    this.logger.info('Initializing Orchestrator...');

    try {
      // 1. StateManager
      this.logger.debug('Initializing StateManager...');
      this.state = new StateManager();
      this.state.init();

      // 2. Logger already initialized

      // 3. BrowserClient
      this.logger.debug('Initializing BrowserClient...');
      this.browser = new BrowserClient();
      
      // Set up browser event handlers
      this.browser.on('connected', () => {
        this.logger.info('Browser connected');
        this.emit('browser:connected');
      });
      
      this.browser.on('disconnected', () => {
        this.logger.warn('Browser disconnected');
        this.emit('browser:disconnected');
      });
      
      this.browser.on('error', (err) => {
        this.logger.error(`Browser error: ${err.message}`);
        this.emit('browser:error', err);
      });

      // 4. Safety layer (RateLimiter, DryRun, Approval)
      this.logger.debug('Initializing Safety layer...');
      this.safety = initSafetyLayer(this.state, this.logger);

      // 5. Capabilities
      this.logger.debug('Initializing capabilities...');
      
      // TwitterService: { browserClient, stateManager, rateLimiter, dryRun, approval }
      this.twitter = new TwitterService({
        browserClient: this.browser,
        stateManager: this.state,
        rateLimiter: this.safety.rateLimiter,
        dryRun: this.safety.dryRun,
        approval: this.safety.approval
      });
      
      // ContentFactory: (stateManager, customConfig)
      this.content = new ContentFactory(this.state);
      this.content.init();
      
      // ExperimentEngine: (stateManager, contentFactory, twitterService, options)
      this.experiments = new ExperimentEngine(this.state, this.content, this.twitter);
      await this.experiments.init();

      // 6. Scheduler
      this.logger.debug('Initializing Scheduler...');
      this.scheduler = new Scheduler(this.state);
      this.scheduler.init(this);

      this.initialized = true;
      this.logger.info('Orchestrator initialized successfully');
      
      return this;

    } catch (error) {
      this.logger.error(`Initialization failed: ${error.message}`);
      throw error;
    }
  }

  /**
   * Start the daemon
   */
  async start() {
    if (!this.initialized) {
      await this.init();
    }

    if (this.running) {
      this.logger.warn('Orchestrator already running');
      return this;
    }

    this.logger.info('Starting Orchestrator...');
    
    // Set up signal handlers
    process.on('SIGINT', this._handleSignal);
    process.on('SIGTERM', this._handleSignal);
    process.on('uncaughtException', this._handleException);
    process.on('unhandledRejection', this._handleRejection);

    // Connect to browser
    try {
      this.logger.info('Connecting to browser...');
      await this.browser.connect();
    } catch (error) {
      this.logger.warn(`Browser connection failed: ${error.message}`);
      this.logger.info('Continuing without browser - some features may be limited');
    }

    // Start scheduler
    this.scheduler.start();

    // Start dashboard server
    try {
      this.logger.info('Starting dashboard server...');
      this.dashboard = new DashboardServer(this);
      await this.dashboard.start();
    } catch (error) {
      this.logger.warn(`Dashboard server failed: ${error.message}`);
      this.logger.info('Continuing without dashboard');
    }

    this.running = true;
    this.startTime = Date.now();
    this.logger.info('Orchestrator started successfully');
    this.emit('started');
    
    return this;
  }

  /**
   * Graceful shutdown
   */
  async stop() {
    if (this.shuttingDown) {
      return this;
    }

    this.shuttingDown = true;
    this.logger.info('Shutting down Orchestrator...');
    this.emit('stopping');

    // Remove signal handlers
    process.off('SIGINT', this._handleSignal);
    process.off('SIGTERM', this._handleSignal);
    process.off('uncaughtException', this._handleException);
    process.off('unhandledRejection', this._handleRejection);

    // Stop scheduler
    if (this.scheduler) {
      this.scheduler.stop();
    }

    // Stop dashboard server
    if (this.dashboard) {
      await this.dashboard.stop();
    }

    // Disconnect browser
    if (this.browser) {
      this.browser.disconnect();
    }

    // Close state
    if (this.state) {
      this.state.close();
    }

    this.running = false;
    this.initialized = false;
    this.logger.info('Orchestrator stopped');
    this.emit('stopped');
    
    return this;
  }

  /**
   * Check health of all components
   * @returns {object} Health status of each component
   */
  async healthCheck() {
    const health = {
      timestamp: new Date().toISOString(),
      running: this.running,
      components: {}
    };

    // State Manager
    try {
      const stats = this.state?.getStats();
      health.components.stateManager = {
        status: 'healthy',
        stats
      };
    } catch (error) {
      health.components.stateManager = {
        status: 'unhealthy',
        error: error.message
      };
    }

    // Browser
    health.components.browser = {
      status: this.browser?.isConnected() ? 'healthy' : 'disconnected',
      connected: this.browser?.isConnected() || false
    };

    // Safety Layer
    health.components.safety = {
      status: 'healthy',
      dryRunEnabled: this.safety?.dryRun?.isEnabled() || false,
      approvalRequired: this.safety?.approval?.requireApproval || false
    };

    // Scheduler
    health.components.scheduler = {
      status: this.scheduler?.running ? 'healthy' : 'stopped',
      activeJobs: this.scheduler?.jobs?.size || 0
    };

    // Capabilities
    health.components.twitter = {
      status: this._isModuleEnabled('twitter') ? 'enabled' : 'disabled',
      failures: this.moduleFailures.get('twitter') || 0
    };

    health.components.content = {
      status: this._isModuleEnabled('content') ? 'enabled' : 'disabled',
      failures: this.moduleFailures.get('content') || 0
    };

    health.components.experiments = {
      status: this._isModuleEnabled('experiments') ? 'enabled' : 'disabled',
      failures: this.moduleFailures.get('experiments') || 0
    };

    // Overall status
    const allHealthy = Object.values(health.components)
      .every(c => c.status === 'healthy' || c.status === 'enabled' || c.status === 'disconnected');
    health.status = allHealthy ? 'healthy' : 'degraded';

    return health;
  }

  /**
   * Execute a scheduled task
   * @param {string} module - Module name (twitter, content, experiments, system)
   * @param {string} action - Action name
   * @returns {any} Task result
   */
  async runTask(module, action) {
    const startTime = Date.now();
    
    // Check if module is disabled due to failures
    if (!this._isModuleEnabled(module)) {
      this.logger.warn(`Module ${module} is disabled due to consecutive failures`);
      return { skipped: true, reason: 'Module disabled' };
    }

    this.logger.debug(`Running task: ${module}.${action}`);

    try {
      let result;
      
      switch (module) {
        case 'twitter':
          result = await this._executeTwitterAction(action);
          break;
        case 'content':
          result = await this._executeContentAction(action);
          break;
        case 'experiments':
          result = await this._executeExperimentAction(action);
          break;
        case 'system':
          result = await this._executeSystemAction(action);
          break;
        default:
          throw new Error(`Unknown module: ${module}`);
      }

      // Reset failure count on success
      this.moduleFailures.set(module, 0);

      // Log success
      const duration = Date.now() - startTime;
      this.state.logAction({
        module,
        action,
        result: typeof result === 'object' ? JSON.stringify(result) : String(result),
        durationMs: duration
      });

      this.emit('task:complete', { module, action, result, duration });
      return result;

    } catch (error) {
      // Track failures
      const failures = (this.moduleFailures.get(module) || 0) + 1;
      this.moduleFailures.set(module, failures);

      if (failures >= this.maxFailures) {
        this.logger.error(`Module ${module} disabled after ${failures} consecutive failures`);
        this.emit('module:disabled', { module, failures });
      }

      // Log failure
      const duration = Date.now() - startTime;
      this.state.logAction({
        module,
        action,
        error: error.message,
        durationMs: duration
      });

      this.emit('task:error', { module, action, error, duration });
      throw error;
    }
  }

  /**
   * Execute Twitter action
   */
  async _executeTwitterAction(action) {
    if (!this.twitter) {
      throw new Error('Twitter module not initialized');
    }

    switch (action) {
      case 'checkMentions':
        return await this.twitter.checkMentions();
      case 'syncBookmarks':
        return await this.twitter.syncBookmarks();
      case 'collectEngagement':
        return await this.twitter.collectEngagement();
      default:
        throw new Error(`Unknown Twitter action: ${action}`);
    }
  }

  /**
   * Execute Content action
   */
  async _executeContentAction(action) {
    if (!this.content) {
      throw new Error('Content module not initialized');
    }

    switch (action) {
      case 'generateContent':
        return await this.content.generateContent();
      case 'postScheduled':
        return await this.content.postScheduled();
      default:
        throw new Error(`Unknown Content action: ${action}`);
    }
  }

  /**
   * Execute Experiment action
   */
  async _executeExperimentAction(action) {
    if (!this.experiments) {
      throw new Error('Experiments module not initialized');
    }

    switch (action) {
      case 'exploreTopics':
        return await this.experiments.exploreTopics();
      case 'analyzeExperiments':
        return await this.experiments.analyzeExperiments();
      default:
        throw new Error(`Unknown Experiment action: ${action}`);
    }
  }

  /**
   * Execute System action
   */
  async _executeSystemAction(action) {
    switch (action) {
      case 'healthCheck':
        return await this.healthCheck();
      case 'cleanup':
        return await this._cleanup();
      default:
        throw new Error(`Unknown System action: ${action}`);
    }
  }

  /**
   * Run cleanup tasks
   */
  async _cleanup() {
    this.logger.info('Running cleanup tasks...');
    
    // Cleanup expired approvals
    if (this.safety?.approval) {
      await this.safety.approval.cleanupExpired();
    }

    // Delete old approval requests
    if (this.safety?.approval) {
      await this.safety.approval.deleteOldRequests(168); // 7 days
    }

    return { cleaned: true, timestamp: new Date().toISOString() };
  }

  /**
   * Check if a module is enabled (not disabled due to failures)
   */
  _isModuleEnabled(module) {
    const failures = this.moduleFailures.get(module) || 0;
    return failures < this.maxFailures;
  }

  /**
   * Handle process signals
   */
  async _handleSignal(signal) {
    this.logger.info(`Received ${signal}, initiating graceful shutdown...`);
    await this.stop();
    process.exit(0);
  }

  /**
   * Handle uncaught exceptions
   */
  _handleException(error) {
    this.logger.error(`Uncaught exception: ${error.message}`);
    this.logger.error(error.stack);
    this.emit('error', error);
    
    // Don't exit immediately - allow for cleanup
    this.stop().then(() => {
      process.exit(1);
    });
  }

  /**
   * Handle unhandled promise rejections
   */
  _handleRejection(reason, promise) {
    this.logger.error(`Unhandled rejection at: ${promise}`);
    this.logger.error(`Reason: ${reason}`);
    this.emit('error', reason);
  }

  /**
   * Enable a previously disabled module
   */
  enableModule(module) {
    this.moduleFailures.set(module, 0);
    this.logger.info(`Module ${module} re-enabled`);
    this.emit('module:enabled', { module });
  }

  /**
   * Get current status
   */
  getStatus() {
    return {
      initialized: this.initialized,
      running: this.running,
      browserConnected: this.browser?.isConnected() || false,
      schedulerRunning: this.scheduler?.running || false,
      moduleFailures: Object.fromEntries(this.moduleFailures)
    };
  }
}

// Export singleton factory
let orchestratorInstance = null;

export function getOrchestrator() {
  if (!orchestratorInstance) {
    orchestratorInstance = new Orchestrator();
  }
  return orchestratorInstance;
}

export default Orchestrator;
