// Desktop Share Agent — Captures the Linux desktop screen
// Communicates with the parent process via JSON over stdout

import { execSync } from 'child_process';
import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';

const AGENT_ID = process.env.AGENT_ID || 'unknown';
const CHANNEL_NAME = process.env.CHANNEL_NAME || 'Desktop Share';
const __dirname = path.dirname(fileURLToPath(import.meta.url));

// ─── IPC helpers ───────────────────────────────────────────────────
function send(type, data = {}) {
  process.stdout.write(JSON.stringify({ type, ...data }) + '\n');
}

function sendFrame(buffer) {
  send('frame', { data: buffer.toString('base64') });
}

function sendLog(text) {
  send('log', { text });
}

function sendStatus(status, text) {
  send('status', { status, text });
}

// ─── Screen capture ────────────────────────────────────────────────
function captureScreen() {
  const tmpFile = `/tmp/agent-desktop-${AGENT_ID}.jpg`;

  // Try multiple capture methods in order of preference
  const methods = [
    // Method 1: xwd + ImageMagick convert (fastest)
    () => {
      const xwd = execSync('xwd -root -silent', { encoding: null, timeout: 3000 });
      return execSync('convert xwd:- -quality 35 -resize 1280x720 jpeg:-', {
        input: xwd, encoding: null, timeout: 5000,
      });
    },
    // Method 2: scrot (fallback)
    () => {
      execSync(`scrot -q 35 "${tmpFile}"`, { timeout: 5000 });
      const data = fs.readFileSync(tmpFile);
      try { fs.unlinkSync(tmpFile); } catch {}
      return data;
    },
    // Method 3: import (ImageMagick)
    () => {
      execSync(`import -window root -quality 35 -resize 1280x720 "${tmpFile}"`, { timeout: 8000 });
      const data = fs.readFileSync(tmpFile);
      try { fs.unlinkSync(tmpFile); } catch {}
      return data;
    },
  ];

  for (const method of methods) {
    try {
      return method();
    } catch (e) {
      // try next method
    }
  }
  throw new Error('No screen capture method available');
}

// ─── Main ──────────────────────────────────────────────────────────
async function main() {
  sendLog(`🚀 Agente "${CHANNEL_NAME}" iniciando...`);
  sendLog(`🖥️  DISPLAY=${process.env.DISPLAY || '(none)'}`);

  // Verify capture works
  try {
    const testFrame = captureScreen();
    sendLog(`✅ Captura de pantalla funcionando (${testFrame.length} bytes)`);
  } catch (e) {
    sendLog(`❌ No se puede capturar la pantalla: ${e.message}`);
    sendLog('💡 Asegúrate de que DISPLAY esté configurado y X11 esté corriendo');
    sendStatus('error', 'No hay pantalla disponible');
    process.exit(1);
  }

  sendStatus('live', 'Transmitiendo escritorio');
  sendLog(`🎥 Transmitiendo como "${CHANNEL_NAME}" (ID: ${AGENT_ID})`);

  let frameCount = 0;

  while (true) {
    try {
      const buffer = captureScreen();
      sendFrame(buffer);
      frameCount++;

      if (frameCount % 30 === 0) {
        sendLog(`📊 Enviados ${frameCount} frames`);
      }

      await new Promise(r => setTimeout(r, 500)); // ~2fps for desktop
    } catch (e) {
      sendLog(`⚠️ Error capturando: ${e.message}`);
      await new Promise(r => setTimeout(r, 2000));
    }
  }
}

main().catch((e) => {
  sendLog(`💥 Fatal: ${e.message}`);
  process.exit(1);
});
