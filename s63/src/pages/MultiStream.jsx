import { useState, useEffect, useRef } from 'react';
import { Link } from 'react-router-dom';
import StreamPlayer from '../components/StreamPlayer';

export default function MultiStream() {
  const [channels, setChannels] = useState([]);
  const [selected, setSelected] = useState([]);
  const [sockets, setSockets] = useState({});
  const socketsRef = useRef({});

  useEffect(() => {
    const fetchChannels = () => {
      fetch('/api/channels')
        .then(r => r.json())
        .then(list => setChannels(list))
        .catch(() => {});
    };
    fetchChannels();
    const interval = setInterval(fetchChannels, 3000);
    return () => clearInterval(interval);
  }, []);

  // Create/destroy sockets as selection changes
  useEffect(() => {
    const currentSockets = { ...socketsRef.current };
    const sysSocket = window.__systemSocket;
    if (!sysSocket) return;

    selected.forEach((chId) => {
      if (!currentSockets[chId]) {
        sysSocket.emit('join:channel', { channelId: chId });
        currentSockets[chId] = sysSocket;
        setSockets(prev => ({ ...prev, [chId]: sysSocket }));
      }
    });

    // Cleanup deselected — leave channel
    Object.entries(currentSockets).forEach(([chId, s]) => {
      if (!selected.includes(chId)) {
        sysSocket.emit('leave:channel', { channelId: chId });
        delete currentSockets[chId];
        setSockets(prev => {
          const next = { ...prev };
          delete next[chId];
          return next;
        });
      }
    });

    // Cleanup deselected
    Object.entries(currentSockets).forEach(([chId, s]) => {
      if (!selected.includes(chId)) {
        sysSocket.emit('leave:channel', { channelId: chId });
        delete currentSockets[chId];
        setSockets(prev => {
          const next = { ...prev };
          delete next[chId];
          return next;
        });
      }
    });

    socketsRef.current = currentSockets;
  }, [selected]);

  useEffect(() => {
    return () => {
      const sys = window.__systemSocket;
      if (sys) Object.keys(socketsRef.current).forEach(chId => sys.emit('leave:channel', { channelId: chId }));
    };
  }, []);

  function toggleChannel(chId) {
    setSelected(prev => {
      if (prev.includes(chId)) return prev.filter(id => id !== chId);
      if (prev.length >= 4) return prev;
      return [...prev, chId];
    });
  }

  function stopAgent(id) {
    fetch(`/api/agents/${id}/stop`, { method: 'POST' });
    setSelected(prev => prev.filter(chId => chId !== id));
  }

  const gridClass = selected.length <= 1 ? 'multi-1col'
    : selected.length === 2 ? 'multi-2col'
    : 'multi-2x2';

  const liveChannels = channels.filter(ch => ch.status === 'live' && !ch.ended);

  return (
    <div className="multi-stream">
      <div className="multi-header">
        <h2>🖥️ Multi-Stream</h2>
        <div className="multi-controls">
          <Link to="/" className="back-link">← Canales</Link>
          <span className="selected-count">{selected.length}/4</span>
        </div>
      </div>

      <div className="multi-channel-selector">
        <span>Selecciona hasta 4 canales:</span>
        <div className="multi-selector-list">
          {liveChannels.map(ch => (
            <button
              key={ch.id}
              className={`multi-select-btn ${selected.includes(ch.id) ? 'active' : ''}`}
              onClick={() => toggleChannel(ch.id)}
            >
              {ch.name}
            </button>
          ))}
          {liveChannels.length === 0 && (
            <span style={{ color: 'var(--text-secondary)', fontSize: '0.85rem' }}>
              No hay canales en vivo — inicia agentes desde la página de canales
            </span>
          )}
        </div>
      </div>

      <div className={`multi-grid ${gridClass}`}>
        {selected.length === 0 ? (
          <div className="multi-empty">
            <div>
              <p style={{ fontSize: '1.1rem', marginBottom: 8 }}>🖥️ Multi-Stream</p>
              <p style={{ color: 'var(--text-secondary)' }}>
                Selecciona canales arriba para ver múltiples streams a la vez
              </p>
              {liveChannels.length === 0 && (
                <Link to="/" style={{ display: 'block', marginTop: 16, color: 'var(--accent)' }}>
                  → Ir a canales para iniciar agentes
                </Link>
              )}
            </div>
          </div>
        ) : (
          selected.map(chId => {
            const ch = channels.find(c => c.id === chId);
            return (
              <div key={chId} className="multi-player-wrapper">
                <div className="multi-player-header">
                  <span>{ch?.name || '...'}</span>
                  <div className="multi-player-actions">
                    <Link to={`/watch/${chId}`} className="multi-expand" title="Abrir en pantalla completa">⛶</Link>
                    <button className="multi-kill" onClick={() => stopAgent(chId)} title="Detener">✕</button>
                  </div>
                </div>
                <div className="multi-player">
                  {sockets[chId] ? (
                    <StreamPlayer socket={sockets[chId]} channelId={chId} compact />
                  ) : (
                    <div className="multi-loading">Conectando...</div>
                  )}
                </div>
              </div>
            );
          })
        )}
      </div>
    </div>
  );
}
