import React, { useState, useEffect, useRef, useCallback } from 'react';
import { createRoot } from 'react-dom/client';
import { LiveKitRoom, RoomAudioRenderer, useVoiceAssistant } from '@livekit/components-react';

const LIVEKIT_URL = `${location.protocol === 'https:' ? 'wss:' : 'ws:'}//${location.host}/livekit`;
const TOKEN_URL = `${location.protocol}//${location.host}/token`;
const LOG_URL = `${location.protocol}//${location.host}/log`;

// ── Browser Log Forwarder ─────────────────────────────────────────────────
// Captures console errors/warnings and sends them to the server for diagnosis

const LOG_LEVEL = 1; // 0=off, 1=errors only, 2=all

function sendLog(level, message, stack) {
  if (LOG_LEVEL === 0) return;
  if (LOG_LEVEL === 1 && level !== 'error') return;
  try {
    const payload = JSON.stringify({ level, message: String(message).slice(0, 500), stack: stack || '' });
    if (navigator.sendBeacon) {
      navigator.sendBeacon(LOG_URL, payload);
    } else {
      fetch(LOG_URL, { method: 'POST', body: payload, keepalive: true }).catch(() => {});
    }
  } catch {}
}

// Intercept console.error
const origError = console.error;
console.error = function(...args) {
  sendLog('error', args.map(a => typeof a === 'object' ? (a?.message || JSON.stringify(a)) : String(a)).join(' '), new Error().stack);
  origError.apply(console, args);
};

// Intercept unhandled rejections
window.addEventListener('unhandledrejection', (e) => {
  sendLog('error', e.reason?.message || String(e.reason), e.reason?.stack);
});

// Intercept runtime errors
window.addEventListener('error', (e) => {
  sendLog('error', e.message, e.error?.stack);
});

// Intercept React render errors via error boundary
class ErrorBoundary extends React.Component {
  constructor(props) { super(props); this.state = { error: null }; }
  static getDerivedStateFromError(error) { return { error }; }
  componentDidCatch(error, info) {
    sendLog('error', error?.message || String(error), error?.stack);
  }
  render() {
    if (this.state.error) return this.props.fallback || React.createElement('div', { style: { padding: 20, color: 'var(--error)', fontSize: 13 } }, 'Error: ' + (this.state.error?.message || 'Unknown'));
    return this.props.children;
  }
}

// Override window.onerror (catches different errors than addEventListener)
window.onerror = function(msg, url, line, col, error) {
  sendLog('error', msg + ' at ' + url + ':' + line + ':' + col, error?.stack);
  return false;
};

// Report connection state changes
sendLog('info', `App loaded at ${location.href}`);

const LLM_PROVIDERS = [
  { id: 'zai-coding-plan', label: 'z.ai Coding Plan', models: [{ id: 'glm-4.5-air', label: 'GLM-4.5-Air' }, { id: 'glm-4.7', label: 'GLM-4.7' }], defaultModel: 'glm-4.5-air' },
  { id: 'openai', label: 'OpenAI', models: [{ id: 'gpt-4o', label: 'GPT-4o' }, { id: 'gpt-4o-mini', label: 'GPT-4o Mini' }], defaultModel: 'gpt-4o' },
  { id: 'cerebras', label: 'Cerebras', models: [{ id: 'llama-3.3-70b', label: 'Llama 3.3 70B' }], defaultModel: 'llama-3.3-70b' },
  { id: 'deepseek', label: 'DeepSeek', models: [{ id: 'deepseek-chat', label: 'DeepSeek V3' }], defaultModel: 'deepseek-chat' },
  { id: 'openrouter', label: 'OpenRouter', models: [{ id: 'openai/gpt-4o', label: 'GPT-4o' }, { id: 'anthropic/claude-3.5-sonnet', label: 'Claude 3.5 Sonnet' }], defaultModel: 'openai/gpt-4o' },
];

function getInitialTheme() {
  try { return localStorage.getItem('vibe-theme') || 'dark'; } catch { return 'dark'; }
}

// ── Conversation ──────────────────────────────────────────────────────────

