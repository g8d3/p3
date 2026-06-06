(function() {
  const listeners = {};
  let ws = null;
  let reconnectTimer = null;

  function connect(path = '/ws') {
    const proto = location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsPort = window.__NIMBO_WS_PORT__;
    const host = wsPort ? location.hostname + ':' + wsPort : location.host;
    ws = new WebSocket(`${proto}//${host}${path}`);

    ws.onopen = () => {
      console.log('[nimbo:ws] connected');
      emit('open');
    };

    ws.onmessage = (e) => {
      let msg;
      try { msg = JSON.parse(e.data); } catch { msg = e.data; }
      emit('message', msg);
      if (msg && msg.type) emit(msg.type, msg);
    };

    ws.onclose = () => {
      emit('close');
      reconnectTimer = setTimeout(() => connect(path), 2000);
    };

    ws.onerror = () => ws && ws.close();
  }

  function send(data) {
    if (ws && ws.readyState === WebSocket.OPEN) {
      ws.send(typeof data === 'string' ? data : JSON.stringify(data));
    }
  }

  function on(event, fn) {
    (listeners[event] = listeners[event] || []).push(fn);
    return () => {
      listeners[event] = (listeners[event] || []).filter(f => f !== fn);
    };
  }

  function emit(event, data) {
    (listeners[event] || []).forEach(fn => fn(data));
  }

  function log(level, content) {
    send(JSON.stringify({type:'log', data:{level, content, source:'client'}}));
  }

  window.nimbo = window.nimbo || {};
  window.nimbo.ws = { connect, send, on };
  window.nimbo.log = log;
})();
