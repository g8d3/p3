#!/usr/bin/env node
/**
 * Orquestador — Spawnea el Developer Agent via sandbox-agent
 *
 * Este es el punto de entrada que lanza al agente desarrollador.
 * Él construirá la aplicación. Nosotros solo observamos, grabamos y transmitimos.
 *
 * El orquestador:
 * 1. Inicia sandbox-agent (local)
 * 2. Crea una sesión de coding agent (Claude Code, Codex u OpenCode)
 * 3. Conecta el Trace Recorder para grabar TODO
 * 4. Conecta el Stage (streaming server) para transmitir en vivo
 * 5. Envía la task al agente
 * 6. Escucha eventos y los reenvía al stage
 * 7. Si el agente se traba, puede spawnear un helper
 */

import { SandboxAgent } from 'sandbox-agent';
import { local } from 'sandbox-agent/local';
import { TraceRecorder } from '../tape/recorder.js';
import { createRequire } from 'module';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const require = createRequire(import.meta.url);

// ─── Config ──────────────────────────────────────────────────────────
const DATA_DIR = path.join(__dirname, '..', 'data');
const AGENT_ID = `dev-${Date.now()}`;
const AGENT_NAME = process.env.AGENT_NAME || '🧑‍💻 Developer Agent';
const AGENT_TYPE = process.env.AGENT_TYPE || 'claude'; // claude | codex | opencode
const AGENT_TASK_FILE = path.join(__dirname, 'developer-task.md');
const STAGE_URL = process.env.STAGE_URL || 'http://localhost:3099';
const SCREENSHOT_INTERVAL = parseInt(process.env.SS_INTERVAL || '10000'); // cada 10s

// ─── Stage Client ───────────────────────────────────────────────────
class StageClient {
  constructor(url) {
    this.url = url;
    this.ws = null;
  }

  connect() {
    const wsUrl = this.url.replace(/^http/, 'ws');
    this.ws = new (require('ws'))(wsUrl);
    
    this.ws.on('open', () => {
      console.log('[Orquestador] Conectado al Stage');
      this.send('agent:register', { agentId: AGENT_ID, name: AGENT_NAME, type: AGENT_TYPE });
    });
    
    this.ws.on('error', (err) => {
      console.log('[Orquestador] Stage error:', err.message);
    });
    
    return new Promise((resolve) => {
      this.ws.on('open', resolve);
      // Timeout después de 5s (el stage puede no estar listo)
      setTimeout(resolve, 5000);
    });
  }

  send(type, data) {
    if (this.ws?.readyState === require('ws').OPEN) {
      this.ws.send(JSON.stringify({ type, ...data }));
    }
  }

  pushEvent(eventType, data) {
    this.send('agent:event', { agentId: AGENT_ID, event: { ts: Date.now(), type: eventType, data } });
  }

  updateStatus(status, meta = {}) {
    this.send('agent:status', { agentId: AGENT_ID, status, meta: { name: AGENT_NAME, type: AGENT_TYPE, ...meta } });
  }
}

