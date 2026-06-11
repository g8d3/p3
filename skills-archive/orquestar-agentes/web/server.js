#!/usr/bin/env node
// webui — Web dashboard for orquestar-agentes
// Serves API + static files. Zero dependencies (built-in http).

const http = require('http');
const fs = require('fs');
const path = require('path');
const { execSync } = require('child_process');
const cfg = require('../lib/config');

const PORT = process.env.PORT || 3030;
const { merged: CONFIG } = cfg.loadConfig();
const BUS = CONFIG.bus.dir || '/tmp/agent-bus';
const WEB_DIR = __dirname;
const STATIC_DIR = __dirname;
const VIDEO_DIRS = ['/tmp/video-cache', '/tmp/agent-bus/videos'];

// ── Helpers ──

function json(res, data, status = 200) {
  res.writeHead(status, {
    'Content-Type': 'application/json',
    'Access-Control-Allow-Origin': '*',
    'Access-Control-Allow-Methods': 'GET, POST, OPTIONS',
    'Access-Control-Allow-Headers': 'Content-Type',
  });
  res.end(JSON.stringify(data, null, 2));
}

function readFile(p) {
  try { return fs.readFileSync(p, 'utf-8'); } catch { return ''; }
}

function readDir(p) {
  try { return fs.readdirSync(p); } catch { return []; }
}

function fileExists(p) {
  try { fs.accessSync(p, fs.constants.F_OK); return true; } catch { return false; }
}

function ageMs(p) {
  try { return Date.now() - fs.statSync(p).mtimeMs; } catch { return 0; }
}

function formatAge(ms) {
  if (ms < 1000) return 'ahora';
  if (ms < 60000) return `${Math.floor(ms/1000)}s`;
  if (ms < 3600000) return `${Math.floor(ms/60000)}m`;
  return `${Math.floor(ms/3600000)}h`;
}
function fmtTime(ts) {
  const d = new Date(ts);
  return `${String(d.getHours()).padStart(2,'0')}:${String(d.getMinutes()).padStart(2,'0')}:${String(d.getSeconds()).padStart(2,'0')}`;
}

// ── Metrics helpers (Linux /proc) ──
let _cpuPrev = { total: 0, idle: 0 };

function readProcStat() {
  try {
    const raw = fs.readFileSync('/proc/stat', 'utf-8');
    const line = raw.split('\n').find(l => l.startsWith('cpu '));
    if (!line) return { total: 0, idle: 0 };
    const parts = line.trim().split(/\s+/).slice(1).map(Number);
    const total = parts.reduce((a, b) => a + b, 0);
    const idle = parts[3] || 0; // idle = 4th column
    return { total, idle };
  } catch { return { total: 0, idle: 0 }; }
}

function readProcMeminfo() {
  try {
    const raw = fs.readFileSync('/proc/meminfo', 'utf-8');
    const totalKb = (raw.match(/MemTotal:\s+(\d+)/) || [])[1];
    const availKb = (raw.match(/MemAvailable:\s+(\d+)/) || [])[1];
    if (!totalKb) return { totalMb: 0, usedMb: 0 };
    const totalMb = Math.round(parseInt(totalKb) / 1024);
    const usedMb = availKb ? Math.round((parseInt(totalKb) - parseInt(availKb)) / 1024) : 0;
    return { totalMb, usedMb };
  } catch { return { totalMb: 0, usedMb: 0 }; }
}

function readProcNetDev() {
  try {
    const raw = fs.readFileSync('/proc/net/dev', 'utf-8');
    const lines = raw.split('\n').slice(2).filter(Boolean);
    let rxTotal = 0, txTotal = 0;
    for (const line of lines) {
      const parts = line.trim().split(/\s+/);
      if (parts[0] === 'lo:') continue; // skip loopback
      rxTotal += parseInt(parts[1]) || 0;    // bytes received
      txTotal += parseInt(parts[9]) || 0;    // bytes transmitted
    }
    return { rxKb: Math.round(rxTotal / 1024), txKb: Math.round(txTotal / 1024) };
  } catch { return { rxKb: 0, txKb: 0 }; }
}

// ── API handlers ──

