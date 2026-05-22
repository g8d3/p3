import express from 'express';
import { createServer } from 'http';
import { spawn } from 'child_process';
import fs from 'fs';
import { WebSocketServer } from 'ws';
import path from 'path';
import { fileURLToPath } from 'url';
import { AgentManager } from './agent-manager.js';
import { RoomManager } from './room-manager.js';
import { logError, getErrors, updateError, setupGlobalHandlers } from './error-logger.js';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const isProduction = process.env.NODE_ENV === 'production';

const app = express();
const httpServer = createServer(app);
const wss = new WebSocketServer({ server: httpServer });

app.use(express.json({ limit: '10mb' }));

const roomManager = new RoomManager(wss);
const agentManager = new AgentManager(roomManager);

setupGlobalHandlers();

// Handle agent crashes
const origSpawn = agentManager.spawnAgent.bind(agentManager);
agentManager.spawnAgent = async (type, name) => {
  const result = await origSpawn(type, name);
  const child = agentManager.agentProcesses.get(result.id);
  if (child) {
    child.on('exit', (code, signal) => {
      if (code !== 0 && signal !== 'SIGTERM' && signal !== 'SIGKILL') {
        logError('agent_crash', `Agent ${result.name} crashed (code=${code}, signal=${signal})`, '', {
          severity: 'error', source: 'agent', channelId: result.id,
        });
      }
    });
  }
  return result;
};

// ─── Push helper ──────────────────────────────────────────────────
function pushError(type, message, stack, context = {}) {
  const entry = logError(type, message, stack, context);
  roomManager.broadcastTo('errors:subscribers', { type: 'errors:update', data: { type: 'new', error: entry } });
  return entry;
}

// ─── In-memory stores ─────────────────────────────────────────────
const bugReports = [];
const taskQueue = [];

// ─── WebSocket handler ─────────────────────────────────────────────
const clientHeartbeats = new Map(); // ws._heartbeatId → { lastBeat, url, channel }

wss.on('connection', (ws, req) => {
  const clientIp = req.socket.remoteAddress;
  console.log(`[WS] Client connected from ${clientIp}`);

  ws._heartbeatId = Date.now() + '-' + Math.random().toString(36).slice(2, 6);
  clientHeartbeats.set(ws._heartbeatId, { lastBeat: Date.now(), url: '/' });

  ws.on('message', (raw) => {
    let msg;
    try { msg = JSON.parse(raw.toString()); }
    catch { return; }

    const info = clientHeartbeats.get(ws._heartbeatId);
    if (info) info.lastBeat = Date.now();

    switch (msg.type) {

      case 'join:channel':
        roomManager.join(ws, `channel:${msg.channelId}`);
        if (info) info.channel = msg.channelId;
        break;

      case 'leave:channel':
        roomManager.leave(ws, `channel:${msg.channelId}`);
        break;

      case 'chat:message': {
        if (!msg.channelId || !msg.text) return;
        const isCommand = msg.text.startsWith('!');
        const chatMsg = {
          type: 'chat:message',
          id: `${Date.now()}-${Math.random().toString(36).slice(2, 8)}`,
          channelId: msg.channelId,
          sender: ws._heartbeatId?.slice(-8) || 'anon',
          text: msg.text,
          timestamp: Date.now(),
          isCommand,
        };
        roomManager.broadcast(`channel:${msg.channelId}`, chatMsg);
        if (isCommand) agentManager.sendCommand(msg.channelId, msg.text, chatMsg.sender);
        else agentManager.sendMessage(msg.channelId, chatMsg);
        break;
      }

      case 'heartbeat':
        // Already updated above
        break;

      case 'client:errors':
        if (Array.isArray(msg.errors)) {
          for (const err of msg.errors) {
            if (!err?.message) continue;
            const entry = logError('client_error', err.message, err.stack, { source: 'client', url: err.url });
            roomManager.broadcastTo('errors:subscribers', { type: 'errors:update', data: { type: 'new', error: entry } });
          }
          console.log(`[WS] ${msg.errors.length} client error(s) reported`);
        }
        break;

      case 'client:error': {
        // Legacy single error
        if (!msg.message) return;
        const entry = logError('client_error', msg.message, msg.stack, { source: 'client', url: msg.url });
        roomManager.broadcastTo('errors:subscribers', { type: 'errors:update', data: { type: 'new', error: entry } });
        break;
      }

      case 'errors:subscribe':
        roomManager.join(ws, 'errors:subscribers');
        ws.send(JSON.stringify({ type: 'errors:state', errors: getErrors() }));
        ws.send(JSON.stringify({ type: 'tasks:state', tasks: taskQueue }));
        break;

      case 'errors:unsubscribe':
        roomManager.leave(ws, 'errors:subscribers');
        break;
    }
  });

  ws.on('close', (code, reason) => {
    const info = clientHeartbeats.get(ws._heartbeatId);
    const elapsed = info ? Date.now() - info.lastBeat : 0;
    if (info && elapsed > 8000) {
      const entry = logError('client_crash',
        `Client crashed/frozen (${Math.round(elapsed/1000)}s since last heartbeat)`,
        '', { source: 'client', url: info.url, channelId: info.channel });
      roomManager.broadcastTo('errors:subscribers', { type: 'errors:update', data: { type: 'new', error: entry } });
    }
    clientHeartbeats.delete(ws._heartbeatId);
    console.log(`[WS] Client disconnected (${elapsed}ms)`);
  });
});

