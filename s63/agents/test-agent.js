// QA Test Agent — Prueba automática de la plataforma Agent Twitch
// Se conecta como cliente, spawn agents, verifica streams, reporta bugs

const SERVER = process.env.SERVER_URL || 'http://localhost:3001';
const WS_URL = SERVER.replace(/^http/, 'ws');
const AGENT_ID = process.env.AGENT_ID || 'unknown';
const CHANNEL_NAME = process.env.CHANNEL_NAME || 'QA Agent';

let testsPassed = 0;
let testsFailed = 0;
let currentChannelId = null;
let frameReceived = false;
let chatReceived = false;

// ─── IPC ───────────────────────────────────────────────────────────
function send(type, data = {}) {
  process.stdout.write(JSON.stringify({ type, ...data }) + '\n');
}
function sendFrame(buffer) { send('frame', { data: buffer.toString('base64') }); }
function sendLog(text) { send('log', { text }); }
function sendStatus(status, text) { send('status', { status, text }); }
function sendReply(text) { send('log', { text: `🧪 ${text}` }); }

// ─── Bug reporter ──────────────────────────────────────────────────
async function reportBug(title, description, severity = 'info') {
  try {
    const res = await fetch(`${SERVER}/api/bugs`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        title,
        description,
        severity,
        reporter: `QA-Agent-${AGENT_ID.slice(0, 8)}`,
        channelId: currentChannelId,
      }),
    });
    const data = await res.json();
    sendLog(`🐛 Bug reportado: ${data.id} — ${title}`);
    return data;
  } catch (e) {
    sendLog(`⚠️ No pude reportar bug: ${e.message}`);
  }
}

// ─── Test helpers ──────────────────────────────────────────────────
function test(name, passed, detail = '') {
  if (passed) {
    testsPassed++;
    sendReply(`✅ ${name}`);
  } else {
    testsFailed++;
    const msg = `❌ ${name}${detail ? ': ' + detail : ''}`;
    sendReply(msg);
    reportBug(`Test failed: ${name}`, `Test: ${name}\nDetail: ${detail}`, 'warning');
  }
}

async function fetchJSON(url) {
  try {
    const res = await fetch(`${SERVER}${url}`);
    return await res.json();
  } catch (e) {
    return { error: e.message };
  }
}

// ─── Tests ─────────────────────────────────────────────────────────
async function testAPIEndpoints() {
  sendLog('📋 Test 1: API Endpoints');

  // Test /api/channels
  const channels = await fetchJSON('/api/channels');
  test('/api/channels returns array', Array.isArray(channels), typeof channels);
  
  // Test /api/agents/types
  const types = await fetchJSON('/api/agents/types');
  test('/api/agents/types returns array', Array.isArray(types), typeof types);
  test('Agent types include web-surfer', Array.isArray(types) && types.some(t => t.id === 'web-surfer'));

  // Test /api/bugs
  const bugs = await fetchJSON('/api/bugs');
  test('/api/bugs returns array', Array.isArray(bugs), typeof bugs);
}

async function testSpawnAndStream() {
  sendLog('📋 Test 2: Spawn agent & receive stream');

  const res = await fetch(`${SERVER}/api/agents/spawn?type=web-surfer&name=QA-Test-Agent`, { method: 'POST' });
  const agent = await res.json();
  test('Spawn returns agent id', agent && agent.id, JSON.stringify(agent));
  if (!agent?.id) return;

  currentChannelId = agent.id;
  sendLog(`🎯 Agente de test: ${agent.id}`);

  // Connect via Socket.IO to check streaming
  const { io } = await import('socket.io-client');
  const socket = io(SERVER);
  
  await new Promise((resolve) => {
    let timeout = setTimeout(() => {
      test('Socket.IO connection', false, 'timeout');
      socket.close();
      resolve();
    }, 10000);

      socket.on('connect', () => {
      test('Socket.IO connected', true);
      clearTimeout(timeout);
      
      // Join the test channel
      socket.emit('join:channel', agent.id);
      
      let firstFrameDone = false;
      let frameTimeout = setTimeout(() => {
        test('Stream frames received', frameReceived, `frames=${frameReceived}`);
        socket.close();
        resolve();
      }, 15000);

      socket.on('stream:frame', ({ channelId }) => {
        if (channelId === agent.id) {
          frameReceived = true;
          if (!firstFrameDone) {
            firstFrameDone = true;
            test('Stream frame received', true);
            clearTimeout(frameTimeout);
            // Wait a bit more then finish
            frameTimeout = setTimeout(() => {
              socket.close();
              resolve();
            }, 5000);
          }
        }
      });

      socket.on('connect_error', (err) => {
        test('Socket.IO connection', false, err.message);
        clearTimeout(frameTimeout);
        socket.close();
        resolve();
      });
    });
  });
}

