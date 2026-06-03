#!/usr/bin/env python3
"""HTTP server: FIFO video stream + dashboard with unified table + CPU/RAM."""
import os, sys, json, threading, struct, subprocess, time
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse
from collections import deque

PIPE_PATH = '/tmp/video-cache/current.mp4'
HOST = '0.0.0.0'
PORT = int(sys.argv[1]) if len(sys.argv) > 1 else 8080
MAX_BUFFER = 30 * 1024 * 1024  # 30MB
BUS_DIR = '/tmp/agent-bus'

buffer = bytearray()
buffer_lock = threading.Lock()
buffer_cond = threading.Condition(buffer_lock)
buffer_ready = threading.Event()

# ── FIFO pipe reader ──
def pipe_reader():
    while True:
        try:
            with open(PIPE_PATH, 'rb') as pipe:
                while True:
                    chunk = pipe.read(65536)
                    if not chunk:
                        break
                    with buffer_lock:
                        buffer.extend(chunk)
                        if len(buffer) > MAX_BUFFER:
                            init_segment = buffer[:10240]
                            del buffer[:10240]
                            trim = len(buffer) - MAX_BUFFER + 10240
                            if trim > 0:
                                del buffer[:trim]
                            buffer[0:0] = init_segment
                        buffer_cond.notify_all()
                    buffer_ready.set()
        except FileNotFoundError:
            buffer_ready.wait(timeout=1)
        except OSError as e:
            sys.stderr.write(f'[pipe_reader] error: {e}\n')
            buffer_ready.wait(timeout=2)

# ── Helpers ──
def read_file(p):
    try:
        with open(p) as f:
            return f.read()
    except:
        return ''

def read_dir(p):
    try:
        return os.listdir(p)
    except:
        return []

def file_exists(p):
    return os.path.exists(p)

def age_ms(p):
    try:
        return int((time.time() - os.path.getmtime(p)) * 1000)
    except:
        return 0

def format_age(ms):
    s = ms // 1000
    if s < 1: return 'ahora'
    if s < 60: return f'{s}s'
    if s < 3600: return f'{s//60}m{s%60}s'
    return f'{s//3600}h{(s%3600)//60}m'

def get_ps():
    try:
        out = subprocess.check_output(['ps', 'aux', '--sort=-%cpu'], timeout=3, stderr=subprocess.DEVNULL)
        lines = out.decode().strip().split('\n')[1:]
        result = []
        for line in lines:
            p = line.split()
            if len(p) < 11: continue
            result.append({
                'pid': int(p[1]), 'cpu': float(p[2]), 'mem': float(p[3]),
                'user': p[0], 'command': ' '.join(p[10:]),
            })
        return result
    except:
        return []

def get_agents():
    agents = []
    if not os.path.isdir(BUS_DIR): return agents
    for name in sorted(os.listdir(BUS_DIR)):
        in_dir = f'{BUS_DIR}/{name}/in'
        if not os.path.isdir(in_dir): continue
        msgs = []
        for f in sorted(os.listdir(in_dir))[-10:]:
            c = read_file(f'{in_dir}/{f}')[:200]
            msgs.append({'file': f, 'content': c, 'age': format_age(age_ms(f'{in_dir}/{f}'))})
        stats_file = f'{BUS_DIR}/../.local/share/orquestar-agentes/stats.json'
        stats = {}
        try: stats = json.loads(read_file(stats_file)) if file_exists(stats_file) else {}
        except: pass
        st = stats.get(name, {})
        agents.append({
            'name': name, 'role': 'free', 'online': True,
            'inbox': msgs, 'inboxCount': len(msgs),
            'starts': st.get('starts', 0), 'crashes': st.get('crashes', 0),
        })
    return agents

