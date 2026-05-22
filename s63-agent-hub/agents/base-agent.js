// Base Agent — clase base para todos los agentes
// Proporciona: IPC, browser, screenshot loop, narración, stats, chat, stdin, stealth
// Cada agente extiende esta clase e implementa decideAction()

import { chromium } from 'playwright';
import readline from 'readline';
import os from 'os';

const SAFE_SITES = [
  { url: 'https://en.wikipedia.org/wiki/Special:Random', label: 'Wikipedia' },
  { url: 'https://news.ycombinator.com', label: 'Hacker News' },
  { url: 'https://github.com/explore', label: 'GitHub Explore' },
  { url: 'https://arxiv.org', label: 'arXiv' },
  { url: 'http://info.cern.ch/hypertext/WWW/TheProject.html', label: 'First Website' },
  { url: 'https://www.kernel.org', label: 'Linux Kernel' },
  { url: 'https://xkcd.com', label: 'xkcd' },
];

export class BaseAgent {
  constructor() {
    this.agentId = process.env.AGENT_ID || 'unknown';
    this.channelName = process.env.CHANNEL_NAME || 'Agent';
    this.apiKey = process.env.OPENCODE_GO_API_KEY || '';
    this.apiBase = 'https://opencode.ai/zen/go/v1';
    this.model = 'deepseek-v4-flash';
    this.startTime = Date.now();
    this.apiCalls = 0;
    this.frameCount = 0;
    this.actionCount = 0;
    this.pendingCommands = [];
    this.navHistory = [];
    this.browser = null;
    this.page = null;
  }

  // ─── IPC ─────────────────────────────────────────────────────────
  send(type, data = {}) { process.stdout.write(JSON.stringify({ type, ...data }) + '\n'); }
  sendFrame(b) { this.send('frame', { data: b.toString('base64') }); }
  sendLog(t) { this.send('log', { text: t }); }
  sendStatus(s, t) { this.send('status', { status: s, text: t }); }
  reply(t) { this.send('reply', { text: t }); }
  narrate(t) { this.send('narrate', { text: t }); }

  sendStats() {
    const mem = process.memoryUsage();
    const uptime = Math.floor((Date.now() - this.startTime) / 1000);
    this.send('stats', {
      uptime, apiCalls: this.apiCalls, frames: this.frameCount,
      memoryRss: Math.round(mem.rss / 1024 / 1024),
      memoryHeap: Math.round(mem.heapUsed / 1024 / 1024),
      cpuLoad: os.loadavg()[0].toFixed(1),
      platform: process.platform,
      nodeVersion: process.version,
      pid: process.pid,
    });
  }

  // ─── Stdin (chat + commands) ─────────────────────────────────────
  setupStdin() {
    const rl = readline.createInterface({ input: process.stdin });
    rl.on('line', (line) => {
      try {
        const msg = JSON.parse(line.trim());
        if (msg.type === 'chat:message') {
          this.sendLog(`💬 ${msg.sender}: ${msg.text}`);
          if (!msg.text.startsWith('!') && msg.sender !== 'system') {
            this.onChatMessage(msg.sender.slice(0, 6), msg.text);
          }
        } else if (msg.type === 'command') {
          this.pendingCommands.push(msg.command);
        }
      } catch (e) {}
    });
  }

  // Override this for custom chat responses
  async onChatMessage(sender, text) {
    this.reply(`👋 ${sender}: gracias por escribir! Estoy explorando. Usa !goto, !click o !search.`);
  }

  // ─── Browser ─────────────────────────────────────────────────────
  async launchBrowser() {
    this.sendLog(`🚀 "${this.channelName}" iniciando...`);
    this.narrate(`Hola! Soy ${this.channelName}, empezando a navegar...`);
    this.sendStatus('starting', 'Lanzando navegador...');

    this.browser = await chromium.launch({
      headless: true,
      args: ['--no-sandbox', '--disable-setuid-sandbox', '--disable-dev-shm-usage',
             '--disable-gpu', '--disable-blink-features=AutomationControlled'],
    });

    const ctx = await this.browser.newContext({
      viewport: { width: 1280, height: 720 },
      userAgent: 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
      locale: 'en-US',
    });
    await ctx.addInitScript(() => {
      Object.defineProperty(navigator, 'webdriver', { get: () => false });
    });
    this.page = await ctx.newPage();
  }

  // ─── Navigation helpers ──────────────────────────────────────────
  async goto(url) {
    if (!url.startsWith('http')) url = 'https://' + url;
    this.narrate(`Navegando a ${url}...`);
    this.sendStatus('navigating', `Yendo a ${url}...`);
    this.sendLog(`🌐 Navegando a: ${url}`);
    try {
      await this.page.goto(url, { waitUntil: 'domcontentloaded', timeout: 15000 });
      this.navHistory.push(url);
      const title = await this.page.title();
      this.reply(`✅ Navegué a: ${url}`);
      this.narrate(`Listo, estoy viendo ${title || url}`);
      this.sendStatus('live', 'Transmitiendo en vivo');
    } catch (e) {
      this.reply(`❌ Error: ${e.message.slice(0, 80)}`);
      this.narrate(`No pude cargar la página`);
    }
  }

