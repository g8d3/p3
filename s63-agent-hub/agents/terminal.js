// Terminal Agent v2 — readline stdin, chat replies
import { chromium } from 'playwright';
import { execSync } from 'child_process';
import readline from 'readline';

const AGENT_ID = process.env.AGENT_ID || 'unknown';
const CHANNEL_NAME = process.env.CHANNEL_NAME || 'Terminal';

let browser, page, cwd = process.env.HOME || '/', pendingCommands = [];

function send(type, data = {}) {
  process.stdout.write(JSON.stringify({ type, ...data }) + '\n');
}
const sendFrame = (b) => send('frame', { data: b.toString('base64') });
const sendLog = (t) => send('log', { text: t });
const sendStatus = (s, t) => send('status', { status: s, text: t });
const reply = (t) => send('reply', { text: t });

// ─── Readline stdin ───────────────────────────────────────────────
const rl = readline.createInterface({ input: process.stdin });
rl.on('line', (line) => {
  try {
    const msg = JSON.parse(line.trim());
    if (msg.type === 'chat:message') sendLog(`💬 ${msg.sender}: ${msg.text}`);
    else if (msg.type === 'command') pendingCommands.push(msg.command);
  } catch (e) {}
});

// ─── Terminal ─────────────────────────────────────────────────────
function stripAnsi(s) { return s.replace(/\x1b\[[0-9;]*[a-zA-Z]/g, ''); }

function addLine(text, cls = 'output') {
  page.evaluate(([t, c]) => { window.addLine(t, c); window.setCursor(true); }, [stripAnsi(text), cls]).catch(() => {});
}

function clearTerm() {
  page.evaluate(() => window.clearTerm()).catch(() => {});
}

async function runCommand(cmd) {
  if (!cmd.trim()) return;
  const prompt = `${process.env.USER || 'agent'}@twitch:${cwd === process.env.HOME ? '~' : cwd.split('/').pop() || '/'}$ `;
  addLine(`${prompt}${cmd}`, 'input-line');
  try {
    const result = execSync(cmd, { cwd, encoding: 'utf-8', timeout: 10000, maxBuffer: 1024 * 1024 });
    if (result.trim()) {
      for (const line of result.trimEnd().split('\n')) addLine(line, 'output');
    }
  } catch (e) {
    if (e.stdout) for (const line of e.stdout.toString().trimEnd().split('\n')) addLine(line, 'output');
    if (e.stderr) for (const line of e.stderr.toString().trimEnd().split('\n')) addLine(line, 'error');
    if (e.status !== null) addLine(`exit code ${e.status}`, 'error');
  }
  try { cwd = execSync('pwd', { cwd, encoding: 'utf-8', timeout: 2000 }).trim(); } catch {}
}

async function processCommands() {
  while (pendingCommands.length > 0) {
    const line = pendingCommands.shift();
    const parts = line.trim().split(/\s+/);
    const cmd = parts[0].toLowerCase();
    const args = parts.slice(1).join(' ');

    switch (cmd) {
      case '!run':
        await runCommand(args);
        reply(`✅ Comando ejecutado`);
        break;
      case '!clear':
        clearTerm();
        reply('🧹 Terminal limpiada');
        break;
      case '!cd':
        if (args) { await runCommand(`cd ${args}`); reply(`📂 cd ${args}`); }
        break;
      default:
        reply(`ℹ️ Comandos: !run <cmd>, !clear, !cd <dir>`);
    }
  }
}

async function main() {
  sendLog(`🚀 "${CHANNEL_NAME}" iniciando...`);
  sendStatus('starting', 'Cargando terminal...');

  browser = await chromium.launch({
    headless: true,
    args: ['--no-sandbox', '--disable-setuid-sandbox', '--disable-dev-shm-usage'],
  });
  const ctx = await browser.newContext({ viewport: { width: 1280, height: 720 } });
  page = await ctx.newPage();
  await page.goto('http://localhost:3001/terminal.html', { waitUntil: 'networkidle', timeout: 10000 });

  addLine(`Bienvenido a Agent Twitch Terminal`, 'info');
  addLine(`Directorio: ${cwd}`, 'info');
  addLine('', 'output');

  sendStatus('live', 'Transmitiendo terminal');
  reply(`✅ Terminal conectada! Usa !run <cmd>, !clear, !cd <dir>`);

  let frameCount = 0;

  while (true) {
    try {
      if (pendingCommands.length > 0) await processCommands();

      const screenshot = await page.screenshot({ type: 'jpeg', quality: 30 });
      sendFrame(screenshot);
      frameCount++;

      if (frameCount % 60 === 0) sendLog(`📊 ${frameCount} frames`);
      await new Promise(r => setTimeout(r, 300));
    } catch (e) {
      sendLog(`❌ ${e.message}`);
      await new Promise(r => setTimeout(r, 2000));
    }
  }
}

main().catch(e => { sendLog(`💥 ${e.message}`); process.exit(1); });
