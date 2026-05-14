/**
 * pi-diag.mjs — Diagnóstico vía process.stdout.write (solo a archivo)
 *
 * Usa un buffer en memoria y escribe cada 500ms para minimizar I/O.
 * Sin filtros, sin stderr, sin alterar el flujo de datos.
 *
 * Uso: PI_DIAG=1 NODE_OPTIONS="--import /ruta/a/pi-diag.mjs" pi
 * Después de la sesión: cat /tmp/pi-render.log
 */

if (!process.env.PI_DIAG) {
  // No activado
} else {
  const fs = await import('node:fs');
  const LOG = '/tmp/pi-render.log';
  
  // Buffer en memoria para log
  let logBuf = [];
  let logTimer = null;
  
  function flushLog() {
    if (logBuf.length > 0) {
      const batch = logBuf.join('');
      logBuf = [];
      try { fs.appendFileSync(LOG, batch); } catch(e) {}
    }
  }
  
  // Vaciar cada 500ms
  const timer = setInterval(flushLog, 500);
  // También vaciar al salir
  process.on('exit', () => { clearInterval(timer); flushLog(); });
  
  // Limpiar log anterior
  try { fs.writeFileSync(LOG, ''); } catch(e) {}
  
  let renderCount = 0;
  
  const origWrite = process.stdout.write.bind(process.stdout);
  
  process.stdout.write = function(data, ...args) {
    if (typeof data === 'string' && data.length > 0) {
      renderCount++;
      
      // Detectar secuencias relevantes
      const seqs = [];
      if (data.includes('\x1b[2J')) seqs.push('2J');
      if (data.includes('\x1b[3J')) seqs.push('3J');
      if (data.includes('\x1b[?2026h')) seqs.push('SYNCH');
      if (data.includes('\x1b[?2026l')) seqs.push('SYNCL');
      if (data.includes('\x1b[S')) seqs.push('SU');
      if (data.includes('\x1b[T')) seqs.push('SD');
      if (data.includes('\x1b[A')) seqs.push('CU');
      if (data.includes('\x1b[B')) seqs.push('CD');
      if (data.includes('\x1b[H')) seqs.push('HOME');
      if (data.includes('\x1b[2K')) seqs.push('CL');
      if (data.includes('\x1b[?1049h')) seqs.push('1049h');
      if (data.includes('\x1b[?1049l')) seqs.push('1049l');
      
      const rnCount = (data.match(/\r\n/g) || []).length;
      const hasText = data.replace(/\x1b\[[0-9;]*[a-zA-Z]/g, '').replace(/\x1b/g, '').trim().length > 0;
      
      // Solo log si hay secuencias relevantes O muchos \r\n O texto significativo
      if (seqs.length > 0 || rnCount > 0 || hasText) {
        // Resumir el contenido legible
        const clean = data
          .replace(/\x1b\[[0-9;]*[a-zA-Z]/g, '')
          .replace(/\x1b\](\d+);[^\x07]*\x07/g, '')
          .replace(/\x1b[^\[]./g, '')
          .replace(/\x1b/g, '')
          .replace(/\r\n/g, '¶')
          .replace(/\r/g, '¶')
          .replace(/\n/g, '¶')
          .substring(0, 80);
        
        const flags = seqs.join('|');
        logBuf.push(`R#${renderCount} len=${data.length} rn=${rnCount} [${flags}] «${clean}»\n`);
      }
    }
    
    return origWrite(data, ...args);
  };
}
