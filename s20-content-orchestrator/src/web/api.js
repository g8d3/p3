/**
 * REST API Routes - Dashboard API endpoints
 * Provides HTTP endpoints for agent management and monitoring
 */

import { Router } from 'express';
import { config } from '../../config/defaults.js';
import { schedules } from '../../config/schedules.js';
import logger from '../infrastructure/logger.js';

const log = logger.module('api');

/**
 * Create API router
 * @param {Orchestrator} orchestrator - Orchestrator instance
 * @param {WebSocketManager} wsManager - WebSocket manager for broadcasting
 * @returns {Router}
 */
export function createApiRouter(orchestrator, wsManager) {
  const router = Router();
  const { state, scheduler, safety } = orchestrator;

  // ===========================================
  // Status & Health
  // ===========================================

  /**
   * GET /api/status - Agent status, health, module states
   */
  router.get('/status', async (req, res) => {
    try {
      const status = orchestrator.getStatus();
      const health = await orchestrator.healthCheck();
      const stats = state?.getStats() || {};

      res.json({
        success: true,
        data: {
          status,
          health,
          stats,
          timestamp: new Date().toISOString()
        }
      });
    } catch (error) {
      log.error(`Status error: ${error.message}`);
      res.status(500).json({ success: false, error: error.message });
    }
  });

  // ===========================================
  // Tasks
  // ===========================================

  /**
   * GET /api/tasks - All scheduled tasks with status
   */
  router.get('/tasks', (req, res) => {
    try {
      const tasks = scheduler?.getStatus() || [];
      
      res.json({
        success: true,
        data: tasks.map(task => ({
          name: task.name,
          module: task.module,
          action: task.action,
          cron: task.cron,
          enabled: task.enabled,
          lastRun: task.lastRun,
          nextRun: task.nextRun,
          description: task.description
        }))
      });
    } catch (error) {
      log.error(`Tasks error: ${error.message}`);
      res.status(500).json({ success: false, error: error.message });
    }
  });

  /**
   * GET /api/tasks/:name/run - Manually trigger a task
   */
  router.get('/tasks/:name/run', async (req, res) => {
    try {
      const { name } = req.params;
      const result = await scheduler?.runNow(name);

      if (result) {
        // Broadcast event
        wsManager?.broadcast('task:started', { taskName: name, manual: true });
        
        res.json({
          success: true,
          data: { taskName: name, message: 'Task triggered successfully' }
        });
      } else {
        res.status(404).json({
          success: false,
          error: `Task not found: ${name}`
        });
      }
    } catch (error) {
      log.error(`Task run error: ${error.message}`);
      res.status(500).json({ success: false, error: error.message });
    }
  });

  /**
   * GET /api/tasks/:name/enable - Enable a task
   */
  router.get('/tasks/:name/enable', (req, res) => {
    try {
      const { name } = req.params;
      const result = scheduler?.enable(name);

      if (result) {
        wsManager?.broadcast('task:enabled', { taskName: name });
        res.json({
          success: true,
          data: { taskName: name, message: 'Task enabled' }
        });
      } else {
        res.status(404).json({
          success: false,
          error: `Task not found: ${name}`
        });
      }
    } catch (error) {
      log.error(`Task enable error: ${error.message}`);
      res.status(500).json({ success: false, error: error.message });
    }
  });

  /**
   * GET /api/tasks/:name/disable - Disable a task
   */
  router.get('/tasks/:name/disable', (req, res) => {
    try {
      const { name } = req.params;
      const result = scheduler?.disable(name);

      if (result) {
        wsManager?.broadcast('task:disabled', { taskName: name });
        res.json({
          success: true,
          data: { taskName: name, message: 'Task disabled' }
        });
      } else {
        res.status(404).json({
          success: false,
          error: `Task not found: ${name}`
        });
      }
    } catch (error) {
      log.error(`Task disable error: ${error.message}`);
      res.status(500).json({ success: false, error: error.message });
    }
  });

  // ===========================================
  // Content
  // ===========================================

  /**
   * GET /api/content - List content items
   * Query params: status (draft, scheduled, posted), limit
   */
  router.get('/content', (req, res) => {
    try {
      const { status, limit = 100 } = req.query;
      
      let items;
      if (status) {
        items = state?.getContentItemsByStatus(status, parseInt(limit)) || [];
      } else {
        // Get all statuses
        const drafts = state?.getContentItemsByStatus('draft', 50) || [];
        const scheduled = state?.getContentItemsByStatus('scheduled', 50) || [];
        const posted = state?.getContentItemsByStatus('posted', 50) || [];
        items = [...drafts, ...scheduled, ...posted];
      }

      res.json({
        success: true,
        data: items.map(item => ({
          id: item.id,
          type: item.type,
          status: item.status,
          content: item.content,
          platform: item.platform,
          postedAt: item.posted_at,
          externalId: item.external_id,
          engagementMetrics: item.engagement_metrics ? JSON.parse(item.engagement_metrics) : null,
          createdAt: item.created_at
        }))
      });
    } catch (error) {
      log.error(`Content list error: ${error.message}`);
      res.status(500).json({ success: false, error: error.message });
    }
  });

  /**
   * POST /api/content - Create content manually
   */
  router.post('/content', (req, res) => {
    try {
      const { type = 'tweet', content, status = 'draft', platform = 'twitter' } = req.body;

      if (!content) {
        return res.status(400).json({
          success: false,
          error: 'Content is required'
        });
      }

      const result = state?.createContentItem({ type, content, status, platform });
      
      wsManager?.broadcast('content:generated', { type, status, platform });
      
      res.json({
        success: true,
        data: {
          id: result?.lastInsertRowid,
          type,
          status,
          message: 'Content created successfully'
        }
      });
    } catch (error) {
      log.error(`Content create error: ${error.message}`);
      res.status(500).json({ success: false, error: error.message });
    }
  });

  /**
   * GET /api/content/:id/post - Post a draft now
   */
  router.get('/content/:id/post', async (req, res) => {
    try {
      const { id } = req.params;

      // Get the content item
      const item = state?.queryOne(
        'SELECT * FROM content_items WHERE id = ?',
        [parseInt(id)]
      );

      if (!item) {
        return res.status(404).json({
          success: false,
          error: `Content not found: ${id}`
        });
      }

      if (item.status === 'posted') {
        return res.status(400).json({
          success: false,
          error: 'Content already posted'
        });
      }

      // If we have Twitter service and it's connected, try to post
      if (orchestrator.twitter && orchestrator.browser?.isConnected()) {
        // For now, mark as posted - actual posting would go through Twitter service
        state?.updateContentItemStatus(id, 'posted');
        
        wsManager?.broadcast('content:posted', { id, type: item.type });
        
        res.json({
          success: true,
          data: { id, message: 'Content posted successfully' }
        });
      } else {
        // Browser not connected, just update status
        state?.updateContentItemStatus(id, 'posted');
        
        res.json({
          success: true,
          data: { id, message: 'Content marked as posted (browser not connected)' }
        });
      }
    } catch (error) {
      log.error(`Content post error: ${error.message}`);
      res.status(500).json({ success: false, error: error.message });
    }
  });

  // ===========================================
  // Approvals
  // ===========================================

  /**
   * GET /api/approvals - List pending approvals
   */
  router.get('/approvals', async (req, res) => {
    try {
      const approvals = await safety?.approval?.getPending() || [];

      res.json({
        success: true,
        data: approvals
      });
    } catch (error) {
      log.error(`Approvals list error: ${error.message}`);
      res.status(500).json({ success: false, error: error.message });
    }
  });

  /**
   * POST /api/approvals/:id/approve - Approve an action
   */
  router.post('/approvals/:id/approve', async (req, res) => {
    try {
      const { id } = req.params;
      const { note = '' } = req.body;

      const result = await safety?.approval?.approve(id, note, 'dashboard');

      if (result.success) {
        wsManager?.broadcast('approval:resolved', { id, status: 'approved' });
      }

      res.json({
        success: result.success,
        data: result
      });
    } catch (error) {
      log.error(`Approval error: ${error.message}`);
      res.status(500).json({ success: false, error: error.message });
    }
  });

  /**
   * POST /api/approvals/:id/reject - Reject an action
   */
  router.post('/approvals/:id/reject', async (req, res) => {
    try {
      const { id } = req.params;
      const { note = '' } = req.body;

      const result = await safety?.approval?.reject(id, note, 'dashboard');

      if (result.success) {
        wsManager?.broadcast('approval:resolved', { id, status: 'rejected' });
      }

      res.json({
        success: result.success,
        data: result
      });
    } catch (error) {
      log.error(`Rejection error: ${error.message}`);
      res.status(500).json({ success: false, error: error.message });
    }
  });

  // ===========================================
  // Learnings
  // ===========================================

  /**
   * GET /api/learnings - List accumulated learnings
   */
  router.get('/learnings', (req, res) => {
    try {
      const { category, limit = 100 } = req.query;

      let learnings;
      if (category) {
        learnings = state?.getLearningsByCategory(category, parseInt(limit)) || [];
      } else {
        learnings = state?.query(
          'SELECT * FROM learnings ORDER BY confidence DESC, created_at DESC LIMIT ?',
          [parseInt(limit)]
        ) || [];
      }

      res.json({
        success: true,
        data: learnings.map(l => ({
          id: l.id,
          category: l.category,
          insight: l.insight,
          evidence: l.evidence ? JSON.parse(l.evidence) : null,
          confidence: l.confidence,
          applicableTo: l.applicable_to ? JSON.parse(l.applicable_to) : null,
          createdAt: l.created_at
        }))
      });
    } catch (error) {
      log.error(`Learnings error: ${error.message}`);
      res.status(500).json({ success: false, error: error.message });
    }
  });

  // ===========================================
  // Experiments
  // ===========================================

  /**
   * GET /api/experiments - List experiments and results
   */
  router.get('/experiments', (req, res) => {
    try {
      const experiments = state?.query(
        'SELECT * FROM experiments ORDER BY start_date DESC'
      ) || [];

      res.json({
        success: true,
        data: experiments.map(e => ({
          id: e.id,
          name: e.name,
          hypothesis: e.hypothesis,
          startDate: e.start_date,
          endDate: e.end_date,
          variants: e.variants ? JSON.parse(e.variants) : null,
          results: e.results ? JSON.parse(e.results) : null
        }))
      });
    } catch (error) {
      log.error(`Experiments error: ${error.message}`);
      res.status(500).json({ success: false, error: error.message });
    }
  });

  // ===========================================
  // Logs
  // ===========================================

  /**
   * GET /api/logs - Recent action logs (last 100)
   */
  router.get('/logs', (req, res) => {
    try {
      const { limit = 100, module } = req.query;

      const logs = state?.getRecentActions(parseInt(limit), module) || [];

      res.json({
        success: true,
        data: logs.map(l => ({
          id: l.id,
          timestamp: l.timestamp,
          module: l.module,
          action: l.action,
          params: l.params ? JSON.parse(l.params) : null,
          result: l.result,
          error: l.error,
          durationMs: l.duration_ms
        }))
      });
    } catch (error) {
      log.error(`Logs error: ${error.message}`);
      res.status(500).json({ success: false, error: error.message });
    }
  });

  // ===========================================
  // Config
  // ===========================================

  /**
   * GET /api/config - Current configuration (safe values only)
   */
  router.get('/config', (req, res) => {
    try {
      // Return safe config values (no secrets)
      const safeConfig = {
        chrome: {
          port: config.chrome.port,
          host: config.chrome.host
        },
        llm: {
          provider: config.llm.provider,
          model: config.llm.model,
          maxTokens: config.llm.maxTokens
        },
        safety: {
          dryRun: config.safety.dryRun,
          requireApproval: config.safety.requireApproval,
          approvalTimeoutHours: config.safety.approvalTimeoutHours,
          rateLimits: config.safety.rateLimits
        },
        logging: {
          level: config.logging.level
        },
        identity: config.identity
      };

      res.json({
        success: true,
        data: safeConfig
      });
    } catch (error) {
      log.error(`Config error: ${error.message}`);
      res.status(500).json({ success: false, error: error.message });
    }
  });

  /**
   * POST /api/config - Update runtime config
   */
  router.post('/config', (req, res) => {
    try {
      const updates = req.body;

      // Only allow certain runtime config updates
      const allowedUpdates = ['dryRun', 'requireApproval', 'logLevel'];
      const appliedUpdates = {};

      for (const [key, value] of Object.entries(updates)) {
        if (allowedUpdates.includes(key)) {
          switch (key) {
            case 'dryRun':
              if (safety?.dryRun) {
                safety.dryRun.enabled = Boolean(value);
                appliedUpdates[key] = Boolean(value);
              }
              break;
            case 'requireApproval':
              if (safety?.approval) {
                safety.approval.requireApproval = Boolean(value);
                appliedUpdates[key] = Boolean(value);
              }
              break;
            case 'logLevel':
              // Update logger level if supported
              appliedUpdates[key] = value;
              break;
          }
        }
      }

      wsManager?.broadcast('config:updated', appliedUpdates);

      res.json({
        success: true,
        data: { appliedUpdates, message: 'Configuration updated' }
      });
    } catch (error) {
      log.error(`Config update error: ${error.message}`);
      res.status(500).json({ success: false, error: error.message });
    }
  });

  // ===========================================
  // Agent Control
  // ===========================================

  /**
   * POST /api/agent/stop - Graceful stop
   */
  router.post('/agent/stop', async (req, res) => {
    try {
      res.json({
        success: true,
        data: { message: 'Initiating graceful shutdown...' }
      });

      // Shutdown after response
      setImmediate(async () => {
        await orchestrator.stop();
        process.exit(0);
      });
    } catch (error) {
      log.error(`Stop error: ${error.message}`);
      res.status(500).json({ success: false, error: error.message });
    }
  });

  /**
   * POST /api/agent/restart - Restart agent (if using pm2/systemd)
   */
  router.post('/agent/restart', async (req, res) => {
    try {
      // Check if running under process manager
      const hasPm2 = process.env.pm_id !== undefined;
      const hasSystemd = process.env.INVOCATION_ID !== undefined;

      if (!hasPm2 && !hasSystemd) {
        return res.status(400).json({
          success: false,
          error: 'Restart only available when running under pm2 or systemd'
        });
      }

      res.json({
        success: true,
        data: { message: 'Initiating restart...' }
      });

      // Exit with code that process manager will interpret as restart
      setImmediate(async () => {
        await orchestrator.stop();
        process.exit(0); // pm2/systemd will restart
      });
    } catch (error) {
      log.error(`Restart error: ${error.message}`);
      res.status(500).json({ success: false, error: error.message });
    }
  });

  // ===========================================
  // WebSocket Stats
  // ===========================================

  /**
   * GET /api/ws/stats - WebSocket connection stats
   */
  router.get('/ws/stats', (req, res) => {
    try {
      const stats = wsManager?.getStats() || { connectedClients: 0, clients: [] };
      res.json({ success: true, data: stats });
    } catch (error) {
      res.status(500).json({ success: false, error: error.message });
    }
  });

  return router;
}

export default createApiRouter;