function apiAgents() {
  const agents = [];
  const agentCfg = CONFIG.agents || {};
  const dirs = readDir(BUS).filter(d => fileExists(`${BUS}/${d}/in`));
  const stats = cfg.readStats();
  for (const name of dirs.sort()) {
    const inDir = `${BUS}/${name}/in`;
    const msgs = readDir(inDir).map(f => ({
      file: f,
      content: readFile(`${inDir}/${f}`).slice(0, 200),
      age: formatAge(ageMs(`${inDir}/${f}`)),
    }));
    const acfg = agentCfg[name] || {};
    const st = stats[name] || {};
    agents.push({
      name,
      role: acfg.role || 'free',
      desc: acfg.desc || '',
      online: true,
      inbox: msgs,
      inboxCount: msgs.length,
      starts: st.starts || 0,
      crashes: st.crashes || 0,
    });
  }
  return agents;
}

function apiStatus() {
  const daemonCfg = CONFIG.daemons || {};
  const daemonPatterns = {
    busd: 'scripts/busd', 'webui': 'server\\.js', 'task-runner': 'task-runner',
    supervisor: 'scripts/supervisor', ciclador: 'scripts/ciclador',
  };
  const daemons = Object.entries(daemonCfg)
    .filter(([_, d]) => d.enabled !== false)
    .map(([name, d]) => {
      const pattern = daemonPatterns[name] || name;
      const pid = execSync(`pgrep -f "${pattern}" 2>/dev/null | head -1`).toString().trim();
      return { name, desc: d.desc || '', pid: pid || null, alive: !!pid, essential: d.enabled !== false };
    });

  return {
    daemons,
    busAlive: fileExists(BUS),
    agents: apiAgents(),
  };
}

function apiLogs() {
  const dataDir = cfg.GLOBAL_DATA;
  return {
    supervisor: readFile(`${dataDir}/supervisor.log`).split('\n').filter(Boolean).slice(-50).reverse(),
    ciclador: readFile(`${dataDir}/ciclador.log`).split('\n').filter(Boolean).slice(-50).reverse(),
    taskrunner: readFile(`${BUS}/logs/task-runner.log`).split('\n').filter(Boolean).slice(-50).reverse(),
  };
}

function apiHistory() {
  const raw = readFile(`${BUS}/history/messages.log`).split('\n').filter(Boolean);
  return raw.slice(-100).map(line => {
    const tsMatch = line.match(/^\[(\d+)\]/);
    if (!tsMatch) return { raw: line };
    const ts = parseInt(tsMatch[1]) * 1000;
    const rest = line.replace(/^\[\d+\]\s*/, '');
    let from = '🌐', to = '?', msg = rest;
    // External: "→ target: msg" | Agent: "source → target: msg"
    if (rest.startsWith('→ ')) {
      // External message (no source)
      const afterArrow = rest.slice(2); // remove "→ "
      const colonIdx = afterArrow.indexOf(': ');
      if (colonIdx !== -1) { to = afterArrow.slice(0, colonIdx); msg = afterArrow.slice(colonIdx + 2); }
    } else {
      const arrowIdx = rest.indexOf(' → ');
      if (arrowIdx !== -1) {
        from = rest.slice(0, arrowIdx).trim();
        const afterArrow = rest.slice(arrowIdx + 3); // skip " → "
        const colonIdx = afterArrow.indexOf(': ');
        if (colonIdx !== -1) { to = afterArrow.slice(0, colonIdx); msg = afterArrow.slice(colonIdx + 2); }
      }
    }
    return { time: fmtTime(ts), from, to, msg: msg.slice(0, 150), ago: formatAge(Date.now() - ts) };
  }).reverse();
}

function scanVideos() {
  const list = [];
  for (const dir of VIDEO_DIRS) {
    if (!fileExists(dir)) continue;
    for (const f of readDir(dir).sort().reverse().slice(0, 20)) {
      if (!f.endsWith('.mp4') || f.startsWith('.')) continue;
      const fp = `${dir}/${f}`;
      try {
        const stat = fs.statSync(fp);
        list.push({ file: f, path: fp, size: stat.size, modified: formatAge(Date.now() - stat.mtimeMs) });
      } catch {}
    }
  }
  return list;
}

function apiVideos() {
  const streamPath = '/tmp/video-cache/current.mp4';
  let streamMtime = null;
  try { streamMtime = fs.statSync(streamPath).mtimeMs; } catch {}
  return {
    videos: scanVideos().map((v, i) => ({ ...v, url: `/api/video/${i}` })),
    stream: { active: fileExists(streamPath), mtime: streamMtime },
  };
}

// ── HTTP Router ──

