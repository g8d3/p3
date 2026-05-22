import { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';

export default function Improvements() {
  const [content, setContent] = useState('');
  const [sections, setSections] = useState([]);

  useEffect(() => {
    // Fetch the IMPROVEMENTS.md file
    fetch('/IMPROVEMENTS.md')
      .then(r => r.text())
      .then(text => {
        setContent(text);
        // Parse sections
        const lines = text.split('\n');
        const parsed = [];
        let currentSection = null;

        for (const line of lines) {
          if (line.startsWith('## ')) {
            if (currentSection) parsed.push(currentSection);
            const title = line.replace('## ', '').trim();
            currentSection = { title, status: extractStatus(title), lines: [] };
          } else if (currentSection) {
            currentSection.lines.push(line);
          }
        }
        if (currentSection) parsed.push(currentSection);
        setSections(parsed);
      })
      .catch(() => {
        setContent('No se pudo cargar el archivo de mejoras.');
      });
  }, []);

  function extractStatus(title) {
    const t = title.toLowerCase();
    if (t.includes('rust')) return 'rust';
    if (t.includes('version') || t.includes('rollback') || t.includes('sandbox')) return 'versioning';
    if (t.includes('webrtc')) return 'webrtc';
    if (t.includes('ide')) return 'ide';
    if (t.includes('multi-idioma') || t.includes('multi')) return 'multi';
    return 'other';
  }

  const statusIcons = {
    rust: '🦀',
    versioning: '📦',
    webrtc: '📡',
    ide: '💻',
    multi: '🌍',
    other: '💡',
  };

  return (
    <div className="improvements-page">
      <div className="improvements-header">
        <div>
          <h2>🚀 Mejoras Potenciales</h2>
          <p style={{ color: 'var(--text-secondary)', fontSize: '0.85rem' }}>
            {sections.length} ideas registradas — ninguna en desarrollo activo
          </p>
        </div>
        <div className="improvements-actions">
          <Link to="/" className="back-link">← Canales</Link>
        </div>
      </div>

      <div className="improvements-list">
        {sections.length === 0 && (
          <div className="no-improvements">
            <p>Cargando ideas de mejora...</p>
          </div>
        )}

        {sections.map((section, i) => (
          <div key={i} className="improvement-card">
            <div className="improvement-card-header">
              <span className="improvement-icon">{statusIcons[section.status] || '💡'}</span>
              <h3>{section.title}</h3>
              <span className="improvement-badge">💡 Idea</span>
            </div>
            <div className="improvement-card-body">
              {section.lines.slice(0, 15).map((line, j) => {
                if (!line.trim()) return null;
                if (line.startsWith('###')) {
                  return <h4 key={j} className="improvement-subtitle">{line.replace('### ', '')}</h4>;
                }
                if (line.startsWith('- **')) {
                  const parts = line.match(/- \*\*(.+?)\*\*(:?.*)/);
                  if (parts) {
                    return (
                      <div key={j} className="improvement-item">
                        <strong>{parts[1]}</strong>{parts[2]}
                      </div>
                    );
                  }
                }
                return <p key={j} className="improvement-line">{line}</p>;
              })}
              {section.lines.length > 15 && (
                <p className="improvement-more">... {section.lines.length - 15} líneas más</p>
              )}
            </div>
          </div>
        ))}
      </div>

      {/* Full content section */}
      <details className="improvements-raw">
        <summary>📄 Ver contenido completo (Markdown)</summary>
        <pre>{content}</pre>
      </details>
    </div>
  );
}