def get_history():
    raw = read_file(f'{BUS_DIR}/history/messages.log').split('\n')
    events = []
    now = time.time() * 1000
    for line in raw:
        if not line: continue
        import re
        m = re.match(r'^\[(\d+)\]\s*(.*)', line)
        if not m: continue
        ts = int(m.group(1)) * 1000
        rest = m.group(2)
        source, target, content = '🌐', '', rest
        if rest.startswith('→ '):
            after = rest[2:]
            ci = after.find(': ')
            if ci != -1:
                target = after[:ci]
                content = after[ci+2:]
        else:
            ai = rest.find(' → ')
            if ai != -1:
                source = rest[:ai].strip()
                after = rest[ai+3:]
                ci = after.find(': ')
                if ci != -1:
                    target = after[:ci]
                    content = after[ci+2:]
        events.append({
            'ts': ts, 'time': time.strftime('%H:%M:%S', time.localtime(ts//1000)),
            'ago': format_age(int(now - ts)),
            'source': source, 'target': target, 'content': content[:150], 'type': 'chat',
        })
    return events

def get_traces():
    trace_dir = f'{BUS_DIR}/traces'
    traces = []
    if not os.path.isdir(trace_dir): return traces
    for f in sorted(os.listdir(trace_dir), reverse=True)[:100]:
        if not f.endswith('.json') or f == 'latest.json': continue
        try:
            data = json.loads(read_file(f'{trace_dir}/{f}'))
            traces.append(data)
        except: pass
    return traces

def scan_videos():
    result = []
    for d in ['/tmp/video-cache', '/tmp/agent-bus/videos']:
        if not os.path.isdir(d): continue
        for f in sorted(os.listdir(d), reverse=True)[:20]:
            if not f.endswith('.mp4') or f.startswith('.'): continue
            fp = f'{d}/{f}'
            try:
                st = os.stat(fp)
                result.append({'file': f, 'path': fp, 'size': st.st_size, 'modified': format_age(int((time.time() - st.st_mtime) * 1000))})
            except: pass
    return result

def get_daemons():
    patterns = {
        'busd': 'busd', 'webui': 'server\\.js', 'task-runner': 'task-runner',
        'supervisor': 'supervisor', 'ciclador': 'ciclador',
    }
    daemons = []
    for name, pat in patterns.items():
        pid = ''
        try:
            out = subprocess.check_output(['pgrep', '-f', pat], timeout=2, stderr=subprocess.DEVNULL)
            pid = out.decode().strip().split('\n')[0]
        except:
            pid = ''
        daemons.append({'name': name, 'pid': pid, 'alive': bool(pid), 'essential': True})
    return daemons

# ── HTML Dashboard ──
HTML_DASHBOARD = r'''<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>s76 — Video Stream</title>
<style>
*{margin:0;padding:0;box-sizing:border-box}
body{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;background:#0d1117;color:#c9d1d9;padding:20px}
h1{font-size:1.2rem;color:#58a6ff;margin-bottom:4px}
.subtitle{font-size:0.8rem;color:#8b949e;margin-bottom:12px}
.view-bar{display:flex;gap:4px;margin-bottom:12px;background:#161b22;border:1px solid #30363d;border-radius:8px;padding:4px;width:fit-content;flex-wrap:wrap}
.view-btn{padding:6px 16px;border-radius:6px;cursor:pointer;font-size:0.8rem;color:#8b949e;user-select:none}
.view-btn:hover{color:#c9d1d9;background:#21262d}
.view-btn.active{background:#238636;color:#fff}
.toolbar{display:flex;gap:8px;align-items:center;margin-bottom:6px;flex-wrap:wrap}
.toolbar input,.toolbar select{padding:5px 10px;border-radius:6px;border:1px solid #30363d;background:#0d1117;color:#c9d1d9;font-size:0.8rem}
.toolbar input{flex:1;min-width:120px}
.table-wrap{overflow-x:auto;border:1px solid #30363d;border-radius:8px;background:#161b22;margin-bottom:12px}
table{width:100%;border-collapse:collapse;font-size:0.82rem;min-width:600px}
thead th{text-align:left;padding:6px 10px;font-size:0.7rem;color:#8b949e;text-transform:uppercase;letter-spacing:0.3px;border-bottom:1px solid #30363d;font-weight:500;background:#0d1117;white-space:nowrap;cursor:pointer;user-select:none}
thead th:hover{color:#c9d1d9}
thead th .sort-arrow{color:#58a6ff;margin-left:3px;font-size:0.65rem}
tbody td{padding:5px 10px;border-bottom:1px solid #21262d;vertical-align:middle;white-space:nowrap}
tbody tr:last-child td{border-bottom:none}
tbody tr:hover{background:rgba(255,255,255,.03)}
.badge{font-size:0.65rem;padding:1px 8px;border-radius:8px;font-weight:500;white-space:nowrap}
.badge.daemon{background:rgba(63,185,80,.12);color:#3fb950;border:1px solid rgba(63,185,80,.2)}
.badge.agent{background:rgba(88,166,255,.12);color:#58a6ff;border:1px solid rgba(88,166,255,.2)}
.badge.process{background:rgba(139,148,158,.12);color:#8b949e;border:1px solid rgba(139,148,158,.2)}
.badge.human{background:rgba(210,153,34,.12);color:#d29922;border:1px solid rgba(210,153,34,.2)}
.badge.active,.badge.online{background:rgba(63,185,80,.12);color:#3fb950}
.badge.offline{background:rgba(139,148,158,.12);color:#8b949e}
.pid{color:#8b949e;font-size:0.75rem;font-family:monospace}
.cpuval{color:#58a6ff;font-size:0.75rem}
.memval{color:#3fb950;font-size:0.75rem}
.bar{display:inline-block;height:8px;border-radius:4px;min-width:2px}
.bar.cpu{background:#58a6ff}
.bar.mem{background:#3fb950}
.pagination{display:flex;gap:4px;align-items:center;padding:8px 14px;justify-content:center;font-size:0.75rem;color:#8b949e}
.pagination button{padding:3px 10px;border-radius:4px;border:1px solid #30363d;background:#0d1117;color:#c9d1d9;cursor:pointer;font-size:0.75rem}
.pagination button:hover{background:#21262d}
.pagination button:disabled{opacity:.4;cursor:not-allowed}
.pagination .pcur{color:#58a6ff;font-weight:600}
.filter-count{color:#8b949e;font-size:0.75rem;margin-left:auto;white-space:nowrap}
.name-col{display:flex;align-items:center;gap:6px;font-weight:600}
.dot{display:inline-block;width:7px;height:7px;border-radius:50%;margin-right:5px;flex-shrink:0}
.dot.green{background:#3fb950}
.dot.red{background:#f85149}
.dot.yellow{background:#d29922}
video{width:100%;max-height:400px;border-radius:8px;background:#000;margin-bottom:12px}
.expand-icon{display:inline-block;width:14px;text-align:center;color:#8b949e;font-size:0.7rem;flex-shrink:0}
tbody tr.expandable{cursor:pointer}
tbody tr.expanded{background:rgba(88,166,255,.04)}
.expand-inner{padding:8px 10px 8px 30px;background:#0d1117;font-size:0.78rem}
.sub-item{padding:3px 0;display:flex;gap:8px;align-items:flex-start;color:#8b949e}
.sub-item .st{color:#c9d1d9;flex:1}
.flow-path{font-family:monospace;color:#58a6ff;font-weight:600}
.flow-tag{padding:2px 8px;border-radius:10px;font-size:0.7rem;font-weight:500}
.status-text.active,.status-text.online{color:#3fb950}
.status-text.down,.status-text.offline{color:#f85149}
#streamStatus{font-size:0.85rem;color:#8b949e;margin-bottom:8px;display:block}
</style>
</head><body>
<h1>🎬 s76 — Video + Dashboard</h1>
<div class="subtitle">Streaming FIFO · Procesos · Eventos</div>
<video autoplay muted controls id="player"></video>
<span id="streamStatus">—</span>
<div style="display:flex;gap:8px;align-items:center;font-size:0.78rem;color:#8b949e;margin-bottom:8px">
  <span id="bufSize">buffer: —</span>
  <span id="playPos">pos: —</span>
  <span id="mseState">init: —</span>
</div>
<div class="view-bar">
  <span class="view-btn active" id="vRaw" onclick="setView('raw')">📋 Raw feed</span>
  <span class="view-btn" id="vAgent" onclick="setView('agent')">🤖 By agent</span>
  <span class="view-btn" id="vFlow" onclick="setView('flow')">🔀 By flow</span>
</div>
<div class="toolbar">
  <input id="filter" placeholder="Filtrar..." oninput="render()">
  <select id="typeFilter" onchange="render()">
    <option value="">Todos</option>
    <option value="agent">Agentes</option>
    <option value="daemon">Daemons</option>
    <option value="process">Procesos</option>
    <option value="human">Humanos</option>
  </select>
  <span class="filter-count" id="count"></span>
</div>
<div class="table-wrap">
  <table><thead><tr id="headers"></tr></thead>
  <tbody id="body"></tbody></table>
  <div class="pagination" id="pagination"></div>
</div>
<script>
// ── State ──
let view = 'raw';
let events = [], procs = [], traces = [];
let sortCol = '', sortDir = 'asc';
let page = 0, pageSize = 25;
let expanded = {};

function esc(s){const d=document.createElement('div');d.textContent=s;return d.innerHTML}

// ── Views ──
function setView(v){view=v;document.querySelectorAll('.view-btn').forEach(b=>b.classList.toggle('active',b.id.replace('v','').toLowerCase()===v));page=0;render()}

function getCols(){
  if(view==='raw') return [
    {id:'time',label:'Hora',always:1},{id:'source',label:'Origen'},{id:'target',label:'Destino'},
    {id:'content',label:'Mensaje',always:1},{id:'type',label:'Tipo'},{id:'ago',label:'Antigüedad'},
  ];
  if(view==='agent') return [
    {id:'name',label:'Nombre',always:1},{id:'type',label:'Tipo'},{id:'status',label:'Estado'},
    {id:'cpu',label:'CPU%'},{id:'mem',label:'RAM%'},{id:'lastMsg',label:'Último mensaje',always:1},{id:'lastSeen',label:'Visto'},
  ];
  return [
    {id:'route',label:'Ruta',always:1},{id:'trigger',label:'Trigger'},{id:'hop',label:'Hop'},
    {id:'status',label:'Estado'},{id:'steps',label:'Steps',always:1},{id:'duration',label:'Duración'},
  ];
}

function buildHeaders(cols){
  document.getElementById('headers').innerHTML=cols.map((c,i)=>{
    const arrow=sortCol===c.id?(sortDir==='asc'?' ▲':' ▼'):'';
    return `<th onclick="sortBy(${i})">${c.label}<span class="sort-arrow">${arrow}</span></th>`;
  }).join('');
}

function sortBy(idx){
  const cols=getCols();
  const c=cols[idx];
  if(sortCol===c.id)sortDir=sortDir==='asc'?'desc':'asc';
  else{sortCol=c.id;sortDir='asc';}
  render();
}

function goPage(d){page=Math.max(0,page+d);render()}
function toggleExpand(k){expanded[k]=!expanded[k];render()}

function render(){
  const cols=getCols();
  buildHeaders(cols);
  const text=(document.getElementById('filter').value||'').toLowerCase();
  const type=document.getElementById('typeFilter').value;

  let items=[];
  if(view==='raw') items=[...events];
  else if(view==='agent'){
    const map={};
    (procs||[]).forEach(p=>{
      const k=p.name.toLowerCase();
      map[k]={name:p.name,type:p.type||'process',status:p.status||'offline',cpu:p.cpu,mem:p.mem,pid:p.pid,desc:p.desc||'',msgs:[]};
    });
    events.forEach(e=>{
      const src=(e.source||'').trim();
      if(!src)return;
      const k=src.toLowerCase().replace(/[^a-z0-9]/g,'');
      if(!map[k]){const t=src==='🌐'?'human':src.includes('trace')?'orchestrator':'agent';map[k]={name:src,type:t,status:'active',cpu:null,mem:null,pid:null,desc:'',msgs:[]};}
      if(!map[k].msgs)map[k].msgs=[];
      map[k].msgs.push(e);
    });
    items=Object.values(map);
  }else{
    items=(traces||[]).map(t=>{
      const route=(t.route||[]).join('→')||'?';
      const hops=t.hops||[];
      const lastHop=hops[hops.length-1]||{};
      const curHop=lastHop.status==='verified'||lastHop.status==='failed'?lastHop.to:(hops.find(h=>h.status==='delivered'||h.status==='sent')||hops[0]||{}).to||'?';
      const now=Date.now();
      const created=t.created?t.created*1000:now;
      const dur=Math.floor((now-created)/1000);
      const durStr=dur<60?dur+'s':dur<3600?Math.floor(dur/60)+'m'+dur%60+'s':Math.floor(dur/3600)+'h'+Math.floor((dur%3600)/60)+'m';
      const msg=(t.message||'').toLowerCase();
      let trigger='Task';
      if(msg.includes('ciclador')||msg.includes('task-'))trigger='Ciclador';
      else if(msg.includes('checker:'))trigger='Checker';
      else if(msg.includes('user')||msg.includes('🌐'))trigger='User';
      let stepIdx=hops.length-1;
      if(t.status==='verified'||t.status==='failed')stepIdx=hops.length;else if(t.status==='planned')stepIdx=0;
      return{route,trigger,currentHop:curHop,status:t.status||'planned',hops,stepIdx,duration:durStr,id:t.id||Math.random().toString(36).slice(2),created};
    });
  }

  // Filter
  if(type){items=items.filter(i=>(i.type||'')===type||(i.source||'').includes(type));}
  if(text){items=items.filter(i=>JSON.stringify(i).toLowerCase().includes(text));}

  // Sort
  if(sortCol){
    items.sort((a,b)=>{
      let va=a[sortCol],vb=b[sortCol];
      if(sortCol==='lastMsg'){va=a.msgs&&a.msgs[0]?a.msgs[0].content:'';vb=b.msgs&&b.msgs[0]?b.msgs[0].content:'';}
      if(sortCol==='lastSeen'){va=a.msgs&&a.msgs[0]?a.msgs[0].time:'';vb=b.msgs&&b.msgs[0]?b.msgs[0].time:'';}
      if(va==null)va='';if(vb==null)vb='';
      if(typeof va==='string')va=va.toLowerCase();
      if(typeof vb==='string')vb=vb.toLowerCase();
      return va<vb?(sortDir==='asc'?-1:1):va>vb?(sortDir==='asc'?1:-1):0;
    });
  }

  // Pagination
  const total=items.length;
  const pages=Math.max(1,Math.ceil(total/pageSize));
  if(page>=pages)page=pages-1;
  const start=page*pageSize;
  const pageData=items.slice(start,start+pageSize);
  document.getElementById('count').textContent=total+' resultados';

  const body=document.getElementById('body');
  if(!pageData.length){body.innerHTML='<tr><td colspan="'+(cols.length)+'" style="color:#8b949e;text-align:center;padding:14px">Sin resultados</td></tr>';}
  else if(view==='raw'){
    body.innerHTML=pageData.map(e=>'<tr>'+cols.map(c=>{
      switch(c.id){
        case'time':return'<td><span class="pid">'+esc(e.time||'')+'</span></td>';
        case'source':return'<td><span class="badge '+(e.source||'?').toLowerCase()+'">'+esc(e.source||'?')+'</span></td>';
        case'target':return'<td>'+(e.target?esc(e.target):'<span style="color:#8b949e">—</span>')+'</td>';
        case'content':return'<td style="max-width:300px;overflow:hidden;text-overflow:ellipsis">'+esc(e.content||'')+'</td>';
        case'type':return'<td><span class="flow-tag">'+(e.type||'chat')+'</span></td>';
        case'ago':return'<td style="color:#8b949e;font-size:0.75rem">'+(e.ago||'')+'</td>';
        default:return'<td></td>';
      }
    }).join('')+'</tr>').join('');
  }else if(view==='agent'){
    body.innerHTML=pageData.map(e=>{
      const isExp=expanded[e.name];
      const msgs=(e.msgs||[]).slice(0,15);
      const lastMsg=msgs[0];
      const lastSeen=lastMsg?lastMsg.time+' '+lastMsg.ago:'—';
      const sd=e.status==='active'||e.status==='online'||e.status==='running'?'green':e.status==='down'||e.status==='offline'?'red':'yellow';
      const st=e.status==='active'?'online':e.status==='down'?'offline':e.status;
      const main='<tr class="expandable'+(isExp?' expanded':'')+'" onclick="toggleExpand(\''+esc(e.name)+'\')">'+
        cols.map(c=>{
          switch(c.id){
            case'name':return'<td><span class="name-col"><span class="expand-icon">'+(isExp?'▼':'▶')+'</span><span class="dot '+sd+'"></span>'+esc(e.name)+'</span></td>';
            case'type':return'<td><span class="badge '+(e.type||'')+'">'+(e.type||'')+'</span></td>';
            case'status':return'<td><span class="status-text '+st+'">'+st+'</span></td>';
            case'cpu':return e.cpu!=null?'<td><span class="cpuval">'+e.cpu.toFixed(1)+'%</span> <span class="bar cpu" style="width:'+Math.min(e.cpu*3,50)+'px"></span></td>':'<td style="color:#8b949e">—</td>';
            case'mem':return e.mem!=null?'<td><span class="memval">'+e.mem.toFixed(1)+'%</span> <span class="bar mem" style="width:'+Math.min(e.mem*20,50)+'px"></span></td>':'<td style="color:#8b949e">—</td>';
            case'lastMsg':return'<td style="max-width:200px;overflow:hidden;text-overflow:ellipsis;font-size:0.78rem;color:#8b949e">'+(lastMsg?esc(lastMsg.content||'').slice(0,60):'—')+'</td>';
            case'lastSeen':return'<td style="color:#8b949e;font-size:0.75rem">'+lastSeen+'</td>';
            default:return'<td></td>';
          }
        }).join('')+'</tr>';
      const expand=isExp?'<tr><td colspan="'+(cols.length)+'"><div class="expand-inner">'+
        (msgs.length?msgs.map(m=>'<div class="sub-item"><span class="pid" style="min-width:50px">'+m.time+'</span><span class="st">'+esc(m.content||'')+'</span><span style="color:#8b949e;font-size:0.7rem">'+m.ago+'</span></div>').join(''):'<div style="color:#8b949e;padding:4px 0">Sin mensajes</div>')+
        '</div></td></tr>':'';
      return main+expand;
    }).join('');
  }else{
    body.innerHTML=pageData.map(f=>{
      const exp=expanded['f-'+f.id];
      const steps=exp?'<tr><td colspan="'+(cols.length)+'"><div class="expand-inner">'+
        f.hops.map((h,i)=>'<div class="sub-item"><span class="pid">#'+(i+1)+'</span><span>'+esc(h.from||'?')+' → '+esc(h.to||'?')+'</span><span class="flow-tag">'+(h.status||'')+'</span></div>').join('')+
        '</div></td></tr>':'';
      return '<tr class="expandable'+(exp?' expanded':'')+'" onclick="toggleExpand(\'f-'+esc(f.id)+'\')">'+
        cols.map(c=>{
          switch(c.id){
            case'route':return'<td><span class="name-col"><span class="expand-icon">'+(exp?'▼':'▶')+'</span><span class="flow-path">'+esc(f.route)+'</span></span></td>';
            case'trigger':return'<td style="font-size:0.78rem">'+esc(f.trigger)+'</td>';
            case'hop':return'<td><span class="badge '+(f.currentHop||'').toLowerCase()+'">'+esc(f.currentHop)+'</span></td>';
            case'status':return'<td><span style="font-size:0.85rem">'+(f.status||'')+'</span></td>';
            case'steps':return'<td style="font-size:0.75rem;color:#8b949e">'+(f.hops||[]).length+' steps</td>';
            case'duration':return'<td style="color:#8b949e;font-size:0.75rem;font-family:monospace">'+f.duration+'</td>';
            default:return'<td></td>';
          }
        }).join('')+'</tr>'+steps;
    }).join('');
  }

  document.getElementById('pagination').innerHTML=pages>1?'<button onclick="goPage(-1)" '+(page===0?'disabled':'')+'>‹</button><span class="pcur">'+(page+1)+'</span><span style="color:#8b949e"> / '+pages+'</span><button onclick="goPage(1)" '+(page>=pages-1?'disabled':'')+'>›</button>':'';
}

// ── MediaSource fMP4 player ──
const player = document.getElementById('player');
const stEl = document.getElementById('streamStatus');
const bufEl = document.getElementById('bufSize');
const posEl = document.getElementById('playPos');
const mseEl = document.getElementById('mseState');

const CODEC = 'video/mp4; codecs="avc1.42C01E, mp4a.40.2"';
const POLL_MS = 2000;
const GC_WINDOW_S = 10;  // keep ~10s window
const INIT_SIZE = 10240;  // init segment is first 10KB

let mediaSource = null;
let sourceBuffer = null;
let fetchedBytes = 0;    // bytes already appended (offset into buffer)
let pendingAppend = false;
let mseReady = false;

function initMSE() {
  if (!window.MediaSource) { stEl.textContent = '❌ MSE not supported'; return; }
  mediaSource = new MediaSource();
  mediaSource.addEventListener('sourceopen', onSourceOpen);
  player.src = URL.createObjectURL(mediaSource);
  mseEl.textContent = 'sourceopen pending';
}

function onSourceOpen() {
  mseEl.textContent = 'sourceopen OK';
  try {
    sourceBuffer = mediaSource.addSourceBuffer(CODEC);
    sourceBuffer.addEventListener('updateend', onAppendDone);
    // Fetch init segment
    fetchInit();
    // Start polling for data
    setTimeout(pollBuffer, POLL_MS);
  } catch (e) {
    mseEl.textContent = 'error: ' + e.message;
  }
}

function onAppendDone() {
  pendingAppend = false;
  mseEl.textContent = 'appending OK';
}

async function fetchInit() {
  try {
    const r = await fetch('/current.mp4', {
      headers: { 'Range': `bytes=0-${INIT_SIZE - 1}` }
    });
    if (r.status !== 206) { stEl.textContent = '❌ init failed (no 206)'; return; }
    const buf = await r.arrayBuffer();
    if (buf.byteLength === 0) { stEl.textContent = '❌ init empty'; return; }
    sourceBuffer.appendBuffer(buf);
    fetchedBytes = buf.byteLength;
    mseReady = true;
    mseEl.textContent = `init ${buf.byteLength}B`;
    stEl.textContent = '🔴 streaming (MSE)';
  } catch (e) {
    stEl.textContent = '❌ init error: ' + e.message;
    mseEl.textContent = 'init err';
  }
}

async function pollBuffer() {
  if (!mseReady || !mediaSource || mediaSource.readyState !== 'open') {
    setTimeout(pollBuffer, POLL_MS);
    return;
  }

  try {
    // Get current buffer size
    const sr = await fetch('/current.mp4/size');
    const { size } = await sr.json();
    bufEl.textContent = `buffer: ${(size / 1024 / 1024).toFixed(1)}MB`;

    if (size === 0) { stEl.textContent = '⏳ waiting for stream...'; }
    else { stEl.textContent = '🔴 streaming (MSE)'; }

    // Fetch new bytes
    if (size > fetchedBytes && !pendingAppend) {
      pendingAppend = true;
      mseEl.textContent = `fetching ${fetchedBytes}→${size}`;
      const end = size - 1;
      const r = await fetch('/current.mp4', {
        headers: { 'Range': `bytes=${fetchedBytes}-${end}` }
      });
      if (r.status === 206) {
        const buf = await r.arrayBuffer();
        if (buf.byteLength > 0) {
          sourceBuffer.appendBuffer(buf);
          fetchedBytes += buf.byteLength;
          mseEl.textContent = `appended ${buf.byteLength}B`;
        } else {
          pendingAppend = false;
          mseEl.textContent = 'empty chunk';
        }
      } else {
        pendingAppend = false;
        mseEl.textContent = `HTTP ${r.status}`;
      }
    } else if (size <= fetchedBytes && size > INIT_SIZE) {
      // Buffer wrapped around — re-fetch from size polled
      if (!pendingAppend) {
        pendingAppend = true;
        const offset = Math.max(INIT_SIZE, size - 1024 * 1024); // last 1MB
        const r = await fetch('/current.mp4', {
          headers: { 'Range': `bytes=${offset}-${size - 1}` }
        });
        if (r.status === 206) {
          const buf = await r.arrayBuffer();
          if (buf.byteLength > 0) {
            sourceBuffer.appendBuffer(buf);
            fetchedBytes = size;
            mseEl.textContent = `wrap fetched ${buf.byteLength}B`;
          }
        }
        pendingAppend = false;
      }
    }

    // Update playback position
    if (!player.paused && sourceBuffer && sourceBuffer.buffered.length > 0) {
      const end = sourceBuffer.buffered.end(sourceBuffer.buffered.length - 1);
      posEl.textContent = `pos: ${end.toFixed(1)}s`;
    }
  } catch (e) {
    if (mseReady) mseEl.textContent = 'poll err: ' + e.message;
  }

  // GC: remove old data beyond 10s window
  if (sourceBuffer && sourceBuffer.buffered.length > 0 && !sourceBuffer.updating) {
    try {
      const end = sourceBuffer.buffered.end(sourceBuffer.buffered.length - 1);
      if (end > GC_WINDOW_S) {
        sourceBuffer.remove(0, end - GC_WINDOW_S);
      }
    } catch {}
  }

  setTimeout(pollBuffer, POLL_MS);
}

// ── Data fetch for dashboard tables ──
async function refresh(){
  try{
    const [eR,pR,tR,vR]=await Promise.all([
      fetch('/api/events').then(r=>r.json()),
      fetch('/api/processes').then(r=>r.json()),
      fetch('/api/traces').then(r=>r.json()),
      fetch('/api/videos').then(r=>r.json()),
    ]);
    events=eR||[];
    procs=(pR.processes)||[];
    traces=(tR.traces)||[];
    render();
  }catch(e){document.getElementById('count').textContent='❌ error de conexión';}
}

// ── Start ──
render();
refresh();
setInterval(refresh, 3000);
initMSE();
</script></body></html>'''

# ── HTTP Handler ──
class Handler(BaseHTTPRequestHandler):
    def _bufsize(self):
        with buffer_lock: return len(buffer)

    def _cors(self):
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, HEAD, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Range, Content-Type')

    def _json(self, data, status=200):
        self.send_response(status)
        self.send_header('Content-Type', 'application/json')
        self._cors()
        self.end_headers()
        self.wfile.write(json.dumps(data, default=str).encode())

    def do_OPTIONS(self):
        self.send_response(204)
        self._cors()
        self.end_headers()

    def do_HEAD(self):
        if self.path == '/current.mp4/size':
            self._json({'size': self._bufsize()})
            return
        if self.path in ('/current.mp4', '/api/stream'):
            sz = self._bufsize()
            self.send_response(200 if sz > 0 else 503)
            self.send_header('Content-Type', 'video/mp4')
            self.send_header('Content-Length', str(sz))
            self.send_header('Accept-Ranges', 'bytes')
            self._cors()
            self.end_headers()
            return
        self.send_response(404)
        self._cors()
        self.end_headers()

    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path

        # ── Video stream endpoints ──
        if path in ('/api/stream', '/current.mp4'):
            if self._bufsize() == 0:
                buffer_ready.wait(timeout=10)
            sz = self._bufsize()
            if sz == 0:
                self._json({'error': 'no data'}, 503)
                return

            range_h = self.headers.get('Range')
            if range_h:
                _, spec = range_h.split('=')
                start_s, end_s = spec.split('-', 1)
                start = int(start_s) if start_s else 0
                end = int(end_s) if end_s else sz - 1
                if start >= sz: start = max(0, sz - 1)
                if end >= sz: end = sz - 1
                length = end - start + 1
                self.send_response(206)
                self.send_header('Content-Type', 'video/mp4')
                self.send_header('Content-Range', f'bytes {start}-{end}/{sz}')
                self.send_header('Content-Length', str(length))
                self.send_header('Accept-Ranges', 'bytes')
                self._cors()
                self.end_headers()
                with buffer_lock:
                    self.wfile.write(bytes(buffer[start:end+1]))
            else:
                self.send_response(200)
                self.send_header('Content-Type', 'video/mp4')
                self.send_header('Content-Length', str(sz))
                self.send_header('Accept-Ranges', 'bytes')
                self._cors()
                self.end_headers()
                with buffer_lock:
                    self.wfile.write(bytes(buffer))
            return

        if path == '/current.mp4/size':
            self._json({'size': self._bufsize()})
            return

        # ── API endpoints ──
        if path == '/api/processes':
            ps = get_ps()
            daemons = get_daemons()
            agents = get_agents()
            ps_map = {p['pid']: p for p in ps}
            rows = []
            for d in daemons:
                pid = int(d['pid']) if d['pid'] else None
                p = ps_map.get(pid) if pid else None
                rows.append({
                    'name': d['name'], 'type': 'daemon', 'status': 'active' if d['alive'] else 'down',
                    'role': 'essential', 'pid': pid,
                    'cpu': p['cpu'] if p else None, 'mem': p['mem'] if p else None,
                    'desc': '', 'removeable': False,
                })
            for a in agents:
                p = next((x for x in ps if x['command'] and 'crush' in x['command']), None)
                rows.append({
                    'name': a['name'], 'type': 'agent', 'status': 'active' if a['online'] else 'offline',
                    'role': a['role'], 'pid': p['pid'] if p else None,
                    'cpu': p['cpu'] if p else None, 'mem': p['mem'] if p else None,
                    'desc': '', 'inbox': a['inboxCount'], 'removeable': True,
                })
            known = {r['pid'] for r in rows if r['pid']}
            for p in ps[:40]:
                if p['pid'] in known: continue
                cmd = p['command']
                if any(x in cmd for x in ['server.js','busd','task-runner','supervisor','ciclador','node ','python','roll-video','ffmpeg']):
                    rows.append({
                        'name': cmd.split('/')[-1].split(' ')[0][:20],
                        'type': 'process', 'status': 'running', 'role': 'spawned',
                        'pid': p['pid'], 'cpu': p['cpu'], 'mem': p['mem'],
                        'desc': cmd[:60], 'removeable': False,
                    })
            self._json({'processes': rows})
            return

        if path == '/api/events':
            self._json(get_history()[:200])
            return

        if path == '/api/traces':
            self._json({'traces': get_traces()})
            return

        if path == '/api/status':
            daemons = get_daemons()
            agents = get_agents()
            self._json({
                'daemons': daemons,
                'busAlive': os.path.isdir(BUS_DIR),
                'agents': [{'name': a['name'], 'role': a['role']} for a in agents],
            })
            return

        if path == '/api/agents':
            self._json(get_agents())
            return

        if path == '/api/videos':
            stream_path = PIPE_PATH
            stream_active = os.path.exists(stream_path)
            self._json({
                'videos': scan_videos(),
                'stream': {'active': stream_active},
            })
            return

        if path == '/api/resources':
            ps = get_ps()
            self._json({'processes': ps})
            return

        # ── Dashboard HTML ──
        if path == '/' or path == '/index.html':
            self.send_response(200)
            self.send_header('Content-Type', 'text/html; charset=utf-8')
            self._cors()
            self.end_headers()
            self.wfile.write(HTML_DASHBOARD.encode())
            return

        self.send_response(404)
        self._cors()
        self.end_headers()
        self.wfile.write(b'404')

    def log_message(self, fmt, *args):
        sys.stderr.write(f'[{self.log_date_time_string()}] {args[0]} {args[1]} {args[2]}\n')

if __name__ == '__main__':
    os.makedirs(os.path.dirname(PIPE_PATH), exist_ok=True)
    reader = threading.Thread(target=pipe_reader, daemon=True, name='pipe-reader')
    reader.start()
    time.sleep(0.5)
    server = HTTPServer((HOST, PORT), Handler)
    print(f'🚀 s76 server on http://{HOST}:{PORT}')
    print(f'   Dashboard: http://{HOST}:{PORT}/')
    print(f'   Stream:    http://{HOST}:{PORT}/api/stream')
    print(f'   APIs:      /api/processes, /api/events, /api/traces, /api/status, /api/videos')
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        server.shutdown()
