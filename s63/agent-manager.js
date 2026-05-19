import { spawn } from 'child_process';
import path from 'path';
import { fileURLToPath } from 'url';
import { StreamRelay } from './stream-relay.js';

const __dirname = path.dirname(fileURLToPath(import.meta.url));

const AGENT_TYPES = {
  'web-surfer': {
    name: 'Web Surfer',
    description: 'Navega la web. Responde a: !goto, !click, !search, !back, !scroll',
    icon: '🌐',
    commands: ['goto', 'click', 'search', 'back', 'scroll'],
  },
  'llm-web-surfer': {
    name: 'Web Surfer IA',
    description: 'Navegador potenciado por IA (deepseek-v4-flash). Decide qué hacer.',
    icon: '🤖',
    commands: ['goto', 'task', 'stop'],
  },
  'terminal': {
    name: 'Terminal',
    description: 'Terminal bash en vivo. Responde a: !run, !clear, !cd',
    icon: '💻',
    commands: ['run', 'clear', 'cd'],
  },
  'desktop-share': {
    name: 'Mi Escritorio',
    description: 'Comparte tu pantalla en vivo.',
    icon: '🖥️',
    commands: [],
  },
  'test-agent': {
    name: 'QA Agent',
    description: 'Testing automático de la plataforma.',
    icon: '🧪',
    commands: ['test', 'status', 'report'],
  },
};

export class AgentManager {
  constructor(roomManager) {
    this.streamRelay = new StreamRelay(roomManager);
    this.roomManager = roomManager;
    this.agents = new Map();
    this.agentProcesses = new Map();
  }

  getAgentTypes() {
    return Object.entries(AGENT_TYPES).map(([id, info]) => ({ id, ...info }));
  }

  async spawnAgent(type, name) {
    const typeInfo = AGENT_TYPES[type];
    if (!typeInfo) throw new Error(`Unknown agent type: ${type}`);

    const id = `${type}-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;
    const agentScript = path.join(__dirname, 'agents', `${type}.js`);

    const channelName = name || `${typeInfo.icon} ${typeInfo.name}`;
    this.streamRelay.createChannel(id, channelName, type);

    console.log(`[AgentManager] Spawning ${type} (${id}) as "${channelName}"`);

    const child = spawn('node', [agentScript], {
      env: {
        ...process.env,
        AGENT_ID: id,
        CHANNEL_NAME: channelName,
        AGENT_TYPE: type,
        PATH: process.env.PATH,
        OPENCODE_GO_API_KEY: process.env.OPENCODE_GO_API_KEY || '',
      },
      stdio: ['pipe', 'pipe', 'pipe'],
      cwd: __dirname,
    });

    let lineBuffer = '';
    child.stdout.on('data', (data) => {
      lineBuffer += data.toString();
      const lines = lineBuffer.split('\n');
      lineBuffer = lines.pop();
      for (const line of lines) {
        if (!line.trim()) continue;
        try {
          const msg = JSON.parse(line.trim());
          switch (msg.type) {
            case 'frame':
              this.streamRelay.broadcastFrame(id, Buffer.from(msg.data, 'base64'));
              break;
            case 'log':
              console.log(`[Agent ${id.slice(0, 12)}] ${msg.text}`);
              break;
            case 'status':
              this.streamRelay.broadcastStatus(id, msg.status, msg.text);
              break;
            case 'reply':
              this.roomManager.broadcast(`channel:${id}`, {
                type: 'chat:message',
                id: `agent-${Date.now()}-${Math.random().toString(36).slice(2, 6)}`,
                channelId: id,
                sender: `🤖 ${this.agents.get(id)?.name || 'Agent'}`,
                text: msg.text,
                timestamp: Date.now(),
                isAgent: true,
              });
              break;
            case 'narrate':
              this.roomManager.broadcast(`channel:${id}`, {
                type: 'agent:narrate',
                channelId: id,
                text: msg.text,
                timestamp: Date.now(),
              });
              break;
            case 'stats':
              this.roomManager.broadcast(`channel:${id}`, {
                type: 'agent:stats',
                channelId: id,
                stats: {
                  uptime: msg.uptime,
                  memoryRss: msg.memoryRss,
                  memoryHeap: msg.memoryHeap,
                  cpuLoad: msg.cpuLoad,
                  frames: msg.frames,
                  apiCalls: msg.apiCalls,
                  platform: msg.platform,
                  nodeVersion: msg.nodeVersion,
                  pid: msg.pid,
                },
              });
              break;
            case 'ai-status':
              this.roomManager.broadcast(`channel:${id}`, {
                type: 'agent:ai-status',
                channelId: id,
                connected: msg.connected,
                provider: msg.provider,
                model: msg.model,
              });
              break;
            case 'ai-log':
              this.roomManager.broadcast(`channel:${id}`, {
                type: 'agent:ai-log',
                channelId: id,
                log: msg.log,
              });
              break;
          }
        } catch (e) { /* skip non-JSON */ }
      }
    });

    child.stderr.on('data', (data) => {
      const text = data.toString().trim();
      if (text) console.error(`[Agent ${id.slice(0, 12)}] ${text}`);
    });

    child.on('exit', (code, signal) => {
      console.log(`[Agent ${id.slice(0, 12)}] exit (code=${code}, signal=${signal})`);
      this.streamRelay.removeChannel(id);
      this.agents.delete(id);
      this.agentProcesses.delete(id);
      this.roomManager.broadcast(`channel:${id}`, { type: 'stream:ended', channelId: id });
    });

    child.on('error', (err) => {
      console.error(`[Agent ${id.slice(0, 12)}] error:`, err.message);
      this.streamRelay.removeChannel(id);
      this.agents.delete(id);
      this.agentProcesses.delete(id);
    });

    this.agents.set(id, { id, type, name: channelName, child, startedAt: Date.now() });
    this.agentProcesses.set(id, child);

    return { id, name: channelName, type, channelId: id };
  }

  stopAgent(id) {
    const child = this.agentProcesses.get(id);
    if (!child) return;
    child.kill('SIGTERM');
    setTimeout(() => {
      try { this.agentProcesses.get(id)?.kill('SIGKILL'); } catch {}
    }, 3000);
  }

  getChannels() { return this.streamRelay.getChannels(); }

  sendMessage(channelId, msg) {
    const child = this.agentProcesses.get(channelId);
    if (child?.stdin?.writable) {
      child.stdin.write(JSON.stringify({ type: 'chat:message', ...msg }) + '\n');
    }
  }

  sendCommand(channelId, command, sender) {
    const child = this.agentProcesses.get(channelId);
    if (child?.stdin?.writable) {
      child.stdin.write(JSON.stringify({ type: 'command', command, sender }) + '\n');
    }
  }
}
