const http = require('http');
const fs = require('fs');
const path = require('path');
const { exec } = require('child_process');

const PORT = 3456;
const BASE = path.join(__dirname, '..');

const AGENTS = {
  'orchestrator': { color: '#e91e63', emoji: '🧠' },
  'html': { color: '#ff9800', emoji: '🟧' },
  'css': { color: '#2196F3', emoji: '🟦' },
  'js': { color: '#ffeb3b', emoji: '🟨' },
  'tests': { color: '#9c27b0', emoji: '🟪' },
  'docs': { color: '#4CAF50', emoji: '🟩' },
  'script-es': { color: '#e91e63', emoji: '🇪🇸' },
  'script-en': { color: '#00bcd4', emoji: '🇺🇸' },
  'audio-en': { color: '#8bc34a', emoji: '🎤' },
  'style-fireship': { color: '#f44336', emoji: '🔥' },
  'style-networkchuck': { color: '#4caf50', emoji: '☕' },
  'style-tiktok': { color: '#000', emoji: '📱' },
  'style-theo': { color: '#2196F3', emoji: '💻' },
  'composer': { color: '#9c27b0', emoji: '🎬' },
};

const APP_AGENTS = ['orchestrator','html','css','js','tests','docs'];
const VIDEO_AGENTS = ['script-es','script-en','audio-en','style-fireship','style-networkchuck','style-tiktok','style-theo','composer'];

function isRunning(name) {
  if (name === 'orchestrator') {
    const timeline = readTimeline();
    const lastOrch = timeline.filter(e => e.agent === 'orchestrator').pop();
    if (lastOrch) return (Date.now() - parseInt(lastOrch.ts)) < 30000;
    return false;
  }
  for (const dir of ['.pids', 'video/.pids']) {
    const pidFile = path.join(BASE, dir, name + '.pid');
    if (fs.existsSync(pidFile)) {
      const pid = parseInt(fs.readFileSync(pidFile, 'utf8').trim());
      try { process.kill(pid, 0); return true; } catch {}
    }
  }
  return false;
}

function getRealStates() {
  const states = {};
  for (const name of Object.keys(AGENTS)) {
    if (isRunning(name)) {
      states[name] = 'running';
    } else {
      const timeline = readTimeline();
      const entries = timeline.filter(e => e.agent === name);
      const last = entries[entries.length - 1];
      states[name] = (last && last.status === 'DONE') ? 'done' : 'idle';
    }
  }
  return states;
}

function readTimeline() {
  const files = [path.join(BASE, '.timeline'), path.join(BASE, 'video', '.timeline')];
  let entries = [];
  for (const f of files) {
    if (!fs.existsSync(f)) continue;
    const lines = fs.readFileSync(f, 'utf8').trim().split('\n').filter(Boolean);
    for (const line of lines) {
      const p = line.split('|');
      if (p.length >= 5) entries.push({ ts: p[0], time: p[1], agent: p[2], status: p[3], msg: p[4] });
    }
  }
  return entries.sort((a, b) => parseInt(a.ts) - parseInt(b.ts));
}

function getLastMessages() {
  const last = {};
  for (const e of readTimeline()) last[e.agent] = e.msg;
  return last;
}

function getVideos() {
  const videoDir = path.join(BASE, 'video', 'output');
  if (!fs.existsSync(videoDir)) return [];
  return fs.readdirSync(videoDir)
    .filter(f => f.endsWith('.mp4'))
    .map(f => {
      const stat = fs.statSync(path.join(videoDir, f));
      const parts = f.replace('.mp4', '').split('-');
      return {
        name: f,
        size: (stat.size / 1024).toFixed(0) + 'KB',
        lang: parts[1] || 'unknown',
        style: parts[2] || 'unknown'
      };
    });
}

