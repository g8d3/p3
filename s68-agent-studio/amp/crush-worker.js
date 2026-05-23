#!/usr/bin/env node
/**
 * Crush Worker — Wrapper que ejecuta Crush (Go, bajo RAM) y transmite todo
 *
 * Este es el "Developer Agent" real. Corre Crush como child process,
 * captura su output, lo streamea al dashboard, lo graba en JSONL,
 * y escucha feedback para intervenir cuando sea necesario.
 *
 * Ventajas sobre OpenCode:
 * - Crush es Go (~20MB RAM vs ~200MB de Node.js)
 * - Podemos correr 5-10 instancias simultáneas
 * - Usa OPENCODE_GO_API_KEY (la que funciona)
 * - Modelo: deepseek-v4-flash (rápido, barato)
 */

import { spawn } from 'node:child_process';
import { WebSocket } from 'ws';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const DATA_DIR = path.join(__dirname, '..', 'data');
const AGENT_ID = `crush-${Date.now()}-${Math.random().toString(36).slice(2, 6)}`;
const AGENT_NAME = process.env.AGENT_NAME || '🧑‍💻 Developer (Crush)';

// ─── Config ──────────────────────────────────────────────────────────
const STAGE_URL = process.env.STAGE_URL || 'ws://localhost:3099';
const CRUSH_MODEL = process.env.CRUSH_MODEL || 'opencode-go/deepseek-v4-flash';
const CRUSH_TASK = process.env.CRUSH_TASK || '';
const CWD = process.env.CRUSH_CWD || process.env.HOME || '/tmp';

// ─── IPC helpers ─────────────────────────────────────────────────────
let ws = null;
let traceStream = null;
let eventCount = 0;
const tracePath = path.join(DATA_DIR, `${AGENT_ID}.jsonl`);

function connectStage() {
  ws = new WebSocket(STAGE_URL);
  
  ws.on('open', () => {
    console.log(`[Worker] Conectado al Stage como ${AGENT_ID}`);
    sendStatus('starting');
    recordTrace('session_start', { agentName: AGENT_NAME });
  });
  
  ws.on('message', (raw) => {
    try {
      const msg = JSON.parse(raw.toString());
      handleStageMessage(msg);
    } catch {}
  });
  
  ws.on('close', () => {
    console.log('[Worker] Desconectado del Stage, reconectando...');
    setTimeout(connectStage, 3000);
  });
  
  ws.on('error', () => {});
}

function sendToStage(type, data) {
  if (ws?.readyState === WebSocket.OPEN) {
    ws.send(JSON.stringify({ type, ...data }));
  }
}

function sendStatus(status, meta = {}) {
  sendToStage('agent:status', {
    agentId: AGENT_ID,
    status,
    meta: { name: AGENT_NAME, type: 'crush', model: CRUSH_MODEL, ...meta },
  });
}

function pushEvent(eventType, data) {
  eventCount++;
  sendToStage('agent:event', {
    agentId: AGENT_ID,
    event: { ts: Date.now(), type: eventType, data },
  });
  recordTrace(eventType, data);
}

function recordTrace(type, data) {
  if (!traceStream) return;
  const line = JSON.stringify({ ts: new Date().toISOString(), seq: eventCount, type, data }) + '\n';
  traceStream.write(line);
}

function handleStageMessage(msg) {
  switch (msg.type) {
    case 'agent:feedback':
      if (msg.agentId === AGENT_ID) {
        console.log(`[Worker] 💬 Feedback de ${msg.from}: ${msg.text}`);
        // Reenviar feedback a Crush (por stdin)
        sendToCrush(`[FEEDBACK de ${msg.from}]: ${msg.text}`);
      }
      break;
    case 'agent:intervene':
      if (msg.agentId === AGENT_ID && msg.command) {
        console.log(`[Worker] 🔧 Intervención de ${msg.from}: ${msg.command}`);
        sendToCrush(`[INTERVENCIÓN de ${msg.from}]: ${msg.command}${msg.reason ? ' (razón: ' + msg.reason + ')' : ''}`);
      }
      break;
  }
}

// ─── Crush Process ───────────────────────────────────────────────────
let crushProcess = null;
let outputBuffer = '';

function sendToCrush(text) {
  if (crushProcess?.stdin?.writable) {
    crushProcess.stdin.write(text + '\n');
    pushEvent('feedback_sent', { text });
  }
}

