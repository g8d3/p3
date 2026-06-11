// config.js — layered config merging for orquestar-agentes
// Modes: base (skill) → global (XDG) → local (project)
// Each overrides the previous.

const fs = require('fs');
const path = require('path');

const SKILL_DIR = path.resolve(__dirname, '..');
const XDG_CONFIG = process.env.XDG_CONFIG_HOME || path.join(process.env.HOME, '.config');
const XDG_DATA = process.env.XDG_DATA_HOME || path.join(process.env.HOME, '.local', 'share');
const XDG_STATE = process.env.XDG_STATE_HOME || path.join(process.env.HOME, '.local', 'state');

const BASE  = path.join(SKILL_DIR, 'cfg');
const GLOBAL_CONFIG = path.join(XDG_CONFIG, 'orquestar-agentes');
const GLOBAL_DATA   = path.join(XDG_DATA, 'orquestar-agentes');
const GLOBAL_STATE  = path.join(XDG_STATE, 'orquestar-agentes');
const LOCAL = '.orquestar-agentes';

const LOCATIONS = {
  base:  { config: BASE,                data: BASE,             state: '/tmp/agent-bus' },
  global:{ config: GLOBAL_CONFIG,       data: GLOBAL_DATA,      state: GLOBAL_STATE },
  local: { config: null,                data: null,             state: null }, // resolved per project
};

function readJSON(filePath) {
  try { return JSON.parse(fs.readFileSync(filePath, 'utf-8')); } catch { return null; }
}

function deepMerge(base, override) {
  const result = { ...base };
  for (const key of Object.keys(override || {})) {
    if (typeof override[key] === 'object' && !Array.isArray(override[key]) && typeof result[key] === 'object') {
      result[key] = deepMerge(result[key], override[key]);
    } else {
      result[key] = override[key];
    }
  }
  return result;
}

// Load project-local config by searching cwd and parents
function findLocalConfig(startDir) {
  let dir = path.resolve(startDir || process.cwd());
  for (let i = 0; i < 10; i++) { // max 10 levels up
    const cfg = path.join(dir, LOCAL, 'config.json');
    if (fs.existsSync(cfg)) return { dir: path.join(dir, LOCAL), config: readJSON(cfg) };
    const parent = path.dirname(dir);
    if (parent === dir) break;
    dir = parent;
  }
  return null;
}

// Ensure all XDG dirs exist
function ensureDirs() {
  for (const d of [GLOBAL_CONFIG, GLOBAL_DATA, GLOBAL_STATE]) {
    try { fs.mkdirSync(d, { recursive: true }); } catch {}
  }
}

function loadConfig(projectDir) {
  ensureDirs();

  // 1. Base (ships with skill)
  const base = readJSON(path.join(BASE, 'config.json')) || {};

  // 2. Global (XDG)
  const global = readJSON(path.join(GLOBAL_CONFIG, 'config.json')) || {};

  // 3. Local (project)
  const local = findLocalConfig(projectDir);

  let merged = deepMerge(base, global);
  if (local) merged = deepMerge(merged, local.config);

  return { merged, local: local?.dir || null, global: GLOBAL_CONFIG };
}

function saveGlobalConfig(config) {
  ensureDirs();
  fs.writeFileSync(path.join(GLOBAL_CONFIG, 'config.json'), JSON.stringify(config, null, 2));
}

function saveLocalConfig(config, projectDir) {
  const localDir = path.join(path.resolve(projectDir || process.cwd()), LOCAL);
  fs.mkdirSync(localDir, { recursive: true });
  fs.writeFileSync(path.join(localDir, 'config.json'), JSON.stringify(config, null, 2));
}

function readStats() {
  // Stats stored at global XDG data dir
  const p = path.join(GLOBAL_DATA, 'stats.json');
  try { return JSON.parse(fs.readFileSync(p, 'utf-8')); } catch { return {}; }
}

function saveStats(stats) {
  try {
    fs.mkdirSync(GLOBAL_DATA, { recursive: true });
    fs.writeFileSync(path.join(GLOBAL_DATA, 'stats.json'), JSON.stringify(stats, null, 2));
  } catch (e) { /* ignore write errors */ }
}

module.exports = {
  LOCATIONS, GLOBAL_CONFIG, GLOBAL_DATA, GLOBAL_STATE, BASE,
  loadConfig, saveGlobalConfig, saveLocalConfig,
  readStats, saveStats, findLocalConfig,
};
