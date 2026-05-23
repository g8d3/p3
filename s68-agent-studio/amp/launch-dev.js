#!/usr/bin/env node
/**
 * Launch Dev Agent — Punto de entrada simple y directo
 *
 * 1. Conecta al Stage (streaming dashboard)
 * 2. Spawnea sandbox-agent + OpenCode
 * 3. Envía la tarea al Developer Agent
 * 4. Graba TODO (eventos estructurados, no video)
 * 5. Transmite en vivo al dashboard
 */

import { SandboxAgent } from 'sandbox-agent';
import { local } from 'sandbox-agent/local';
import { TraceRecorder } from '../tape/recorder.js';
import { WebSocket } from 'ws';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const DATA_DIR = path.join(__dirname, '..', 'data');
const AGENT_ID = `dev-${Date.now()}`;
const AGENT_NAME = process.env.AGENT_NAME || '🧑‍💻 Developer Agent';
const AGENT_MODEL = process.env.AGENT_MODEL || 'opencode/deepseek-v4-flash';
const STAGE_URL = process.env.STAGE_URL || 'http://localhost:3099';

// ─── Helpers ─────────────────────────────────────────────────────────
const wsUrl = STAGE_URL.replace(/^http/, 'ws');
let ws = null;
let traceStream = null;
let eventCount = 0;
const tracePath = path.join(DATA_DIR, `${AGENT_ID}.jsonl`);