function Conversation({ messages }) {
  const scrollRef = useRef(null);
  useEffect(() => { if (scrollRef.current) scrollRef.current.scrollTop = scrollRef.current.scrollHeight; }, [messages]);
  return (
    <div ref={scrollRef} style={{ flex: 1, overflowY: 'auto', padding: '10px', WebkitOverflowScrolling: 'touch' }}>
      {messages.length === 0 && (
        <div style={{ textAlign: 'center', color: 'var(--text3)', marginTop: '60px' }}>
          <div style={{ fontSize: '36px', marginBottom: '8px' }}>🎙️</div>
          <p style={{ fontSize: '15px' }}>Start speaking</p>
          <p style={{ fontSize: '12px', marginTop: '4px' }}>The AI will respond with voice</p>
        </div>
      )}
      {messages.map(msg => (
        <div key={msg.id} style={{ marginBottom: '8px', display: 'flow-root' }}>
          <div style={{
            float: msg.role === 'user' ? 'right' : 'left',
            maxWidth: '85%', padding: '10px 14px',
            borderRadius: '14px',
            background: msg.role === 'user' ? 'var(--accent)' : 'var(--card-bg)',
            border: msg.role === 'assistant' ? '1px solid var(--border)' : 'none',
            color: msg.role === 'user' ? '#fff' : 'var(--text)',
          }}>
            <div style={{ fontSize: '11px', opacity: 0.7, marginBottom: '4px' }}>
              {msg.role === 'user' ? 'You' : 'AI'}
            </div>
            <div style={{ fontSize: '14px', lineHeight: 1.5 }}>{msg.text}</div>
            {msg.code && (
              <pre style={{ marginTop: '8px', padding: '8px', background: 'var(--code-bg)', borderRadius: '8px', fontSize: '10px', overflowX: 'auto', border: '1px solid var(--border)' }}>{msg.code}</pre>
            )}
          </div>
        </div>
      ))}
    </div>
  );
}

// ── Code View ─────────────────────────────────────────────────────────────

function CodeView({ messages }) {
  const codeMsgs = messages.filter(m => m.code);
  if (!codeMsgs.length) {
    return <div style={{ padding: '20px', textAlign: 'center', color: 'var(--text3)', fontSize: '13px' }}>No code generated yet</div>;
  }
  const latest = codeMsgs[codeMsgs.length - 1];
  return (
    <div style={{ padding: '12px', overflowY: 'auto', WebkitOverflowScrolling: 'touch' }}>
      <div style={{ fontSize: '11px', color: 'var(--text2)', marginBottom: '8px', textTransform: 'uppercase' }}>Latest Code</div>
      <pre style={{ fontSize: '11px', lineHeight: 1.5, whiteSpace: 'pre-wrap', fontFamily: 'monospace' }}>{latest.code}</pre>
      {latest.codeResult && <div style={{ marginTop: '8px', fontSize: '12px', color: 'var(--success)' }}>→ {latest.codeResult}</div>}
    </div>
  );
}

// ── Room UI (mobile-first with tabs) ──────────────────────────────────────

