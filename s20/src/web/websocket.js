/**
 * WebSocket Manager - Real-time event broadcasting
 * Handles WebSocket connections and broadcasts events to clients
 */

import { WebSocketServer } from 'ws';
import logger from '../infrastructure/logger.js';

const log = logger.module('websocket');

/**
 * WebSocketManager - Manages WebSocket connections and event broadcasting
 */
export class WebSocketManager {
  constructor() {
    this.wss = null;
    this.clients = new Map(); // Map of ws -> { subscriptions: Set }
    this.heartbeatInterval = null;
    this.heartbeatFrequency = 30000; // 30 seconds
  }

  /**
   * Initialize WebSocket server
   * @param {http.Server} server - HTTP server instance
   */
  init(server) {
    this.wss = new WebSocketServer({ server, path: '/ws' });
    
    this.wss.on('connection', (ws, req) => {
      const clientIp = req.socket.remoteAddress;
      const clientId = `${clientIp}:${Date.now()}`;
      
      // Store client with empty subscriptions (subscribe to all by default)
      this.clients.set(ws, {
        id: clientId,
        ip: clientIp,
        connectedAt: new Date(),
        subscriptions: new Set() // Empty = all events
      });

      log.info(`Client connected: ${clientId}`);
      
      // Send welcome message
      this.sendToClient(ws, {
        type: 'connected',
        data: {
          message: 'Connected to agent dashboard',
          timestamp: new Date().toISOString()
        }
      });

      // Handle incoming messages (subscriptions)
      ws.on('message', (data) => {
        try {
          const message = JSON.parse(data.toString());
          this._handleClientMessage(ws, message);
        } catch (error) {
          log.warn(`Invalid message from client: ${error.message}`);
        }
      });

      // Handle disconnect
      ws.on('close', () => {
        const client = this.clients.get(ws);
        if (client) {
          log.info(`Client disconnected: ${client.id}`);
          this.clients.delete(ws);
        }
      });

      // Handle errors
      ws.on('error', (error) => {
        log.error(`WebSocket error: ${error.message}`);
      });

      // Setup ping/pong for connection health
      ws.isAlive = true;
      ws.on('pong', () => {
        ws.isAlive = true;
      });
    });

    // Start heartbeat interval
    this._startHeartbeat();

    log.info(`WebSocket server initialized, path: /ws`);
    return this;
  }

  /**
   * Handle incoming client messages (subscriptions)
   * @param {WebSocket} ws - WebSocket client
   * @param {object} message - Parsed message
   */
  _handleClientMessage(ws, message) {
    const client = this.clients.get(ws);
    if (!client) return;

    switch (message.type) {
      case 'subscribe':
        // Subscribe to specific event types
        if (Array.isArray(message.events)) {
          for (const event of message.events) {
            client.subscriptions.add(event);
          }
          log.debug(`Client ${client.id} subscribed to: ${message.events.join(', ')}`);
        }
        this.sendToClient(ws, {
          type: 'subscribed',
          data: { events: Array.from(client.subscriptions) }
        });
        break;

      case 'unsubscribe':
        // Unsubscribe from event types
        if (Array.isArray(message.events)) {
          for (const event of message.events) {
            client.subscriptions.delete(event);
          }
          log.debug(`Client ${client.id} unsubscribed from: ${message.events.join(', ')}`);
        }
        this.sendToClient(ws, {
          type: 'unsubscribed',
          data: { events: Array.from(client.subscriptions) }
        });
        break;

      case 'ping':
        // Respond to ping
        this.sendToClient(ws, { type: 'pong', data: { timestamp: Date.now() } });
        break;

      default:
        log.warn(`Unknown message type from client: ${message.type}`);
    }
  }

  /**
   * Send a message to a specific client
   * @param {WebSocket} ws - WebSocket client
   * @param {object} message - Message to send
   */
  sendToClient(ws, message) {
    if (ws.readyState === 1) { // WebSocket.OPEN
      ws.send(JSON.stringify(message));
    }
  }

