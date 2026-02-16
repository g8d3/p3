/**
 * Scheduler - Cron job scheduler using node-cron
 * Manages scheduled tasks and integrates with the Orchestrator
 */

import cron from 'node-cron';
import { schedules } from '../../config/schedules.js';
import logger from '../infrastructure/logger.js';

/**
 * Scheduler class for managing cron-based task execution
 */
export class Scheduler {
  constructor(stateManager) {
    this.stateManager = stateManager;
    this.jobs = new Map();
    this.orchestrator = null;
    this.running = false;
    this.logger = logger.module('scheduler');
  }

  /**
   * Initialize scheduler with orchestrator reference
   * @param {Orchestrator} orchestrator - Main orchestrator instance
   */
  init(orchestrator) {
    this.orchestrator = orchestrator;
    this.logger.info('Scheduler initialized');
    return this;
  }

  /**
   * Start the scheduler - register all enabled cron jobs
   */
  start() {
    if (this.running) {
      this.logger.warn('Scheduler already running');
      return this;
    }

    this.logger.info('Starting scheduler...');
    
    for (const schedule of schedules) {
      if (schedule.enabled) {
        this._registerJob(schedule);
      } else {
        this.logger.debug(`Skipping disabled task: ${schedule.name}`);
      }
    }

    this.running = true;
    this.logger.info(`Scheduler started with ${this.jobs.size} active jobs`);
    return this;
  }

  /**
   * Stop all scheduled jobs
   */
  stop() {
    this.logger.info('Stopping scheduler...');
    
    for (const [name, jobInfo] of this.jobs) {
      try {
        if (jobInfo.job && typeof jobInfo.job.stop === 'function') {
          jobInfo.job.stop();
        }
        this.logger.debug(`Stopped job: ${name}`);
      } catch (error) {
        this.logger.error(`Error stopping job ${name}: ${error.message}`);
      }
    }

    this.jobs.clear();
    this.running = false;
    this.logger.info('Scheduler stopped');
    return this;
  }

  /**
   * Register a cron job from schedule config
   * @param {object} schedule - Schedule configuration
   */
  _registerJob(schedule) {
    const { name, module, action, cron: cronExpr, description } = schedule;

    // Validate cron expression
    if (!cron.validate(cronExpr)) {
      this.logger.error(`Invalid cron expression for ${name}: ${cronExpr}`);
      return;
    }

    const job = cron.schedule(cronExpr, async () => {
      await this._executeTask(name, module, action);
    }, {
      scheduled: true,
      timezone: 'UTC'
    });

    this.jobs.set(name, {
      job,
      schedule,
      enabled: true,
      lastRun: null,
      nextRun: this._getNextRun(cronExpr)
    });

    this.logger.info(`Registered job: ${name} (${cronExpr}) - ${description}`);
  }

  /**
   * Execute a scheduled task
   * @param {string} name - Task name
   * @param {string} module - Module name
   * @param {string} action - Action name
   */
  async _executeTask(name, module, action) {
    const jobInfo = this.jobs.get(name);
    const startTime = Date.now();

    this.logger.info(`Executing task: ${name} (${module}.${action})`);

    try {
      // Update last_run in state
      const now = new Date().toISOString();
      
      // Execute through orchestrator
      if (this.orchestrator) {
        await this.orchestrator.runTask(module, action);
      }

      // Update job info
      if (jobInfo) {
        jobInfo.lastRun = now;
        jobInfo.nextRun = this._getNextRun(jobInfo.schedule.cron);
      }

      // Persist to state
      await this._persistTaskState(name, now, jobInfo?.nextRun);

      const duration = Date.now() - startTime;
      this.logger.info(`Task completed: ${name} (${duration}ms)`);

    } catch (error) {
      this.logger.error(`Task failed: ${name} - ${error.message}`);
      
      // Log failure to action log
      if (this.stateManager) {
        this.stateManager.logAction({
          module,
          action,
          error: error.message,
          durationMs: Date.now() - startTime
        });
      }
    }
  }