// ─── Heartbeat check ──────────────────────────────────────────────
setInterval(() => {
  const now = Date.now();
  for (const [id, info] of clientHeartbeats) {
    if (now - info.lastBeat > 15000) {
      const entry = logError('client_crash',
        `Client timed out (${Math.round((now - info.lastBeat)/1000)}s without heartbeat)`,
        '', { source: 'client', url: info.url, channelId: info.channel });
      roomManager.broadcastTo('errors:subscribers', { type: 'errors:update', data: { type: 'new', error: entry } });
      clientHeartbeats.delete(id);
    }
  }
}, 10000);

// ─── API routes ────────────────────────────────────────────────────
// Helper: log+push errors
function apiLogError(type, message, stack, context) {
  const entry = logError(type, message, stack, context);
  roomManager.broadcastTo('errors:subscribers', { type: 'errors:update', data: { type: 'new', error: entry } });
  return entry;
}

app.get('/api/channels', (_req, res) => {
  try { res.json(agentManager.getChannels()); }
  catch (e) { apiLogError('api_error', e.message, e.stack); res.status(500).json({ error: e.message }); }
});

app.get('/api/agents/types', (_req, res) => res.json(agentManager.getAgentTypes()));

app.get('/api/agents/:id', (req, res) => {
  const ch = agentManager.streamRelay.channels.get(req.params.id);
  if (!ch) return res.status(404).json({ error: 'not found' });
  res.json({ id: ch.id, name: ch.name, agentType: ch.agentType, status: ch.status, startedAt: ch.startedAt, frameCount: ch.frameCount });
});

app.post('/api/agents/spawn', async (req, res) => {
  const type = req.query.type || 'web-surfer';
  const name = req.query.name || null;
  try {
    const info = await agentManager.spawnAgent(type, name);
    res.json(info);
  } catch (err) {
    apiLogError('spawn_error', err.message, err.stack, { agentType: type });
    res.status(500).json({ error: err.message });
  }
});

app.post('/api/agents/:id/stop', (req, res) => {
  agentManager.stopAgent(req.params.id);
  res.json({ ok: true });
});

app.post('/api/agents/:id/command', (req, res) => {
  const { command } = req.body || {};
  if (!command) return res.status(400).json({ error: 'no command' });
  agentManager.sendCommand(req.params.id, command, 'api');
  res.json({ ok: true });
});

