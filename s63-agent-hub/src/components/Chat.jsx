import { useState, useEffect, useRef } from 'react';

const COMMANDS = ['!goto', '!click', '!search', '!back', '!scroll', '!run', '!clear', '!cd', '!task', '!stop', '!stats', '!ai-log', '!report', '!improve'];

export default function Chat({ socket, channelId }) {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState('');
  const [connected, setConnected] = useState(false);
  const [showCommands, setShowCommands] = useState(false);
  const messagesEndRef = useRef(null);
  const inputRef = useRef(null);

  useEffect(() => {
    if (!socket) return;
    setConnected(socket.connected);

    socket.on('connect', () => setConnected(true));
    socket.on('disconnect', () => setConnected(false));

    socket.on('chat:message', (msg) => {
      if (msg.channelId === channelId) {
        setMessages(prev => [...prev, msg]);
      }
    });

    return () => {
      socket.off('connect');
      socket.off('disconnect');
      socket.off('chat:message');
    };
  }, [socket, channelId]);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  function send(e) {
    e.preventDefault();
    if (!input.trim() || !socket) return;
    socket.emit('chat:message', { channelId, text: input.trim() });
    setInput('');
    setShowCommands(false);
  }

  function handleKeyDown(e) {
    if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); send(e); }
  }

  function handleInputChange(e) {
    const val = e.target.value;
    setInput(val);
    setShowCommands(val.startsWith('!') && val.length <= 3);
  }

  function insertCommand(cmd) {
    setInput(cmd + ' ');
    setShowCommands(false);
    inputRef.current?.focus();
  }

  return (
    <div className="chat">
      <div className="chat-header">
        <span>Chat</span>
        <span style={{ fontSize: '0.75rem', color: 'var(--text-secondary)' }}>
          {connected ? '🟢' : '🔴'}
        </span>
      </div>

      <div className="chat-messages">
        {messages.length === 0 && (
          <div className="chat-empty">
            <p>No hay mensajes aún</p>
            <p className="chat-hint">💡 Usa <strong>!comandos</strong> para hablar con el agente</p>
          </div>
        )}
        {messages.map(m => (
          <div key={m.id} className={`chat-message ${m.isCommand ? 'command' : ''} ${m.isAgent ? 'agent-reply' : ''}`}>
            <span className="sender" style={{
              color: m.isAgent ? '#4ec9b0' : m.isCommand ? '#ce9178' : 'var(--accent)',
            }}>
              {m.sender}:
            </span>
            {m.text}
          </div>
        ))}
        <div ref={messagesEndRef} />
      </div>

      {showCommands && (
        <div className="chat-commands-popup">
          {COMMANDS.filter(c => c.startsWith(input)).map(cmd => (
            <button key={cmd} className="cmd-suggestion" onClick={() => insertCommand(cmd)}>
              {cmd}
            </button>
          ))}
        </div>
      )}

      <form className="chat-input" onSubmit={send}>
        <input
          ref={inputRef}
          value={input}
          onChange={handleInputChange}
          onKeyDown={handleKeyDown}
          placeholder="!goto !click !search !run ..."
          disabled={!connected}
        />
        <button type="submit" disabled={!connected || !input.trim()}>Enviar</button>
      </form>
      {/* Command quick buttons */}
      <div className="chat-quick-buttons">
        {['!goto', '!click', '!search', '!back', '!stats', '!ai-log', '!report'].map(cmd => (
          <button key={cmd} className="quick-cmd" onClick={() => { setInput(cmd + ' '); inputRef.current?.focus(); }}>
            {cmd}
          </button>
        ))}
      </div>
    </div>
  );
}
