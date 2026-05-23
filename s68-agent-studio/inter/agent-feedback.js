/**
 * Inter — Sistema de Feedback e Intervención entre Agentes
 *
 * Permite que un agente (o humano) observe el trabajo de otro agente
 * y le envíe feedback, sugerencias o incluso comandos de intervención.
 *
 * Esto es el corazón de la colaboración entre agentes:
 * - Un Reviewer Agent puede ver el stream de un Worker Agent
 * - Si el worker se traba, el reviewer puede sugerirle cómo seguir
 * - Si el worker comete un error, el reviewer puede corregirlo
 * - Los humanos también participan en el mismo canal
 */

import { SandboxAgent } from 'sandbox-agent';
import { WebSocket } from 'ws';

export class AgentFeedback {
  /**
   * @param {string} stageUrl - URL del Stage server (ws://host:port)
   * @param {string} agentId - ID único de este agente
   * @param {string} agentName - Nombre visible
   * @param {string} agentType - Tipo (reviewer, helper, supervisor)
   */
  constructor(stageUrl, agentId, agentName, agentType = 'reviewer') {
    this.stageUrl = stageUrl.replace(/^http/, 'ws');
    this.agentId = agentId;
    this.agentName = agentName;
    this.agentType = agentType;
    this.ws = null;
    this.watching = null; // agentId al que estamos observando
    this.feedbackListeners = [];
    this.interventionListeners = [];
  }

  /**
   * Conecta al Stage para recibir eventos y enviar feedback
   */
  connect() {
    return new Promise((resolve, reject) => {
      this.ws = new WebSocket(this.stageUrl);
      
      this.ws.on('open', () => {
        console.log(`[${this.agentName}] Conectado al Stage`);
        
        // Registrarse como agente
        this._send('agents:register', {
          agentId: this.agentId,
          name: this.agentName,
          type: this.agentType,
        });
        
        resolve();
      });

      this.ws.on('message', (raw) => {
        try {
          const msg = JSON.parse(raw.toString());
          this._handleMessage(msg);
        } catch {}
      });

      this.ws.on('error', reject);
      this.ws.on('close', () => {
        console.log(`[${this.agentName}] Desconectado del Stage`);
        // Reconectar después de 3s
        setTimeout(() => this.connect(), 3000);
      });
    });
  }

  /**
   * Empieza a observar a otro agente
   */
  watch(agentId) {
    this.watching = agentId;
    this._send('watch:agent', { agentId });
    console.log(`[${this.agentName}] Observando a ${agentId}`);
  }

  /**
   * Deja de observar
   */
  unwatch() {
    if (this.watching) {
      this._send('unwatch:agent', { agentId: this.watching });
      this.watching = null;
    }
  }

  /**
   * Envía feedback al agente que estamos observando
   */
  sendFeedback(text) {
    if (!this.watching) {
      console.log(`[${this.agentName}] No estoy observando a nadie`);
      return;
    }
    this._send('feedback', {
      agentId: this.watching,
      from: `${this.agentName} 🤖`,
      text,
      isAgent: true,
    });
  }

  /**
   * Interviene directamente: envía un comando al agente
   */
  intervene(command, reason = '') {
    if (!this.watching) return;
    this._send('intervene', {
      agentId: this.watching,
      from: `${this.agentName} 🤖`,
      command,
      reason,
    });
  }

  /**
   * Escucha feedback dirigido a este agente
   */
  onFeedback(callback) {
    this.feedbackListeners.push(callback);
  }

  /**
   * Escucha intervenciones dirigidas a este agente
   */
  onIntervention(callback) {
    this.interventionListeners.push(callback);
  }

  /**
   * Envía un evento de estado
   */
  emitStatus(status, meta = {}) {
    this._send('agent:status', {
      agentId: this.agentId,
      status,
      meta: { name: this.agentName, type: this.agentType, ...meta },
    });
  }

  _send(type, data) {
    if (this.ws?.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify({ type, ...data }));
    }
  }

  _handleMessage(msg) {
    // Feedback para mí
    if (msg.type === 'agent:feedback' && msg.agentId === this.agentId) {
      for (const cb of this.feedbackListeners) {
        cb(msg.from, msg.text, msg);
      }
    }

    // Intervención para mí
    if (msg.type === 'agent:intervene' && msg.agentId === this.agentId) {
      for (const cb of this.interventionListeners) {
        cb(msg.from, msg.command, msg.reason, msg);
      }
    }

    // Eventos del agente que estoy observando
    if (msg.type === 'agent:event' && msg.agentId === this.watching) {
      // El agente revisor procesa estos eventos
      this._processObservedEvent(msg.event);
    }
  }

  _processObservedEvent(event) {
    // Lógica básica de revisión:
    // Si el agente observado tiene un error, sugerir solución
    // Si está mucho tiempo sin actividad, preguntar si necesita ayuda
    // Si repite el mismo patrón, sugerir optimización
    
    switch (event.type) {
      case 'error':
        this.sendFeedback(`Veo que tienes un error: ${event.data?.message || 'desconocido'}. ¿Necesitas ayuda para resolverlo?`);
        break;
        
      case 'tool_call':
        // Si es un tool_call que ya vimos muchas veces, es un loop
        this._toolCallCount = this._toolCallCount || new Map();
        const title = event.data?.title || 'unknown';
        const count = (this._toolCallCount.get(title) || 0) + 1;
        this._toolCallCount.set(title, count);
        
        if (count > 10) {
          this.sendFeedback(`Noto que has ejecutado "${title}" ${count} veces. ¿Estás en un loop? Prueba con un enfoque diferente.`);
          this._toolCallCount.set(title, 0); // Reset para no spam
        }
        break;
    }
  }

  close() {
    this.unwatch();
    this.ws?.close();
  }
}


/**
 * Helper Agent — Un agente que se spawnea para ayudar a otro
 */
export class HelperAgent {
  constructor(stageUrl, agentId, name) {
    this.feedback = new AgentFeedback(stageUrl, agentId, name, 'helper');
  }

  async start(watchAgentId) {
    await this.feedback.connect();
    this.feedback.watch(watchAgentId);
    this.feedback.emitStatus('standby', { role: 'helper', watching: watchAgentId });
    
    this.feedback.onIntervention((from, command, reason) => {
      console.log(`[Helper] ${from} me pide: ${command} (${reason})`);
    });
  }

  /**
   * Ejecuta una investigación y reporta resultados
   */
  async investigate(sdk, task) {
    this.feedback.emitStatus('working', { phase: 'investigating' });
    
    const session = await sdk.createSession({
      agent: 'claude',
      cwd: '/workspace',
    });

    return session;
  }
}