// ─── Improvements API ─────────────────────────────────────────────
app.get('/api/improvements', (_req, res) => {
  try {
    const md = fs.readFileSync(path.join(__dirname, 'IMPROVEMENTS.md'), 'utf-8');
    const sections = [];
    let current = null;
    for (const line of md.split('\n')) {
      const m = line.match(/^## (\d+)\. (.+)$/);
      if (m) {
        if (current) sections.push(current);
        current = { id: parseInt(m[1]), title: m[2], status: 'idea', lines: [] };
      } else if (current) {
        current.lines.push(line);
        if (line.startsWith('**Estado:**')) {
          current.status = line.replace('**Estado:**', '').trim();
        }
      }
    }
    if (current) sections.push(current);
    res.json({ sections, total: sections.length });
  } catch (e) {
    res.status(500).json({ error: e.message });
  }
});
app.get('/api/errors', (_req, res) => {
  try { res.json(getErrors()); }
  catch (e) { res.json([]); }
});

app.post('/api/errors/:id/ignore', (req, res) => {
  const error = updateError(req.params.id, { status: 'ignored' });
  res.json(error || { error: 'not found' });
});

app.post('/api/errors/:id/fix', async (req, res) => {
  const errors = getErrors();
  const error = errors.find(e => e.id === req.params.id);
  if (!error) return res.status(404).json({ error: 'not found' });

  updateError(req.params.id, { status: 'fix_ready' });

  const task = {
    id: `task-${Date.now()}-${Math.random().toString(36).slice(2, 6)}`,
    errorId: error.id,
    type: 'auto-fix',
    status: 'queued',
    createdAt: Date.now(),
    error,
  };
  taskQueue.push(task);

  roomManager.broadcastTo('errors:subscribers', { type: 'task:new', task });
  console.log(`[TaskQueue] Fix task created for error ${error.id}`);

  // Auto-spawn Fix Agent
  const fixAgentPath = path.join(__dirname, 'agents', 'fix-agent.js');
  const fixChild = spawn('node', [fixAgentPath, error.id], {
    stdio: ['pipe', 'pipe', 'pipe'],
    env: { ...process.env, OPENCODE_GO_API_KEY: process.env.OPENCODE_GO_API_KEY || '' },
    cwd: __dirname,
  });
  let fixLog = '';
  fixChild.stdout.on('data', d => fixLog += d.toString());
  fixChild.stderr.on('data', d => fixLog += d.toString());
  fixChild.on('exit', (code) => {
    task.status = code === 0 ? 'completed' : 'failed';
    task.completedAt = Date.now();
    task.output = fixLog.slice(0, 2000);
    roomManager.broadcastTo('errors:subscribers', { type: 'task:update', task });
    console.log(`[TaskQueue] Fix task ${task.id} completed (code=${code})`);
  });

  res.json({ task, error: { ...error, status: 'fix_ready' } });
});

app.get('/api/tasks', (_req, res) => res.json(taskQueue));
app.post('/api/tasks/:id/cancel', (req, res) => {
  const task = taskQueue.find(t => t.id === req.params.id);
  if (task) task.status = 'cancelled';
  res.json({ ok: true });
});

// ─── Bug reporting API ─────────────────────────────────────────────
app.get('/api/bugs', (_req, res) => res.json(bugReports));
app.post('/api/bugs', (req, res) => {
  const { title, description, severity, reporter, channelId } = req.body || {};
  const bug = {
    id: `bug-${Date.now()}-${Math.random().toString(36).slice(2, 6)}`,
    title: title || 'Untitled bug',
    description: description || '',
    severity: severity || 'info',
    reporter: reporter || 'unknown',
    channelId: channelId || null,
    timestamp: Date.now(),
    status: 'open',
  };
  bugReports.push(bug);
  roomManager.broadcastAll({ type: 'bug:new', bug });
  res.json(bug);
});
app.post('/api/bugs/:id/resolve', (req, res) => {
  const bug = bugReports.find(b => b.id === req.params.id);
  if (bug) bug.status = 'resolved';
  res.json({ ok: true });
});

// ─── Accept client error reports (via sendBeacon / fetch) ──────────
app.post('/api/errors/client-batch', (req, res) => {
  try {
    const data = Array.isArray(req.body) ? req.body : [];
    for (const item of data) {
      if (!item?.message) continue;
      const entry = logError('client_error', item.message, item.stack, {
        source: 'client', url: item.url, userAgent: item.userAgent,
      });
      roomManager.broadcastTo('errors:subscribers', { type: 'errors:update', data: { type: 'new', error: entry } });
    }
  } catch {}
  res.json({ ok: true });
});

app.post('/api/errors/client', (req, res) => {
  try {
    const data = req.body || {};
    const entry = logError('client_error', data.message, data.stack, {
      source: 'client', url: data.url, userAgent: data.userAgent,
    });
    roomManager.broadcastTo('errors:subscribers', { type: 'errors:update', data: { type: 'new', error: entry } });
  } catch {}
  res.json({ ok: true });
});

// ─── Static files ─────────────────────────────────────────────────
app.get('/IMPROVEMENTS.md', (_req, res) => res.sendFile(path.join(__dirname, 'IMPROVEMENTS.md')));
app.get('/terminal.html', (_req, res) => res.sendFile(path.join(__dirname, 'terminal.html')));

if (isProduction) {
  app.use(express.static(path.join(__dirname, 'dist')));
  app.get('*', (_req, res) => res.sendFile(path.join(__dirname, 'dist', 'index.html')));
}

// ─── Error middleware ──────────────────────────────────────────────
app.use((err, req, res, _next) => {
  apiLogError('http_error', err.message, err.stack, { url: req?.originalUrl, method: req?.method });
  res?.status(500).json({ error: err.message });
});

// ─── Start ─────────────────────────────────────────────────────────
const PORT = process.env.PORT || 3001;
const HOST = '0.0.0.0';

httpServer.listen(PORT, HOST, async () => {
  console.log(`
╔══════════════════════════════════════════════╗
║   🎬 Agent Twitch — Live AI Streams         ║
║   🔌 Native WebSocket (no Socket.IO)        ║
║   📋 Error Logging & Auto-Fix System Active ║
║──────────────────────────────────────────────║
║  Server:  http://0.0.0.0:${PORT}
║  Errors:  http://<tu-ip>:${PORT}/errors
╚══════════════════════════════════════════════╝
  `);

  pushError('info', 'Server started', '', { severity: 'info', type: 'startup' });

  setTimeout(async () => {
    try {
      await agentManager.spawnAgent('web-surfer', '🤖 Web Surfer');
    } catch (e) {
      pushError('startup_error', `Failed to start web-surfer: ${e.message}`, e.stack);
    }
  }, 500);
});
