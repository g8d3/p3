#!/usr/bin/env node
/**
 * Run Direct — Ejecuta OpenCode directamente, captura output, streamea, graba
 *
 * Alternativa a sandbox-agent. Más simple, funciona directo.
 * No da eventos estructurados (tool_calls), pero captura todo el texto.
 * Para eventos estructurados, sandbox-agent es mejor — cuando funcione.
 */

import { spawn } from 'node:child_process';
import { WebSocket } from 'ws';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const DATA_DIR = path.join(__dirname, '..', 'data');
const AGENT_ID = `oc-${Date.now()}`;
const AGENT_NAME = process.env.AGENT_NAME || '🧑‍💻 Developer Agent';
const MODEL = process.env.OC_MODEL || 'opencode-go/deepseek-v4-flash';
const STAGE_URL = process.env.STAGE_URL || 'http://localhost:3099';
const CWD = '/home/vuos/code/p3/s68-agent-studio';

// ─── State ───────────────────────────────────────────────────────────
let ws = null;
let traceStream = null;
let eventCount = 0;
let ocProcess = null;
const tracePath = path.join(DATA_DIR, `${AGENT_ID}.jsonl`);

// ─── Helpers ─────────────────────────────────────────────────────────
function connectStage() {
  return new Promise((resolve) => {
    const wsUrl = STAGE_URL.replace(/^http/, 'ws');
    ws = new WebSocket(wsUrl);
    ws.on('open', () => { console.log('[Run] Conectado al Stage'); resolve(); });
    ws.on('error', () => {});
    setTimeout(resolve, 3000);
  });
}

function sendToStage(type, data) {
  if (ws?.readyState === WebSocket.OPEN) {
    ws.send(JSON.stringify({ type, ...data }));
  }
}

function pushEvent(stageType, data) {
  eventCount++;
  sendToStage('agent:event', {
    agentId: AGENT_ID,
    event: { ts: Date.now(), type: stageType, data },
  });
  sendToStage('agent:status', {
    agentId: AGENT_ID, status: 'working',
    meta: { name: AGENT_NAME, type: 'opencode', model: MODEL, eventCount },
  });
  if (traceStream) {
    traceStream.write(JSON.stringify({ ts: new Date().toISOString(), seq: eventCount, type: stageType, data }) + '\n');
  }
}

function updateStatus(status, meta = {}) {
  sendToStage('agent:status', { agentId: AGENT_ID, status, meta: { name: AGENT_NAME, type: 'opencode', model: MODEL, ...meta } });
}

// Lee un archivo y devuelve mensajes de texto chunked (cada chunk <= maxChars)
function chunkTask(text, maxChars = 1500) {
  const chunks = [];
  for (let i = 0; i < text.length; i += maxChars) {
    chunks.push({ type: 'text', text: text.slice(i, i + maxChars) });
  }
  return chunks;
}

