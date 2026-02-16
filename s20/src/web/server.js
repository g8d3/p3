/**
 * Dashboard Server - Express + WebSocket server for agent dashboard
 * Provides REST API and real-time updates via WebSocket
 */

import express from 'express';
import cors from 'cors';
import { createServer } from 'http';
import { fileURLToPath } from 'url';
import { dirname, join } from 'path';
import { existsSync } from 'fs';
import { config } from '../../config/defaults.js';
import logger from '../infrastructure/logger.js';
import { createApiRouter } from './api.js';
import { getWebSocketManager } from './websocket.js';

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);

const log = logger.module('server');

/**
 * DashboardServer - Web server for agent dashboard
 */
export class DashboardServer {
  constructor(orchestrator) {
    this.orchestrator = orchestrator;
    this.app = null;
    this.server = null;
    this.wsManager = null;
    this.port = parseInt(process.env.DASHBOARD_PORT) || 3456;
    this.host = process.env.DASHBOARD_HOST || '0.0.0.0';
    this.authEnabled = !!(process.env.USERNAME && process.env.PASSWORD);
    this.running = false;
  }

  /**
   * Initialize and start the server
   */
  async start() {
    if (this.running) {
      log.warn('Dashboard server already running');
      return this;
    }

    // Create Express app
    this.app = express();

    // Create HTTP server
    this.server = createServer(this.app);

    // Initialize WebSocket manager
    this.wsManager = getWebSocketManager();
    this.wsManager.init(this.server);

    // Setup WebSocket events from orchestrator
    this.wsManager.setupOrchestratorEvents(this.orchestrator);

    // Store reference in orchestrator for broadcasting
    this.orchestrator.wsManager = this.wsManager;

    // Middleware
    this._setupMiddleware();

    // Routes
    this._setupRoutes();

    // Start listening
    await new Promise((resolve) => {
      this.server.listen(this.port, this.host, () => {
        resolve();
      });
    });

    this.running = true;
    log.info(`Dashboard server started on http://${this.host}:${this.port}`);
    
    if (this.authEnabled) {
      log.info('Basic authentication enabled');
    }

    return this;
  }

  /**
   * Setup Express middleware
   */
  _setupMiddleware() {
    // CORS - allow all origins for remote access
    this.app.use(cors({
      origin: '*',
      methods: ['GET', 'POST', 'PUT', 'DELETE', 'OPTIONS'],
      allowedHeaders: ['Content-Type', 'Authorization']
    }));

    // JSON body parser
    this.app.use(express.json());

    // URL-encoded body parser
    this.app.use(express.urlencoded({ extended: true }));

    // Basic authentication (optional)
    if (this.authEnabled) {
      this.app.use((req, res, next) => {
        // Skip auth for health check and WebSocket upgrade
        if (req.path === '/health' || req.headers.upgrade === 'websocket') {
          return next();
        }

        const authHeader = req.headers.authorization;
        
        if (!authHeader) {
          res.setHeader('WWW-Authenticate', 'Basic realm="Agent Dashboard"');
          return res.status(401).send('Authentication required');
        }

        const [scheme, credentials] = authHeader.split(' ');
        
        if (scheme !== 'Basic') {
          return res.status(401).send('Invalid authentication scheme');
        }

        const [username, password] = Buffer.from(credentials, 'base64')
          .toString()
          .split(':');

        if (username !== process.env.USERNAME || password !== process.env.PASSWORD) {
          res.setHeader('WWW-Authenticate', 'Basic realm="Agent Dashboard"');
          return res.status(401).send('Invalid credentials');
        }

        next();
      });
    }

    // Request logging
    this.app.use((req, res, next) => {
      const start = Date.now();
      
      res.on('finish', () => {
        const duration = Date.now() - start;
        log.debug(`${req.method} ${req.path} - ${res.statusCode} (${duration}ms)`);
      });

      next();
    });
  }

  /**
   * Setup routes
   */
  _setupRoutes() {
    // Health check endpoint (no auth required)
    this.app.get('/health', (req, res) => {
      res.json({
        status: 'ok',
        timestamp: new Date().toISOString(),
        uptime: process.uptime()
      });
    });

    // API routes
    const apiRouter = createApiRouter(this.orchestrator, this.wsManager);
    this.app.use('/api', apiRouter);

    // Static files from public directory
    const publicPath = join(__dirname, 'public');
    if (existsSync(publicPath)) {
      this.app.use(express.static(publicPath));
      log.debug(`Serving static files from ${publicPath}`);
    }

    // SPA fallback - serve index.html for unmatched routes
    this.app.get('*', (req, res) => {
      const indexPath = join(publicPath, 'index.html');
      if (existsSync(indexPath)) {
        res.sendFile(indexPath);
      } else {
        res.status(404).json({
          error: 'Not found',
          message: 'The requested resource was not found',
          hint: 'API endpoints are available at /api/*'
        });
      }
    });

    // Error handler
    this.app.use((err, req, res, next) => {
      log.error(`Unhandled error: ${err.message}`);
      log.error(err.stack);
      
      res.status(500).json({
        success: false,
        error: 'Internal server error',
        message: process.env.NODE_ENV === 'development' ? err.message : undefined
      });
    });
  }

  /**
   * Stop the server gracefully
   */
  async stop() {
    if (!this.running) {
      return this;
    }

    log.info('Stopping dashboard server...');

    // Close WebSocket connections
    if (this.wsManager) {
      this.wsManager.close();
    }

    // Close HTTP server
    if (this.server) {
      await new Promise((resolve) => {
        this.server.close(() => {
          log.info('HTTP server closed');
          resolve();
        });
      });
    }

    this.running = false;
    log.info('Dashboard server stopped');
    
    return this;
  }

  /**
   * Get server info
   */
  getInfo() {
    return {
      running: this.running,
      port: this.port,
      host: this.host,
      authEnabled: this.authEnabled,
      websocketClients: this.wsManager?.clients?.size || 0
    };
  }
}

/**
 * Create and start a dashboard server
 * @param {Orchestrator} orchestrator - Orchestrator instance
 * @param {object} options - Server options
 * @returns {Promise<DashboardServer>}
 */
export async function createDashboardServer(orchestrator, options = {}) {
  const server = new DashboardServer(orchestrator);
  
  if (options.port) {
    server.port = options.port;
  }
  if (options.host) {
    server.host = options.host;
  }

  await server.start();
  return server;
}

export default DashboardServer;
