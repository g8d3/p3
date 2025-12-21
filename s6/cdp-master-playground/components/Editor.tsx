
import React, { useState, useEffect } from 'react';
import { CDPCommand } from '../types';

interface EditorProps {
  command: CDPCommand | null;
  onExecute: (method: string, params: any) => void;
  isExecuting: boolean;
  activeConnectionUrl?: string;
  isAttached: boolean;
}

const Editor: React.FC<EditorProps> = ({ command, onExecute, isExecuting, activeConnectionUrl, isAttached }) => {
  const [paramsJson, setParamsJson] = useState('{}');
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (command) {
      const defaultParams: Record<string, any> = {};
      command.parameters.forEach(p => {
        if (!p.optional) {
          if (p.type === 'string') defaultParams[p.name] = '';
          if (p.type === 'integer' || p.type === 'number') defaultParams[p.name] = 0;
          if (p.type === 'boolean') defaultParams[p.name] = false;
          if (p.type === 'object') defaultParams[p.name] = {};
        }
      });
      setParamsJson(JSON.stringify(defaultParams, null, 2));
    }
  }, [command]);

  const handleRun = () => {
    if (!command) return;
    try {
      const parsed = JSON.parse(paramsJson);
      setError(null);
      onExecute(`${command.domain}.${command.method}`, parsed);
    } catch (e) {
      setError("Invalid JSON parameters");
    }
  };

  const isBrowserLevel = activeConnectionUrl?.includes('/devtools/browser/');
  const isPageCommand = command?.domain === 'Page' || command?.domain === 'Network' || command?.domain === 'Runtime';
  // If we are attached to a target, we are using a sessionId, so "Scope Mismatch" is no longer true
  const showWarning = isBrowserLevel && isPageCommand && !isAttached;

  if (!command) {
    return (
      <div className="h-full flex items-center justify-center text-slate-500 bg-slate-900/30 flex-col gap-4 p-8 text-center">
        <svg className="w-12 h-12 opacity-20" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1} d="M10 20l4-16m4 4l4 4-4 4M6 16l-4-4 4-4" />
        </svg>
        <div className="max-w-xs">
          <h3 className="text-slate-300 font-semibold mb-1">No Command Selected</h3>
          <p className="text-sm">Select a method from the Explorer to begin.</p>
        </div>
      </div>
    );
  }

  return (
    <div className="flex flex-col h-full bg-slate-900 overflow-hidden border-r border-slate-700">
      <div className="p-4 border-b border-slate-700 bg-slate-800/40">
        {showWarning && (
          <div className="mb-4 p-2 bg-amber-950/40 border border-amber-900/50 rounded text-[10px] text-amber-300 flex items-start gap-2 animate-pulse">
            <svg className="w-4 h-4 shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
            </svg>
            <div>
              <p className="font-bold uppercase mb-1">Scope Warning</p>
              <p className="opacity-80 leading-snug">
                This command requires a <b>Target Session</b>. Select a tab in the sidebar to attach before running.
              </p>
            </div>
          </div>
        )}

        <div className="flex items-center justify-between mb-2">
          <div className="flex items-center gap-2">
            <span className="text-blue-400 font-mono text-sm">{command.domain}.</span>
            <span className="text-white font-mono text-sm font-bold">{command.method}</span>
            {isAttached && (
              <span className="text-[8px] bg-blue-500/20 text-blue-400 px-1 rounded border border-blue-500/30 uppercase font-black">Attached</span>
            )}
          </div>
          <button 
            onClick={handleRun}
            disabled={isExecuting}
            className={`px-4 py-1.5 rounded text-xs font-bold transition-all flex items-center gap-2 ${
              isExecuting 
              ? 'bg-slate-700 text-slate-500 cursor-not-allowed' 
              : 'bg-emerald-600 hover:bg-emerald-500 text-white shadow-lg shadow-emerald-900/20'
            }`}
          >
            {isExecuting ? (
              <>
                <svg className="animate-spin h-3 w-3" viewBox="0 0 24 24">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none" />
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
                </svg>
                Running
              </>
            ) : 'Execute Command'}
          </button>
        </div>
        <p className="text-xs text-slate-400 leading-relaxed italic">{command.description}</p>
      </div>

      <div className="flex-1 flex flex-col min-h-0">
        <div className="flex items-center px-4 py-2 bg-slate-800/20 text-[10px] uppercase tracking-wider text-slate-500 font-bold border-b border-slate-800">
          Parameters (JSON)
        </div>
        <div className="flex-1 relative bg-[#010409]">
          <textarea
            value={paramsJson}
            onChange={(e) => setParamsJson(e.target.value)}
            className="absolute inset-0 w-full h-full bg-transparent p-4 font-mono text-xs text-blue-100 resize-none focus:outline-none"
            spellCheck={false}
          />
        </div>
        {error && (
          <div className="px-4 py-2 bg-red-900/30 text-red-400 text-[10px] font-medium border-t border-red-900/50">
            {error}
          </div>
        )}
      </div>

      <div className="h-1/3 border-t border-slate-700 bg-slate-900/50 flex flex-col">
        <div className="flex items-center px-4 py-2 bg-slate-800/20 text-[10px] uppercase tracking-wider text-slate-500 font-bold border-b border-slate-800">
          Documentation
        </div>
        <div className="flex-1 overflow-y-auto p-4 space-y-4">
          {command.parameters.length === 0 ? (
            <p className="text-xs text-slate-500 italic">No parameters required.</p>
          ) : (
            command.parameters.map(p => (
              <div key={p.name} className="space-y-1">
                <div className="flex items-center gap-2">
                  <span className="text-xs font-bold text-slate-200">{p.name}</span>
                  <span className="text-[10px] px-1 bg-slate-800 rounded text-slate-400 border border-slate-700">{p.type}</span>
                  {p.optional && <span className="text-[10px] text-slate-500 italic">optional</span>}
                </div>
                <p className="text-[11px] text-slate-400 leading-snug">{p.description}</p>
              </div>
            ))
          )}
        </div>
      </div>
    </div>
  );
};

export default Editor;