const HTML = `<!DOCTYPE html>
<html lang="es">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>🤖 Agent Team Dashboard</title>
  <style>
    * { margin: 0; padding: 0; box-sizing: border-box; }
    body { font-family: -apple-system, sans-serif; background: #0a0a0a; color: #e0e0e0; padding: 20px; }
    .header { text-align: center; padding: 20px; border-bottom: 1px solid #333; margin-bottom: 20px; }
    .header h1 { font-size: 28px; color: #00ff88; }
    .section { margin-bottom: 30px; }
    .section h2 { color: #00ff88; margin-bottom: 15px; padding-bottom: 5px; border-bottom: 1px solid #333; }
    .agents { display: grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); gap: 10px; }
    .agent-card { background: #111; border: 1px solid #333; border-radius: 8px; padding: 10px; }
    .agent-card.running { border-color: #00ff88; }
    .agent-card.done { border-color: #4CAF50; opacity: 0.8; }
    .agent-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 5px; }
    .agent-name { font-size: 13px; font-weight: bold; }
    .agent-status { padding: 2px 6px; border-radius: 10px; font-size: 10px; }
    .status-running { background: #1b5e20; color: #4CAF50; animation: pulse 1.5s infinite; }
    .status-done { background: #004d40; color: #00ff88; }
    .status-idle { background: #333; color: #888; }
    .agent-msg { font-size: 10px; color: #888; }
    
    .videos { display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 15px; }
    .video-card { background: #111; border: 1px solid #333; border-radius: 8px; padding: 15px; }
    .video-card h3 { font-size: 14px; margin-bottom: 5px; }
    .video-card .meta { font-size: 11px; color: #888; margin-bottom: 10px; }
    .video-card video { width: 100%; border-radius: 4px; }
    .video-card .btn { display: inline-block; margin-top: 8px; padding: 5px 10px; background: #222; border: 1px solid #444; color: #fff; border-radius: 4px; cursor: pointer; font-size: 11px; text-decoration: none; }
    .video-card .btn:hover { background: #333; }
    
    .controls { margin-top: 20px; display: flex; gap: 10px; justify-content: center; flex-wrap: wrap; }
    .btn { padding: 10px 20px; border: 2px solid #444; background: #222; color: #fff; border-radius: 8px; cursor: pointer; font-size: 13px; }
    .btn:hover { background: #333; }
    .btn-start { border-color: #4CAF50; color: #4CAF50; }
    .btn-stop { border-color: #f44336; color: #f44336; }
    
    .timeline { background: #111; border: 1px solid #333; border-radius: 8px; padding: 15px; max-height: 250px; overflow-y: auto; }
    .timeline-entry { display: flex; gap: 8px; padding: 2px 0; font-size: 11px; border-bottom: 1px solid #1a1a1a; }
    .timeline-time { color: #666; min-width: 55px; }
    .timeline-agent { min-width: 90px; font-weight: bold; }
    
    @keyframes pulse { 0%,100%{opacity:1} 50%{opacity:0.5} }
    .es { color: #ff9800; }
    .en { color: #2196F3; }
    .fireship { color: #f44336; }
    .networkchuck { color: #4CAF50; }
    .tiktok { color: #fff; }
    .theo { color: #00bcd4; }
  </style>
</head>
<body>
  <div class="header">
    <h1>🤖 Agent Team Dashboard</h1>
    <p>Actualización en tiempo real • <span id="clock"></span></p>
  </div>
  
  <div class="section">
    <h2>📹 Videos Generados (<span id="video-count">0</span>)</h2>
    <div class="videos" id="videos"></div>
  </div>
  
  <div class="section">
    <h2>📱 Agentes App</h2>
    <div class="agents" id="app-agents"></div>
  </div>
  
  <div class="section">
    <h2>🎬 Agentes Video</h2>
    <div class="agents" id="video-agents"></div>
  </div>
  
  <div class="timeline">
    <h2>⏱️ Timeline</h2>
    <div id="timeline-entries"></div>
  </div>
  
  <div class="controls">
    <button class="btn btn-start" onclick="apiPost('/api/start-app')">🚀 Lanzar App</button>
    <button class="btn btn-start" onclick="apiPost('/api/start-video')">🎬 Lanzar Video</button>
    <button class="btn btn-stop" onclick="apiPost('/api/stop')">🛑 Detener Todo</button>
    <button class="btn" onclick="location.reload()">🔄 Refrescar</button>
  </div>

  <script>
    const APP_AGENTS = ${JSON.stringify(APP_AGENTS)};
    const VIDEO_AGENTS = ${JSON.stringify(VIDEO_AGENTS)};
    const COLORS = ${JSON.stringify(Object.fromEntries(Object.entries(AGENTS).map(([k,v]) => [k, v.color])))};
    const EMOJIS = ${JSON.stringify(Object.fromEntries(Object.entries(AGENTS).map(([k,v]) => [k, v.emoji])))};
    
    setInterval(() => document.getElementById('clock').textContent = new Date().toLocaleTimeString(), 1000);
    
    const evtSource = new EventSource('/events');
    evtSource.onmessage = (e) => {
      const d = JSON.parse(e.data);
      if (d.type === 'update') {
        renderAgents(d.agents, d.lastMsg);
        renderTimeline(d.timeline);
        renderVideos(d.videos);
      }
    };
    
    function renderAgents(states, lastMsg) {
      renderGroup('app-agents', APP_AGENTS, states, lastMsg);
      renderGroup('video-agents', VIDEO_AGENTS, states, lastMsg);
    }
    
    function renderGroup(id, list, states, lastMsg) {
      document.getElementById(id).innerHTML = list.map(name => {
        const state = states[name] || 'idle';
        const msg = lastMsg[name] || 'Esperando...';
        const color = COLORS[name] || '#fff';
        return \`<div class="agent-card \${state}">
          <div class="agent-header">
            <span class="agent-name" style="color:\${color}">\${EMOJIS[name]||'⚪'} \${name}</span>
            <span class="agent-status status-\${state}">\${state}</span>
          </div>
          <div class="agent-msg">\${msg}</div>
        </div>\`;
      }).join('');
    }
    
    function renderTimeline(entries) {
      document.getElementById('timeline-entries').innerHTML = entries.slice(-25).map(e => {
        const color = COLORS[e.agent] || '#fff';
        const icon = {START:'🚀',WORKING:'⚙️',DONE:'✅',ERROR:'❌',STOPPED:'🛑'}[e.status]||'';
        return \`<div class="timeline-entry">
          <span class="timeline-time">\${e.time}</span>
          <span class="timeline-agent" style="color:\${color}">\${e.agent}</span>
          <span>\${icon}</span>
          <span>\${e.msg}</span>
        </div>\`;
      }).join('');
      const el = document.getElementById('timeline-entries');
      el.scrollTop = el.scrollHeight;
    }
    
    let lastVideoHash = '';
    function renderVideos(videos) {
      const hash = videos.map(v => v.name).join(',');
      if (hash === lastVideoHash) return;
      lastVideoHash = hash;
      document.getElementById('video-count').textContent = videos.length;
      document.getElementById('videos').innerHTML = videos.map(v => \`
        <div class="video-card">
          <h3 class="\${v.lang}">\${v.lang === 'es' ? '🇪🇸' : '🇺🇸'} \${v.lang.toUpperCase()}</h3>
          <p class="meta \${v.style}">Estilo: \${v.style} • \${v.size}</p>
          <video controls preload="none">
            <source src="/video/\${v.name}" type="video/mp4">
          </video>
          <a href="/video/\${v.name}" class="btn" target="_blank">📥 Descargar</a>
        </div>
      \`).join('');
    }
    
    async function apiPost(url) { await fetch(url, { method: 'POST' }); }
    
    fetch('/api/state').then(r=>r.json()).then(d => {
      renderAgents(d.agents, d.lastMsg);
      renderTimeline(d.timeline);
      renderVideos(d.videos);
    });
  </script>
</body>
</html>`;

