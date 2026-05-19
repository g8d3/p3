// Web Surfer — navegación basada en bucle de sitios seguros
import { BaseAgent } from './base-agent.js';

class WebSurfer extends BaseAgent {
  async decideAction() {
    // Si hay comandos pendientes, no decidir autónomamente
    if (this.pendingCommands.length > 0) return null;

    // Navegar a un sitio seguro aleatorio
    const sites = [
      'https://en.wikipedia.org/wiki/Special:Random',
      'https://news.ycombinator.com',
      'https://github.com/explore',
      'https://arxiv.org',
      'https://www.kernel.org',
    ];
    const url = sites[Math.floor(Math.random() * sites.length)];
    return { action: 'goto', args: url };
  }

  async onChatMessage(sender, text) {
    this.reply(`👋 ${sender}: gracias! Estoy explorando sitios web. Usa !goto, !click, !search.`);
  }
}

new WebSurfer().run();
