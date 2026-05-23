/**
 * Stage — Streaming Server
 *
 * Recibe eventos de los agentes y los transmite en vivo vía WebSocket.
 * Cualquier humano (o agente) puede conectarse y ver lo que está pasando.
 *
 * Basado en patrones de s63-agent-hub pero más simple y enfocado.
 * - WebSocket nativo (no Socket.IO)
 * - Canales por sesión de agente
 * - Dashboard web en /watch
 */

import express from 'express';
import { createServer } from 'http';
import { WebSocketServer } from 'ws';
import path from 'path';
import { fileURLToPath } from 'url';
import fs from 'fs';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const PORT = process.env.STAGE_PORT || 3099;

const app = express();
const httpServer = createServer(app);
const wss = new WebSocketServer({ server: httpServer });

app.use(express.json({ limit: '10mb' }));
app.use(express.static(path.join(__dirname, 'public')));

// ─── Canales / Rooms ──────────────────────────────────────────────────
const rooms = new Map(); // roomName → Set<WebSocket>

function joinRoom(ws, room) {
  if (!rooms.has(room)) rooms.set(room, new Set());
  rooms.get(room).add(ws);
}

function leaveRoom(ws, room) {
  const set = rooms.get(room);
  if (set) {
    set.delete(ws);
    if (set.size === 0) rooms.delete(room);
  }
}

function broadcast(room, message) {
  const set = rooms.get(room);
  if (!set) return;
  const data = JSON.stringify(message);
  for (const ws of set) {
    if (ws.readyState === WebSocket.OPEN) {
      ws.send(data);
    }
  }
}

function broadcastAll(message) {
  const data = JSON.stringify(message);
  wss.clients.forEach(ws => {
    if (ws.readyState === WebSocket.OPEN) ws.send(data);
  });
}

// ─── Estado global de agentes ─────────────────────────────────────────
const agents = new Map(); // agentId → { name, type, status, events: [...] }

export function updateAgentStatus(agentId, status, meta = {}) {
  const agent = agents.get(agentId) || { id: agentId, name: meta.name || agentId, type: meta.type || 'unknown', status: 'starting', startedAt: Date.now(), events: [] };
  agent.status = status;
  Object.assign(agent, meta);
  agent.updatedAt = Date.now();
  agents.set(agentId, agent);
  
  broadcast(`agent:${agentId}`, { type: 'agent:status', agentId, status, meta });
  broadcastAll({ type: 'agents:update', agents: listAgents() });
}

export function pushAgentEvent(agentId, eventType, data) {
  const agent = agents.get(agentId);
  if (!agent) return;
  
  const event = { ts: Date.now(), type: eventType, data };
  agent.events.push(event);
  // Mantener solo los últimos 1000 eventos en memoria
  if (agent.events.length > 1000) agent.events.splice(0, agent.events.length - 1000);
  
  broadcast(`agent:${agentId}`, { type: 'agent:event', agentId, event });
  
  // También broadcast al canal global de ese tipo de evento
  broadcastAll({ type: `event:${eventType}`, agentId, data });
}

function listAgents() {
  return Array.from(agents.values()).map(a => ({
    id: a.id, name: a.name, type: a.type, status: a.status,
    startedAt: a.startedAt, updatedAt: a.updatedAt,
    eventCount: a.events.length,
  }));
}

export function registerAgent(agentId, name, type) {
  agents.set(agentId, { id: agentId, name, type, status: 'spawning', startedAt: Date.now(), events: [] });
  broadcastAll({ type: 'agents:update', agents: listAgents() });
  return agentId;
}

// ─── WebSocket ────────────────────────────────────────────────────────
wss.on('connection', (ws, req) => {
  const clientIp = req.socket.remoteAddress;
  console.log(`[Stage] Viewer connected: ${clientIp}`);

  // Enviar lista actual de agentes al conectar
  ws.send(JSON.stringify({ type: 'agents:update', agents: listAgents() }));

  ws.on('message', (raw) => {
    let msg;
    try { msg = JSON.parse(raw.toString()); } catch { return; }

    switch (msg.type) {
      case 'watch:agent':
        joinRoom(ws, `agent:${msg.agentId}`);
        // Enviar eventos recientes del agente
        const agent = agents.get(msg.agentId);
        if (agent) {
          ws.send(JSON.stringify({ type: 'agent:history', agentId: msg.agentId, events: agent.events.slice(-200) }));
        }
        break;

      case 'unwatch:agent':
        leaveRoom(ws, `agent:${msg.agentId}`);
        break;

      case 'feedback': {
        // Humano u otro agente envía feedback
        broadcast(`agent:${msg.agentId}`, {
          type: 'agent:feedback',
          agentId: msg.agentId,
          from: msg.from || 'anonymous',
          text: msg.text,
          isAgent: msg.isAgent || false,
          ts: Date.now(),
        });
        break;
      }

      case 'intervene': {
        // Intervención directa — solo si el agente la acepta
        broadcast(`agent:${msg.agentId}`, {
          type: 'agent:intervene',
          agentId: msg.agentId,
          from: msg.from || 'anonymous',
          command: msg.command,
          reason: msg.reason || '',
          ts: Date.now(),
        });
        break;
      }

      case 'agents:list':
        ws.send(JSON.stringify({ type: 'agents:update', agents: listAgents() }));
        break;
    }
  });

  ws.on('close', () => {
    // Limpiar rooms
    for (const [room, set] of rooms) {
      if (set.has(ws)) leaveRoom(ws, room);
    }
  });
});

// ─── API REST ─────────────────────────────────────────────────────────
// Endpoints para que otros agentes (no solo humanos) puedan ver el estado

app.get('/api/agents', (_req, res) => res.json(listAgents()));

app.get('/api/agents/:id', (req, res) => {
  const agent = agents.get(req.params.id);
  if (!agent) return res.status(404).json({ error: 'agent not found' });
  res.json(agent);
});

app.get('/api/agents/:id/events', (req, res) => {
  const agent = agents.get(req.params.id);
  if (!agent) return res.status(404).json({ error: 'agent not found' });
  const limit = parseInt(req.query.limit) || 100;
  res.json(agent.events.slice(-limit));
});

app.post('/api/feedback', (req, res) => {
  const { agentId, from, text, isAgent } = req.body || {};
  if (!agentId || !text) return res.status(400).json({ error: 'agentId and text required' });
  broadcast(`agent:${agentId}`, {
    type: 'agent:feedback', agentId, from: from || 'api', text, isAgent: !!isAgent, ts: Date.now(),
  });
  res.json({ ok: true });
});

app.post('/api/intervene', (req, res) => {
  const { agentId, from, command, reason } = req.body || {};
  if (!agentId || !command) return res.status(400).json({ error: 'agentId and command required' });
  broadcast(`agent:${agentId}`, {
    type: 'agent:intervene', agentId, from: from || 'api', command, reason: reason || '', ts: Date.now(),
  });
  res.json({ ok: true });
});

// ─── Start ────────────────────────────────────────────────────────────
httpServer.listen(PORT, '0.0.0.0', () => {
  console.log(`
╔══════════════════════════════════════════════╗
║   🎬 Agent Studio — Live Agent Streams      ║
║                                              ║
║   Dashboard:  http://0.0.0.0:${PORT}         ║
║   Watch API:  http://0.0.0.0:${PORT}/api     ║
║                                              ║
║   Humanos y agentes pueden ver,              ║
║   dar feedback e intervenir en vivo.         ║
╚══════════════════════════════════════════════╝
  `);
});
