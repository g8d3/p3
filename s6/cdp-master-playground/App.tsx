
import React, { useState, useCallback, useRef, useEffect } from 'react';
import Sidebar from './components/Sidebar';
import CommandExplorer from './components/CommandExplorer';
import Editor from './components/Editor';
import Console from './components/Console';
import Assistant from './components/Assistant';
import { Target, BrowserConnection, CDPCommand, LogEntry, TestStep } from './types';

const STORAGE_KEY = 'cdp_playground_config_v4';

const App: React.FC = () => {
  const [connections, setConnections] = useState<BrowserConnection[]>(() => {
    try {
      const saved = localStorage.getItem(STORAGE_KEY);
      if (saved) {
        const parsed = JSON.parse(saved);
        return (Array.isArray(parsed) ? parsed : []).map((p: any) => ({
          ...p,
          id: p.id || Math.random().toString(36).substring(7),
          status: 'disconnected',
          error: undefined
        }));
      }
    } catch (e) {
      console.error("Persistence Load Error", e);
    }
    return [];
  });

  const [activeConnectionId, setActiveConnectionId] = useState<string>('');
  const [targets, setTargets] = useState<Target[]>([]);
  const [activeTargetId, setActiveTargetId] = useState('');
  const [sessionMappings, setSessionMappings] = useState<Record<string, string>>({});
  const [selectedCommand, setSelectedCommand] = useState<CDPCommand | null>(null);
  const [logs, setLogs] = useState<LogEntry[]>([]);
  const [isExecuting, setIsExecuting] = useState(false);
  
  const [testSteps, setTestSteps] = useState<TestStep[]>([]);
  const [isTesting, setIsTesting] = useState(false);

  const sockets = useRef<Map<string, WebSocket>>(new Map());
  const rpcIdCounter = useRef(1);
  const pendingCalls = useRef<Map<number, (res: any) => void>>(new Map());

  useEffect(() => {
    const toSave = connections.map(c => ({ id: c.id, name: c.name, url: c.url }));
    localStorage.setItem(STORAGE_KEY, JSON.stringify(toSave));
  }, [connections]);

  const activeConnection = connections.find(c => c.id === activeConnectionId);
  const activeSessionId = sessionMappings[activeTargetId];

  const addLog = useCallback((direction: 'sent' | 'received' | 'event' | 'error' | 'test', browserId: string, method: string, payload: any, targetId?: string) => {
    setLogs(prev => [
      ...prev,
      {
        id: Math.random().toString(36).substring(7),
        timestamp: Date.now(),
        direction,
        browserId,
        targetId,
        method,
        payload
      }
    ].slice(-400));
  }, []);

  const connectToUrl = useCallback((connId: string, url: string) => {
    setConnections(prev => prev.map(c => c.id === connId ? { ...c, status: 'connecting', error: undefined } : c));

    try {
      if (sockets.current.has(connId)) {
        sockets.current.get(connId)?.close();
      }

      const socket = new WebSocket(url);
      sockets.current.set(connId, socket);

      socket.onopen = () => {
        setConnections(prev => prev.map(c => c.id === connId ? { ...c, status: 'connected', error: undefined } : c));
        const discoverId = rpcIdCounter.current++;
        socket.send(JSON.stringify({ id: discoverId, method: 'Target.setDiscoverTargets', params: { discover: true } }));
        addLog('event', connId, 'System', { message: `WebSocket connected` });
      };

      socket.onmessage = (event) => {
        const data = JSON.parse(event.data);
        if (data.id && pendingCalls.current.has(data.id)) {
          const resolve = pendingCalls.current.get(data.id);
          resolve?.(data);
          pendingCalls.current.delete(data.id);
        }
        if (data.method) {
          if (data.method === 'Target.targetCreated' || data.method === 'Target.targetInfoChanged') {
            const info = data.params.targetInfo;
            setTargets(prev => {
              const existing = prev.find(t => t.id === info.targetId && t.browserId === connId);
              if (existing) return prev.map(t => t.id === info.targetId && t.browserId === connId ? { ...t, name: info.title || info.url, url: info.url, type: info.type } : t);
              return [...prev, { id: info.targetId, browserId: connId, name: info.title || info.url, url: info.url, status: 'connected', type: info.type }];
            });
          } else if (data.method === 'Target.targetDestroyed') {
            setTargets(prev => prev.filter(t => !(t.id === data.params.targetId && t.browserId === connId)));
          }
          addLog('event', connId, data.method, data.params, data.sessionId);
        } else if (data.id !== 9999) {
           addLog('received', connId, `RPC Response #${data.id}`, data.result || data.error);
        }
      };

      socket.onclose = (e) => {
        setConnections(prev => prev.map(c => c.id === connId ? { ...c, status: 'disconnected', error: e.code === 1006 ? 'CORS Error - Check --remote-allow-origins' : undefined } : c));
        setTargets(prev => prev.filter(t => t.browserId !== connId));
        sockets.current.delete(connId);
      };

      socket.onerror = (err) => {
        addLog('error', connId, 'WebSocket Error', { message: 'Connection failed. Check browser args.' });
      };

    } catch (err) {
      setConnections(prev => prev.map(c => c.id === connId ? { ...c, status: 'error', error: String(err) } : c));
    }
  }, [addLog]);

  const attachToTarget = async (connId: string, targetId: string) => {
    const socket = sockets.current.get(connId);
    if (!socket || socket.readyState !== WebSocket.OPEN) return null;

    const id = rpcIdCounter.current++;
    const request = { id, method: 'Target.attachToTarget', params: { targetId, flatten: true } };
    addLog('sent', connId, 'Target.attachToTarget', request.params);

    return new Promise<string | null>((resolve) => {
      pendingCalls.current.set(id, (response: any) => {
        if (response.result?.sessionId) {
          const sId = response.result.sessionId;
          setSessionMappings(prev => ({ ...prev, [targetId]: sId }));
          resolve(sId);
        } else {
          resolve(null);
        }
      });
      socket.send(JSON.stringify(request));
    });
  };

  const handleExecute = async (method: string, params: any, customConnectionId?: string) => {
    const targetConnId = customConnectionId || activeConnectionId;
    const conn = connections.find(c => c.id === targetConnId);
    if (!conn) return;

    setIsExecuting(true);
    
    const isBrowserLevel = method.startsWith('Browser.') || method.startsWith('Target.');
    let sessionId = isBrowserLevel ? undefined : sessionMappings[activeTargetId];
    
    if (!isBrowserLevel && activeTargetId && !sessionId) {
        sessionId = (await attachToTarget(conn.id, activeTargetId)) || undefined;
    }

    const id = rpcIdCounter.current++;
    const request: any = { id, method, params };
    if (sessionId) request.sessionId = sessionId;

    addLog('sent', conn.id, method, params, sessionId || (isBrowserLevel ? undefined : activeTargetId));

    try {
      const responsePromise = new Promise((resolve) => {
        pendingCalls.current.set(id, resolve);
      });

      const socket = sockets.current.get(conn.id);
      if (socket?.readyState === WebSocket.OPEN) {
        socket.send(JSON.stringify(request));
      } else {
        addLog('error', conn.id, 'Connection Closed', { message: 'WebSocket is not open.' });
        setIsExecuting(false);
        return;
      }
      
      return await responsePromise;
    } finally {
      setIsExecuting(false);
    }
  };

  const runSmokeTest = async () => {
    setIsTesting(true);
    const steps: TestStep[] = [
      { name: 'GET http://localhost:9223/json/version', status: 'running' },
      { name: 'WebSocket Handshake', status: 'pending' },
      { name: 'CDP Verification (Browser.getVersion)', status: 'pending' }
    ];
    setTestSteps([...steps]);

    const diagnosticLogs: any[] = [];
    const logDiag = (msg: string, data?: any) => {
        diagnosticLogs.push({ msg, data, time: new Date().toISOString() });
        addLog('test', 'smoke-test', msg, data);
    };

    try {
      // Step 1: Fetch with deep error inspection
      logDiag("Starting discovery fetch...");
      let response: Response;
      try {
        response = await fetch('http://localhost:9223/json/version', { mode: 'cors' });
      } catch (fetchErr: any) {
        // Inspection of common browser error states
        const isHttps = window.location.protocol === 'https:';
        const errorMsg = `Network Error: ${fetchErr.message || 'Unknown Fetch Failure'}`;
        const suggestions = [];
        if (isHttps) suggestions.push("App is running on HTTPS but attempting to call HTTP localhost (Mixed Content block).");
        suggestions.push("Browser might be blocking Private Network Access (PNA).");
        suggestions.push("Check if --remote-allow-origins='*' is strictly applied.");
        
        throw new Error(`${errorMsg}. Hints: ${suggestions.join(' ')}`);
      }

      if (!response.ok) {
        const statusText = response.statusText;
        const statusCode = response.status;
        throw new Error(`HTTP ${statusCode} ${statusText}: Could not reach metadata endpoint.`);
      }

      const data = await response.json();
      logDiag("Metadata Received", data);
      
      const wsUrl = data.webSocketDebuggerUrl;
      if (!wsUrl) throw new Error("Metadata JSON parsed but 'webSocketDebuggerUrl' key is missing.");
      
      steps[0].status = 'passed';
      setTestSteps([...steps]);

      // Step 2: WebSocket Connection
      steps[1].status = 'running';
      setTestSteps([...steps]);
      
      const connId = 'smoke-test-' + Date.now();
      const name = "Diagnostic Target";
      setConnections(prev => [...prev, { id: connId, name, url: wsUrl, status: 'connecting' }]);
      setActiveConnectionId(connId);
      connectToUrl(connId, wsUrl);

      let isConnected = false;
      logDiag("Attempting WebSocket handshake...", { url: wsUrl });
      
      for (let i = 0; i < 60; i++) {
        await new Promise(r => setTimeout(r, 100));
        const socket = sockets.current.get(connId);
        if (socket?.readyState === WebSocket.OPEN) {
          isConnected = true;
          break;
        }
        if (socket?.readyState === WebSocket.CLOSED) {
            throw new Error("WebSocket closed immediately after handshake attempt. Check 'Remote debugging' security settings.");
        }
      }

      if (!isConnected) throw new Error("WebSocket connection timeout (6s). The protocol pipe did not open.");
      
      steps[1].status = 'passed';
      setTestSteps([...steps]);

      // Step 3: Command execution
      steps[2].status = 'running';
      setTestSteps([...steps]);
      
      logDiag("Sending Browser.getVersion...");
      const result: any = await handleExecute('Browser.getVersion', {}, connId);
      
      if (result?.result?.browser) {
        logDiag("Verification Success", result.result);
        steps[2].status = 'passed';
        steps[2].message = `Engine: ${result.result.browser}`;
      } else if (result?.error) {
        throw new Error(`CDP Error: ${result.error.message || JSON.stringify(result.error)}`);
      } else {
        throw new Error("Received malformed or empty response from browser.");
      }
      setTestSteps([...steps]);

    } catch (e: any) {
      logDiag("Smoke Test Failure Trace", { 
          errorMessage: e.message, 
          stack: e.stack,
          windowContext: {
              protocol: window.location.protocol,
              origin: window.location.origin,
              isSecureContext: window.isSecureContext
          }
      });
      
      const currentIdx = steps.findIndex(s => s.status === 'running' || s.status === 'pending');
      if (currentIdx !== -1) {
        steps[currentIdx].status = 'failed';
        steps[currentIdx].message = e.message;
      }
      setTestSteps([...steps]);
      addLog('error', 'system', 'Smoke Test Aborted', { error: e.message, diagnostics: diagnosticLogs });
    } finally {
      setIsTesting(false);
    }
  };

  return (
    <div className="flex h-screen w-screen overflow-hidden bg-[#05070a] text-slate-200 font-sans">
      <Sidebar 
        connections={connections}
        targets={targets}
        activeTargetId={activeTargetId}
        activeConnectionId={activeConnectionId}
        onSelectTarget={(tid) => {
            const t = targets.find(x => x.id === tid);
            if(t) {
                setActiveTargetId(tid);
                setActiveConnectionId(t.browserId);
                if (!sessionMappings[tid]) attachToTarget(t.browserId, tid);
            }
        }}
        onSelectConnection={setActiveConnectionId}
        onAddConnection={(url) => {
          const connId = Math.random().toString(36).substring(7);
          const name = url.includes('127.0.0.1') || url.includes('localhost') ? 'Local Debugger' : 'Remote Browser';
          setConnections(prev => [...prev, { id: connId, name, url, status: 'disconnected' }]);
          setActiveConnectionId(connId);
          connectToUrl(connId, url);
        }}
        onRemoveConnection={(id) => {
          setConnections(prev => prev.filter(c => c.id !== id));
          setTargets(prev => prev.filter(t => t.browserId !== id));
          sockets.current.get(id)?.close();
        }}
        onReconnect={(id) => {
          const conn = connections.find(c => c.id === id);
          if (conn) connectToUrl(id, conn.url);
        }}
      />

      <div className="flex-1 flex flex-col min-w-0">
        <div className="h-12 bg-[#0d1117] border-b border-slate-800 flex items-center px-6 justify-between z-10">
           <div className="flex items-center gap-3">
              <div className="bg-blue-600 p-1.5 rounded shadow-lg shadow-blue-500/20">
                 <svg className="w-3.5 h-3.5 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={3} d="M10 20l4-16m4 4l4 4-4 4M6 16l-4-4 4-4" />
                 </svg>
              </div>
              <h1 className="text-[10px] font-black tracking-[0.3em] uppercase text-white">CDP MASTER</h1>
           </div>
           {activeConnection && (
              <div className="flex items-center gap-2">
                <span className="text-[9px] text-slate-500 font-mono hidden md:inline truncate max-w-[200px]">{activeConnection.url}</span>
                <span className={`text-[8px] px-1.5 py-0.5 rounded font-bold uppercase ${
                  activeConnection.status === 'connected' ? 'bg-green-500/10 text-green-400 border border-green-500/20' : 'bg-red-500/10 text-red-400 border border-red-500/20'
                }`}>
                  {activeConnection.status}
                </span>
              </div>
           )}
        </div>

        <div className="flex-1 flex min-h-0">
          <CommandExplorer onSelectCommand={setSelectedCommand} />
          <div className="flex-1 flex flex-col min-w-0">
             <div className="flex-1 min-h-0 bg-[#0d1117]">
                <Editor 
                    command={selectedCommand} 
                    onExecute={handleExecute}
                    isExecuting={isExecuting}
                    isAttached={!!activeSessionId}
                />
             </div>
             <div className="h-[45%] border-t border-slate-800">
                <Console logs={logs} onClear={() => setLogs([])} />
             </div>
          </div>
          <Assistant onRunTest={runSmokeTest} testSteps={testSteps} isTesting={isTesting} />
        </div>
      </div>
    </div>
  );
};

export default App;
