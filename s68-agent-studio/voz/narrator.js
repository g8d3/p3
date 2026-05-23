/**
 * Voz — Narrador del agente
 *
 * Convierte eventos del agente en narración hablada y subtítulos.
 * Cuando el agente codea, el narrador describe lo que está pasando.
 *
 * Esto es lo que permite:
 * - Generar videos con voz en off después
 * - Subtítulos en vivo en el stream
 * - Traducción a múltiples idiomas
 * - Diferentes voces para diferentes tipos de evento
 *
 * Integración futura con TTS real (Inworld, ElevenLabs, Kokoro, etc.)
 */

export class Narrator {
  constructor(options = {}) {
    this.lang = options.lang || 'es';
    this.voice = options.voice || 'default';
    this.narrationListeners = [];
  }

  /**
   * Genera narración a partir de un evento del agente
   */
  narrate(event, agentName = 'Developer') {
    const { type, data } = event;
    let text = '';

    switch (type) {
      case 'tool_call':
        text = this._narrateToolCall(data, agentName);
        break;
      case 'tool_call_update':
        text = this._narrateToolResult(data);
        break;
      case 'agent_message':
        text = this._narrateMessage(data, agentName);
        break;
      case 'agent_thought':
        text = this._narrateThought(data);
        break;
      case 'plan':
        text = this._narratePlan(data);
        break;
      case 'error':
        text = this._narrateError(data);
        break;
      case 'screenshot':
        text = this._narrateScreenshot();
        break;
      default:
        return null; // No narrar eventos irrelevantes
    }

    if (text) {
      for (const cb of this.narrationListeners) {
        cb(text, type, event);
      }
    }

    return text;
  }

  /**
   * Escucha narraciones generadas
   */
  onNarration(callback) {
    this.narrationListeners.push(callback);
  }

  _narrateToolCall(data, agentName) {
    const title = data?.title || '';
    const toolName = data?.toolName || '';
    
    // Simplificar el título para narración
    const actions = {
      'Read': 'leyendo',
      'Write': 'escribiendo',
      'Edit': 'editando',
      'Search': 'buscando',
      'Run': 'ejecutando',
      'Create': 'creando',
      'Delete': 'eliminando',
      'List': 'listando',
      'Replace': 'reemplazando',
      'Bash': 'ejecutando comando en terminal',
      'Execute': 'ejecutando',
    };

    for (const [key, verb] of Object.entries(actions)) {
      if (title.startsWith(key) || toolName.startsWith(key)) {
        return `${agentName} está ${verb} ${title.slice(key.length).trim() || '...'}`;
      }
    }

    return `${agentName} ejecuta: ${title || toolName || 'una herramienta'}`;
  }

  _narrateToolResult(data) {
    const status = data?.status;
    if (status === 'completed') return null; // No narrar éxitos mundanos
    if (status === 'error') return `La operación falló: ${data?.error || 'error desconocido'}`;
    return null;
  }

  _narrateMessage(data, agentName) {
    const text = data?.content?.text || data?.content || '';
    if (!text) return null;
    
    // Solo narrar mensajes cortos (< 100 chars) o que parezcan decisiones
    const clean = text.replace(/```[\s\S]*?```/g, '').trim();
    if (clean.length > 200) return null;
    if (clean.length < 10) return null;
    
    return `${agentName} dice: ${clean}`;
  }

  _narrateThought(data) {
    const text = data?.content?.text || data?.content || '';
    if (!text) return null;
    
    const clean = text.replace(/```[\s\S]*?```/g, '').trim();
    if (clean.length > 300) return clean.slice(0, 300) + '...';
    return clean;
  }

  _narratePlan(data) {
    const entries = data?.entries || [];
    const pending = entries.filter(e => e.status !== 'completed');
    if (pending.length === 0) return null;
    
    const nextSteps = pending.slice(0, 3).map(e => e.content).join(', ');
    return `Plan: ${pending.length} pasos pendientes. Siguiente: ${nextSteps}`;
  }

  _narrateError(data) {
    return `Error: ${data?.message || 'algo salió mal'}. El agente va a intentar resolverlo.`;
  }

  _narrateScreenshot() {
    return null; // No narrar screenshots individualmente
  }
}


/**
 * Generador de subtítulos SRT desde un trace
 */
export function generateSubtitles(traceEvents, narrator) {
  const subtitles = [];
  let index = 1;
  let currentTime = 0;

  for (const event of traceEvents) {
    const text = narrator.narrate(event);
    if (!text) {
      currentTime += 0.5; // saltar 0.5s por evento no narrado
      continue;
    }

    const duration = Math.max(2, Math.min(8, text.length * 0.05)); // 50ms por char
    const start = currentTime;
    const end = currentTime + duration;
    currentTime = end + 0.3; // 300ms de pausa entre subtítulos

    subtitles.push({ index, start, end, text });
    index++;
  }

  return subtitles;
}

/**
 * Convierte subtítulos a formato SRT
 */
export function subtitlesToSRT(subtitles) {
  function fmt(seconds) {
    const h = Math.floor(seconds / 3600);
    const m = Math.floor((seconds % 3600) / 60);
    const s = seconds % 60;
    const ms = Math.floor((s % 1) * 1000);
    return `${String(h).padStart(2, '0')}:${String(m).padStart(2, '0')}:${String(Math.floor(s)).padStart(2, '0')},${String(ms).padStart(3, '0')}`;
  }

  return subtitles.map(s =>
    `${s.index}\n${fmt(s.start)} --> ${fmt(s.end)}\n${s.text}\n`
  ).join('\n');
}