function RoomUI({ token, llmConfig, onLeave }) {
  const [messages, setMessages] = useState([]);
  const [tab, setTab] = useState('chat');
  const addMessage = useCallback((msg) => setMessages(p => [...p, { id: Date.now().toString() + Math.random(), ...msg }]), []);

  function VoiceBridge() {
    const { agentTranscript, userTranscript } = useVoiceAssistant();
    const lastA = useRef(''); const lastU = useRef('');
    useEffect(() => { if (agentTranscript && agentTranscript !== lastA.current) { lastA.current = agentTranscript; addMessage({ role: 'assistant', text: agentTranscript }); } }, [agentTranscript]);
    useEffect(() => { if (userTranscript && userTranscript !== lastU.current) { lastU.current = userTranscript; addMessage({ role: 'user', text: userTranscript }); } }, [userTranscript]);
    return null;
  }

  return (
    <LiveKitRoom
      token={token} serverUrl={LIVEKIT_URL} connect={true}
      onDisconnected={() => addMessage({ role: 'system', text: 'Disconnected' })}
      style={{ display: 'flex', flexDirection: 'column', height: '100%', background: 'var(--bg)' }}
      onConnected={(room) => { room.localParticipant.setMetadata(JSON.stringify(llmConfig)); }}
    >
      <RoomAudioRenderer />
      <VoiceBridge />

      {/* Header — compact for mobile */}
      <header style={{
        padding: '8px 12px', borderBottom: '1px solid var(--border)',
        display: 'flex', justifyContent: 'space-between', alignItems: 'center',
        background: 'var(--header-bg)', flexShrink: 0,
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <span style={{ fontSize: '18px' }}>🎙️</span>
          <span style={{ fontSize: '14px', fontWeight: 600 }}>Vibe</span>
        </div>
        <div style={{ display: 'flex', gap: '6px', alignItems: 'center' }}>
          <span style={{ fontSize: '9px', color: 'var(--text2)', background: 'var(--bg3)', padding: '2px 6px', borderRadius: '4px', maxWidth: '100px', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
            {llmConfig.model}
          </span>
          <span style={{ fontSize: '9px', color: 'var(--success)' }}>●</span>
          <button onClick={onLeave} style={{ padding: '2px 8px', borderRadius: '6px', border: '1px solid var(--border)', background: 'transparent', color: 'var(--text2)', fontSize: '11px', cursor: 'pointer' }}>✕</button>
        </div>
      </header>

      {/* Tab bar */}
      <div style={{ display: 'flex', borderBottom: '1px solid var(--border)', background: 'var(--bg)', flexShrink: 0 }}>
        {['chat', 'code', 'config'].map(t => (
          <button key={t} onClick={() => setTab(t)} style={{
            flex: 1, padding: '10px', border: 'none', background: tab === t ? 'var(--accent)' : 'transparent',
            color: tab === t ? '#fff' : 'var(--text2)', fontSize: '13px', fontWeight: tab === t ? 600 : 400,
            cursor: 'pointer', transition: 'background 0.15s',
          }}>
            {t === 'chat' ? '💬 Chat' : t === 'code' ? '📄 Code' : '⚙️ Model'}
          </button>
        ))}
      </div>

      {/* Content */}
      <div style={{ flex: 1, overflow: 'hidden' }}>
        {tab === 'chat' && <Conversation messages={messages} />}
        {tab === 'code' && <CodeView messages={messages} />}
        {tab === 'config' && (
          <div style={{ padding: '16px', color: 'var(--text2)', fontSize: '13px' }}>
            <p><strong>LLM:</strong> {llmConfig.provider} / {llmConfig.model}</p>
            <p style={{ marginTop: '8px' }}><strong>STT:</strong> Deepgram Nova-3</p>
            <p style={{ marginTop: '4px' }}><strong>TTS:</strong> Kokoro (Chutes)</p>
            <p style={{ marginTop: '4px' }}><strong>Code:</strong> OpenCode</p>
          </div>
        )}
      </div>

      {/* Status bar */}
      <div style={{
        padding: '6px 12px', borderTop: '1px solid var(--border)',
        fontSize: '10px', color: 'var(--text3)', display: 'flex', justifyContent: 'space-around', flexShrink: 0,
      }}>
        <span>🎤 Speak</span>
        <span>✋ Interrupt</span>
        <span>🔊 AI responds</span>
      </div>
    </LiveKitRoom>
  );
}

async function fetchToken(roomName, identity) {
  const resp = await fetch(`${TOKEN_URL}?room=${encodeURIComponent(roomName)}&identity=${encodeURIComponent(identity)}`);
  if (!resp.ok) throw new Error(`Token server error: ${resp.status}`);
  return (await resp.json()).token;
}

// ── Login ─────────────────────────────────────────────────────────────────

function Login({ onJoin }) {
  const [roomName, setRoomName] = useState('vibe');
  const [provider, setProvider] = useState(LLM_PROVIDERS[0].id);
  const [model, setModel] = useState(LLM_PROVIDERS[0].defaultModel);
  const [theme, setTheme] = useState(getInitialTheme);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  const prov = LLM_PROVIDERS.find(p => p.id === provider) || LLM_PROVIDERS[0];

  useEffect(() => { document.documentElement.setAttribute('data-theme', theme); try { localStorage.setItem('vibe-theme', theme); } catch {} }, [theme]);
  useEffect(() => { setModel(prov.defaultModel); }, [provider]);

  const handleJoin = async () => {
    setLoading(true); setError('');
    try {
      const identity = `user-${Math.random().toString(36).slice(2, 8)}`;
      const token = await fetchToken(`${roomName}--${identity}`, identity);
      onJoin(token, { provider, model });
    } catch (e) { setError(e.message || 'Connection failed'); }
    finally { setLoading(false); }
  };

  return (
    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: '100%', padding: '16px', background: 'var(--bg)' }}>
      <div style={{ width: '100%', maxWidth: '360px', display: 'flex', flexDirection: 'column', gap: '14px' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
          <div>
            <div style={{ fontSize: '36px' }}>🎙️</div>
            <h1 style={{ fontSize: '22px', fontWeight: 700, color: 'var(--text)', marginTop: '4px' }}>Vibe Coding</h1>
            <p style={{ fontSize: '13px', color: 'var(--text2)', marginTop: '4px' }}>Speak to build software with AI</p>
          </div>
          <button onClick={() => setTheme(t => t === 'dark' ? 'light' : 'dark')} style={{ background: 'none', border: 'none', fontSize: '22px', cursor: 'pointer', padding: '4px' }}>
            {theme === 'dark' ? '☀️' : '🌙'}
          </button>
        </div>

        <input value={roomName} onChange={e => setRoomName(e.target.value)} placeholder="Room name"
          style={{ padding: '12px 14px', borderRadius: '10px', border: '1px solid var(--border)', background: 'var(--input-bg)', color: 'var(--text)', fontSize: '15px', width: '100%', outline: 'none' }} />

        <div>
          <label style={{ fontSize: '12px', color: 'var(--text2)', marginBottom: '4px', display: 'block' }}>Provider</label>
          <select value={provider} onChange={e => setProvider(e.target.value)} style={{ padding: '12px 14px', borderRadius: '10px', border: '1px solid var(--border)', background: 'var(--input-bg)', color: 'var(--text)', fontSize: '15px', width: '100%', outline: 'none', cursor: 'pointer' }}>
            {LLM_PROVIDERS.map(p => <option key={p.id} value={p.id}>{p.label}</option>)}
          </select>
        </div>

        <div>
          <label style={{ fontSize: '12px', color: 'var(--text2)', marginBottom: '4px', display: 'block' }}>Model</label>
          <select value={model} onChange={e => setModel(e.target.value)} style={{ padding: '12px 14px', borderRadius: '10px', border: '1px solid var(--border)', background: 'var(--input-bg)', color: 'var(--text)', fontSize: '15px', width: '100%', outline: 'none', cursor: 'pointer' }}>
            {prov.models.map(m => <option key={m.id} value={m.id}>{m.label}</option>)}
          </select>
        </div>

        {error && <div style={{ fontSize: '12px', color: 'var(--error)', textAlign: 'center' }}>{error}</div>}

        <button onClick={handleJoin} disabled={loading} style={{
          padding: '14px', borderRadius: '10px', border: 'none', background: loading ? 'var(--accent2)' : 'var(--accent)',
          color: '#fff', fontSize: '16px', fontWeight: 600, cursor: loading ? 'default' : 'pointer',
        }}>
          {loading ? 'Connecting...' : 'Start Coding'}
        </button>
      </div>
    </div>
  );
}

function App() {
  const [token, setToken] = useState(null);
  const [llmConfig, setLlmConfig] = useState(null);
  if (token) return <RoomUI token={token} llmConfig={llmConfig} onLeave={() => { setToken(null); setLlmConfig(null); }} />;
  return <Login onJoin={(tok, cfg) => { setToken(tok); setLlmConfig(cfg); }} />;
}

createRoot(document.getElementById('root')).render(
  <ErrorBoundary fallback={<div style={{padding:20,color:'var(--error)'}}>Something went wrong. Check console.</div>}>
    <App />
  </ErrorBoundary>
);