// ─── Main ────────────────────────────────────────────────────────────
async function main() {
  fs.mkdirSync(DATA_DIR, { recursive: true });
  traceStream = fs.createWriteStream(tracePath, { flags: 'a' });

  console.log(`
╔══════════════════════════════════════════════╗
║   🧑‍💻 Agent Studio — Developer Direct        ║
║                                              ║
║   Agente:  ${AGENT_NAME.padEnd(36)}║
║   Motor:   OpenCode CLI directo              ║
║   Modelo:  ${MODEL.padEnd(36)}║
║   PID:     process.pid                       ║
║                                              ║
║   📡 ${STAGE_URL}               ║
║   💾 ${tracePath}║
╚══════════════════════════════════════════════╝
  `);

  await connectStage();
  updateStatus('starting');
  pushEvent('session_start', { agentName: AGENT_NAME, model: MODEL });

  // Leer la task
  const taskFile = path.join(__dirname, 'developer-task.md');
  const fullTask = fs.readFileSync(taskFile, 'utf-8');

  // Primera tarea: explorar y construir
  const firstTask = `Eres un Developer Agent. Trabajas en ${CWD}.

INSTRUCCIONES:
1. Lee el archivo developer-task.md para entender tu misión
2. Lee la estructura del proyecto: stage/server.js, tape/recorder.js, amp/orquestador.js
3. Construye el dashboard React
4. Construye tape/player.js

IMPORTANTE:
- Puedes usar terminal, leer/escribir archivos
- Todo lo que haces es grabado
- Humanos pueden darte feedback

Empieza explorando el proyecto.`;

  console.log('[Run] Lanzando OpenCode...');
  updateStatus('working', { phase: 'starting-opencode' });

  // Spawn OpenCode
  ocProcess = spawn('opencode', ['run', firstTask, '--model', MODEL], {
    cwd: CWD,
    env: {
      ...process.env,
      OPENCODE_GO_API_KEY: process.env.OPENCODE_GO_API_KEY || '',
    },
    stdio: ['pipe', 'pipe', 'pipe'],
  });

  pushEvent('process_start', { model: MODEL, task: firstTask.slice(0, 200) });

  // Capturar stdout
  ocProcess.stdout.on('data', (data) => {
    const text = data.toString();
    pushEvent('agent_message', { content: { text: text.trim() } });
  });

  // Capturar stderr (progreso, pensamientos)
  ocProcess.stderr.on('data', (data) => {
    const text = data.toString().trim();
    if (!text) return;
    // Clasificar: si parece progreso o pensamiento
    if (text.includes('·') || text.includes('>') || text.includes('•') || text.startsWith('  ')) {
      pushEvent('agent_thought', { content: { text: text.slice(0, 500) } });
    } else {
      pushEvent('log', { text: text.slice(0, 500) });
    }
  });

  ocProcess.on('exit', (code, signal) => {
    console.log(`[Run] OpenCode terminó (code=${code}, signal=${signal})`);
    pushEvent('process_exit', { code, signal });
    updateStatus(code === 0 ? 'completed' : 'error', { exitCode: code });

    if (code === 0) {
      // Agente completó su tarea. Podríamos enviarle más tareas...
      console.log('[Run] Tarea completada. Enviando siguiente tarea...');
      setTimeout(() => runNextTask(), 2000);
    } else {
      console.log('[Run] Error. Cerrando sesión.');
      closeSession();
    }
  });

  ocProcess.on('error', (err) => {
    console.error(`[Run] Error: ${err.message}`);
    pushEvent('error', { message: err.message });
    updateStatus('error', { error: err.message });
  });
}

function runNextTask() {
  const nextTask = `Buen trabajo. Ahora construye el cliente React dashboard.

Pasos:
1. Crea client/ con Vite + React
2. Crea una página que se conecte al WebSocket del stage
3. Muestra eventos en tiempo real
4. Panel de feedback

Trabajas en ${CWD}.`;

  console.log('[Run] Siguiente tarea...');
  updateStatus('working', { phase: 'building-dashboard' });
  pushEvent('task_sent', { task: nextTask.slice(0, 200) });

  ocProcess = spawn('opencode', ['run', nextTask, '--model', MODEL], {
    cwd: CWD,
    env: {
      ...process.env,
      OPENCODE_GO_API_KEY: process.env.OPENCODE_GO_API_KEY || '',
    },
    stdio: ['pipe', 'pipe', 'pipe'],
  });

  ocProcess.stdout.on('data', (data) => {
    pushEvent('agent_message', { content: { text: data.toString().trim() } });
  });

  ocProcess.stderr.on('data', (data) => {
    const text = data.toString().trim();
    if (text) pushEvent('log', { text: text.slice(0, 500) });
  });

  ocProcess.on('exit', (code) => {
    pushEvent('process_exit', { code });
    if (code === 0) {
      console.log('[Run] Dashboard construido. Cerrando.');
    }
    closeSession();
  });
}

function closeSession() {
  const stats = {
    events: eventCount,
    traceSize: fs.existsSync(tracePath) ? fs.statSync(tracePath).size : 0,
  };
  stats.traceSizeFormatted = stats.traceSize < 1024 ? `${stats.traceSize}B` :
    stats.traceSize < 1024 * 1024 ? `${(stats.traceSize/1024).toFixed(1)}KB` :
    `${(stats.traceSize/(1024*1024)).toFixed(1)}MB`;

  pushEvent('session_end', stats);
  updateStatus('completed', stats);
  
  if (traceStream) traceStream.end();
  
  console.log(`[Run] 📊 ${stats.events} eventos, ${stats.traceSizeFormatted}`);
  console.log(`[Run] 📁 Trace: ${tracePath}`);
  
  setTimeout(() => process.exit(0), 1000);
}

process.on('SIGINT', () => {
  console.log('\n[Run] Cerrando...');
  if (ocProcess && !ocProcess.killed) ocProcess.kill('SIGTERM');
  closeSession();
});

main().catch(err => {
  console.error('[Run] Error:', err.message);
  updateStatus('error', { error: err.message });
  if (traceStream) traceStream.end();
  process.exit(1);
});