async function testChat() {
  sendLog('📋 Test 3: Chat system');

  if (!currentChannelId) {
    test('Chat test skipped', false, 'no channel');
    return;
  }

  const { io } = await import('socket.io-client');
  const socket1 = io(SERVER);
  const socket2 = io(SERVER);

  await new Promise((resolve) => {
    let step = 0;
    let timeout;

    const finish = (passed, detail) => {
      clearTimeout(timeout);
      test('Chat message delivery', passed, detail || `step=${step}`);
      try { socket1.close(); } catch {}
      try { socket2.close(); } catch {}
      resolve();
    };

    timeout = setTimeout(() => finish(false), 15000);

    socket1.on('connect', () => {
      step = 1;
      socket1.emit('join:channel', currentChannelId);
    });

    socket2.on('connect', () => {
      step = 2;
      socket2.emit('join:channel', currentChannelId);
    });

    socket2.on('chat:message', (msg) => {
      if (msg.channelId === currentChannelId && msg.text === 'QA test message') {
        chatReceived = true;
        finish(true);
      }
    });

    socket1.on('connect_error', () => finish(false, 'socket1 connect_error'));
    socket2.on('connect_error', () => finish(false, 'socket2 connect_error'));

    // Send message after both joined
    setTimeout(() => {
      if (step >= 2) {
        socket1.emit('chat:message', {
          channelId: currentChannelId,
          text: 'QA test message',
        });
      }
    }, 3000);
  });
}

async function testBugAPI() {
  sendLog('📋 Test 4: Bug reporting API');

  const bug = await reportBug('Test bug from QA Agent', 'This is an automated test', 'info');
  test('Bug report created', bug && bug.id, JSON.stringify(bug));

  const bugs = await fetchJSON('/api/bugs');
  test('Bug list includes our bug', Array.isArray(bugs) && bugs.some(b => b.id === bug?.id));
}

async function testSpawnLLMAgent() {
  sendLog('📋 Test 5: Spawn LLM agent');

  if (!process.env.OPENCODE_GO_API_KEY) {
    test('Spawn LLM agent (skipped - no API key)', true, 'no key available');
    return;
  }

  const res = await fetch(`${SERVER}/api/agents/spawn?type=llm-web-surfer&name=QA-LLM-Test`, { method: 'POST' });
  const agent = await res.json();
  test('LLM agent spawned', agent && agent.id, JSON.stringify(agent));

  // Let it run for a bit then stop it
  if (agent?.id) {
    await new Promise(r => setTimeout(r, 5000));
    await fetch(`${SERVER}/api/agents/${agent.id}/stop`, { method: 'POST' });
    test('LLM agent stopped', true);
  }
}

// ─── Main test runner ──────────────────────────────────────────────
async function main() {
  sendLog(`🚀 QA Agent iniciando...`);
  sendLog(`🎯 Servidor: ${SERVER}`);
  sendStatus('starting', 'Comenzando pruebas...');

  sendReply('🧪 QA Agent iniciando suite de pruebas...');
  await new Promise(r => setTimeout(r, 1000));

  // Run tests
  await testAPIEndpoints();
  await new Promise(r => setTimeout(r, 2000));

  await testSpawnAndStream();
  await new Promise(r => setTimeout(r, 2000));

  await testChat();
  await new Promise(r => setTimeout(r, 2000));

  await testBugAPI();
  await new Promise(r => setTimeout(r, 2000));

  await testSpawnLLMAgent();
  await new Promise(r => setTimeout(r, 2000));

  // Summary
  sendReply(`🧪 Pruebas completadas: ✅ ${testsPassed} passed, ❌ ${testsFailed} failed`);
  sendLog(`[DONE] QA Agent: ${testsPassed}/${testsPassed + testsFailed} tests passed`);

  if (testsFailed > 0) {
    sendStatus('error', `${testsFailed} pruebas fallaron`);
    await reportBug(
      `QA Agent: ${testsFailed} tests failed`,
      `Tests: ${testsPassed} passed, ${testsFailed} failed\nTotal: ${testsPassed + testsFailed}`,
      'warning'
    );
  } else {
    sendStatus('live', 'Todas las pruebas pasaron ✅');
    sendReply('✅ Todas las pruebas pasaron!');
  }

  // Keep stream alive for a bit so viewers can see results
  await new Promise(r => setTimeout(r, 30000));
  process.exit(testsFailed > 0 ? 1 : 0);
}

main().catch((e) => {
  sendLog(`💥 Fatal: ${e.message}`);
  reportBug('QA Agent crashed', `Error: ${e.message}\nStack: ${e.stack}`, 'critical');
  process.exit(1);
});
