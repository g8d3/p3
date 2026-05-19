import { useEffect, useState } from 'react';
import { useParams, Link, useNavigate } from 'react-router-dom';
import StreamPlayer from '../components/StreamPlayer';
import Chat from '../components/Chat';

export default function Watch() {
  const { channelId } = useParams();
  const navigate = useNavigate();
  const [socket, setSocket] = useState(null);
  const [ended, setEnded] = useState(false);
  const [channel, setChannel] = useState(null);

  useEffect(() => {
    // Use the system socket instead of creating a new one
    // This avoids React StrictMode double-mount issues in dev
    const s = window.__systemSocket;
    if (!s || !s.emit) return;
    
    console.log('[Watch] Joining channel via system socket:', channelId);
    setSocket(s);

    // Always listen for connect AND emit immediately if already connected
    // This handles both initial mount and reconnections after network loss
    const onConnect = () => {
      s.emit('join:channel', { channelId });
    };
    s.on('connect', onConnect);
    if (s.connected) onConnect();

    s.on('stream:ended', ({ channelId: cid }) => {
      if (cid === channelId) setEnded(true);
    });

    return () => {
      s.off('connect', onConnect);
      s.emit('leave:channel', { channelId });
    };
  }, [channelId]);

  useEffect(() => {
    const fetchChannels = () => {
      fetch('/api/channels')
        .then(r => r.json())
        .then(list => {
          const ch = list.find(c => c.id === channelId);
          if (ch) setChannel(ch);
          else setEnded(true);
        })
        .catch(() => {});
    };
    fetchChannels();
    const interval = setInterval(fetchChannels, 3000);
    return () => clearInterval(interval);
  }, [channelId]);

  async function stopAgent() {
    await fetch(`/api/agents/${channelId}/stop`, { method: 'POST' });
    navigate('/');
  }

  if (ended) {
    return (
      <div className="watch-ended" style={{ textAlign: 'center', padding: 60 }}>
        <h2>🔴 Transmisión finalizada</h2>
        <p style={{ marginTop: 12, color: 'var(--text-secondary)' }}>El agente ya no está transmitiendo</p>
        <Link to="/" style={{ display: 'inline-block', marginTop: 20, color: 'var(--accent)' }}>← Volver a canales</Link>
      </div>
    );
  }

  if (!socket) {
    return <div style={{ padding: 40, textAlign: 'center', color: 'var(--text-secondary)' }}>Conectando...</div>;
  }

  return (
    <div className="watch">
      <div className="stream-container">
        <div className="stream-top-bar">
          <Link to="/" className="back-link">← Canales</Link>
          <span className="stream-title">{channel?.name || 'Cargando...'}</span>
          <button className="stop-btn" onClick={stopAgent} title="Detener y cerrar">🛑 Detener</button>
        </div>
        <StreamPlayer socket={socket} channelId={channelId} />
      </div>
      <div className="watch-sidebar">
        <Chat socket={socket} channelId={channelId} />
      </div>
    </div>
  );
}
