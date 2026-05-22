import { useState, useEffect, useCallback } from 'react';
import { Link } from 'react-router-dom';

export default function Browse() {
  const [channels, setChannels] = useState([]);
  const [agentTypes, setAgentTypes] = useState([]);
  const [loading, setLoading] = useState(true);

  const fetchData = useCallback(async () => {
    try {
      const [chRes, typesRes] = await Promise.all([
        fetch('/api/channels'),
        fetch('/api/agents/types'),
      ]);
      setChannels(await chRes.json());
      setAgentTypes(await typesRes.json());
      setLoading(false);
    } catch {}
  }, []);

  useEffect(() => {
    fetchData();
    const interval = setInterval(fetchData, 3000);
    return () => clearInterval(interval);
  }, [fetchData]);

  async function spawnAgent(typeId) {
    await fetch(`/api/agents/spawn?type=${typeId}`, { method: 'POST' });
    setTimeout(fetchData, 1500);
  }

  async function stopAgent(id, e) {
    e.preventDefault();
    e.stopPropagation();
    await fetch(`/api/agents/${id}/stop`, { method: 'POST' });
    setTimeout(fetchData, 500);
  }

  const liveCount = channels.filter(c => c.status === 'live').length;
  const hasChannels = channels.length > 0;

  return (
    <div className="browse">
      <div className="browse-header">
        <h2>{loading ? 'Cargando...' : `🔴 Canales en Vivo (${liveCount})`}</h2>
        {hasChannels && channels.length > 1 && (
          <button className="kill-all-btn" onClick={async () => {
            await Promise.all(channels.map(c => fetch(`/api/agents/${c.id}/stop`, { method: 'POST' })));
            setTimeout(fetchData, 1000);
          }}>
            🛑 Matar Todos
          </button>
        )}
      </div>

      <div className="channel-grid">
        {!hasChannels && !loading && (
          <div className="no-channels">
            <p style={{ fontSize: '1.1rem', marginBottom: 8 }}>No hay canales activos</p>
            <p style={{ fontSize: '0.85rem', color: 'var(--text-secondary)' }}>
              Inicia un agente abajo para comenzar a transmitir
            </p>
          </div>
        )}

        {channels.map(ch => (
          <div key={ch.id} className="channel-card-wrapper">
            <Link to={`/watch/${ch.id}`} className="channel-card">
              <div className="channel-card-header">
                <span className="live-badge">
                  {ch.status === 'live' ? 'EN VIVO' : ch.status.toUpperCase()}
                </span>
                <span className="agent-type">{ch.agentType}</span>
              </div>
              <div className="channel-card-body">
                <h3>{ch.name}</h3>
                <p>{ch.frameCount > 0 ? `📡 ${ch.frameCount} frames` : '⏳ Iniciando...'}</p>
                <p className="channel-time">{new Date(ch.startedAt).toLocaleTimeString()}</p>
                {/* Resource usage */}
                <p className="channel-resource">PID: {ch.id.slice(-6)}</p>
              </div>
            </Link>
            <button className="stop-btn" onClick={(e) => stopAgent(ch.id, e)} title="Detener agente">
              ✕
            </button>
          </div>
        ))}
      </div>

      <div className="spawn-section">
        <h3>🚀 Iniciar Nuevo Agente</h3>
        <p className="spawn-hint">
          Los agentes usan ~200-400MB RAM cada uno. No inicies más de 2-3 simultáneos.
        </p>
        <div className="spawn-buttons">
          {agentTypes.map(t => (
            <button key={t.id} onClick={() => spawnAgent(t.id)} title={t.description}>
              {t.icon} {t.name}
            </button>
          ))}
        </div>
      </div>
    </div>
  );
}