function spawnCrush(task) {
  console.log(`[Worker] Spawneando Crush (${CRUSH_MODEL})...`);
  console.log(`[Worker] Task: ${task.slice(0, 200)}...`);
  
  // Preparar el prompt para Crush
  const prompt = buildPrompt(task);
  
  const env = {
    ...process.env,
    OPENCODE_API_KEY: process.env.OPENCODE_GO_API_KEY || process.env.OPENCODE_API_KEY || '',
    ZAI_API_KEY: process.env.ZAI_CODING_PLAN_API_KEY || process.env.ZAI_API_KEY || '',
    // Forzar que Crush no pida confirmación (yolo mode)
    CRUSH_YOLO: 'true',
    CRUSH_AUTO_ACCEPT: 'true',
  };
  
  // --quiet para output mínimo, --model para el modelo
  const crushArgs = [
    'run', prompt,
    '--model', CRUSH_MODEL,
    '--quiet',
  ];
  
  console.log(`[Worker] Ejecutando: crush ${crushArgs.join(' ')}`);
  pushEvent('crush_spawn', { model: CRUSH_MODEL, args: crushArgs });
  
  crushProcess = spawn('crush', crushArgs, {
    env,
    cwd: CWD,
    stdio: ['pipe', 'pipe', 'pipe'],
  });
  
  // Capturar stdout (respuestas de Crush)
  crushProcess.stdout.on('data', (data) => {
    const text = data.toString();
    outputBuffer += text;
    
    // Enviar como evento de mensaje
    pushEvent('agent_message', { content: { text: text.trim() } });
    
    // Si hay líneas completas, también enviar como log
    const lines = text.split('\n').filter(l => l.trim());
    for (const line of lines) {
      pushEvent('log', { text: line.trim() });
    }
  });
  
  // Capturar stderr (logs, errores, pensamientos internos)
  crushProcess.stderr.on('data', (data) => {
    const text = data.toString().trim();
    if (!text) return;
    
    // Clasificar el tipo de mensaje
    if (text.includes('[ERROR]') || text.includes('error:')) {
      pushEvent('error', { message: text });
    } else if (text.includes('[THINK]') || text.includes('thinking')) {
      pushEvent('agent_thought', { content: { text } });
    } else {
      pushEvent('log', { text });
    }
  });
  
  crushProcess.on('exit', (code, signal) => {
    console.log(`[Worker] Crush terminó (code=${code}, signal=${signal})`);
    pushEvent('crush_exit', { code, signal, outputLength: outputBuffer.length });
    sendStatus(code === 0 ? 'completed' : 'error', { exitCode: code });
    
    // Si fue exitoso, cerrar sesión
    if (code === 0) {
      closeSession();
    } else {
      // Si falló, intentar de nuevo con un mensaje de error
      pushEvent('error', { message: `Crush terminó con código ${code}` });
      sendStatus('failed', { exitCode: code });
    }
  });
  
  crushProcess.on('error', (err) => {
    console.error(`[Worker] Error de Crush: ${err.message}`);
    pushEvent('error', { message: err.message });
    sendStatus('error', { error: err.message });
  });
  
  sendStatus('working', { phase: 'crush-running' });
}

function buildPrompt(task) {
  return `Eres un Developer Agent. Tu trabajo es construir software.

${task}

IMPORTANTE:
- Trabajas en: ${CWD}
- Puedes leer, escribir, editar archivos
- Puedes ejecutar comandos en la terminal
- TODO lo que haces está siendo grabado y transmitido en vivo
- Humanos y otros agentes pueden verte y darte feedback
- Si recibes un mensaje [FEEDBACK de ...], es alguien ayudándote
- Si recibes [INTERVENCIÓN de ...], es una instrucción directa

Adelante. Construye algo increíble.
`;
}

// ─── Session lifecycle ───────────────────────────────────────────────
function closeSession() {
  const stats = {
    events: eventCount,
    tracePath,
    traceSize: fs.existsSync(tracePath) ? fs.statSync(tracePath).size : 0,
  };
  
  pushEvent('session_end', stats);
  sendStatus('completed', stats);
  
  if (traceStream) {
    traceStream.end();
    traceStream = null;
  }
  
  console.log(`[Worker] 📊 Sesión completa: ${stats.events} eventos, ${(stats.traceSize / 1024).toFixed(1)}KB`);
  console.log(`[Worker] 📁 Trace: ${tracePath}`);
}

function cleanup() {
  if (crushProcess && !crushProcess.killed) {
    crushProcess.kill('SIGTERM');
    setTimeout(() => {
      if (crushProcess && !crushProcess.killed) crushProcess.kill('SIGKILL');
    }, 5000);
  }
  closeSession();
  if (ws) ws.close();
}

// ─── Main ────────────────────────────────────────────────────────────
function main() {
  fs.mkdirSync(DATA_DIR, { recursive: true });
  traceStream = fs.createWriteStream(tracePath, { flags: 'a' });
  
  console.log(`
╔══════════════════════════════════════════════╗
║   🧑‍💻 Crush Worker — Developer Agent         ║
║                                              ║
║   ID:    ${AGENT_ID.padEnd(36)}║
║   Model: ${CRUSH_MODEL.padEnd(36)}║
║   RAM:   ~20MB (Go binary)                   ║
║                                              ║
║   Transmitiendo en: ws://localhost:3099       ║
║   Grabando en:     ${tracePath}║
╚══════════════════════════════════════════════╝
  `);
  
  recordTrace('session_start', { agentId: AGENT_ID, agentName: AGENT_NAME, model: CRUSH_MODEL });
  
  // Conectar al Stage
  connectStage();
  
  // Esperar conexión y luego spawnear Crush
  const waitForConnection = setInterval(() => {
    if (ws?.readyState === WebSocket.OPEN) {
      clearInterval(waitForConnection);
      
      // Pequeña pausa para que el Stage registre el agente
      setTimeout(() => {
        const task = CRUSH_TASK || fs.readFileSync(
          path.join(__dirname, 'developer-task.md'),
          'utf-8'
        );
        spawnCrush(task);
      }, 1000);
    }
  }, 500);
  
  // Timeout: si no se conecta en 10s, spawnear igual
  setTimeout(() => {
    clearInterval(waitForConnection);
    if (!crushProcess) {
      const task = CRUSH_TASK || 'Dime "HOLA MUNDO, soy Crush worker" y qué modelo usas';
      spawnCrush(task);
    }
  }, 10000);
  
  // Limpiar al salir
  process.on('SIGINT', () => {
    console.log('\n[Worker] Cerrando...');
    cleanup();
    process.exit(0);
  });
  
  process.on('SIGTERM', () => {
    cleanup();
    process.exit(0);
  });
}

main();