  async click(target) {
    if (!target) { this.reply('ℹ️ Usa: !click <texto>'); return; }
    this.narrate(`Buscando "${target}"...`);
    try {
      let el = this.page.locator(`a:has-text("${target}")`).first();
      if (await el.count() > 0) {
        await el.click({ timeout: 5000 });
        await new Promise(r => setTimeout(r, 1500));
        this.navHistory.push(this.page.url());
        this.reply(`✅ Click en "${target}"`);
        this.narrate(`Hice click en "${target}"`);
      } else {
        el = this.page.locator(`button:has-text("${target}")`).first();
        if (await el.count() > 0) {
          await el.click({ timeout: 5000 });
          await new Promise(r => setTimeout(r, 1500));
          this.reply(`✅ Click en botón "${target}"`);
          this.narrate(`Presioné el botón "${target}"`);
        } else {
          this.reply(`❌ No encontré "${target}"`);
          this.narrate(`No encontré "${target}"`);
        }
      }
    } catch (e) { this.reply(`❌ Error: ${e.message.slice(0, 80)}`); }
  }

  async search(query) {
    if (!query) { this.reply('ℹ️ Usa: !search <consulta>'); return; }
    this.narrate(`Buscando "${query}"...`);
    this.sendStatus('navigating', `Buscando: ${query}...`);
    try {
      await this.page.goto(`https://www.google.com/search?q=${encodeURIComponent(query)}`,
        { waitUntil: 'domcontentloaded', timeout: 15000 });
      this.navHistory.push(this.page.url());
      this.reply(`🔍 Buscando "${query}"`);
      this.narrate(`Resultados para "${query}"`);
      this.sendStatus('live', 'Transmitiendo en vivo');
    } catch (e) { this.reply(`❌ Error: ${e.message.slice(0, 80)}`); }
  }

  async goBack() {
    if (this.navHistory.length < 2) { this.reply('ℹ️ No hay páginas anteriores'); return; }
    this.navHistory.pop();
    this.narrate(`Volviendo atrás...`);
    await this.page.goto(this.navHistory[this.navHistory.length - 1],
      { waitUntil: 'domcontentloaded', timeout: 15000 });
    this.reply('⬅️ Volví atrás');
    this.narrate(`De vuelta en la página anterior`);
  }

  async scroll(dir) {
    await this.page.evaluate((a) => window.scrollBy(0, a), dir === 'up' ? -500 : 500);
    this.narrate(`Desplazándome ${dir || 'abajo'}`);
    this.reply(`📜 Scroll ${dir || 'down'}`);
  }

  // ─── Random navigation (fallback for idle) ───────────────────────
  async navigateRandom() {
    const site = SAFE_SITES[Math.floor(Math.random() * SAFE_SITES.length)];
    this.narrate(`Explorando ${site.label}...`);
    this.sendLog(`🌐 Explorando: ${site.label}`);
    this.sendStatus('navigating', `Visitando ${site.label}...`);
    try {
      await this.page.goto(site.url, { waitUntil: 'domcontentloaded', timeout: 15000 });
      this.navHistory.push(site.url);
      await new Promise(r => setTimeout(r, 1000));
      this.narrate(`Estoy viendo ${await this.page.title() || site.label}`);
      this.sendStatus('live', 'Transmitiendo en vivo');
    } catch (e) { this.sendLog(`⚠️ ${e.message}`); }
  }

  // ─── LLM API helper ──────────────────────────────────────────────
  async callLLM(messages, maxTokens = 400) {
    if (!this.apiKey) return '';
    this.apiCalls++;
    const start = Date.now();
    try {
      const res = await fetch(`${this.apiBase}/chat/completions`, {
        method: 'POST',
        headers: { 'Authorization': `Bearer ${this.apiKey}`, 'Content-Type': 'application/json' },
        body: JSON.stringify({ model: this.model, messages, max_tokens: maxTokens, temperature: 0.3 }),
      });
      const duration = Date.now() - start;
      if (!res.ok) throw new Error(`API ${res.status}`);
      const data = await res.json();
      const reply = data.choices?.[0]?.message?.content || '';
      // Store in request log (keep last 50)
      if (!this._aiLog) this._aiLog = [];
      this._aiLog.push({
        ts: start, duration,
        prompt: messages[messages.length - 1]?.content?.slice(0, 200) || '',
        response: reply.slice(0, 200),
        model: this.model,
      });
      if (this._aiLog.length > 50) this._aiLog.shift();
      return reply;
    } catch (e) {
      this.sendLog(`⚠️ LLM: ${e.message}`);
      return '';
    }
  }

