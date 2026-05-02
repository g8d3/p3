import WebSocket from 'ws';
import http from 'http';
import EventEmitter from 'events';
import { config } from '../../config/defaults.js';

/**
 * BrowserClient - Chrome DevTools Protocol automation client
 * 
 * Events:
 * - 'connected': Emitted when WebSocket connection is established
 * - 'disconnected': Emitted when connection is closed
 * - 'error': Emitted on errors (err: Error)
 * - 'reconnecting': Emitted when attempting reconnection (attempt: number, delay: number)
 */
class BrowserClient extends EventEmitter {
  constructor(options = {}) {
    super();
    
    // Configuration
    this.host = options.host || config.chrome.host;
    this.port = options.port || config.chrome.port;
    this.reconnectConfig = {
      maxAttempts: options.maxAttempts ?? config.chrome.reconnect.maxAttempts,
      baseDelay: options.baseDelay ?? config.chrome.reconnect.baseDelay,
      maxDelay: options.maxDelay ?? config.chrome.reconnect.maxDelay
    };
    this.commandTimeout = options.commandTimeout || 30000; // 30 seconds default
    
    // Connection state
    this.ws = null;
    this.connected = false;
    this.reconnectAttempts = 0;
    this.reconnectTimer = null;
    this.intentionallyClosed = false;
    
    // Message correlation
    this.messageId = 0;
    this.pendingCommands = new Map();
    
    // Bind methods
    this._handleMessage = this._handleMessage.bind(this);
    this._handleClose = this._handleClose.bind(this);
    this._handleError = this._handleError.bind(this);
  }
  
  /**
   * Get the HTTP base URL for Chrome DevTools Protocol
   */
  get _httpBaseUrl() {
    return `http://${this.host}:${this.port}`;
  }
  
  /**
   * Make an HTTP request to Chrome DevTools Protocol
   */
  async _requestJSON(path, method = 'GET') {
    return new Promise((resolve, reject) => {
      const url = `${this._httpBaseUrl}${path}`;
      const req = http.request(url, { method }, (res) => {
        let data = '';
        res.on('data', (chunk) => data += chunk);
        res.on('end', () => {
          try {
            resolve(data ? JSON.parse(data) : {});
          } catch (e) {
            reject(new Error(`Failed to parse response: ${e.message}`));
          }
        });
      });
      req.on('error', reject);
      req.end();
    });
  }
  
  /**
   * Check if currently connected to Chrome
   */
  isConnected() {
    return this.connected && this.ws && this.ws.readyState === WebSocket.OPEN;
  }
  
  /**
   * Connect to Chrome DevTools Protocol
   * @returns {Promise<void>}
   */
  async connect() {
    if (this.isConnected()) {
      return;
    }
    
    this.intentionallyClosed = false;
    
    try {
      // Get available targets from Chrome
      const targets = await this._requestJSON('/json');
      
      if (!targets || targets.length === 0) {
        throw new Error('No Chrome targets available. Ensure Chrome is running with --remote-debugging-port=9222');
      }
      
      // Find a page target or use the first available
      const target = targets.find(t => t.type === 'page') || targets[0];
      const wsUrl = target.webSocketDebuggerUrl;
      
      if (!wsUrl) {
        throw new Error('No WebSocket debugger URL found in Chrome targets');
      }
      
      await this._connectWebSocket(wsUrl);
      
    } catch (error) {
      this.emit('error', error);
      throw error;
    }
  }
  
  /**
   * Establish WebSocket connection
   * @param {string} wsUrl - WebSocket URL to connect to
   * @returns {Promise<void>}
   */
  _connectWebSocket(wsUrl) {
    return new Promise((resolve, reject) => {
      this.ws = new WebSocket(wsUrl);
      
      const onOpen = () => {
        this.connected = true;
        this.reconnectAttempts = 0;
        this.emit('connected');
        resolve();
      };
      
      const onError = (err) => {
        cleanup();
        reject(err);
      };
      
      const cleanup = () => {
        this.ws.removeListener('open', onOpen);
        this.ws.removeListener('error', onError);
      };
      
      this.ws.once('open', onOpen);
      this.ws.once('error', onError);
      
      this.ws.on('message', this._handleMessage);
      this.ws.on('close', this._handleClose);
      this.ws.on('error', this._handleError);
    });
  }
  
  /**
   * Handle incoming WebSocket messages
   */
  _handleMessage(data) {
    try {
      const message = JSON.parse(data.toString());
      
      // Handle command response
      if (message.id !== undefined) {
        const pending = this.pendingCommands.get(message.id);
        if (pending) {
          this.pendingCommands.delete(message.id);
          clearTimeout(pending.timeout);
          
          if (message.error) {
            pending.reject(new Error(message.error.message || 'CDP command failed'));
          } else {
            pending.resolve(message.result);
          }
        }
      }
      
      // Handle events (messages without id)
      if (message.method) {
        this.emit('event', message);
      }
      
    } catch (error) {
      this.emit('error', new Error(`Failed to parse message: ${error.message}`));
    }
  }
  
