import { useState, useEffect, useCallback } from 'react';
import { Link } from 'react-router-dom';

const SEVERITY_COLORS = { critical: '#ff3b30', error: '#ff9f0a', warning: '#ffcc00', info: '#30d158' };
const STATUS_COLORS = { open: '#ff9f0a', fixing: '#58a6ff', fix_ready: '#4ec9b0', needs_review: '#daa520', resolved: '#30d158', ignored: '#8b949e' };

function timeAgo(ts) {
  const secs = Math.floor((Date.now() - ts) / 1000);
  if (secs < 60) return `${secs}s`;
  if (secs < 3600) return `${Math.floor(secs/60)}m`;
  if (secs < 86400) return `${Math.floor(secs/3600)}h`;
  return `${Math.floor(secs/86400)}d`;
}

function formatDate(ts) {
  const d = new Date(ts);
  return d.toLocaleString('es-ES', {
    day: '2-digit', month: '2-digit', year: 'numeric',
    hour: '2-digit', minute: '2-digit', second: '2-digit'
  });
}

export default function Errors() {
  const [errors, setErrors] = useState([]);
  const [tasks, setTasks] = useState([]);
  const [selectedError, setSelectedError] = useState(null);
  const [filter, setFilter] = useState('all');
  const [connected, setConnected] = useState(false);
  const [socket, setSocket] = useState(null);
  const [page, setPage] = useState(1);
  const PER_PAGE = 50;

  // ── Connect via system WebSocket for real-time updates ──────────
  useEffect(() => {
    const sysSocket = window.__systemSocket;
    if (!sysSocket) return;

    setSocket(sysSocket);

    function onConnect() {
      setConnected(true);
      sysSocket.emit('errors:subscribe');
    }

    function onDisconnect() {
      setConnected(false);
    }

    // Real-time error updates
    function onErrorUpdate({ type, error }) {
      if (type === 'new') {
        setErrors(prev => [error, ...prev]);
      }
    }

    // Real-time task updates
    function onTaskUpdate({ task }) {
      setTasks(prev => {
        const idx = prev.findIndex(t => t.id === task.id);
        if (idx >= 0) {
          const next = [...prev];
          next[idx] = task;
          return next;
        }
        return [...prev, task];
      });
    }

    // Initial state
    function onErrorState({ errors }) {
      if (errors) setErrors(errors);
    }
    function onTaskState({ tasks }) {
      if (tasks) setTasks(tasks);
    }

    if (sysSocket.connected) {
      onConnect();
    }

    sysSocket.on('connect', onConnect);
    sysSocket.on('disconnect', onDisconnect);
    sysSocket.on('errors:update', onErrorUpdate);
    sysSocket.on('task:update', onTaskUpdate);
    sysSocket.on('errors:state', onErrorState);
    sysSocket.on('tasks:state', onTaskState);

    // Fallback: poll every 5s if socket not connected
    const pollInterval = setInterval(() => {
      if (!sysSocket.connected) {
        fetchErrors();
      }
    }, 5000);

    return () => {
      sysSocket.emit('errors:unsubscribe');
      sysSocket.off('connect', onConnect);
      sysSocket.off('disconnect', onDisconnect);
      sysSocket.off('errors:update', onErrorUpdate);
      sysSocket.off('task:update', onTaskUpdate);
      sysSocket.off('errors:state', onErrorState);
      sysSocket.off('tasks:state', onTaskState);
      clearInterval(pollInterval);
    };
  }, []);

  // Fallback fetch
  const fetchErrors = useCallback(async () => {
    try {
      const [errRes, taskRes] = await Promise.all([
        fetch('/api/errors'),
        fetch('/api/tasks'),
      ]);
      setErrors(await errRes.json());
      setTasks(await taskRes.json());
    } catch {}
  }, []);

  const filtered = filter === 'all' ? errors : errors.filter(e => e.status === filter);
  const sorted = [...filtered].sort((a, b) => b.timestamp - a.timestamp);
  const paged = sorted.slice(0, page * PER_PAGE);
  const hasMore = paged.length < sorted.length;

  function setFilterAndPage(f) { setFilter(f); setPage(1); }
  const openCount = errors.filter(e => e.status === 'open').length;
  const fixingCount = errors.filter(e => ['fixing', 'fix_ready'].includes(e.status)).length;
  const reviewCount = errors.filter(e => e.status === 'needs_review').length;

  async function triggerFix(errorId) {
    await fetch(`/api/errors/${errorId}/fix`, { method: 'POST' });
  }

  async function ignoreError(errorId) {
    await fetch(`/api/errors/${errorId}/ignore`, { method: 'POST' });
    setErrors(prev => prev.map(e => e.id === errorId ? { ...e, status: 'ignored' } : e));
  }

  return (
    <div className="errors-page">
      <div className="errors-header">
        <div>
          <h2>📋 Centro de Errores {connected ? '🟢' : '🔴'}</h2>
          <p style={{ color: 'var(--text-secondary)', fontSize: '0.85rem' }}>
            {errors.length} total · {openCount} abiertos · {fixingCount} en fix · {reviewCount} revisión
            {!connected && ' · ⚠️ Sin conexión en vivo'}
          </p>
        </div>
        <div className="errors-actions">
          <button className="refresh-btn" onClick={fetchErrors}>↻ Recargar</button>
          <Link to="/" className="back-link">← Canales</Link>
        </div>
      </div>

      <div className="errors-summary">
        <div className="summary-card" onClick={() => setFilterAndPage('all')}>
          <strong>{errors.length}</strong> Total
        </div>
        <div className="summary-card warning" onClick={() => setFilterAndPage('open')}>
          <strong>{openCount}</strong> Abiertos
        </div>
        <div className="summary-card info" onClick={() => setFilterAndPage('fixing')}>
          <strong>{fixingCount}</strong> En fix
        </div>
        <div className="summary-card review" onClick={() => setFilterAndPage('needs_review')}>
          <strong>{reviewCount}</strong> Revisión
        </div>
        <div className="summary-card ok" onClick={() => setFilterAndPage('resolved')}>
          <strong>{errors.filter(e => e.status === 'resolved').length}</strong> Resueltos
        </div>
      </div>

      <div className="errors-list">
        {paged.length === 0 && (
          <div className="no-errors">
            <p>✅ No hay errores con este filtro</p>
          </div>
        )}
        {paged.map(err => (
          <div key={err.id} className={`error-card ${selectedError?.id === err.id ? 'selected' : ''}`}
            onClick={() => setSelectedError(selectedError?.id === err.id ? null : err)}
            style={err._new ? { animation: 'fade-in 0.3s ease', borderLeft: '3px solid var(--accent)' } : {}}>
            <div className="error-card-header">
              <span className="error-severity" style={{ background: SEVERITY_COLORS[err.severity] || '#888' }}>
                {err.severity}
              </span>
              <span className="error-status" style={{ color: STATUS_COLORS[err.status] || '#888' }}>
                {err.status}
              </span>
              <span className="error-time" title={formatDate(err.timestamp)}>
                {timeAgo(err.timestamp)}
                <span className="error-time-full">{formatDate(err.timestamp)}</span>
              </span>
              <div className="error-card-actions" onClick={e => e.stopPropagation()}>
                {(err.status === 'open' || err.status === 'fix_ready') && (
                  <button className="fix-btn" onClick={() => triggerFix(err.id)}>🔧 Fix</button>
                )}
                {err.status === 'needs_review' && <span className="review-badge">👀 Revisar</span>}
                <button className="ignore-btn" onClick={() => ignoreError(err.id)}>✕</button>
              </div>
            </div>
            <div className="error-card-body">
              <strong>{err.type}</strong>: {err.message}
            </div>
            {selectedError?.id === err.id && (
              <div className="error-detail">
                {err.stack && (
                  <div className="error-section"><h4>Stack Trace</h4><pre>{err.stack}</pre></div>
                )}
                {err.fixPlan && (
                  <div className="error-section">
                    <h4>Plan de Fix (IA)</h4>
                    <div className="fix-plan">
                      <p><strong>Causa:</strong> {err.fixPlan.rootCause}</p>
                      <p><strong>Estrategia:</strong> {err.fixPlan.fixStrategy}</p>
                      {err.fixPlan.filesToModify && <p><strong>Archivos:</strong> {err.fixPlan.filesToModify.join(', ')}</p>}
                      {err.fixPlan.fixCode && <><p><strong>Código:</strong></p><pre>{err.fixPlan.fixCode}</pre></>}
                    </div>
                  </div>
                )}
                <div className="error-section">
                  <h4>Contexto</h4>
                  <pre>{JSON.stringify(err.context || {}, null, 2)}</pre>
                </div>
              </div>
            )}
          </div>
        ))}
        {hasMore && (
          <div className="load-more" onClick={() => setPage(p => p + 1)}>
            📋 Mostrar más ({sorted.length - paged.length} restantes)
          </div>
        )}
      </div>

      {tasks.length > 0 && (
        <div className="tasks-section">
          <h3>📋 Cola de Tareas ({tasks.filter(t => t.status !== 'cancelled').length})</h3>
          {tasks.filter(t => t.status !== 'cancelled').reverse().map(task => (
            <div key={task.id} className="task-card">
              <span className="task-status" style={{ color: task.status === 'completed' ? '#30d158' : task.status === 'failed' ? '#ff3b30' : 'var(--accent)' }}>
                {task.status}
              </span>
              <span className="task-type">{task.type}</span>
              <span className="task-desc">{task.error?.message?.slice(0, 60) || task.id}</span>
              <span className="task-time">{timeAgo(task.createdAt)}</span>
            </div>
          ))}
        </div>
      )}

      <div className="errors-info">
        <p>🟢 <strong>Live:</strong> los errores nuevos aparecen automáticamente vía Socket.IO</p>
        <p>🔴 <strong>Fallback:</strong> si la conexión se pierde, se usa polling cada 5s</p>
        <p>💡 Los errores se registran en <code>errors.jsonl</code> aunque la página esté cerrada</p>
        <p>🔧 El Fix Agent analiza errores con IA (deepseek-v4-flash)</p>
      </div>
    </div>
  );
}
