
import React, { useState } from 'react';
import { Target, BrowserConnection } from '../types';

interface SidebarProps {
  connections: BrowserConnection[];
  targets: Target[];
  activeTargetId: string;
  activeConnectionId: string;
  onSelectTarget: (id: string) => void;
  onSelectConnection: (id: string) => void;
  onAddConnection: (url: string) => void;
  onRemoveConnection: (id: string) => void;
  onReconnect: (id: string) => void;
}

const Sidebar: React.FC<SidebarProps> = ({ 
  connections,
  targets, 
  activeTargetId, 
  activeConnectionId,
  onSelectTarget, 
  onSelectConnection,
  onAddConnection,
  onRemoveConnection,
  onReconnect
}) => {
  const [newUrl, setNewUrl] = useState('');
  const [metadataUrl, setMetadataUrl] = useState('http://localhost:9223/json/version');
  const [showAdd, setShowAdd] = useState(true);
  const [isFetching, setIsFetching] = useState(false);
  const [fetchError, setFetchError] = useState<{ message: string; trace?: any } | null>(null);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (newUrl.trim()) {
      onAddConnection(newUrl.trim());
      setShowAdd(false);
      setNewUrl('');
    }
  };

  const handleAutoFetch = async () => {
    setIsFetching(true);
    setFetchError(null);
    try {
      const response = await fetch(metadataUrl, { mode: 'cors' });
      if (!response.ok) {
        setFetchError({ message: `HTTP Error: ${response.status} ${response.statusText}` });
        setIsFetching(false);
        return;
      }
      const data = await response.json();
      const wsUrl = data.webSocketDebuggerUrl;
      if (wsUrl) {
        setNewUrl(wsUrl);
      } else {
        setFetchError({ message: "Metadata loaded, but 'webSocketDebuggerUrl' is missing.", trace: data });
      }
    } catch (e: any) {
      const isHttps = window.location.protocol === 'https:';
      let msg = "Failed to fetch.";
      if (isHttps) msg += " Detected HTTPS -> HTTP block (Mixed Content). Use an HTTP tab for this app.";
      else msg += " Likely a CORS or Network error. Ensure --remote-allow-origins=* is set.";
      
      setFetchError({ 
        message: msg, 
        trace: { 
            error: e.message, 
            protocol: window.location.protocol,
            target: metadataUrl 
        } 
      });
      console.error("Discovery Fetch Error:", e);
    } finally {
      setIsFetching(false);
    }
  };

  return (
    <div className="w-72 bg-slate-900 border-r border-slate-700 flex flex-col h-full">
      <div className="p-4 border-b border-slate-700 flex justify-between items-center bg-slate-800/50">
        <h2 className="font-bold text-slate-200 uppercase tracking-widest text-xs flex items-center gap-2">
          <svg className="w-3.5 h-3.5 text-blue-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 12a9 9 0 01-9 9m9-9a9 9 0 00-9-9m9 9H3m9 9a9 9 0 01-9-9m9 9c1.657 0 3-4.03 3-9s-1.343-9-3-9m0 18c-1.657 0-3-4.03-3-9s1.343-9 3-9m-9 9a9 9 0 019-9" />
          </svg>
          Connections
        </h2>
        <button 
          onClick={() => setShowAdd(!showAdd)}
          className={`p-1.5 rounded-full transition-all ${showAdd ? 'bg-red-500/10 text-red-400 rotate-45' : 'bg-blue-500/10 text-blue-400 hover:bg-blue-500/20'}`}
        >
          <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
          </svg>
        </button>
      </div>

      {showAdd && (
        <div className="p-4 border-b border-slate-700 bg-slate-800/40 space-y-4">
          <div className="space-y-2">
            <label className="block text-[10px] text-slate-500 uppercase font-bold mb-1">1. Discovery URL</label>
            <div className="flex gap-1">
              <input 
                type="text"
                placeholder="http://localhost:9223/json/version"
                value={metadataUrl}
                onChange={(e) => setMetadataUrl(e.target.value)}
                className="flex-1 bg-slate-900 border border-slate-700 rounded p-1.5 text-[10px] text-slate-400 font-mono outline-none focus:border-purple-500"
              />
              <button 
                onClick={handleAutoFetch}
                disabled={isFetching}
                className="bg-purple-600 hover:bg-purple-500 px-3 rounded text-[10px] font-bold uppercase transition-colors disabled:opacity-50"
              >
                {isFetching ? '...' : 'Fetch'}
              </button>
            </div>
            {fetchError && (
              <div className="text-[9px] text-red-400 leading-tight italic bg-red-900/20 p-2 rounded border border-red-900/30">
                <p className="font-bold mb-1">Discovery Failure:</p>
                <p className="mb-2">{fetchError.message}</p>
                {fetchError.trace && (
                    <details className="mt-1 opacity-60">
                        <summary className="cursor-pointer hover:underline">View Trace</summary>
                        <pre className="mt-1 p-1 bg-black/40 rounded overflow-x-auto text-[8px]">
                            {JSON.stringify(fetchError.trace, null, 2)}
                        </pre>
                    </details>
                )}
              </div>
            )}
          </div>

          <form onSubmit={handleSubmit} className="space-y-2 pt-2 border-t border-slate-700/50">
            <label className="block text-[10px] text-slate-500 uppercase font-bold mb-1">2. WebSocket Debugger URL</label>
            <input 
              type="text"
              placeholder="ws://127.0.0.1:9223/devtools/browser/..."
              value={newUrl}
              onChange={(e) => setNewUrl(e.target.value)}
              className="w-full bg-slate-900 border border-slate-700 rounded p-1.5 text-[10px] text-blue-300 outline-none focus:border-blue-500 font-mono"
            />
            <button type="submit" className="w-full bg-blue-600 hover:bg-blue-500 py-2 rounded text-[10px] font-black uppercase tracking-wider shadow-lg shadow-blue-900/40 transition-all">
              Launch Explorer
            </button>
          </form>
        </div>
      )}
      
      <div className="flex-1 overflow-y-auto p-2 space-y-3">
        {connections.length === 0 && !showAdd && (
          <div className="py-10 text-center px-4">
             <p className="text-[10px] text-slate-500 uppercase font-black opacity-40">No connections</p>
          </div>
        )}
        {connections.map(conn => (
          <div 
            key={conn.id} 
            className={`space-y-1 bg-slate-800/20 rounded-lg p-1 border transition-all ${
              activeConnectionId === conn.id ? 'border-blue-500/50 bg-blue-500/5' : 'border-slate-800 hover:border-slate-700'
            }`}
          >
            <div 
              className="flex items-center justify-between px-2 py-1 cursor-pointer group"
              onClick={() => onSelectConnection(conn.id)}
            >
              <div className="flex items-center gap-2 overflow-hidden">
                <div className={`w-2 h-2 rounded-full ${
                  conn.status === 'connected' ? 'bg-green-500 shadow-[0_0_8px_rgba(34,197,94,0.4)]' : 
                  conn.status === 'connecting' ? 'bg-yellow-500 animate-pulse' : 'bg-red-500'
                }`} />
                <span className={`text-[10px] font-black truncate uppercase tracking-tighter ${activeConnectionId === conn.id ? 'text-blue-400' : 'text-slate-400'}`}>
                  {conn.name}
                </span>
              </div>
              <div className="flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
                <button 
                  onClick={(e) => { e.stopPropagation(); onReconnect(conn.id); }}
                  className="text-slate-500 hover:text-emerald-400 p-1 rounded transition-colors"
                >
                  <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
                  </svg>
                </button>
                <button 
                  onClick={(e) => { e.stopPropagation(); onRemoveConnection(conn.id); }} 
                  className="text-slate-500 hover:text-red-400 p-1 rounded transition-colors"
                >
                  <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                  </svg>
                </button>
              </div>
            </div>

            <div className="space-y-1 pl-2 pb-1">
              {targets.filter(t => t.browserId === conn.id).map(target => (
                <div 
                  key={target.id}
                  onClick={() => onSelectTarget(target.id)}
                  className={`p-2 rounded border cursor-pointer transition-all ${
                    activeTargetId === target.id 
                    ? 'bg-blue-600/30 border-blue-500 shadow-md translate-x-1' 
                    : 'bg-slate-900/40 border-slate-800 hover:bg-slate-800/80'
                  }`}
                >
                  <div className="flex items-center gap-2 mb-1">
                    <div className="text-[10px] font-bold text-slate-200 truncate flex-1">
                      {target.name || 'Tab'}
                    </div>
                    <span className="text-[7px] px-1 bg-slate-800 rounded text-slate-500 uppercase font-black">{target.type}</span>
                  </div>
                  <div className="text-[9px] text-slate-500 truncate opacity-50 font-mono italic">{target.url}</div>
                </div>
              ))}
            </div>
          </div>
        ))}
      </div>

      <div className="p-4 border-t border-slate-700 text-[10px] text-slate-500 bg-slate-800/20">
        <p className="uppercase font-black text-[9px] tracking-widest opacity-60 mb-2 italic">Discovery Tips</p>
        <p className="leading-tight opacity-80">
          Browser restricts local fetches by default. Start with <code>--remote-allow-origins=*</code> to enable discovery.
        </p>
      </div>
    </div>
  );
};

export default Sidebar;
