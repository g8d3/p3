
import React, { useEffect, useRef } from 'react';
import { LogEntry } from '../types';

interface ConsoleProps {
  logs: LogEntry[];
  onClear: () => void;
}

const Console: React.FC<ConsoleProps> = ({ logs, onClear }) => {
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [logs]);

  return (
    <div className="flex flex-col h-full bg-[#0d1117] border-t border-slate-700">
      <div className="flex items-center justify-between px-4 py-2 bg-slate-800/30 border-b border-slate-700/50">
        <div className="flex items-center gap-4">
          <span className="text-[10px] font-bold text-slate-400 uppercase tracking-widest">Protocol Monitor</span>
          <div className="flex items-center gap-2">
            <div className="w-1.5 h-1.5 rounded-full bg-blue-500 animate-pulse"></div>
            <span className="text-[10px] text-slate-500">Live Traffic</span>
          </div>
        </div>
        <button 
          onClick={onClear}
          className="p-1 hover:text-slate-200 text-slate-500 transition-colors"
          title="Clear Console"
        >
          <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
          </svg>
        </button>
      </div>

      <div className="flex-1 overflow-y-auto p-2 font-mono text-[11px] space-y-1">
        {logs.length === 0 && (
          <div className="h-full flex items-center justify-center text-slate-600 italic px-8 text-center">
            Waiting for protocol activities. Connect to a browser and execute commands to see the raw CDP frames.
          </div>
        )}
        {logs.map((log) => (
          <div key={log.id} className={`group border-b border-slate-800/20 pb-1 hover:bg-slate-800/10 ${log.direction === 'error' ? 'bg-red-950/20' : ''}`}>
            <div className="flex items-center gap-2 mb-0.5">
               <span className="text-slate-600 text-[10px]">
                {new Date(log.timestamp).toLocaleTimeString([], { hour12: false, hour: '2-digit', minute: '2-digit', second: '2-digit' })}
              </span>
              <span className={`text-[9px] font-bold px-1 rounded uppercase ${
                log.direction === 'sent' ? 'bg-blue-900/40 text-blue-400' : 
                log.direction === 'received' ? 'bg-emerald-900/40 text-emerald-400' :
                log.direction === 'event' ? 'bg-purple-900/40 text-purple-400' :
                'bg-red-900/40 text-red-400'
              }`}>
                {log.direction}
              </span>
              {log.targetId && (
                <span className="text-[9px] text-slate-500 bg-slate-800 rounded px-1 truncate max-w-[80px]">
                  ID: {log.targetId.substring(0, 6)}
                </span>
              )}
              <span className={`font-bold truncate ${log.direction === 'error' ? 'text-red-400' : 'text-slate-200'}`}>
                {log.method}
              </span>
            </div>
            <div className="pl-4 text-slate-400">
              <pre className={`whitespace-pre-wrap break-all opacity-80 group-hover:opacity-100 transition-opacity ${log.direction === 'error' ? 'text-red-300' : ''}`}>
                {JSON.stringify(log.payload, null, 2)}
              </pre>
            </div>
          </div>
        ))}
        <div ref={bottomRef} />
      </div>
    </div>
  );
};

export default Console;
