// LLM Web Surfer — navegación autónoma con IA (deepseek-v4-flash)
import { BaseAgent } from './base-agent.js';

class LLMWebSurfer extends BaseAgent {
  constructor() {
    super();
    this.taskDescription = 'Explora sitios web interesantes y variados. Sé curioso.';
    this.aiConnected = false;
  }

  async init() {
    // Test API key and connectivity
    this.sendLog('🔌 Probando conexión con IA...');
    this.sendStatus('starting', 'Conectando con IA...');
    this.aiConnected = false;
    this.aiProvider = 'opencode.go';
    this.aiModel = this.model;
    const test = await this.callLLM([
      { role: 'user', content: 'say only: OK' }
    ], 50);
    this.aiConnected = test.trim() === 'OK';
    if (this.aiConnected) {
      this.reply('✅ IA conectada (' + this.model + ')');
      this.sendLog('✅ IA conectada correctamente');
    } else {
      this.reply('⚠️ Sin conexión IA — uso modo exploración aleatoria');
      this.sendLog('⚠️ IA no disponible, usando fallback');
    }
    // Send AI status immediately
    this.send('ai-status', {
      connected: this.aiConnected,
      provider: this.aiProvider,
      model: this.aiModel,
    });
  }

  async decideAction() {
    if (this.pendingCommands.length > 0) return null;
    if (!this.page) return { action: 'wait', args: '2' };

    const title = await this.page.title();
    const url = this.page.url();
    const text = await this.page.evaluate(
      () => document.body?.innerText?.slice(0, 2000) || ''
    );

    const reply = await this.callLLM([
      { role: 'system', content: `Eres un agente de navegación curioso.
Tarea: ${this.taskDescription}
Siempre elige una acción activa. Responde SOLO JSON:
{"action":"goto|click|search|scroll|back","args":"..."}
- goto: URL completa (ej: "https://xkcd.com")
- click: texto del enlace (ej: "Read more")
- search: tema interesante
- scroll: "down"
- back: ""
Historial: ${this.navHistory.slice(-4).join(' → ') || 'inicio'}` },
      { role: 'user', content: `URL: ${url}\nTítulo: ${title}\n\n${text.slice(0,1500)}\n\n¿Qué acción?` },
    ]);

    try { return JSON.parse(reply); }
    catch {
      // Si la IA falla, ir a un sitio aleatorio
      const fallbacks = ['https://en.wikipedia.org/wiki/Special:Random', 'https://news.ycombinator.com'];
      return { action: 'goto', args: fallbacks[Math.floor(Math.random() * fallbacks.length)] };
    }
  }

  async onChatMessage(sender, text) {
    // Use real AI to respond to chat messages
    const reply = await this.callLLM([
      { role: 'system', content: `Eres un agente de IA en un stream en vivo.
Responde al usuario de forma breve, natural y amigable (máx 3 oraciones).
No uses markdown ni JSON.` },
      { role: 'user', content: `${sender} dice: ${text}` },
    ], 200);
    if (reply && reply.length > 5) {
      this.reply(`💬 ${reply}`);
    } else {
      this.reply(`👋 ${sender}: gracias por tu mensaje!`);
    }
  }
}

new LLMWebSurfer().run();
