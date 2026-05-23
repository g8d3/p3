/**
 * Tape — Trace Recorder
 *
 * Graba TODO lo que hace un agente en formato JSONL (JSON Lines).
 * No es video. Es el rastro estructurado de programación en texto puro:
 * tool_calls, mensajes, pensamientos, errores, screenshots periódicos.
 *
 * Esto es mucho más valioso que un video porque:
 * 1. Ocupa 1/1000 del espacio (KB vs MB por minuto)
 * 2. Es buscable y consultable
 * 3. Se puede RECONSTRUIR como video después con TTS + screenshots
 * 4. Se puede comprimir (gzip) a ~5% del tamaño original
 *
 * Formato: {"ts":<iso>, "type":"<tipo>", "data":{...}}
 */

import fs from 'node:fs';
import path from 'node:path';
import { createGzip } from 'node:zlib';

export class TraceRecorder {
  constructor(outputDir, options = {}) {
    this.outputDir = outputDir;
    this.sessionId = options.sessionId || `dev-${Date.now()}`;
    this.compress = options.compress !== false;
    this.maxSizeMb = options.maxSizeMb || 50; // Rotar a nuevo archivo
    this.keepScreenshotsEveryMs = options.keepScreenshotsEveryMs || 30000; // cada 30s
    
    // Dos archivos: trace principal + screenshots separados (binarios grandes)
    this.tracePath = path.join(outputDir, `${this.sessionId}.jsonl`);
    this.screenshotsDir = path.join(outputDir, `${this.sessionId}-screenshots`);
    
    fs.mkdirSync(outputDir, { recursive: true });
    fs.mkdirSync(this.screenshotsDir, { recursive: true });
    
    this.traceStream = fs.createWriteStream(this.tracePath, { flags: 'a' });
    this.byteCount = 0;
    this.fileIndex = 0;
    this.lastScreenshotTs = 0;
    this.eventCount = 0;
    
    this._write({ type: 'session_start', data: { sessionId: this.sessionId, startedAt: new Date().toISOString() } });
  }

  /**
   * Registra un evento del agente
   * @param {string} type - tool_call | tool_call_update | agent_message | agent_thought | plan | usage | error | screenshot | status
   * @param {object} data - payload del evento
   */
  record(type, data) {
    this._write({ type, data });
  }

  /**
   * Conecta el recorder a una sesión de sandbox-agent
   * Escucha todos los eventos y los graba automáticamente
   */
  connectToSession(session) {
    const unsubscribe = session.onEvent((event) => {
      const { sender, payload } = event;
      const update = payload?.sessionUpdate;
      
      if (!update) return;
      
      switch (update) {
        case 'tool_call':
          this.record('tool_call', {
            toolCallId: payload.toolCallId,
            title: payload.title,
            status: payload.status,
            rawInput: payload.rawInput,
            toolName: payload.toolName,
            timestamp: new Date().toISOString(),
          });
          break;

        case 'tool_call_update':
          this.record('tool_call_update', {
            toolCallId: payload.toolCallId,
            status: payload.status,
            content: payload.content,
            error: payload.error,
            timestamp: new Date().toISOString(),
          });
          break;

        case 'agent_message_chunk':
          this.record('agent_message', {
            content: payload.content,
            timestamp: new Date().toISOString(),
          });
          break;

        case 'agent_thought_chunk':
          this.record('agent_thought', {
            content: payload.content,
            timestamp: new Date().toISOString(),
          });
          break;

        case 'plan':
          this.record('plan', {
            entries: payload.entries,
            timestamp: new Date().toISOString(),
          });
          break;

        case 'usage_update':
          this.record('usage', {
            usage: payload.usage,
            timestamp: new Date().toISOString(),
          });
          break;

        case 'session_info_update':
          this.record('session_info', {
            title: payload.title,
            timestamp: new Date().toISOString(),
          });
          break;

        case 'error':
          this.record('error', {
            message: payload.message,
            code: payload.code,
            stack: payload.stack,
            timestamp: new Date().toISOString(),
          });
          break;
      }
    });

    return unsubscribe;
  }