  /**
   * Broadcast an event to all connected clients (or subscribed clients)
   * @param {string} eventType - Event type (e.g., 'task:started')
   * @param {object} data - Event data
   */
  broadcast(eventType, data) {
    const message = {
      type: eventType,
      data,
      timestamp: new Date().toISOString()
    };

    const messageStr = JSON.stringify(message);
    let recipientCount = 0;

    for (const [ws, client] of this.clients) {
      // Check if client should receive this event
      if (this._shouldSendToClient(client, eventType)) {
        if (ws.readyState === 1) { // WebSocket.OPEN
          ws.send(messageStr);
          recipientCount++;
        }
      }
    }

    log.debug(`Broadcast ${eventType} to ${recipientCount} clients`);
  }

  /**
   * Check if client should receive an event based on subscriptions
   * @param {object} client - Client info
   * @param {string} eventType - Event type
   * @returns {boolean}
   */
  _shouldSendToClient(client, eventType) {
    // Empty subscriptions = receive all events
    if (client.subscriptions.size === 0) {
      return true;
    }
    // Check if subscribed to this event type
    return client.subscriptions.has(eventType);
  }

  /**
   * Start heartbeat to detect dead connections
   */
  _startHeartbeat() {
    this.heartbeatInterval = setInterval(() => {
      for (const [ws, client] of this.clients) {
        if (!ws.isAlive) {
          log.debug(`Terminating dead connection: ${client.id}`);
          ws.terminate();
          this.clients.delete(ws);
          continue;
        }

        ws.isAlive = false;
        ws.ping();
      }

      // Broadcast agent status heartbeat
      this.broadcast('agent:heartbeat', {
        clients: this.clients.size,
        uptime: process.uptime()
      });
    }, this.heartbeatFrequency);
  }

  /**
   * Setup event listeners on orchestrator to broadcast events
   * @param {Orchestrator} orchestrator - Orchestrator instance
   */
  setupOrchestratorEvents(orchestrator) {
    // Task events
    orchestrator.on('task:complete', ({ module, action, result, duration }) => {
      this.broadcast('task:complete', { module, action, result, duration });
    });

    orchestrator.on('task:error', ({ module, action, error, duration }) => {
      this.broadcast('task:error', { module, action, error: error.message, duration });
    });

    // Module events
    orchestrator.on('module:enabled', ({ module }) => {
      this.broadcast('module:enabled', { module });
    });

    orchestrator.on('module:disabled', ({ module, failures }) => {
      this.broadcast('module:disabled', { module, failures });
    });

    // Lifecycle events
    orchestrator.on('started', () => {
      this.broadcast('agent:started', { timestamp: new Date().toISOString() });
    });

    orchestrator.on('stopping', () => {
      this.broadcast('agent:stopping', { timestamp: new Date().toISOString() });
    });

    orchestrator.on('stopped', () => {
      this.broadcast('agent:stopped', { timestamp: new Date().toISOString() });
    });

    // Browser events
    orchestrator.on('browser:connected', () => {
      this.broadcast('browser:connected', { timestamp: new Date().toISOString() });
    });

    orchestrator.on('browser:disconnected', () => {
      this.broadcast('browser:disconnected', { timestamp: new Date().toISOString() });
    });

    log.info('Orchestrator event listeners registered');
  }

  /**
   * Get WebSocket server statistics
   * @returns {object}
   */
  getStats() {
    return {
      connectedClients: this.clients.size,
      clients: Array.from(this.clients.values()).map(c => ({
        id: c.id,
        connectedAt: c.connectedAt,
        subscriptions: Array.from(c.subscriptions)
      }))
    };
  }

  /**
   * Close WebSocket server
   */
  close() {
    if (this.heartbeatInterval) {
      clearInterval(this.heartbeatInterval);
      this.heartbeatInterval = null;
    }

    if (this.wss) {
      // Close all client connections
      for (const [ws] of this.clients) {
        ws.close(1001, 'Server shutting down');
      }
      this.clients.clear();

      // Close server
      this.wss.close(() => {
        log.info('WebSocket server closed');
      });
    }
  }
}

// Export singleton
let wsManagerInstance = null;

export function getWebSocketManager() {
  if (!wsManagerInstance) {
    wsManagerInstance = new WebSocketManager();
  }
  return wsManagerInstance;
}

export default WebSocketManager;
