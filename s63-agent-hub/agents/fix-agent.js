// Fix Agent — Lee errores de errors.jsonl, los analiza con IA, y aplica fixes
// Corre como child process. Recibe un error ID por stdin y lo procesa.

import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const ERROR_LOG = path.join(__dirname, '..', 'errors.jsonl');
const API_BASE = 'https://opencode.ai/zen/go/v1';
const API_KEY = process.env.OPENCODE_GO_API_KEY || '';
const MODEL = 'deepseek-v4-flash';

const AGENT_ID = process.env.AGENT_ID || 'fix-agent';
const CHANNEL_NAME = process.env.CHANNEL_NAME || '🔧 Fix Agent';

// ─── IPC ───────────────────────────────────────────────────────────
function send(type, data = {}) {
  process.stdout.write(JSON.stringify({ type, ...data }) + '\n');
}
const sendLog = (t) => send('log', { text: t });
const sendStatus = (s, t) => send('status', { status: s, text: t });
const reply = (t) => send('reply', { text: t });

// ─── Read/write errors ────────────────────────────────────────────
function getErrors() {
  try {
    return fs.readFileSync(ERROR_LOG, 'utf-8')
      .split('\n').filter(Boolean).map(line => JSON.parse(line));
  } catch { return []; }
}

function updateError(id, updates) {
  const errors = getErrors();
  const idx = errors.findIndex(e => e.id === id);
  if (idx === -1) return;
  errors[idx] = { ...errors[idx], ...updates, lastModified: Date.now() };
  fs.writeFileSync(ERROR_LOG, errors.map(e => JSON.stringify(e)).join('\n') + '\n');
}

// ─── LLM call ──────────────────────────────────────────────────────
async function callLLM(messages) {
  try {
    const res = await fetch(`${API_BASE}/chat/completions`, {
      method: 'POST',
      headers: { 'Authorization': `Bearer ${API_KEY}`, 'Content-Type': 'application/json' },
      body: JSON.stringify({ model: MODEL, messages, max_tokens: 2000, temperature: 0.1 }),
    });
    if (!res.ok) throw new Error(`API ${res.status}`);
    const data = await res.json();
    return data.choices?.[0]?.message?.content || '';
  } catch (e) {
    sendLog(`⚠️ LLM error: ${e.message}`);
    return '';
  }
}

// ─── Analyze error ─────────────────────────────────────────────────
async function analyzeError(error) {
  sendLog(`🔍 Analizando error: ${error.id}`);
  sendLog(`   Tipo: ${error.type}`);
  sendLog(`   Mensaje: ${error.message.slice(0, 100)}`);
  sendStatus('fixing', `Analizando error: ${error.type}`);

  const codeContext = '';
  const prompt = `Eres un ingeniero de software experto en debugging.

Error ID: ${error.id}
Tipo: ${error.type}
Mensaje: ${error.message}
Stack: ${error.stack?.slice(0, 1000) || 'N/A'}
Severidad: ${error.severity}
Fuente: ${error.source}
Contexto: ${JSON.stringify(error.context || {})}

Analiza este error y responde con un plan de fix en JSON:
{
  "rootCause": "Explicación de la causa raíz",
  "fixStrategy": "Qué hay que cambiar para arreglarlo",
  "filesToModify": ["ruta/archivo.js"],
  "fixCode": "Código de reemplazo o instrucciones detalladas",
  "testStrategy": "Cómo verificar que el fix funciona"
}

Si el error no tiene suficiente información para arreglarlo, responde:
{"rootCause":"insufficient_info","fixStrategy":"No hay suficiente información para diagnosticar"}`;

  const analysis = await callLLM([
    { role: 'system', content: 'Eres un debugger experto. Respondes SOLO con JSON.' },
    { role: 'user', content: prompt },
  ]);

  try {
    const plan = JSON.parse(analysis);
    sendLog(`📋 Análisis completo`);
    sendLog(`   Causa: ${plan.rootCause?.slice(0, 100)}`);
    sendLog(`   Estrategia: ${plan.fixStrategy?.slice(0, 100)}`);
    
    // Store the fix plan in the error
    updateError(error.id, {
      fixPlan: plan,
      status: plan.rootCause === 'insufficient_info' ? 'needs_review' : 'fix_ready',
    });
    
    return plan;
  } catch {
    sendLog(`⚠️ No pude parsear el análisis de la IA`);
    updateError(error.id, { status: 'needs_review', fixPlan: { raw: analysis } });
    return null;
  }
}

// ─── Apply fix ─────────────────────────────────────────────────────
async function applyFix(error, plan) {
  if (!plan || plan.rootCause === 'insufficient_info') {
    reply(`❌ Error ${error.id}: No hay suficiente información para arreglarlo`);
    return false;
  }

  sendLog(`🔧 Aplicando fix...`);
  sendStatus('fixing', `Aplicando fix: ${plan.fixStrategy?.slice(0, 60)}`);
  reply(`🔧 Arreglando error ${error.id}: ${plan.fixStrategy?.slice(0, 80)}...`);

  // For now, the fix agent analyzes but doesn't auto-apply changes
  // (to avoid making changes without review)
  // Instead, it writes the fix plan and marks as needs_review
  updateError(error.id, {
    status: 'needs_review',
    fixApplied: false,
    fixNote: 'Auto-fix plan generated. Review and approve before applying.',
  });

  reply(`✅ Plan de fix generado para error ${error.id}. Revisar en /errors`);
  sendLog(`✅ Fix plan ready. Error ${error.id} moved to needs_review`);
  return true;
}

// ─── Main ──────────────────────────────────────────────────────────
async function main() {
  const targetErrorId = process.argv[2]; // Optional: specific error ID to fix
  
  sendLog(`🚀 Fix Agent iniciando...`);
  sendStatus('starting', 'Revisando errores pendientes...');

  let errors;
  if (targetErrorId) {
    errors = getErrors().filter(e => e.id === targetErrorId);
    sendLog(`🎯 Procesando error específico: ${targetErrorId}`);
  } else {
    errors = getErrors().filter(e => e.status === 'open' || e.status === 'fix_ready');
    sendLog(`📊 ${errors.length} errores pendientes`);
  }

  if (errors.length === 0) {
    reply(`✅ No hay errores pendientes de arreglar`);
    sendLog(`🏁 No pending errors`);
    sendStatus('live', 'Sin errores pendientes');
    await new Promise(r => setTimeout(r, 3000));
    process.exit(0);
  }

  // Process errors by severity (critical first)
  const severityOrder = { critical: 0, error: 1, warning: 2, info: 3 };
  errors.sort((a, b) => (severityOrder[a.severity] || 99) - (severityOrder[b.severity] || 99));

  for (const error of errors) {
    sendLog(`\n📌 Procesando error ${error.id}: ${error.message.slice(0, 80)}`);
    reply(`📌 Procesando: ${error.message.slice(0, 80)}...`);
    
    // Mark as fixing
    updateError(error.id, { status: 'fixing' });
    
    const plan = await analyzeError(error);
    if (plan) {
      await applyFix(error, plan);
    } else {
      updateError(error.id, { status: 'needs_review' });
    }
    
    await new Promise(r => setTimeout(r, 1000));
  }

  reply(`✅ Fix Agent completó su ronda. ${errors.length} errores procesados.`);
  sendLog(`🏁 Fix Agent completed`);
  sendStatus('live', `Procesados ${errors.length} errores`);
  
  await new Promise(r => setTimeout(r, 5000));
  process.exit(0);
}

main().catch(e => {
  sendLog(`💥 ${e.message}`);
  process.exit(1);
});
