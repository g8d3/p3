
import React, { useState, useEffect } from 'react';
import { explainProtocol } from '../services/geminiService';
import { TestStep } from '../types';

interface AssistantProps {
  onRunTest: () => Promise<void>;
  testSteps: TestStep[];
  isTesting: boolean;
}

const Assistant: React.FC<AssistantProps> = ({ onRunTest, testSteps, isTesting }) => {
  const [query, setQuery] = useState('');
  const [loading, setLoading] = useState(false);
  const [answer, setAnswer] = useState<string | null>(null);

  const handleAsk = async (e: React.FormEvent | string) => {
    if (typeof e !== 'string') e.preventDefault();
    const finalQuery = typeof e === 'string' ? e : query;
    if (!finalQuery.trim()) return;
    
    setLoading(true);
    setAnswer(null);
    const result = await explainProtocol(finalQuery);
    setAnswer(result || "No explanation found.");
    setLoading(false);
  };

  const troubleshootConnection = () => {
    handleAsk("I'm getting WebSocket Error 1006. My browser is running with --remote-debugging-port=9222. Why can't I connect from this web app? List CORS, Mixed Content (HTTPS), and Insecure Content settings.");
  };

  return (
    <div className="w-80 border-l border-slate-700 bg-slate-900 flex flex-col h-full">
      <div className="p-4 border-b border-slate-700 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <div className="w-2 h-2 rounded-full bg-purple-500 shadow-[0_0_8px_rgba(168,85,247,0.5)]"></div>
          <h2 className="font-bold text-slate-200 uppercase tracking-widest text-xs">AI Guide & Test</h2>
        </div>
      </div>

      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {/* Test Section */}
        <div className="bg-slate-800/40 rounded-lg p-3 border border-slate-700/50">
          <div className="flex items-center justify-between mb-3">
             <span className="text-[10px] font-black uppercase text-slate-400">Smoke Test Suite</span>
             <button 
               onClick={onRunTest}
               disabled={isTesting}
               className={`text-[9px] px-2 py-1 rounded font-bold uppercase transition-all ${
                 isTesting ? 'bg-slate-700 text-slate-500' : 'bg-blue-600 hover:bg-blue-500 text-white shadow-lg shadow-blue-900/40'
               }`}
             >
               {isTesting ? 'Running...' : 'Run Diagnostics'}
             </button>
          </div>
          
          {testSteps.length > 0 && (
            <div className="space-y-2">
              {testSteps.map((step, idx) => (
                <div key={idx} className="flex items-center gap-2 text-[10px]">
                  {step.status === 'running' && <div className="w-2 h-2 rounded-full bg-blue-500 animate-pulse" />}
                  {step.status === 'passed' && <div className="w-2 h-2 rounded-full bg-green-500" />}
                  {step.status === 'failed' && <div className="w-2 h-2 rounded-full bg-red-500" />}
                  {step.status === 'pending' && <div className="w-2 h-2 rounded-full bg-slate-700" />}
                  <span className={step.status === 'failed' ? 'text-red-400' : step.status === 'passed' ? 'text-green-400' : 'text-slate-300'}>
                    {step.name}
                  </span>
                </div>
              ))}
            </div>
          )}
        </div>

        {answer ? (
          <div className="space-y-4">
             <div className="prose prose-invert prose-xs text-slate-300 text-sm leading-relaxed whitespace-pre-wrap">
                {answer}
             </div>
             <button 
                onClick={() => setAnswer(null)}
                className="w-full py-2 bg-slate-800 hover:bg-slate-700 rounded text-xs font-semibold text-slate-400 transition-colors"
             >
                New Question
             </button>
          </div>
        ) : !isTesting && (
          <div className="flex flex-col items-center justify-center text-center space-y-4 opacity-60 pt-8">
            <svg className="w-12 h-12 text-purple-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1} d="M13 10V3L4 14h7v7l9-11h-7z" />
            </svg>
            <div>
              <p className="text-xs font-semibold text-slate-200">Protocol Expert</p>
              <p className="text-[10px] text-slate-400 mt-1 px-4">Ask about commands, payloads, or connection errors.</p>
            </div>
            <button 
              onClick={troubleshootConnection}
              className="text-[9px] text-purple-400 border border-purple-500/30 px-2 py-0.5 rounded hover:bg-purple-500/10 transition-colors uppercase font-bold"
            >
              Troubleshoot
            </button>
          </div>
        )}
      </div>

      <div className="p-4 border-t border-slate-700 bg-slate-800/30">
        <form onSubmit={handleAsk} className="relative">
          <input 
            type="text"
            placeholder="Ask a question..."
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            disabled={loading || isTesting}
            className="w-full bg-slate-800 border border-slate-700 rounded-md py-2 px-3 pr-10 text-xs focus:outline-none focus:ring-1 focus:ring-purple-500 placeholder-slate-500 disabled:opacity-50"
          />
          <button 
            type="submit"
            disabled={loading || isTesting}
            className="absolute right-2 top-1.5 p-1 text-purple-400 hover:text-purple-300 transition-colors disabled:opacity-50"
          >
            {loading ? (
               <svg className="animate-spin h-4 w-4" viewBox="0 0 24 24">
                 <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none" />
                 <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
               </svg>
            ) : (
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M14 5l7 7m0 0l-7 7m7-7H3" />
              </svg>
            )}
          </button>
        </form>
      </div>
    </div>
  );
};

export default Assistant;
