import React from 'react';
import ReactDOM from 'react-dom/client';
import { BrowserRouter } from 'react-router-dom';
import App from './App';
import './App.css';

// ─── RENDER FIRST ──────────────────────────────────────────────────
try {
  ReactDOM.createRoot(document.getElementById('root')).render(
    React.createElement(React.StrictMode, null,
      React.createElement(BrowserRouter, null,
        React.createElement(App, null)
      )
    )
  );
} catch (e) {
  console.log('[FATAL] Render failed:', e);
}

// ─── Native WebSocket Client (replaces Socket.IO) ─────────────────
// Simple event-based wrapper that mimics socket.io-client interface
// so existing code (socket.on/emit) works without changes.
// No Engine.IO, no upgrade, no RangeError.

class WsClient {
  constructor(url) {
    this._listeners = {};
    this._connected = false;
    this._url = url;
    this._connect();
  }

  get connected() { return this._connected; }

  _connect() {
    var self = this;
    self._connected = false; // Reset on reconnect (prevents stale state)
    try {
      self.ws = new WebSocket(self._url);
    } catch (e) {
      console.log('[WS] Connection failed:', e.message);
      self._reconnect();
      return;
    }

    self.ws.onopen = function() {
      self._connected = true;
      self._emit('connect');
    };

    self.ws.onclose = function() {
      self._connected = false;
      self._emit('disconnect');
      self._reconnect();
    };

    self.ws.onerror = function() {
      // onclose will fire after this
    };

    self.ws.onmessage = function(event) {
      try {
        var msg = JSON.parse(event.data);
        var payload = msg.data || msg;
        self._emit(msg.type, payload);
        self._emit('message', msg);
      } catch (e) {
        console.log('[WS] Invalid message:', e.message);
      }
    };
  }

  _emit(event, data) {
    if (event === 'stream:frame') console.log('[WsClient] stream:frame received, frameCount:', data?.frameCount);
    var listeners = this._listeners[event];
    if (listeners) {
      var copy = listeners.slice();
      for (var i = 0; i < copy.length; i++) {
        copy[i](data);
      }
    } else {
      if (event === 'stream:frame') console.log('[WsClient] No listeners for stream:frame!');
    }
  }

  _reconnect() {
    var self = this;
    setTimeout(function() {
      if (!self._connected) self._connect();
    }, 3000);
  }

  on(event, callback) {
    if (!this._listeners[event]) this._listeners[event] = [];
    this._listeners[event].push(callback);
    return this;
  }

  off(event, callback) {
    if (!this._listeners[event]) return this;
    if (callback) {
      this._listeners[event] = this._listeners[event].filter(function(cb) { return cb !== callback; });
    } else {
      delete this._listeners[event];
    }
    return this;
  }

  emit(event, data) {
    if (data === undefined) data = {};
    console.log('[WsClient] emit called:', event, this._connected, !!this.ws);
    if (this._connected && this.ws) {
      var msg = { type: event };
      for (var key in data) msg[key] = data[key];
      this.ws.send(JSON.stringify(msg));
      console.log('[WsClient] emit sent:', event);
    } else {
      console.log('[WsClient] emit BLOCKED:', event, 'connected:', this._connected, 'ws:', !!this.ws);
    }
  }

  close() {
    var self = this;
    if (self.ws) {
      self.ws.onclose = null;
      self.ws.close();
      self.ws = null;
    }
  }
}

// ─── Create system WebSocket connection ────────────────────────────
// In dev mode (Vite on port 5173), connect directly to backend (port 3001)
// In production, connect to same origin
const isDev = window.location.port === '5173';
const wsPort = isDev ? '3001' : window.location.port || '80';
const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
const wsUrl = `${protocol}//${window.location.hostname}:${wsPort}`;

const systemSocket = new WsClient(wsUrl);
window.__systemSocket = systemSocket;
window.__WsClient = WsClient;

systemSocket.on('connect', () => {
  console.log('[System] Connected:', wsUrl);
  flushErrorBuffer();
});

// ─── Error Buffer ──────────────────────────────────────────────────
const errorBuffer = [];
let bufferTimer = null;
let lastReportTime = 0;
let reportsThisSecond = 0;

function flushErrorBuffer() {
  if (errorBuffer.length === 0) return;
  const batch = errorBuffer.splice(0);
  if (systemSocket?.connected) {
    systemSocket.emit('client:errors', { errors: batch });
  }
  try {
    navigator.sendBeacon?.('/api/errors/client-batch',
      new Blob([JSON.stringify(batch)], { type: 'application/json' }));
  } catch {}
}

function scheduleFlush() {
  if (bufferTimer) return;
  bufferTimer = setTimeout(() => {
    bufferTimer = null;
    flushErrorBuffer();
  }, 2000);
}

function flushNow() {
  if (bufferTimer) { clearTimeout(bufferTimer); bufferTimer = null; }
  flushErrorBuffer();
}

function canReport() {
  const now = Date.now();
  if (now - lastReportTime > 1000) {
    reportsThisSecond = 0;
    lastReportTime = now;
  }
  reportsThisSecond++;
  return reportsThisSecond <= 10;
}

let _reporting = false;

function reportError(message, stack) {
  if (_reporting) return;
  if (!canReport()) return;

  _reporting = true;
  try {
    const msg = String(message || '');
    errorBuffer.push({
      message: msg,
      stack: String(stack || ''),
      url: window.location.href,
      timestamp: Date.now(),
    });
    if (msg.includes('RangeError') || msg.includes('stack') || msg.includes('Maximum')) {
      flushNow();
    } else {
      scheduleFlush();
    }
  } catch (e) {
    try { console.log('[ER]', String(e)); } catch {}
  }
  _reporting = false;
}

try {
  const pending = localStorage.getItem('__twitch_pending_errors');
  if (pending) {
    localStorage.removeItem('__twitch_pending_errors');
    try { JSON.parse(pending).forEach(e => errorBuffer.push(e)); scheduleFlush(); } catch {}
  }
} catch {}

window.__sendError = reportError;

// ─── Console.error override (with safety valve) ────────────────────
let consoleErrorCount = 0;
let consoleErrorResetTimer = null;
const _origConsoleError = console.error;

try {
  console.error = (...args) => {
    consoleErrorCount++;
    if (!consoleErrorResetTimer) {
      consoleErrorResetTimer = setTimeout(() => {
        consoleErrorCount = 0;
        consoleErrorResetTimer = null;
      }, 1000);
    }
    if (consoleErrorCount > 30) {
      if (_origConsoleError) _origConsoleError.apply(console, args);
      return;
    }
    let stack = '';
    let message = '';
    for (const arg of args) {
      if (arg instanceof Error) {
        message = arg.message;
        stack = arg.stack || '';
        break;
      }
      if (typeof arg === 'string' && !message) message = arg;
    }
    if (message) reportError(message, stack);
    if (_origConsoleError) _origConsoleError.apply(console, args);
  };
} catch (e) {}

// ─── Heartbeat ─────────────────────────────────────────────────────
setInterval(() => {
  if (systemSocket?.connected) {
    systemSocket.emit('heartbeat', { url: window.location.href, timestamp: Date.now() });
  }
}, 5000);