  /**
   * Handle WebSocket close event
   */
  _handleClose() {
    const wasConnected = this.connected;
    this.connected = false;
    
    // Reject all pending commands
    for (const [id, pending] of this.pendingCommands) {
      clearTimeout(pending.timeout);
      pending.reject(new Error('Connection closed'));
    }
    this.pendingCommands.clear();
    
    if (wasConnected) {
      this.emit('disconnected');
    }
    
    // Attempt reconnection if not intentionally closed
    if (!this.intentionallyClosed && this.reconnectAttempts < this.reconnectConfig.maxAttempts) {
      this._scheduleReconnect();
    }
  }
  
  /**
   * Handle WebSocket error event
   */
  _handleError(err) {
    this.emit('error', err);
  }
  
  /**
   * Schedule a reconnection attempt with exponential backoff
   */
  _scheduleReconnect() {
    this.reconnectAttempts++;
    
    // Calculate delay with exponential backoff
    const delay = Math.min(
      this.reconnectConfig.baseDelay * Math.pow(2, this.reconnectAttempts - 1),
      this.reconnectConfig.maxDelay
    );
    
    this.emit('reconnecting', this.reconnectAttempts, delay);
    
    this.reconnectTimer = setTimeout(async () => {
      try {
        await this.connect();
      } catch (error) {
        // Error is already emitted, reconnect will be scheduled again if attempts remain
        if (this.reconnectAttempts >= this.reconnectConfig.maxAttempts) {
          this.emit('error', new Error(`Max reconnection attempts (${this.reconnectConfig.maxAttempts}) reached`));
        }
      }
    }, delay);
  }
  
  /**
   * Disconnect from Chrome
   */
  disconnect() {
    this.intentionallyClosed = true;
    
    if (this.reconnectTimer) {
      clearTimeout(this.reconnectTimer);
      this.reconnectTimer = null;
    }
    
    // Reject all pending commands
    for (const [id, pending] of this.pendingCommands) {
      clearTimeout(pending.timeout);
      pending.reject(new Error('Disconnected'));
    }
    this.pendingCommands.clear();
    
    if (this.ws) {
      this.ws.close();
      this.ws = null;
    }
    
    this.connected = false;
    this.emit('disconnected');
  }
  
  /**
   * Send a CDP command
   * @param {string} method - CDP method name
   * @param {object} params - Command parameters
   * @param {number} timeout - Optional timeout in ms
   * @returns {Promise<any>} Command result
   */
  sendCommand(method, params = {}, timeout = this.commandTimeout) {
    return new Promise((resolve, reject) => {
      if (!this.isConnected()) {
        reject(new Error('Not connected to Chrome'));
        return;
      }
      
      const id = ++this.messageId;
      
      const message = {
        id,
        method,
        params
      };
      
      // Set up timeout
      const timeoutId = setTimeout(() => {
        this.pendingCommands.delete(id);
        reject(new Error(`Command ${method} timed out after ${timeout}ms`));
      }, timeout);
      
      // Store pending command
      this.pendingCommands.set(id, {
        resolve,
        reject,
        timeout: timeoutId
      });
      
      // Send message
      try {
        this.ws.send(JSON.stringify(message));
      } catch (error) {
        this.pendingCommands.delete(id);
        clearTimeout(timeoutId);
        reject(error);
      }
    });
  }
  
  /**
   * Get list of open tabs/pages
   * @returns {Promise<Array>} List of tab objects
   */
  async getTabs() {
    try {
      const targets = await this._requestJSON('/json');
      return targets.filter(t => t.type === 'page');
    } catch (error) {
      this.emit('error', error);
      throw error;
    }
  }
  
  /**
   * Create a new tab with the given URL
   * @param {string} url - URL to open in new tab
   * @returns {Promise<object>} New tab info
   */
  async createTab(url) {
    try {
      const encodedUrl = encodeURIComponent(url);
      const tab = await this._requestJSON(`/json/new?${encodedUrl}`, 'PUT');
      return tab;
    } catch (error) {
      this.emit('error', error);
      throw error;
    }
  }
  
  /**
   * Close a tab by target ID
   * @param {string} targetId - Target ID of tab to close
   * @returns {Promise<void>}
   */
  async closeTab(targetId) {
    try {
      await this._requestJSON(`/json/close/${targetId}`);
    } catch (error) {
      this.emit('error', error);
      throw error;
    }
  }
}

export default BrowserClient;
export { BrowserClient };
