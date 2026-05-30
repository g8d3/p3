"""NOVA SPA — single-page web app.

Rendered server-side. No external dependencies.
"""

from __future__ import annotations
import os
import json

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def create_defaults():
    return {
        "provider_url": os.getenv("LLM_URL", "http://localhost:11434/v1/chat/completions"),
        "provider_model": os.getenv("LLM_MODEL", "llama3.2:1b"),
        "provider_key": os.getenv("LLM_API_KEY", ""),
        "provider_configured": bool(os.getenv("LLM_URL") or os.getenv("OPENCODE_GO_API_KEY")),
        "port": int(os.getenv("NOVA_PORT", "8777")),
    }


def build_spa(configured: bool, provider: str = "", model: str = "") -> str:
    """Generate the single-page application HTML."""
    return PAGE_HTML.replace("{{configured}}", json.dumps(configured)) \
                    .replace("{{provider}}", json.dumps(provider)) \
                    .replace("{{model}}", json.dumps(model))


PAGE_HTML = """<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="utf-8"/>
<meta name="viewport" content="width=device-width,initial-scale=1,maximum-scale=1"/>
<title>NOVA</title>
<style>
*{margin:0;padding:0;box-sizing:border-box}
body{background:#0d1117;color:#c9d1d9;font:15px/1.5 system-ui,sans-serif;height:100dvh;display:flex;flex-direction:column}
a{color:#58a6ff}
input,select,textarea{background:#0d1117;border:1px solid #30363d;border-radius:6px;color:#c9d1d9;padding:10px 14px;font:14px/1.4 inherit;width:100%;outline:none}
input:focus,textarea:focus{border-color:#58a6ff}
button{background:#238636;border:none;color:#fff;padding:10px 20px;border-radius:6px;cursor:pointer;font:600 14px/1 inherit}
button:hover{background:#2ea043}
button:disabled{opacity:.5;cursor:default}
.btn-outline{background:transparent;border:1px solid #30363d;color:#c9d1d9;padding:8px 16px}
.btn-outline:hover{background:#161b22}
.btn-danger{background:#da3633}
.btn-danger:hover{background:#f85149}
.card{background:#161b22;border:1px solid #30363d;border-radius:8px;padding:24px;margin:8px 0}
.hidden{display:none!important}
.flex{display:flex}
.flex-col{flex-direction:column}
.gap-2{gap:8px}
.gap-4{gap:16px}
.items-center{align-items:center}
.justify-between{justify-content:space-between}
.flex-1{flex:1}
.text-center{text-align:center}
.text-sm{font-size:13px;color:#8b949e}
.text-xs{font-size:11px;color:#484f58}
.mt-2{margin-top:8px}
.mt-4{margin-top:16px}
.mb-2{margin-bottom:8px}
.p-4{padding:16px}

/* Setup Page */
#setup-page{align-items:center;justify-content:center;min-height:100dvh;padding:20px}
#setup-page .card{max-width:480px;width:100%}
#setup-page h1{font-size:22px;margin-bottom:4px;color:#f0f6fc}
#setup-page .sub{color:#8b949e;font-size:13px;margin-bottom:20px}
.form-group{margin-bottom:14px}
.form-group label{display:block;font-size:12px;color:#8b949e;margin-bottom:4px;text-transform:uppercase}
.form-group .hint{font-size:11px;color:#484f58;margin-top:3px}
#test-result{padding:8px 12px;border-radius:6px;font-size:13px;margin-top:8px}
#test-result.ok{background:#23863622;color:#3fb950;border:1px solid #23863644}
#test-result.err{background:#da363322;color:#f85149;border:1px solid #da363344}

/* Chat Layout */
#chat-page{height:100dvh;display:flex;flex-direction:column}
#chat-header{padding:10px 16px;border-bottom:1px solid #21262d;display:flex;align-items:center;gap:12px;flex-shrink:0}
#chat-header .status{width:8px;height:8px;border-radius:50%;display:inline-block}
#chat-header .status.online{background:#3fb950}
#chat-header .status.offline{background:#f85149}
#chat-header .provider-info{font-size:12px;color:#8b949e}
#chat-messages{flex:1;overflow-y:auto;padding:16px;display:flex;flex-direction:column;gap:12px}
.message{max-width:85%;padding:12px 16px;border-radius:10px;line-height:1.5;font-size:14px;animation:fadeIn .2s}
.message.user{background:#1f6feb33;align-self:flex-end;border:1px solid #1f6feb44}
.message.assistant{background:#161b22;align-self:flex-start;border:1px solid #30363d}
.message.system{background:#161b22;align-self:center;border:1px solid #d2992244;color:#d29922;font-size:12px;text-align:center;max-width:70%}
.message .timestamp{font-size:10px;color:#484f58;margin-top:4px}
.message .code-block{background:#0d1117;border:1px solid #21262d;border-radius:6px;padding:12px;margin:8px 0;font:13px/1.4 monospace;overflow-x:auto;white-space:pre-wrap}
.message .tool-call{background:#0d1117;border:1px solid #1f6feb33;border-radius:6px;padding:8px 12px;margin:4px 0;font-size:12px;color:#58a6ff}
.message .tool-result{background:#0d1117;border:1px solid #3fb95033;border-radius:6px;padding:8px 12px;margin:4px 0;font-size:12px;color:#3fb950}
#chat-input-area{padding:12px 16px;border-top:1px solid #21262d;flex-shrink:0}
#chat-input-wrap{display:flex;gap:8px}
#chat-input{resize:none;padding:12px 16px;border-radius:8px;max-height:120px;min-height:44px}
#chat-send{padding:10px 20px;border-radius:8px;flex-shrink:0}

/* Live Preview */
#preview-panel{display:none;border-left:1px solid #21262d;flex-shrink:0}
#preview-panel.open{display:flex;flex-direction:column;width:45%}
#preview-header{padding:8px 12px;border-bottom:1px solid #21262d;font-size:12px;color:#8b949e;display:flex;align-items:center;justify-content:space-between}
#preview-frame{flex:1;border:none;background:#fff}

/* Overlay */
#settings-overlay{position:fixed;inset:0;background:rgba(0,0,0,.7);z-index:100;display:none;align-items:center;justify-content:center}
#settings-overlay.open{display:flex}
#settings-overlay .card{max-width:440px;width:90%}

/* Animations */
@keyframes fadeIn{from{opacity:0;transform:translateY(4px)}to{opacity:1;transform:translateY(0)}}
@keyframes pulse{0%,100%{opacity:1}50%{opacity:.4}}
.typing-dots span{display:inline-block;animation:pulse 1.4s infinite;font-size:20px;line-height:1}
.typing-dots span:nth-child(2){animation-delay:.2s}
.typing-dots span:nth-child(3){animation-delay:.4s}

/* Markdown-like formatting */
.message.assistant strong{color:#f0f6fc}
.message.assistant code{background:#0d1117;padding:1px 4px;border-radius:3px;font-size:13px}
.message.assistant ul,.message.assistant ol{padding-left:20px;margin:6px 0}
.message.assistant li{margin:2px 0}
.message.assistant h1,.message.assistant h2,.message.assistant h3{color:#f0f6fc;margin:8px 0 4px}
.message.assistant p{margin:4px 0}
.message.assistant hr{border:none;border-top:1px solid #21262d;margin:12px 0}
@media(max-width:768px){#preview-panel.open{position:fixed;inset:0;width:100%;z-index:50}}
</style>
</head>
<body>

<!-- ===== SETUP PAGE ===== -->
<div id="setup-page" class="flex flex-col">
  <div class="card">
    <h1>🚀 NOVA</h1>
    <p class="sub">Conectá un proveedor de IA para empezar. Necesitás una API compatible con OpenAI.</p>
    <div class="form-group">
      <label>API URL</label>
      <input id="setup-url" type="url" placeholder="https://api.openai.com/v1/chat/completions" value="http://localhost:11434/v1/chat/completions"/>
      <div class="hint">Ej: OpenAI, OpenCode, Ollama (local), o cualquier API compatible</div>
    </div>
    <div class="form-group">
      <label>Modelo</label>
      <input id="setup-model" placeholder="gpt-4o, deepseek-v4-flash, llama3.2:1b..." value="llama3.2:1b"/>
    </div>
    <div class="form-group">
      <label>API Key <span class="text-xs">(dejá vacío si es local, o usá $NOMBRE_DE_VAR)</span></label>
      <input id="setup-key" type="password" placeholder="sk-... o $MI_VARIABLE"/>
    </div>
    <button id="setup-test" class="btn-outline" onclick="testProvider()">Testear conexión</button>
    <div id="test-result" class="hidden"></div>
    <button id="setup-save" class="mt-4" onclick="saveProvider()" disabled style="width:100%">Guardar y empezar</button>
    <p class="text-center text-sm mt-4">¿No tenés proveedor? <a href="#" onclick="useOllama()">Usá Ollama local (gratis)</a></p>
  </div>
</div>

<!-- ===== CHAT PAGE ===== -->
<div id="chat-page" class="hidden">
  <div id="chat-header">
    <span class="status online" id="status-dot"></span>
    <strong>NOVA</strong>
    <span class="provider-info" id="provider-info"></span>
    <div style="margin-left:auto;display:flex;gap:6px">
      <button class="btn-outline" onclick="togglePreview()" style="padding:6px 12px;font-size:12px">👁 Vista previa</button>
      <button class="btn-outline" onclick="openSettings()" style="padding:6px 12px;font-size:12px">⚙</button>
    </div>
  </div>

  <div style="display:flex;flex:1;overflow:hidden">
    <div style="flex:1;display:flex;flex-direction:column">
      <div id="chat-messages"></div>
      <div id="chat-input-area">
        <div id="chat-input-wrap">
          <textarea id="chat-input" rows="1" placeholder="Creá un CRM, un clon de TikTok, un blog..." onkeydown="if(e.key==='Enter'&&!e.shiftKey){e.preventDefault();sendMessage()}"></textarea>
          <button id="chat-send" onclick="sendMessage()">Enviar</button>
        </div>
      </div>
    </div>
    <div id="preview-panel">
      <div id="preview-header">
        <span>🔍 Vista previa</span>
        <button class="btn-outline" onclick="togglePreview()" style="padding:2px 8px;font-size:11px">✕</button>
      </div>
      <iframe id="preview-frame" src="about:blank"></iframe>
    </div>
  </div>
</div>

<!-- ===== SETTINGS OVERLAY ===== -->
<div id="settings-overlay" onclick="if(e.target===this)closeSettings()">
  <div class="card" onclick="event.stopPropagation()">
    <h2 style="font-size:16px;margin-bottom:12px">⚙ Configurar proveedor</h2>
    <div class="form-group">
      <label>API URL</label>
      <input id="settings-url"/>
    </div>
    <div class="form-group">
      <label>Modelo</label>
      <input id="settings-model"/>
    </div>
    <div class="form-group">
      <label>API Key</label>
      <input id="settings-key" type="password"/>
    </div>
    <div style="display:flex;gap:8px;margin-top:16px">
      <button onclick="updateProvider()" style="flex:1">Actualizar</button>
      <button class="btn-danger" onclick="disconnectProvider()">Desconectar</button>
      <button class="btn-outline" onclick="closeSettings()">Cancelar</button>
    </div>
  </div>
</div>

<script>
const STATE = {configured: false, provider: '', model: '', streaming: false};

async function api(path, opts={}) {
  const r = await fetch(path, {...opts, headers:{'Content-Type':'application/json',...opts.headers}});
  if(!r.ok){const t=await r.text().catch(()=>'');throw new Error(t.slice(0,200))}
  return r.json();
}

// ── SETUP ──
async function testProvider() {
  const el = document.getElementById('test-result');
  el.className = 'hidden';
  const url = document.getElementById('setup-url').value.trim();
  const model = document.getElementById('setup-model').value.trim();
  const key = document.getElementById('setup-key').value.trim();
  document.getElementById('setup-test').disabled = true;
  document.getElementById('setup-test').textContent = 'Testeando...';
  try {
    const r = await api('/api/provider/test', {method:'POST', body:JSON.stringify({url,model,key})});
    el.className = r.ok ? 'ok' : 'err';
    el.textContent = r.ok ? `✅ Conexión exitosa — respuesta: "${r.response}"` : `❌ ${r.error}`;
    document.getElementById('setup-save').disabled = !r.ok;
  } catch(e) {
    el.className = 'err';
    el.textContent = `❌ ${e.message}`;
  }
  document.getElementById('setup-test').disabled = false;
  document.getElementById('setup-test').textContent = 'Testear conexión';
}

async function saveProvider() {
  const url = document.getElementById('setup-url').value.trim();
  const model = document.getElementById('setup-model').value.trim();
  const key = document.getElementById('setup-key').value.trim();
  await api('/api/provider/configure', {method:'POST', body:JSON.stringify({url,model,key})});
  STATE.configured = true;
  STATE.provider = url;
  STATE.model = model;
  enterChat();
}

function useOllama() {
  document.getElementById('setup-url').value = 'http://localhost:11434/v1/chat/completions';
  document.getElementById('setup-model').value = 'llama3.2:1b';
  document.getElementById('setup-key').value = '';
}

// ── CHAT ──
function enterChat() {
  document.getElementById('setup-page').classList.add('hidden');
  document.getElementById('chat-page').classList.remove('hidden');
  document.getElementById('provider-info').textContent = `⚡ ${STATE.model}`;
  addMessage('system', '¡Listo! NOVA está conectada a **' + STATE.model + '**. Decime qué querés crear.');
}

function addMessage(role, content, extra='') {
  const div = document.createElement('div');
  div.className = 'message ' + role;
  if(role === 'assistant' && content === '...') {
    div.innerHTML = '<div class="typing-dots"><span>.</span><span>.</span><span>.</span></div>';
    div.id = 'typing-indicator';
  } else {
    div.innerHTML = formatContent(content) + extra;
  }
  document.getElementById('chat-messages').appendChild(div);
  div.scrollIntoView({behavior:'smooth'});
  return div;
}

function formatContent(text) {
  // Escape HTML
  let s = text.replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');
  // Bold
  s = s.replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>');
  // Inline code
  s = s.replace(/`(.+?)`/g, '<code>$1</code>');
  // Code blocks
  s = s.replace(/```(\w*)\n([\s\S]*?)```/g, '<div class="code-block">$2</div>');
  // Lists
  s = s.replace(/^- (.+)/gm, '<li>$1</li>');
  s = s.replace(/(<li>.*<\/li>\n?)+/g, '<ul>$&</ul>');
  // Line breaks
  s = s.replace(/\n/g, '<br/>');
  return s.replace(/<br\/><\/li>/g, '</li>').replace(/<br\/><\/ul>/g, '</ul>');
}

let abortController = null;

async function sendMessage() {
  const input = document.getElementById('chat-input');
  const text = input.value.trim();
  if(!text || STATE.streaming) return;
  input.value = '';
  input.style.height = '44px';

  addMessage('user', text);
  const loading = addMessage('assistant', '...');

  abortController = new AbortController();
  STATE.streaming = true;
  document.getElementById('chat-send').disabled = true;

  try {
    const r = await fetch('/api/chat', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({message: text}),
      signal: abortController.signal,
    });
    if (!r.ok) throw new Error((await r.text()).slice(0,200));

    const reader = r.body.getReader();
    const decoder = new TextDecoder();
    let fullText = '';
    let inCodeBlock = false;

    loading.id = '';
    loading.innerHTML = '';

    while(true) {
      const {done, value} = await reader.read();
      if(done) break;
      const chunk = decoder.decode(value, {stream: true});
      const lines = chunk.split('\n');
      for (const line of lines) {
        if (line.startsWith('data: ')) {
          const data = line.slice(6).trim();
          if (data === '[DONE]') continue;
          try {
            const parsed = JSON.parse(data);
            if (parsed.type === 'text') {
              fullText += parsed.content;
              loading.innerHTML = formatContent(fullText);
            } else if (parsed.type === 'tool_call') {
              const toolDiv = document.createElement('div');
              toolDiv.className = 'tool-call';
              toolDiv.textContent = `🔧 ${parsed.tool}: ${parsed.params}`;
              loading.appendChild(toolDiv);
            } else if (parsed.type === 'tool_result') {
              const resultDiv = document.createElement('div');
              resultDiv.className = 'tool-result';
              resultDiv.textContent = `✅ ${parsed.result}`;
              loading.appendChild(resultDiv);
            } else if (parsed.type === 'app_updated') {
              updatePreview(parsed.url);
            } else if (parsed.type === 'error') {
              loading.innerHTML += `<div style="color:#f85149;margin-top:8px">❌ ${parsed.message}</div>`;
            }
          } catch(e) {}
        }
      }
    }

    // Auto-scroll
    loading.scrollIntoView({behavior:'smooth'});

  } catch(e) {
    if (e.name !== 'AbortError') {
      loading.innerHTML = `<div style="color:#f85149">❌ Error: ${e.message}</div>`;
    }
  }

  STATE.streaming = false;
  document.getElementById('chat-send').disabled = false;
  abortController = null;
}

// ── LIVE PREVIEW ──
function togglePreview() {
  const panel = document.getElementById('preview-panel');
  panel.classList.toggle('open');
}

function updatePreview(url) {
  const frame = document.getElementById('preview-frame');
  frame.src = url || 'http://localhost:' + window.location.port;
}

// ── SETTINGS ──
function openSettings() {
  document.getElementById('settings-url').value = STATE.provider;
  document.getElementById('settings-model').value = STATE.model;
  document.getElementById('settings-key').value = '';
  document.getElementById('settings-overlay').classList.add('open');
}

function closeSettings() {
  document.getElementById('settings-overlay').classList.remove('open');
}

async function updateProvider() {
  const url = document.getElementById('settings-url').value.trim();
  const model = document.getElementById('settings-model').value.trim();
  const key = document.getElementById('settings-key').value.trim();
  const r = await api('/api/provider/configure', {method:'POST', body:JSON.stringify({url,model,key})});
  STATE.provider = url;
  STATE.model = model;
  document.getElementById('provider-info').textContent = `⚡ ${STATE.model}`;
  closeSettings();
}

async function disconnectProvider() {
  await api('/api/provider/disconnect', {method:'POST'});
  STATE.configured = false;
  document.getElementById('chat-page').classList.add('hidden');
  document.getElementById('setup-page').classList.remove('hidden');
  document.getElementById('setup-save').disabled = true;
  document.getElementById('test-result').className = 'hidden';
  closeSettings();
}

// ── INIT ──
document.addEventListener('DOMContentLoaded', () => {
  const configured = {{configured}};
  const provider = {{provider}};
  const model = {{model}};
  if (configured) {
    STATE.configured = true;
    STATE.provider = provider;
    STATE.model = model;
    enterChat();
  }
  // Auto-resize textarea
  const input = document.getElementById('chat-input');
  input.addEventListener('input', () => {
    input.style.height = '44px';
    input.style.height = Math.min(input.scrollHeight, 120) + 'px';
  });
});
</script>
</body>
</html>"""