function connectStage() {
  return new Promise((resolve) => {
    ws = new WebSocket(wsUrl);
    ws.on('open', () => { console.log('[Launch] Conectado al Stage'); resolve(); });
    ws.on('error', () => {});
    ws.on('close', () => {});
    // Timeout si el stage no está listo
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
  // Al Stage
  sendToStage('agent:event', {
    agentId: AGENT_ID,
    event: { ts: Date.now(), type: stageType, data },
  });
  sendToStage('agent:status', {
    agentId: AGENT_ID,
    status: 'working',
    meta: { name: AGENT_NAME, type: 'opencode', model: AGENT_MODEL, eventCount },
  });
  // Al trace
  if (traceStream) {
    traceStream.write(JSON.stringify({ ts: new Date().toISOString(), seq: eventCount, type: stageType, data }) + '\n');
  }
}

function updateStatus(status, meta = {}) {
  sendToStage('agent:status', { agentId: AGENT_ID, status, meta: { name: AGENT_NAME, type: 'opencode', model: AGENT_MODEL, ...meta } });
}

// ─── Main ────────────────────────────────────────────────────────────
async function main() {
  fs.mkdirSync(DATA_DIR, { recursive: true });
  traceStream = fs.createWriteStream(tracePath, { flags: 'a' });

  console.log(`
╔══════════════════════════════════════════════╗
║   🚀 Agent Studio — Lanzando Developer       ║
║                                              ║
║   Agente:  ${AGENT_NAME.padEnd(36)}║
║   Motor:   sandbox-agent + OpenCode          ║
║   Modelo:  ${AGENT_MODEL.padEnd(36)}║
║                                              ║
║   📡 Transmitiendo en: ${STAGE_URL}║
║   💾 Grabando en:      ${tracePath}║
╚══════════════════════════════════════════════╝
  `);

  // 1. Conectar al Stage
  await connectStage();
  updateStatus('starting');

  // 2. Escribir primer evento
  traceStream.write(JSON.stringify({ ts: new Date().toISOString(), seq: eventCount++, type: 'session_start', data: { agentId: AGENT_ID, agentName: AGENT_NAME, model: AGENT_MODEL } }) + '\n');
  pushEvent('session_start', { agentName: AGENT_NAME, model: AGENT_MODEL });

  // 3. Iniciar sandbox-agent local
  console.log('[Launch] Iniciando sandbox-agent...');
  updateStatus('starting', { phase: 'sandbox' });

  // Las API keys se pasan al sandbox-agent para que OpenCode las tenga
  const sdk = await SandboxAgent.start({
    sandbox: local(),
    spawn: {
      env: {
        // OpenCode necesita alguna de estas para arrancar
        ANTHROPIC_API_KEY: process.env.ANTHROPIC_API_KEY || '',
        OPENAI_API_KEY: process.env.OPENAI_API_KEY || '',
        // Pasamos también las keys propias de OpenCode
        OPENCODE_GO_API_KEY: process.env.OPENCODE_GO_API_KEY || '',
      },
    },
  });
  console.log(`[Launch] sandbox-agent listo: ${sdk.sandboxId}`);
  pushEvent('sandbox_ready', { sandboxId: sdk.sandboxId });

  // 4. Crear sesión OpenCode
  console.log('[Launch] Creando sesión OpenCode...');
  updateStatus('starting', { phase: 'session' });

  const session = await sdk.createSession({
    agent: 'opencode',
    cwd: '/home/vuos/code/p3/s68-agent-studio',
  });
  console.log(`[Launch] Sesión: ${session.id}`);
  pushEvent('session_ready', { sessionId: session.id });

  // Si el modelo está disponible, configurarlo
  try {
    await session.setModel(AGENT_MODEL);
    console.log(`[Launch] Modelo configurado: ${AGENT_MODEL}`);
  } catch (e) {
    console.log(`[Launch] No se pudo configurar modelo: ${e.message}`);
  }

  // 5. Conectar recorder a eventos
  console.log('[Launch] Conectando recorder a eventos...');
  const unsubscribeRecorder = connectRecorder(session, sdk);

  // 6. Enviar la tarea al agente
  const taskFile = path.join(__dirname, 'developer-task.md');
  const task = fs.readFileSync(taskFile, 'utf-8');

  // Task resumida para el primer prompt
  const firstPrompt = `Eres el Developer Agent. Tu misión está en el archivo developer-task.md.

PRIMEROS PASOS:
1. Lee developer-task.md
2. Lee la estructura del proyecto (stage/server.js, tape/recorder.js, amp/orquestador.js)
3. Construye el cliente React dashboard en client/
4. Construye tape/player.js para reproducir grabaciones

Trabajas en /home/vuos/code/p3/s68-agent-studio.
Todo lo que haces es grabado y transmitido en vivo.
`;

  console.log('[Launch] Enviando tarea al Developer Agent...');
  console.log('─'.repeat(60));
  console.log(firstPrompt.slice(0, 500) + '...');
  console.log('─'.repeat(60));

  updateStatus('working', { phase: 'building' });
  pushEvent('task_sent', { task: firstPrompt.slice(0, 300) });

  const result = await session.prompt([
    { type: 'text', text: firstPrompt },
  ]);

  console.log(`[Launch] Respuesta: stopReason=${result.stopReason}`);
  pushEvent('task_response', { stopReason: result.stopReason });

  // 7. El agente puede seguir trabajando en más prompts
  // Por ahora, esperamos y mantenemos la sesión abierta
  console.log('[Launch] Developer Agent trabajando. Grabando y transmitiendo...');
  console.log('[Launch] Presiona Ctrl+C para detener');

  // Mantener abierto hasta Ctrl+C
  await new Promise(() => {
    process.on('SIGINT', async () => {
      console.log('\n[Launch] Cerrando...');
      unsubscribeRecorder();
      const stats = closeSession();
      await sdk.destroySandbox();
      console.log(`[Launch] 📊 ${stats.events} eventos, ${stats.traceSizeFormatted}`);
      process.exit(0);
    });
  });
}

// ─── Event Recorder ──────────────────────────────────────────────────
function connectRecorder(session, sdk) {
  // Conectar a eventos de la sesión
  const unsubscribe = session.onEvent((event) => {
    const payload = event.payload;
    const update = payload?.sessionUpdate;

    if (!update) return;

    // Normalizar y enviar
    let stageType = update;
    let data = {};

    switch (update) {
      case 'tool_call':
        data = {
          toolCallId: payload.toolCallId,
          title: payload.title,
          status: payload.status,
          rawInput: payload.rawInput,
          toolName: payload.toolName,
        };
        break;
      case 'tool_call_update':
        data = {
          toolCallId: payload.toolCallId,
          status: payload.status,
          content: payload.content?.slice(0, 500),
          error: payload.error,
        };
        break;
      case 'agent_message_chunk':
        data = { content: payload.content };
        break;
      case 'agent_thought_chunk':
        data = { content: payload.content };
        break;
      case 'plan':
        data = { entries: payload.entries };
        break;
      case 'usage_update':
        data = { usage: payload.usage };
        break;
      case 'session_info_update':
        data = { title: payload.title };
        break;
      default:
        data = payload;
    }

    pushEvent(stageType, data);
  });

  return unsubscribe;
}

// ─── Session close ───────────────────────────────────────────────────
function closeSession() {
  pushEvent('session_end', { eventCount });

  if (traceStream) {
    traceStream.end();
    traceStream = null;
  }

  let traceSize = 0;
  try { traceSize = fs.statSync(tracePath).size; } catch {}

  const stats = {
    events: eventCount,
    tracePath,
    traceSize,
    traceSizeFormatted: traceSize < 1024 ? `${traceSize}B` :
      traceSize < 1024 * 1024 ? `${(traceSize/1024).toFixed(1)}KB` :
      `${(traceSize/(1024*1024)).toFixed(1)}MB`,
  };

  updateStatus('completed', stats);
  return stats;
}

main().catch(async (err) => {
  console.error('[Launch] Error:', err.message);
  updateStatus('error', { error: err.message, stack: err.stack });
  if (traceStream) {
    traceStream.write(JSON.stringify({ ts: new Date().toISOString(), type: 'fatal_error', data: { message: err.message, stack: err.stack } }) + '\n');
    traceStream.end();
  }
  process.exit(1);
});