  /**
   * Manually trigger a task by name
   * @param {string} taskName - Name of the task to run
   */
  async runNow(taskName) {
    const jobInfo = this.jobs.get(taskName);
    
    if (!jobInfo) {
      // Check if it exists in schedules but is disabled
      const schedule = schedules.find(s => s.name === taskName);
      if (schedule) {
        this.logger.info(`Running disabled task: ${taskName}`);
        await this._executeTask(taskName, schedule.module, schedule.action);
        return true;
      }
      
      this.logger.error(`Task not found: ${taskName}`);
      return false;
    }

    this.logger.info(`Manually triggering task: ${taskName}`);
    await this._executeTask(taskName, jobInfo.schedule.module, jobInfo.schedule.action);
    return true;
  }

  /**
   * Enable a disabled task
   * @param {string} taskName - Name of the task to enable
   */
  enable(taskName) {
    const jobInfo = this.jobs.get(taskName);
    
    if (jobInfo) {
      if (!jobInfo.enabled) {
        jobInfo.job.start();
        jobInfo.enabled = true;
        this.logger.info(`Enabled task: ${taskName}`);
      }
      return true;
    }

    // Task not registered, check schedules
    const schedule = schedules.find(s => s.name === taskName);
    if (schedule) {
      this._registerJob({ ...schedule, enabled: true });
      this.logger.info(`Registered and enabled task: ${taskName}`);
      return true;
    }

    this.logger.error(`Cannot enable unknown task: ${taskName}`);
    return false;
  }

  /**
   * Disable an enabled task
   * @param {string} taskName - Name of the task to disable
   */
  disable(taskName) {
    const jobInfo = this.jobs.get(taskName);
    
    if (!jobInfo) {
      this.logger.error(`Task not found: ${taskName}`);
      return false;
    }

    if (jobInfo.enabled) {
      jobInfo.job.stop();
      jobInfo.enabled = false;
      this.logger.info(`Disabled task: ${taskName}`);
    }

    return true;
  }

  /**
   * Get status of all scheduled tasks
   * @returns {Array} Array of task statuses
   */
  getStatus() {
    const status = [];
    
    for (const [name, info] of this.jobs) {
      status.push({
        name,
        module: info.schedule.module,
        action: info.schedule.action,
        cron: info.schedule.cron,
        enabled: info.enabled,
        lastRun: info.lastRun,
        nextRun: info.nextRun,
        description: info.schedule.description
      });
    }

    // Include disabled tasks from config
    for (const schedule of schedules) {
      if (!this.jobs.has(schedule.name)) {
        status.push({
          name: schedule.name,
          module: schedule.module,
          action: schedule.action,
          cron: schedule.cron,
          enabled: false,
          lastRun: null,
          nextRun: null,
          description: schedule.description
        });
      }
    }

    return status;
  }

  /**
   * Get next run time for a cron expression
   * @param {string} cronExpr - Cron expression
   * @returns {string} ISO timestamp of next run
   */
  _getNextRun(cronExpr) {
    try {
      // node-cron doesn't expose next run directly, so we use a simple approximation
      // In production, consider using cron-parser package for accurate next run times
      const next = cron.schedule(cronExpr, () => {}, { scheduled: false });
      // Return null since we can't easily calculate next run without cron-parser
      return null;
    } catch {
      return null;
    }
  }

  /**
   * Persist task run times to state
   * @param {string} name - Task name
   * @param {string} lastRun - Last run timestamp
   * @param {string} nextRun - Next run timestamp
   */
  async _persistTaskState(name, lastRun, nextRun) {
    if (!this.stateManager) return;

    try {
      this.stateManager.set(`task:${name}:lastRun`, lastRun);
      if (nextRun) {
        this.stateManager.set(`task:${name}:nextRun`, nextRun);
      }
    } catch (error) {
      this.logger.error(`Failed to persist task state for ${name}: ${error.message}`);
    }
  }
}

export default Scheduler;