// ─── Main ────────────────────────────────────────────────────────────
async function main() {
  console.log(`
╔══════════════════════════════════════════════╗
║   🚀 Agent Studio — Orquestador              ║
║                                              ║
║   Agente: ${AGENT_NAME.padEnd(36)}║
║   Tipo:   ${AGENT_TYPE.padEnd(36)}║
║                                              ║
║   Va a construir la aplicación mientras       ║
║   grabamos y transmitimos todo.              ║
╚══════════════════════════════════════════════╝
  `);

  // 1. Inicializar Trace Recorder
  const recorder = new TraceRecorder(DATA_DIR, {
    sessionId: AGENT_ID,
    compress: true,
    keepScreenshotsEveryMs: SCREENSHOT_INTERVAL,
  });
  console.log(`[Orquestador] Trace → ${recorder.tracePath}`);

  // 2. Conectar al Stage (streaming)
  const stage = new StageClient(STAGE_URL);
  await stage.connect();
  stage.updateStatus('starting');
  stage.pushEvent('session_start', { agentId: AGENT_ID, name: AGENT_NAME });

  // 3. Iniciar sandbox-agent local
  console.log('[Orquestador] Iniciando sandbox-agent...');
  const sdk = await SandboxAgent.start({
    sandbox: local(),
    spawn: {
      env: {
        ANTHROPIC_API_KEY: process.env.ANTHROPIC_API_KEY || '',
        OPENAI_API_KEY: process.env.OPENAI_API_KEY || '',
      },
    },
  });
  console.log(`[Orquestador] sandbox-agent listo → ${sdk.sandboxId}`);

  // 4. Crear sesión del agente
  console.log(`[Orquestador] Creando sesión ${AGENT_TYPE}...`);
  const task = fs.readFileSync(AGENT_TASK_FILE, 'utf-8');
  
  const session = await sdk.createSession({
    agent: AGENT_TYPE,
    cwd: '/workspace',
    sessionInit: {
      cwd: '/workspace',
    },
  });
  
  console.log(`[Orquestador] Sesión creada: ${session.id}`);
  stage.updateStatus('working', { sessionId: session.id });

  // 5. Conectar recorder a los eventos de la sesión
  const unsubscribeRecorder = recorder.connectToSession(session);

  // 6. Escuchar eventos y reenviar al stage
  const unsubscribeStage = session.onEvent((event) => {
    const { sender, payload } = event;
    const update = payload?.sessionUpdate;
    
    if (!update) return;
    
    // Reenviar al stage
    switch (update) {
      case 'tool_call':
        stage.pushEvent('tool_call', {
          toolCallId: payload.toolCallId,
          title: payload.title,
          status: payload.status,
          rawInput: payload.rawInput,
          toolName: payload.toolName,
        });
        break;
      case 'tool_call_update':
        stage.pushEvent('tool_call_update', {
          toolCallId: payload.toolCallId,
          status: payload.status,
        });
        break;
      case 'agent_message_chunk':
        stage.pushEvent('agent_message', {
          content: payload.content,
        });
        break;
      case 'agent_thought_chunk':
        stage.pushEvent('agent_thought', {
          content: payload.content,
        });
        break;
      case 'plan':
        stage.pushEvent('plan', {
          entries: payload.entries,
        });
        break;
      case 'usage_update':
        stage.pushEvent('usage', {
          usage: payload.usage,
        });
        break;
      case 'error':
        stage.pushEvent('error', {
          message: payload.message,
          code: payload.code,
        });
        break;
    }
  });

  // 7. Tomar screenshots periódicos (via Desktop API si está disponible)
  let screenshotInterval = null;
  try {
    const desktopStatus = await sdk.getDesktopStatus();
    if (desktopStatus.state === 'active') {
      screenshotInterval = setInterval(async () => {
        try {
          const png = await sdk.takeDesktopScreenshot({ format: 'jpeg', quality: 40 });
          recorder.recordScreenshot(png);
          stage.pushEvent('screenshot', { size: png.length });
        } catch {}
      }, SCREENSHOT_INTERVAL);
    }
  } catch {
    // Sin desktop API, continuar solo con eventos de texto
  }

  // 8. Enviar la task al agente
  console.log('[Orquestador] Enviando task al Developer Agent...');
  console.log('─'.repeat(60));
  console.log(task.slice(0, 1000) + '...');
  console.log('─'.repeat(60));

  stage.updateStatus('working', { phase: 'building' });

  const response = await session.prompt([
    { type: 'text', text: task },
  ]);

  console.log(`[Orquestador] Agent response: stopReason=${response.stopReason}`);

  // 9. Esperar mientras el agente trabaja
  // El agente puede trabajar por horas. Nosotros seguimos grabando.
  console.log('[Orquestador] Developer Agent trabajando. Grabando y transmitiendo...');
  console.log('[Orquestador] Presiona Ctrl+C para detener (la grabación se guardará)');
  
  // Mantener el proceso vivo hasta Ctrl+C
  await new Promise(() => {
    process.on('SIGINT', async () => {
      console.log('\n[Orquestador] Deteniendo...');
      
      // Cerrar recorder
      unsubscribeRecorder();
      unsubscribeStage();
      if (screenshotInterval) clearInterval(screenshotInterval);
      
      const stats = recorder.close();
      console.log(`[Orquestador] 📊 Estadísticas de grabación:`);
      console.log(`  Eventos:     ${stats.events}`);
      console.log(`  Trace:       ${stats.traceSizeFormatted}`);
      console.log(`  Screenshots: ${stats.screenshotCount} (${stats.screenshotSizeFormatted})`);
      console.log(`  Archivo:     ${recorder.tracePath}`);
      
      stage.updateStatus('stopped');
      stage.pushEvent('session_end', { events: stats.events });
      
      await sdk.destroySandbox();
      process.exit(0);
    });
  });
}

main().catch(async (err) => {
  console.error('[Orquestador] Error fatal:', err);
  
  try {
    const recorder = new TraceRecorder(DATA_DIR, { sessionId: AGENT_ID });
    recorder.record('error', { message: err.message, stack: err.stack });
    recorder.close();
  } catch {}
  
  process.exit(1);
});