  // ─── Each agent implements this ──────────────────────────────────
  async decideAction() {
    // Returns { action: "goto|click|search|scroll|back|wait|done", args: "..." }
    // Default: visit a random safe site
    const site = SAFE_SITES[Math.floor(Math.random() * SAFE_SITES.length)];
    return { action: 'goto', args: site.url };
  }

  // ─── Process commands from stdin ─────────────────────────────────
  async processCommands() {
    const handlers = {
      '!goto': async (a) => { if (a) await this.goto(a); },
      '!click': async (a) => { if (a) await this.click(a); },
      '!search': async (a) => { if (a) await this.search(a); },
      '!back': async () => { await this.goBack(); },
      '!scroll': async (a) => { await this.scroll(a); },
      '!stats': async () => { this.sendStats(); this.reply('📊 Estadísticas enviadas'); },
      '!ai-log': async () => {
        if (!this._aiLog || this._aiLog.length === 0) { this.reply('📋 No hay requests IA aún'); return; }
        const log = this._aiLog.slice(-10).map(r =>
          `[${new Date(r.ts).toLocaleTimeString()} ${r.duration}ms] ${r.prompt.slice(0,60)} → ${r.response.slice(0,60)}`
        ).join('\n');
        this.reply(`📋 Últimos ${Math.min(10, this._aiLog.length)} requests:\n${log}`);
        this.send('ai-log', { log: this._aiLog.slice(-20) });
      },
    };

    while (this.pendingCommands.length > 0) {
      const line = this.pendingCommands.shift();
      const parts = line.trim().split(/\s+/);
      const cmd = parts[0].toLowerCase();
      const args = parts.slice(1).join(' ');
      const handler = handlers[cmd];
      if (handler) await handler(args);
      else this.reply(`ℹ️ Comandos: !goto, !click, !search, !back, !scroll`);
      await new Promise(r => setTimeout(r, 300));
    }
  }

  // ─── Init hook (override to test API keys, etc.) ────────────────
  async init() { /* override in subclasses */ }

  // ─── Main loop ───────────────────────────────────────────────────
  async run() {
    this.setupStdin();
    await this.init();  // ← Hook for subclasses
    await this.launchBrowser();

    this.sendStatus('live', 'Transmitiendo en vivo');
    this.sendLog(`🎥 Transmitiendo como "${this.channelName}"`);
    this.reply(`✅ ${this.channelName} conectado! Usa !goto, !click, !search, !back, !scroll`);

    let idleTicks = 0;

    while (true) {
      try {
        if (this.pendingCommands.length > 0) {
          await this.processCommands();
          idleTicks = 0;
        }

        // Take screenshot
        const screenshot = await this.page.screenshot({ type: 'jpeg', quality: 35 });
        this.sendFrame(screenshot);
        this.frameCount++;

        // Every 25 frames, let the agent decide an action
        if (this.frameCount % 25 === 0 && this.pendingCommands.length === 0) {
          const decision = await this.decideAction();
          if (decision) {
            this.sendLog(`🧠 ${decision.action}: ${decision.args || ''}`);
            await this.executeAction(decision);
            this.actionCount++;
          }
        }

        // Idle: random navigation every 60 frames
        idleTicks++;
        if (idleTicks >= 60 && this.pendingCommands.length === 0) {
          await this.navigateRandom();
          idleTicks = 0;
        }

        // Stats + narration every 150 frames
        if (this.frameCount % 150 === 0) {
          this.sendLog(`📊 ${this.frameCount} frames · ${this.actionCount} acciones`);
          this.sendStats();
          this.narrate(`Ya llevo ${this.frameCount} frames transmitidos`);
        }

        await new Promise(r => setTimeout(r, 200));
      } catch (e) {
        this.sendLog(`❌ ${e.message}`);
        try { await this.page.goto('about:blank', { timeout: 3000 }); } catch {}
        await new Promise(r => setTimeout(r, 2000));
      }
    }
  }

  // ─── Execute a decision action ───────────────────────────────────
  async executeAction(decision) {
    const { action, args } = decision || {};
    try {
      switch (action) {
        case 'goto': await this.goto(args); break;
        case 'click': await this.click(args); break;
        case 'search': await this.search(args); break;
        case 'scroll': await this.scroll(args); break;
        case 'back': await this.goBack(); break;
        case 'wait': await new Promise(r => setTimeout(r, (parseInt(args) || 2) * 1000)); break;
        case 'done': this.reply(`✅ ${args || 'Completado'}`); this.narrate(`Misión completa`); break;
        default: this.sendLog(`⚠️ Acción desconocida: ${action}`);
      }
    } catch (e) { this.sendLog(`⚠️ ${action}: ${e.message}`); }
    this.sendStatus('live', 'Transmitiendo en vivo');
  }
}
