import { useEffect, useRef, useState } from 'react';

const LOADING_TIMEOUT = 10000;

export default function StreamPlayer({ socket, channelId, compact = false }) {
  const imgRef = useRef(null);
  const [fps, setFps] = useState(0);
  const [statusText, setStatusText] = useState('🟡 Conectando...');
  const [statusClass, setStatusClass] = useState('connecting');
  const [hasFrame, setHasFrame] = useState(false);
  const [stuck, setStuck] = useState(false);
  const [subtitle, setSubtitle] = useState('');
  const [showSubtitles, setShowSubtitles] = useState(true);
  const [stats, setStats] = useState(null);
  const [showStats, setShowStats] = useState(false);
  const [aiStatus, setAiStatus] = useState(null); // null = unknown, true = connected, false = error
  const [voices, setVoices] = useState([]);
  const [selectedVoice, setSelectedVoice] = useState(null);
  const [showVoicePicker, setShowVoicePicker] = useState(false);
  const fpsCount = useRef(0);
  const lastFrameTime = useRef(0);
  const stuckTimer = useRef(null);
  const speechSynth = useRef(null);
  const ttsEnabled = useRef(false);
  const [, forceUpdate] = useState(0);

  // ─── Cargar voces disponibles ─────────────────────────────────────
  useEffect(() => {
    if (typeof window === 'undefined' || !window.speechSynthesis) return;
    speechSynth.current = window.speechSynthesis;

    function loadVoices() {
      const v = speechSynth.current.getVoices();
      if (v.length > 0) {
        // Group by language and pick default per language
        const langs = {};
        v.forEach(voice => {
          const lang = voice.lang.split('-')[0]; // "es-MX" → "es"
          if (!langs[lang]) langs[lang] = [];
          langs[lang].push(voice);
        });
        setVoices(v);
        // Auto-select Spanish voice if available
        const spanish = v.find(vc => vc.lang.startsWith('es'));
        if (spanish) setSelectedVoice(spanish.voiceURI);
        else if (v.length > 0) setSelectedVoice(v[0].voiceURI);
      }
    }
    loadVoices();
    // Chrome loads voices async
    if (speechSynth.current.onvoiceschanged !== undefined) {
      speechSynth.current.onvoiceschanged = loadVoices;
    }
  }, []);

  // ─── TTS function (no state, reads from ref) ────────────────────
  function speak(text) {
    if (!ttsEnabled.current || !speechSynth.current) return;
    try {
      speechSynth.current.cancel();
      const utterance = new SpeechSynthesisUtterance(text);
      utterance.rate = 0.9;
      // Prefer selected voice, fallback to Spanish, then any
      const selected = voices.find(v => v.voiceURI === selectedVoice);
      if (selected) utterance.voice = selected;
      else {
        const spanish = voices.find(v => v.lang.startsWith('es'));
        if (spanish) utterance.voice = spanish;
      }
      speechSynth.current.speak(utterance);
    } catch (e) { /* ignore TTS errors */ }
  }

  function toggleTTS() {
    ttsEnabled.current = !ttsEnabled.current;
    forceUpdate(n => n + 1); // re-render button only
    if (!ttsEnabled.current && speechSynth.current) {
      speechSynth.current.cancel();
    }
  }

  // ─── Main effect (NO ttsEnabled dependency) ──────────────────────
  useEffect(() => {
    if (!socket) return;

    setStatusText('🟡 Conectando...');
    setStatusClass('connecting');
    setHasFrame(false);
    setStuck(false);

    const fpsInterval = setInterval(() => {
      setFps(fpsCount.current);
      fpsCount.current = 0;
    }, 1000);

    const startTime = Date.now();
    stuckTimer.current = setInterval(() => {
      if (!hasFrame && Date.now() - startTime > LOADING_TIMEOUT) {
        setStuck(true);
        setStatusText('🔴 Sin señal — el agente no está transmitiendo');
        setStatusClass('ended');
        const sendError = window.__sendError;
        if (sendError) sendError('Stream stuck: no frames for 10s', '', window.location.href);
      }
    }, 2000);

    socket.on('stream:frame', ({ channelId: cid, frame }) => {
      if (cid !== channelId) return;
      if (imgRef.current) {
        imgRef.current.src = `data:image/jpeg;base64,${frame}`;
      }
      if (!hasFrame) {
        setHasFrame(true);
        setStuck(false);
        clearInterval(stuckTimer.current);
      }
      fpsCount.current++;
      lastFrameTime.current = Date.now();
      setStatusText('🔴 EN VIVO');
      setStatusClass('live');
    });

    socket.on('stream:ended', ({ channelId: cid }) => {
      if (cid === channelId) {
        setStatusText('🔴 Transmisión finalizada');
        setStatusClass('ended');
        setStuck(true);
      }
    });

    socket.on('agent:status', ({ channelId: cid, status }) => {
      if (cid !== channelId) return;
      // Only show "EN VIVO" — navigation status goes to subtitles
      setStatusText(status === 'live' ? '🔴 EN VIVO' : status === 'ended' ? '🔴 Finalizado' : '🔴 EN VIVO');
      setStatusClass(status);
    });

    socket.on('agent:narrate', ({ channelId: cid, text }) => {
      if (cid !== channelId) return;
      setSubtitle(text);
      speak(text);
      setTimeout(() => setSubtitle(prev => prev === text ? '' : prev), 8000);
    });

    socket.on('agent:stats', ({ channelId: cid, stats: s }) => {
      if (cid !== channelId) return;
      setStats(s);
    });

    // AI connection status
    socket.on('agent:ai-status', ({ channelId: cid, connected, provider, model }) => {
      if (cid !== channelId) return;
      setAiStatus({ connected, provider, model });
    });

    return () => {
      clearInterval(fpsInterval);
      clearInterval(stuckTimer.current);
      socket.off('stream:frame');
      socket.off('stream:ended');
      socket.off('agent:status');
      socket.off('agent:narrate');
      socket.off('agent:stats');
      socket.off('agent:ai-status');
      if (speechSynth.current) speechSynth.current.cancel();
    };
  }, [socket, channelId]); // ← ttsEnabled removed! No re-render on toggle

  // ─── Group voices by language for the picker ────────────────────
  const voicesByLang = {};
  voices.forEach(v => {
    const lang = v.lang || 'unknown';
    if (!voicesByLang[lang]) voicesByLang[lang] = [];
    voicesByLang[lang].push(v);
  });
  const selectedVoiceObj = voices.find(v => v.voiceURI === selectedVoice);
  const selectedLang = selectedVoiceObj ? selectedVoiceObj.lang : '';
  const sortedLangs = Object.keys(voicesByLang).sort((a, b) => {
    if (a === selectedLang) return -1;
    if (b === selectedLang) return 1;
    return a.localeCompare(b);
  });

  return (
    <div className={`stream-player ${compact ? 'compact' : ''} ${hasFrame ? 'has-frame' : 'no-frame'}`}>
      {!hasFrame && !stuck && (
        <div className="stream-loading">
          <div className="stream-loading-spinner"></div>
          <span>Esperando señal del agente...</span>
          <span className="stream-loading-hint">El agente está iniciando su navegador</span>
        </div>
      )}
      {!hasFrame && stuck && (
        <div className="stream-loading stream-error">
          <span className="stream-error-icon">📡</span>
          <span>Sin conexión con el agente</span>
          <span className="stream-loading-hint">El agente puede haber crasheado o no existe</span>
        </div>
      )}
      <img
        ref={imgRef}
        className="stream-img"
        alt="Agent stream"
        style={{ display: hasFrame ? 'block' : 'none' }}
      />

      {/* Subtítulos de narración */}
      {subtitle && showSubtitles && (
        <div className="stream-subtitle">
          <span className="subtitle-text">{subtitle}</span>
        </div>
      )}

      {!compact && (
        <div className="stream-overlay">
          <div style={{display:'flex',alignItems:'center',gap:'6px'}}>
            <span className="fps-counter">{fps} FPS</span>
            <span className={`status ${statusClass}`}>{statusText}</span>
            {aiStatus && (
              <span className="fps-counter" style={{color: aiStatus.connected ? '#30d158' : '#ff9f0a', fontSize:'0.65rem'}}>
                {aiStatus.connected ? `🤖 ${aiStatus.model}` : '🤖 Sin conexión'}
              </span>
            )}
          </div>
          <div className="overlay-buttons">
            <button className="overlay-btn"
              onClick={toggleTTS} title={ttsEnabled.current ? 'Desactivar voz' : 'Activar voz'}>
              {ttsEnabled.current ? '🔊' : '🔇'}
            </button>
            <button className="overlay-btn"
              onClick={() => setShowSubtitles(!showSubtitles)} title={showSubtitles ? 'Ocultar subtítulos' : 'Mostrar subtítulos'}>
              {showSubtitles ? '📝' : '📵'}
            </button>
            {voices.length > 0 && (
              <button className="overlay-btn" style={{width:'auto',padding:'0 6px',fontSize:'0.65rem'}}
                onClick={() => setShowVoicePicker(!showVoicePicker)} title="Seleccionar voz">
                {selectedLang || '🎤'}
              </button>
            )}
            <button className={`overlay-btn ${showStats ? 'active' : ''}`}
              onClick={() => {
                setShowStats(!showStats);
                if (socket) socket.emit('chat:message', { channelId, text: '!stats' });
              }} title="Estadísticas">
              📊
            </button>
          </div>
        </div>
      )}

      {/* Voice picker panel */}
      {showVoicePicker && voices.length > 0 && (
        <div className="voice-panel" onClick={e => e.stopPropagation()}>
          <div className="voice-panel-header">
            <span>Seleccionar voz</span>
            <button className="voice-close" onClick={() => setShowVoicePicker(false)}>✕</button>
          </div>
          <div className="voice-list">
            {sortedLangs.map(lang => (
              <div key={lang} className="voice-lang-group">
                <div className="voice-lang-label">{lang}</div>
                {voicesByLang[lang].map((v, i) => (
                  <div key={i}
                    className={`voice-option ${selectedVoice === v.voiceURI ? 'active' : ''}`}
                    onClick={() => { setSelectedVoice(v.voiceURI); setShowVoicePicker(false); }}>
                    <span>{v.name.replace(/(Microsoft|Google|Mozilla)\s*/g, '')}</span>
                    <span className="voice-lang-tag">{v.lang}</span>
                  </div>
                ))}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Stats panel */}
      {showStats && (
        <div className="stats-panel">
          {!stats ? (
            <div className="stats-row" style={{justifyContent:'center'}}>⏳ Esperando datos del agente...</div>
          ) : (
            <>
              <div className="stats-row"><span>⏱️ Activo</span><span>{Math.floor(stats.uptime / 60)}m {stats.uptime % 60}s</span></div>
              <div className="stats-row"><span>🧠 RSS</span><span>{stats.memoryRss} MB</span></div>
              <div className="stats-row"><span>💾 Heap</span><span>{stats.memoryHeap} MB</span></div>
              <div className="stats-row"><span>⚡ CPU load</span><span>{stats.cpuLoad}</span></div>
              <div className="stats-row"><span>📡 Frames</span><span>{stats.frames}</span></div>
              <div className="stats-row"><span>🤖 API calls</span><span>{stats.apiCalls}</span></div>
              {aiStatus && (
                <div className="stats-row" style={{borderTop:'1px solid rgba(255,255,255,0.1)', marginTop:4, paddingTop:4}}>
                  <span>🧠 IA</span>
                  <span style={{color: aiStatus.connected ? '#30d158' : '#ff9f0a', fontSize:'0.7rem'}}>
                    {aiStatus.connected ? `✅ ${aiStatus.provider}/${aiStatus.model}` : '⚠️ Desconectada'}
                  </span>
                </div>
              )}
              <div className="stats-row"><span>🖥️ {stats.platform}</span><span>{stats.nodeVersion}</span></div>
            </>
          )}
        </div>
      )}
    </div>
  );
}
