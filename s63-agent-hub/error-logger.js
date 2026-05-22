// Error Logger — captura todos los errores y los persiste en errors.jsonl
import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const ERROR_LOG = path.join(__dirname, 'errors.jsonl');

// Ensure file exists
if (!fs.existsSync(ERROR_LOG)) {
  fs.writeFileSync(ERROR_LOG, '');
}

// ─── Write error entry ────────────────────────────────────────────
export function logError(type, message, stack, context = {}) {
  const entry = {
    id: `err-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`,
    timestamp: Date.now(),
    type,
    message: message?.slice(0, 500) || 'Unknown error',
    stack: stack?.slice(0, 3000) || '',
    context,
    severity: context.severity || 'error',
    status: 'open',
    source: context.source || 'server',
    fixAttempts: [],
    channelId: context.channelId || null,
  };
  try {
    fs.appendFileSync(ERROR_LOG, JSON.stringify(entry) + '\n');
  } catch (e) {
    console.error('[ErrorLogger] Failed to write error:', e.message);
  }
  return entry;
}

// ─── Read all errors ──────────────────────────────────────────────
export function getErrors() {
  try {
    const content = fs.readFileSync(ERROR_LOG, 'utf-8');
    return content.split('\n').filter(Boolean).map(line => JSON.parse(line));
  } catch {
    return [];
  }
}

// ─── Update error status ──────────────────────────────────────────
export function updateError(id, updates) {
  const errors = getErrors();
  const idx = errors.findIndex(e => e.id === id);
  if (idx === -1) return null;
  errors[idx] = { ...errors[idx], ...updates, lastModified: Date.now() };
  fs.writeFileSync(ERROR_LOG, errors.map(e => JSON.stringify(e)).join('\n') + '\n');
  return errors[idx];
}

// ─── Add fix attempt record ───────────────────────────────────────
export function addFixAttempt(errorId, attempt) {
  const error = updateError(errorId, {
    fixAttempts: [
      ...(getErrors().find(e => e.id === errorId)?.fixAttempts || []),
      { ...attempt, timestamp: Date.now() },
    ],
  });
  return error;
}

// ─── Express error middleware ──────────────────────────────────────
export function errorMiddleware(err, req, res, _next) {
  const entry = logError('http_error', err.message, err.stack, {
    severity: 'error',
    source: 'http',
    url: req?.originalUrl,
    method: req?.method,
  });
  console.error(`[ErrorLogger] ${entry.id}: ${err.message}`);
  res?.status(500).json({ error: err.message, errorId: entry.id });
}

// ─── Process/window error handlers ─────────────────────────────────
export function setupGlobalHandlers() {
  process.on('uncaughtException', (err) => {
    logError('uncaught_exception', err.message, err.stack, { severity: 'critical' });
    console.error(`[ErrorLogger] UNCAUGHT: ${err.message}`);
  });

  process.on('unhandledRejection', (reason) => {
    logError('unhandled_rejection', reason?.message || String(reason), reason?.stack, { severity: 'critical' });
    console.error(`[ErrorLogger] UNHANDLED REJECTION: ${reason}`);
  });

  // Agent crash handler (called from agent-manager)
  return { logAgentError, logAgentCrash };
}

// ─── Agent-specific errors ─────────────────────────────────────────
export function logAgentCrash(agentId, agentName, exitCode, signal) {
  return logError('agent_crash', `Agent ${agentName} crashed (code=${exitCode}, signal=${signal})`, '', {
    severity: 'error',
    source: 'agent',
    channelId: agentId,
    exitCode,
    signal,
    agentName,
  });
}

export function logAgentError(agentId, agentName, message, stack) {
  return logError('agent_error', `[${agentName}] ${message}`, stack, {
    severity: 'warning',
    source: 'agent',
    channelId: agentId,
    agentName,
  });
}