  /**
   * Toma un screenshot y lo guarda (comprimido, con referencia en el trace)
   */
  recordScreenshot(imageBuffer) {
    const now = Date.now();
    if (now - this.lastScreenshotTs < this.keepScreenshotsEveryMs) return;
    this.lastScreenshotTs = now;

    const filename = `ss-${now}.jpg`;
    const filepath = path.join(this.screenshotsDir, filename);
    
    // Guardar screenshot como JPEG comprimido (~30-80KB)
    fs.writeFileSync(filepath, imageBuffer);
    
    // Solo una referencia en el trace principal (no el binario)
    this.record('screenshot', {
      file: filename,
      size: imageBuffer.length,
      timestamp: new Date(now).toISOString(),
    });
  }

  _write(entry) {
    const line = JSON.stringify({
      ts: new Date().toISOString(),
      seq: this.eventCount++,
      ...entry,
    }) + '\n';
    
    this.traceStream.write(line);
    this.byteCount += Buffer.byteLength(line);
    
    // Rotar si excede el tamaño máximo
    if (this.byteCount > this.maxSizeMb * 1024 * 1024) {
      this.rotate();
    }
  }

  rotate() {
    this.traceStream.end();
    this.fileIndex++;
    const newPath = this.tracePath.replace('.jsonl', `.${this.fileIndex}.jsonl`);
    this.tracePath = newPath;
    this.traceStream = fs.createWriteStream(this.tracePath, { flags: 'a' });
    this.byteCount = 0;
    
    // Comprimir el archivo anterior en background
    const oldPath = this.tracePath.replace(`.${this.fileIndex}.jsonl`, `.${this.fileIndex - 1}.jsonl`);
    if (fs.existsSync(oldPath)) {
      const readStream = fs.createReadStream(oldPath);
      const writeStream = fs.createWriteStream(oldPath + '.gz');
      const gzip = createGzip();
      readStream.pipe(gzip).pipe(writeStream).on('finish', () => {
        fs.unlinkSync(oldPath); // eliminar original después de comprimir
      });
    }
  }

  /**
   * Cierra el recorder y comprime todo
   */
  close() {
    this._write({ type: 'session_end', data: { endedAt: new Date().toISOString(), totalEvents: this.eventCount } });
    this.traceStream.end();
    
    // Resumen
    const stats = this.getStats();
    return stats;
  }

  getStats() {
    let traceSize = 0;
    let screenshotCount = 0;
    let screenshotSize = 0;
    
    try {
      // Trace files
      const traceFiles = fs.readdirSync(this.outputDir)
        .filter(f => f.startsWith(this.sessionId) && f.endsWith('.jsonl'));
      for (const f of traceFiles) {
        traceSize += fs.statSync(path.join(this.outputDir, f)).size;
      }
      
      // Screenshots
      if (fs.existsSync(this.screenshotsDir)) {
        const ssFiles = fs.readdirSync(this.screenshotsDir);
        screenshotCount = ssFiles.length;
        for (const f of ssFiles) {
          screenshotSize += fs.statSync(path.join(this.screenshotsDir, f)).size;
        }
      }
    } catch {}

    return {
      sessionId: this.sessionId,
      events: this.eventCount,
      traceSizeBytes: traceSize,
      traceSizeFormatted: this._formatBytes(traceSize),
      screenshotCount,
      screenshotSizeFormatted: this._formatBytes(screenshotSize),
    };
  }

  _formatBytes(bytes) {
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  }
}


/**
 * Replayer — Lee un trace y reproduce eventos en tiempo real
 * Útil para reconstruir videos después
 */
export class TraceReplayer {
  constructor(tracePath) {
    this.tracePath = tracePath;
  }

  async *play(rate = 1.0) {
    const lines = fs.readFileSync(this.tracePath, 'utf-8').split('\n').filter(Boolean);
    let prevTs = null;
    
    for (const line of lines) {
      const event = JSON.parse(line);
      
      // Respetar timing original
      if (prevTs && event.ts) {
        const delay = (new Date(event.ts) - new Date(prevTs)) / rate;
        if (delay > 0) {
          await new Promise(r => setTimeout(r, Math.min(delay, 5000)));
        }
      }
      prevTs = event.ts || prevTs;
      
      yield event;
    }
  }
}
