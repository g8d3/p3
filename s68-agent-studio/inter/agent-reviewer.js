#!/usr/bin/env node
/**
 * Reviewer Agent — Un agente que observa el trabajo de otros y da feedback
 *
 * Se conecta al Stage, elige un agente para observar,
 * analiza sus eventos en tiempo real, y le envía sugerencias.
 *
 * Este es el prototipo de "agentes que revisan agentes".
 */

import { AgentFeedback } from './agent-feedback.js';

const STAGE_URL = process.env.STAGE_URL || 'ws://localhost:3099';
const REVIEWER_ID = `reviewer-${Date.now()}`;
const REVIEWER_NAME = process.env.REVIEWER_NAME || '🔍 Code Reviewer';
const WATCH_AGENT_ID = process.env.WATCH_AGENT_ID || null; // null = revisar al primero disponible

async function main() {
  console.log(`
╔══════════════════════════════════════════════╗
║   🔍 Agent Studio — Reviewer Agent           ║
║                                              ║
║   Observa a developers trabajando            ║
║   y les da feedback en vivo.                 ║
╚══════════════════════════════════════════════╝
  `);

  const feedback = new AgentFeedback(STAGE_URL, REVIEWER_ID, REVIEWER_NAME, 'reviewer');
  await feedback.connect();
  feedback.emitStatus('idle', { role: 'reviewer' });

  // Si nos dijeron a quién observar, lo hacemos
  if (WATCH_AGENT_ID) {
    feedback.watch(WATCH_AGENT_ID);
    feedback.sendFeedback('👋 Hola, soy un Reviewer Agent. Estoy aquí para observarte y ayudarte si te atascas.');
  } else {
    console.log('[Reviewer] Esperando agentes disponibles...');
    
    // Esperar y buscar agentes cada 10s
    const interval = setInterval(async () => {
      try {
        const response = await fetch(`${STAGE_URL.replace(/^ws/, 'http')}/api/agents`);
        const agents = await response.json();
        const developers = agents.filter(a => a.type !== 'reviewer' && a.type !== 'helper' && a.status !== 'stopped');
        
        if (developers.length > 0 && !feedback.watching) {
          const target = developers[0];
          clearInterval(interval);
          feedback.watch(target.id);
          feedback.sendFeedback(`👋 Hola @${target.name || target.id}, soy un Reviewer Agent. Estoy aquí para ayudarte.`);
        }
      } catch {}
    }, 10000);
  }

  // Escuchar feedback dirigido a nosotros
  feedback.onFeedback((from, text) => {
    console.log(`[Reviewer] Feedback de ${from}: ${text}`);
  });

  // Escuchar intervenciones
  feedback.onIntervention((from, command, reason) => {
    console.log(`[Reviewer] Intervención de ${from}: ${command} (${reason})`);
    if (command === 'review:report') {
      feedback.sendFeedback('Generando reporte de calidad...');
      // Aquí generaría un reporte estructurado
    }
  });

  // Mantener vivo
  process.on('SIGINT', () => {
    feedback.close();
    process.exit(0);
  });

  console.log('[Reviewer] Listo. Presiona Ctrl+C para detener.');
}

main().catch(console.error);