const server = http.createServer((req, res) => {
  res.setHeader('Access-Control-Allow-Origin', '*');
  
  if (req.url === '/') {
    res.writeHead(200, { 'Content-Type': 'text/html' });
    res.end(HTML);
  } else if (req.url?.startsWith('/video/')) {
    const filename = req.url.replace('/video/', '');
    const filepath = path.join(BASE, 'video', 'output', filename);
    if (fs.existsSync(filepath)) {
      const stat = fs.statSync(filepath);
      res.writeHead(200, { 'Content-Type': 'video/mp4', 'Content-Length': stat.size });
      fs.createReadStream(filepath).pipe(res);
    } else {
      res.writeHead(404); res.end('Not found');
    }
  } else if (req.url === '/events') {
    res.writeHead(200, { 'Content-Type': 'text/event-stream', 'Cache-Control': 'no-cache', 'Connection': 'keep-alive' });
    const iv = setInterval(() => {
      res.write(`data: ${JSON.stringify({ type: 'update', timeline: readTimeline(), agents: getRealStates(), lastMsg: getLastMessages(), videos: getVideos() })}\n\n`);
    }, 1000);
    req.on('close', () => clearInterval(iv));
  } else if (req.url === '/api/state') {
    res.writeHead(200, { 'Content-Type': 'application/json' });
    res.end(JSON.stringify({ timeline: readTimeline(), agents: getRealStates(), lastMsg: getLastMessages(), videos: getVideos() }));
  } else if (req.url === '/api/start-app' && req.method === 'POST') {
    res.writeHead(200); res.end(JSON.stringify({ ok: true }));
    exec(`cd ${BASE} && ./launch.sh start`, () => {});
  } else if (req.url === '/api/start-video' && req.method === 'POST') {
    res.writeHead(200); res.end(JSON.stringify({ ok: true }));
    exec(`cd ${BASE}/video && ./launch-video.sh start`, () => {});
  } else if (req.url === '/api/stop' && req.method === 'POST') {
    res.writeHead(200); res.end(JSON.stringify({ ok: true }));
    exec(`cd ${BASE} && ./launch.sh stop`, () => {});
    exec(`cd ${BASE}/video && ./launch-video.sh stop`, () => {});
  } else {
    res.writeHead(404); res.end();
  }
});

server.listen(PORT, '0.0.0.0', () => {
  console.log(`🚀 Dashboard: http://localhost:${PORT}`);
  console.log(`🚀 Tailscale: http://100.102.52.59:${PORT}`);
});