function serveFile(res, filePath) {
  const extMap = { '.html': 'text/html', '.js': 'application/javascript', '.css': 'text/css' };
  const ext = path.extname(filePath);
  try {
    const content = fs.readFileSync(filePath);
    res.writeHead(200, { 'Content-Type': extMap[ext] || 'text/plain' });
    res.end(content);
  } catch {
    res.writeHead(404);
    res.end('Not found');
  }
}

const server = http.createServer((req, res) => {
  const url = new URL(req.url, `http://localhost:${PORT}`);

  if (req.method === 'OPTIONS') {
    res.writeHead(204, { 'Access-Control-Allow-Origin': '*', 'Access-Control-Allow-Methods': 'GET, POST, OPTIONS', 'Access-Control-Allow-Headers': 'Content-Type' });
    return res.end();
  }

  if (url.pathname === '/api/stream') {
    const filePath = '/tmp/video-cache/current.mp4';

    // GET /api/stream?info — return file size + mtime as JSON
    if (url.searchParams.get('info') === '1') {
      try {
        const stat = fs.statSync(filePath);
        return json(res, { size: stat.size, mtime: stat.mtimeMs, exists: true });
      } catch {
        return json(res, { size: 0, exists: false });
      }
    }

    // GET /api/stream?init — serve first bytes (ftyp+moov via faststart)
    if (url.searchParams.get('init') === '1') {
      try {
        const stat = fs.statSync(filePath);
        if (stat.size === 0) throw new Error('empty');
        const initSize = Math.min(stat.size, 4096);
        const fd = fs.openSync(filePath, 'r');
        const buf = Buffer.alloc(initSize);
        fs.readSync(fd, buf, 0, initSize, 0);
        fs.closeSync(fd);
        res.writeHead(200, { 'Content-Type': 'video/mp4' });
        return res.end(buf);
      } catch {
        res.writeHead(503);
        return res.end('No file');
      }
    }

    // Serve file with full 206 Partial Content support
    try {
      const stat = fs.statSync(filePath);
      if (stat.size === 0) throw new Error('empty');
      const fileSize = stat.size;
      const range = req.headers.range;

      if (range) {
        const parts = range.replace(/bytes=/, '').split('-');
        const start = parseInt(parts[0], 10);
        const end = parts[1] ? parseInt(parts[1], 10) : fileSize - 1;
        const chunkSize = end - start + 1;
        res.writeHead(206, {
          'Content-Range': `bytes ${start}-${end}/${fileSize}`,
          'Accept-Ranges': 'bytes',
          'Content-Length': chunkSize,
          'Content-Type': 'video/mp4',
          'Cache-Control': 'no-cache',
        });
        fs.createReadStream(filePath, { start, end }).pipe(res);
      } else {
        res.writeHead(200, {
          'Content-Length': fileSize,
          'Content-Type': 'video/mp4',
          'Accept-Ranges': 'bytes',
          'Cache-Control': 'no-cache',
        });
        fs.createReadStream(filePath).pipe(res);
      }
    } catch {
      res.writeHead(404, { 'Content-Type': 'text/plain' });
      res.end('No stream available');
    }
    return;
  }

  if (url.pathname === '/api/status') return json(res, apiStatus());
  if (url.pathname === '/api/agents') return json(res, apiAgents());
  if (url.pathname === '/api/notes') {
    const notesDir = BUS + '/design-notes';
    const files = readDir(notesDir).filter(f => f.endsWith('.txt'));
    const notes = files.map(f => ({
      name: f,
      content: readFile(notesDir + '/' + f),
      modified: formatAge(ageMs(notesDir + '/' + f)),
    }));
    return json(res, notes);
  }
  if (url.pathname === '/api/config') {
    if (req.method === 'GET') return json(res, CONFIG);
    if (req.method === 'POST') {
      let body = '';
      req.on('data', c => body += c);
      req.on('end', () => {
        try {
          const newCfg = JSON.parse(body);
          cfg.saveGlobalConfig(newCfg);
          Object.assign(CONFIG, newCfg);
          json(res, { ok: true });
        } catch (e) { json(res, { ok: false, error: e.message }, 400); }
      });
      return;
    }
  }
  if (url.pathname === '/api/stats') return json(res, cfg.readStats());

  // GET /api/metrics — CPU, RAM, network from /proc
  if (url.pathname === '/api/metrics') {
    // CPU: compare total ticks between samples
    const cpuNow = readProcStat();
    let cpuPercent = 0;
    if (_cpuPrev.total > 0) {
      const delta = cpuNow.total - _cpuPrev.total;
      const idle = cpuNow.idle - _cpuPrev.idle;
      cpuPercent = delta > 0 ? parseFloat(((1 - idle / delta) * 100).toFixed(1)) : 0;
    }
    _cpuPrev = cpuNow;

    // RAM
    const mem = readProcMeminfo();

    // Network
    const net = readProcNetDev();

    return json(res, {
      server: {
        cpu_percent: cpuPercent,
        ram_total_mb: mem.totalMb,
        ram_used_mb: mem.usedMb,
        net_rx_kb: net.rxKb,
        net_tx_kb: net.txKb,
      },
      client: {},
      fetched_at: Date.now(),
    });
  }

  // GET /api/resources — ps-based CPU/RAM per process
  if (url.pathname === '/api/resources') {
    try {
      const out = execSync('ps aux --sort=-%cpu 2>/dev/null | head -80').toString();
      const procs = out.trim().split('\n').slice(1).filter(Boolean).map(line => {
        const p = line.trim().split(/\s+/);
        if (p.length < 11) return null;
        return { pid: parseInt(p[1]), cpu: parseFloat(p[2]), mem: parseFloat(p[3]), command: p.slice(10).join(' ') };
      }).filter(Boolean);
      return json(res, { processes: procs });
    } catch { return json(res, { processes: [] }); }
  }

  // GET /api/processes — unified list: daemons + agents + spawned, with CPU/RAM
  if (url.pathname === '/api/processes') {
    const status = apiStatus();
    const agents = apiAgents();
    let allPs = [];
    try {
      const out = execSync('ps aux --sort=-%cpu 2>/dev/null').toString();
      allPs = out.trim().split('\n').slice(1).filter(Boolean).map(line => {
        const p = line.trim().split(/\s+/);
        if (p.length < 11) return null;
        return { pid: parseInt(p[1]), cpu: parseFloat(p[2]), mem: parseFloat(p[3]), user: p[0], command: p.slice(10).join(' ') };
      }).filter(Boolean);
    } catch {}
    const psMap = {};
    allPs.forEach(p => { psMap[p.pid] = p; });

    const rows = [];

    // Daemons
    (status.daemons || []).forEach(d => {
      const ps = d.pid ? psMap[parseInt(d.pid)] : null;
      rows.push({
        name: d.name, type: 'daemon', status: d.alive ? 'active' : 'down',
        role: d.essential ? 'essential' : 'optional', pid: d.pid ? parseInt(d.pid) : null,
        cpu: ps ? ps.cpu : null, mem: ps ? ps.mem : null,
        desc: d.desc || '', inbox: null, starts: null, crashes: null,
        removeable: false,
      });
    });

    // Agents
    agents.forEach(a => {
      // Try to find matching process by name
      let ps = allPs.find(p => p.command && p.command.includes('crush') && p.user === process.env.USER);
      if (!ps) ps = allPs.find(p => p.command && p.command.includes(a.name));
      rows.push({
        name: a.name, type: 'agent', status: a.online ? 'active' : 'offline',
        role: a.role || 'free', pid: ps ? ps.pid : null,
        cpu: ps ? ps.cpu : null, mem: ps ? ps.mem : null,
        desc: a.desc || '', inbox: a.inboxCount || 0, starts: a.starts || 0, crashes: a.crashes || 0,
        removeable: true,
      });
    });

    // Spawned processes (from ps that aren't daemons or agents)
    const knownPids = new Set(rows.map(r => r.pid).filter(Boolean));
    allPs.slice(0, 40).forEach(p => {
      if (knownPids.has(p.pid)) return;
      if (p.command.includes('server.js') || p.command.includes('busd') || p.command.includes('task-runner') ||
          p.command.includes('supervisor') || p.command.includes('ciclador') || p.command.includes('node ') ||
          p.command.includes('python') || p.command.includes('roll-video') || p.command.includes('ffmpeg')) {
        rows.push({
          name: p.command.split('/').pop().split(' ')[0].slice(0, 20),
          type: 'process', status: 'running', role: 'spawned', pid: p.pid,
          cpu: p.cpu, mem: p.mem,
          desc: p.command.slice(0, 60), inbox: null, starts: null, crashes: null,
          removeable: false,
        });
      }
    });

    return json(res, { processes: rows });
  }

  // GET /api/events — unified time-ordered feed of all sources
  if (url.pathname === '/api/events') {
    const events = [];
    const now = Date.now();
    // 1. History (messages.log)
    const raw = readFile(BUS + '/history/messages.log').split('\n').filter(Boolean);
    raw.slice(-150).forEach(line => {
      const tsMatch = line.match(/^\[(\d+)\]/);
      if (!tsMatch) return;
      const ts = parseInt(tsMatch[1]) * 1000;
      const rest = line.replace(/^\[\d+\]\s*/, '');
      let source = '🌐', target = '', content = rest;
      if (rest.startsWith('→ ')) {
        const afterArrow = rest.slice(2);
        const ci = afterArrow.indexOf(': ');
        if (ci !== -1) { target = afterArrow.slice(0, ci); content = afterArrow.slice(ci + 2); }
      } else {
        const ai = rest.indexOf(' → ');
        if (ai !== -1) {
          source = rest.slice(0, ai).trim();
          const afterArrow = rest.slice(ai + 3);
          const ci = afterArrow.indexOf(': ');
          if (ci !== -1) { target = afterArrow.slice(0, ci); content = afterArrow.slice(ci + 2); }
        }
      }
      // Extract trace_id from content suffix: [trace_id=<value>]
      let traceId = null;
      const traceMatch = content.match(/\[trace_id=([^\]]+)\]\s*$/);
      if (traceMatch) {
        traceId = traceMatch[1];
        content = content.slice(0, traceMatch.index).trim();
      }
      events.push({ ts, time: fmtTime(ts), ago: formatAge(now - ts), source, target, content: content.slice(0, 150), type: 'chat', trace_id: traceId });
    });
    // 2. Daemon logs
    const logFiles = [
      { path: cfg.GLOBAL_DATA + '/supervisor.log', name: 'supervisor' },
      { path: cfg.GLOBAL_DATA + '/ciclador.log', name: 'ciclador' },
      { path: BUS + '/logs/task-runner.log', name: 'task-runner' },
    ];
    logFiles.forEach(({ path: fp, name }) => {
      const lines = readFile(fp).split('\n').filter(Boolean).slice(-50);
      lines.forEach(line => {
        const m = line.match(/^\[(\d{2}:\d{2}:\d{2})\]\s*(.*)/);
        if (m) {
          const [h, mm, s] = m[1].split(':').map(Number);
          const d = new Date(); d.setHours(h, mm, s, 0);
          events.push({ ts: d.getTime(), time: m[1], ago: formatAge(now - d.getTime()), source: name, target: '', content: m[2], type: 'log' });
        } else {
          events.push({ ts: now, time: fmtTime(now), ago: 'ahora', source: name, target: '', content: line, type: 'log' });
        }
      });
    });
    // 3. Traces
    const traceDir = cfg.GLOBAL_DATA + '/traces';
    let tfiles = [];
    try { tfiles = fs.readdirSync(traceDir); } catch {}
    tfiles.filter(f => f.endsWith('.json') && f !== 'latest.json').forEach(f => {
      try {
        const d = JSON.parse(readFile(traceDir + '/' + f));
        const ts = (d.created || 0) * 1000;
        events.push({ ts, time: fmtTime(ts), ago: formatAge(now - ts), source: '📋 trace', target: (d.route||[]).join('→'), content: d.message||'', type: 'trace', trace_status: d.status, hops: d.hops||[] });
      } catch {}
    });
    events.sort((a, b) => b.ts - a.ts);
    return json(res, events.slice(0, 500));
  }

  // GET /api/traces — message flow traces
  if (url.pathname === '/api/traces') {
    const traceDir = cfg.GLOBAL_DATA + '/traces';
    const traces = [];
    let files = [];
    try { files = fs.readdirSync(traceDir); } catch {}
    for (const f of files.sort().reverse().slice(0, 100)) {
      if (!f.endsWith('.json') || f === 'latest.json') continue;
      try {
        const data = JSON.parse(readFile(traceDir + '/' + f));
        traces.push(data);
      } catch {}
    }
    // Aggregate multi-hop traces by matching message content overlap
    return json(res, { traces });
  }

  // GET /api/video/:id — serve video file by index (safe, no path exposure)
  if (url.pathname.startsWith('/api/video/')) {
    const id = parseInt(url.pathname.replace('/api/video/', ''), 10);
    const list = scanVideos();
    const video = list[id];
    if (!video || !fileExists(video.path)) { res.writeHead(404); res.end('Video not found'); return; }
    const stat = fs.statSync(video.path);
    const fileSize = stat.size;
    const range = req.headers.range;

    if (range) {
      const parts = range.replace(/bytes=/, '').split('-');
      const start = parseInt(parts[0], 10);
      const end = parts[1] ? parseInt(parts[1], 10) : fileSize - 1;
      const chunkSize = (end - start) + 1;
      res.writeHead(206, {
        'Content-Range': `bytes ${start}-${end}/${fileSize}`,
        'Accept-Ranges': 'bytes',
        'Content-Length': chunkSize,
        'Content-Type': 'video/mp4',
      });
      fs.createReadStream(video.path, { start, end }).pipe(res);
    } else {
      res.writeHead(200, {
        'Content-Type': 'video/mp4',
        'Content-Length': fileSize,
        'Accept-Ranges': 'bytes',
      });
      fs.createReadStream(video.path).pipe(res);
    }
    return;
  }

  // POST /api/agents/add — create new agent inbox
  if (url.pathname === '/api/agents/add' && req.method === 'POST') {
    let body = '';
    req.on('data', c => body += c);
    req.on('end', () => {
      try {
        const { name, role } = JSON.parse(body);
        if (!name || !role) return json(res, { ok: false, error: 'name and role required' }, 400);
        const agentDir = '/tmp/agent-bus/' + name + '/in';
        require('fs').mkdirSync(agentDir, { recursive: true });
        // Also create tmux window
        require('child_process').execSync('tmux new-window -d -n ' + name + ' "export PATH=$HOME/.agents/bin:$PATH; exec zsh -i -c crush --yolo"', { stdio: 'ignore' });
        json(res, { ok: true, name, role });
      } catch(e) { json(res, { ok: false, error: e.message }, 500); }
    });
    return;
  }

  // POST /api/agents/remove — delete agent inbox and tmux window
  if (url.pathname === '/api/agents/remove' && req.method === 'POST') {
    let body = '';
    req.on('data', c => body += c);
    req.on('end', () => {
      try {
        const { name } = JSON.parse(body);
        if (!name) return json(res, { ok: false, error: 'name required' }, 400);
        // Remove inbox dir
        try { fs.rmSync(BUS + '/' + name, { recursive: true, force: true }); } catch {}
        // Kill tmux window — try without session first, then with main:
        try { execSync('tmux kill-window -t ' + name + ' 2>/dev/null', { stdio: 'ignore' }); } catch {}
        try { execSync('tmux kill-window -t main:' + name + ' 2>/dev/null', { stdio: 'ignore' }); } catch {}
        // Also kill any remaining crush process for that agent
        try { execSync('pkill -f "crush.*--name ' + name + '" 2>/dev/null', { stdio: 'ignore' }); } catch {}
        json(res, { ok: true });
      } catch(e) { json(res, { ok: false, error: e.message }, 500); }
    });
    return;
  }

  // GET /api/agent-states — supervisor-tracked agent statuses
  if (url.pathname === '/api/agent-states') {
    try {
      const data = JSON.parse(readFile(BUS + '/agent-states.json'));
      return json(res, data);
    } catch {
      return json(res, {});
    }
  }

  // POST /api/send — write message to agent inbox
  if (url.pathname === '/api/send' && req.method === 'POST') {
    let body = '';
    req.on('data', c => body += c);
    req.on('end', () => {
      try {
        const { target, message } = JSON.parse(body);
        if (!target || !message) return json(res, { ok: false, error: 'target and message required' }, 400);
        const f = `${BUS}/${target}/in/msg-${Date.now()}`;
        fs.writeFileSync(f, message);
        json(res, { ok: true, target, message });
      } catch (e) { json(res, { ok: false, error: e.message }, 400); }
    });
    return;
  }

  // Serve index.html
  if (url.pathname === '/' || url.pathname === '/index.html') {
    return serveFile(res, path.join(WEB_DIR, 'index.html'));
  }

  // Other static files
  const f = path.join(WEB_DIR, url.pathname);
  if (f.startsWith(WEB_DIR) && fileExists(f)) return serveFile(res, f);

  serveFile(res, path.join(WEB_DIR, 'index.html'));
});

server.listen(PORT, () => {
  console.log(`🌐 WebUI en http://localhost:${PORT}`);
  console.log(`   API: /api/status, /api/agents, /api/logs, POST /api/send`);
});
