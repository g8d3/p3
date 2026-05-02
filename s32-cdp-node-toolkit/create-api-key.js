#!/usr/bin/env node
/**
 * create-api-key.js
 *
 * Automates API key creation for AI services with free tiers.
 * Uses a hybrid approach: API-first, browser fallback, LLM as last resort.
 *
 * Usage:
 *   node create-api-key.js [options] <service>
 *
 * Options:
 *   --save-to <backend>   Where to save the key: env, zshrc, bitwarden (default: env)
 *   --key-name <name>     Name for the API key (default: auto-generated)
 *   --llm-base-url <url>  OpenAI-compatible LLM URL (for selector discovery)
 *   --llm-api-key <key>   LLM API key
 *   --llm-model <model>   LLM model (default: gpt-4o-mini)
 *   --port <n>            CDP port (default: 9222)
 *   --no-llm              Skip LLM fallback
 *   --dry-run             Don't create key, just show what would happen
 *
 * Storage backends:
 *   env      → appends to .env file in current directory
 *   zshrc    → appends export to ~/.zshrc
 *   bitwarden→ creates item via `bw` CLI
 *
 * Examples:
 *   node create-api-key.js groq
 *   node create-api-key.js --save-to zshrc groq
 *   node create-api-key.js --save-to bitwarden --key-name prod-key openai
 */

const http = require("http");
const https = require("https");
const fs = require("fs");
const path = require("path");
const { execSync } = require("child_process");
const WebSocket = require("ws");

// ─── Config ─────────────────────────────────────────────────────────────────

const DIR = __dirname;
const CSV_PATH = path.join(DIR, "ai-services.csv");
const KEYS_OUTPUT = path.join(DIR, "api-keys.csv");
const CDP_PORT = 9222;

// ─── CLI ────────────────────────────────────────────────────────────────────

function parseArgs(argv) {
  const args = { port: CDP_PORT, saveTo: "env", noLlm: false, dryRun: false };
  const positional = [];
  for (let i = 2; i < argv.length; i++) {
    switch (argv[i]) {
      case "--save-to": args.saveTo = argv[++i]; break;
      case "--key-name": args.keyName = argv[++i]; break;
      case "--llm-base-url": args.llmBaseUrl = argv[++i]; break;
      case "--llm-api-key": args.llmApiKey = argv[++i]; break;
      case "--llm-model": args.llmModel = argv[++i]; break;
      case "--port": args.port = Number(argv[++i]); break;
      case "--no-llm": args.noLlm = true; break;
      case "--dry-run": args.dryRun = true; break;
      default: positional.push(argv[i]);
    }
  }
  args.service = positional[0];
  args.llmBaseUrl = args.llmBaseUrl || process.env.LLM_BASE_URL;
  args.llmApiKey = args.llmApiKey || process.env.LLM_API_KEY;
  args.llmModel = args.llmModel || process.env.LLM_MODEL || "gpt-4o-mini";
  return args;
}

// ─── CSV ────────────────────────────────────────────────────────────────────

// RFC 4180 CSV parser: handles quoted fields with commas inside
function parseCSVLine(line) {
  const fields = [];
  let current = "";
  let inQuotes = false;
  for (let i = 0; i < line.length; i++) {
    const ch = line[i];
    if (inQuotes) {
      if (ch === '"' && line[i + 1] === '"') { current += '"'; i++; }
      else if (ch === '"') inQuotes = false;
      else current += ch;
    } else {
      if (ch === '"') inQuotes = true;
      else if (ch === ",") { fields.push(current); current = ""; }
      else current += ch;
    }
  }
  fields.push(current);
  return fields;
}

function loadCSV() {
  const lines = fs.readFileSync(CSV_PATH, "utf-8").trim().split("\n");
  const headers = parseCSVLine(lines[0]);
  return lines.slice(1).map((line) => {
    const vals = parseCSVLine(line);
    const obj = {};
    headers.forEach((h, i) => (obj[h.trim()] = (vals[i] || "").trim()));
    return obj;
  });
}

function saveCSV(services) {
  const headers = "service,sign_in_url,login_pattern,keys_page_url,api_create_endpoint,key_response_field,key_pattern,create_btn_selector,name_input_selector,confirm_btn_selector,key_display_selector,login_result,last_verified";
  const keys = headers.split(",");
  const escape = (v) => (v && v.includes(",") ? `"${v}"` : v || "");
  const rows = services.map((s) => keys.map((k) => escape(s[k.trim()])).join(","));
  fs.writeFileSync(CSV_PATH, [headers, ...rows].join("\n") + "\n");
}

// ─── Key Storage ────────────────────────────────────────────────────────────

function saveKey(service, key, backend) {
  const envName = `${service.toUpperCase().replace(/[^A-Z0-9]/g, "_")}_API_KEY`;

  switch (backend) {
    case "env": {
      const envPath = path.join(process.cwd(), ".env");
      let existing = "";
      if (fs.existsSync(envPath)) existing = fs.readFileSync(envPath, "utf-8");
      const filtered = existing.split("\n").filter((l) => !l.startsWith(`${envName}=`));
      filtered.push(`${envName}=${key}`);
      fs.writeFileSync(envPath, filtered.join("\n") + "\n");
      console.log(`   Saved to ${envPath}: ${envName}=${key.substring(0, 10)}...`);
      break;
    }
    case "zshrc": {
      const zshrc = path.join(process.env.HOME, ".zshrc");
      const line = `export ${envName}="${key}"`;
      let existing = "";
      if (fs.existsSync(zshrc)) existing = fs.readFileSync(zshrc, "utf-8");
      const filtered = existing.split("\n").filter((l) => !l.includes(envName));
      filtered.push(line);
      fs.writeFileSync(zshrc, filtered.join("\n") + "\n");
      console.log(`   Saved to ${zshrc}: export ${envName}="..."`);
      console.log(`   Run: source ~/.zshrc`);
      break;
    }
    case "bitwarden": {
      try {
        const name = `${service} API Key`;
        execSync(`bw get item "${name}" 2>/dev/null`, { stdio: "pipe" });
        const item = JSON.parse(execSync(`bw get item "${name}"`, { encoding: "utf-8" }));
        item.notes = key;
        fs.writeFileSync("/tmp/bw-item.json", JSON.stringify(item));
        execSync(`bw encode < /tmp/bw-item.json | bw edit item ${item.id}`, { stdio: "pipe" });
        console.log(`   Updated Bitwarden item: ${name}`);
      } catch {
        const template = JSON.stringify({
          organizationId: null, folderId: null, type: 2,
          name: `${service} API Key`, notes: key, favorite: false,
        });
        fs.writeFileSync("/tmp/bw-item.json", template);
        execSync(`bw encode < /tmp/bw-item.json | bw create item`, { stdio: "pipe" });
        console.log(`   Created Bitwarden item: ${service} API Key`);
      }
      break;
    }
    default:
      console.error(`   Unknown storage backend: ${backend}`);
      return false;
  }
  return true;
}

// ─── CDP ────────────────────────────────────────────────────────────────────

class CDPClient {
  constructor(wsUrl) { this.wsUrl = wsUrl; this.ws = null; this.id = 0; this.callbacks = new Map(); }
  async connect() {
    return new Promise((resolve, reject) => {
      this.ws = new WebSocket(this.wsUrl);
      this.ws.on("open", resolve);
      this.ws.on("error", reject);
      this.ws.on("message", (data) => {
        const msg = JSON.parse(data.toString());
        if (msg.id && this.callbacks.has(msg.id)) {
          const cb = this.callbacks.get(msg.id); this.callbacks.delete(msg.id);
          msg.error ? cb.reject(new Error(msg.error.message)) : cb.resolve(msg.result);
        }
      });
    });
  }
  send(method, params = {}, sessionId) {
    return new Promise((resolve, reject) => {
      const id = ++this.id;
      this.callbacks.set(id, { resolve, reject });
      const msg = { id, method, params };
      if (sessionId) msg.sessionId = sessionId;
      this.ws.send(JSON.stringify(msg));
    });
  }
  close() { if (this.ws) try { this.ws.close(); } catch {} }
}

const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

function httpGet(url) {
  return new Promise((resolve, reject) => {
    http.get(url, (res) => { let b = ""; res.on("data", (d) => (b += d)); res.on("end", () => resolve(b)); }).on("error", reject);
  });
}

async function evalJS(cdp, sessionId, expression) {
  const result = await cdp.send("Runtime.evaluate", { expression, returnByValue: true, awaitPromise: true }, sessionId);
  if (result.exceptionDetails) throw new Error(result.exceptionDetails.text || result.exceptionDetails.exception?.description);
  return result.result?.value;
}

// ─── LLM ────────────────────────────────────────────────────────────────────

async function callLLM(baseUrl, apiKey, model, prompt) {
  const url = new URL("/v1/chat/completions", baseUrl);
  const body = JSON.stringify({ model, messages: [{ role: "user", content: prompt }], temperature: 0, max_tokens: 1000 });
  const proto = url.protocol === "https:" ? https : http;
  return new Promise((resolve, reject) => {
    const req = proto.request(url, { method: "POST", headers: { "Content-Type": "application/json", Authorization: `Bearer ${apiKey}` } }, (res) => {
      let data = ""; res.on("data", (d) => (data += d)); res.on("end", () => {
        try { resolve(JSON.parse(data).choices?.[0]?.message?.content || ""); }
        catch { reject(new Error(`LLM error: ${data.substring(0, 200)}`)); }
      });
    });
    req.on("error", reject);
    req.write(body); req.end();
  });
}

// ─── Main ───────────────────────────────────────────────────────────────────

async function main() {
  const args = parseArgs(process.argv);

  if (!args.service) {
    const services = loadCSV();
    console.error("Usage: node create-api-key.js [options] <service>");
    console.error(`Services: ${services.map((s) => s.service).join(", ")}`);
    process.exit(1);
  }

  const services = loadCSV();
  const svc = services.find((s) => s.service === args.service.toLowerCase());

  if (!svc) {
    console.error(`Unknown service: ${args.service}`);
    console.error(`Available: ${services.map((s) => s.service).join(", ")}`);
    process.exit(1);
  }

  console.log(`\n🔑 API Key Creator: ${svc.service}`);
  console.log(`   Keys page: ${svc.keys_page_url}`);
  console.log(`   Storage: ${args.saveTo}`);
  if (svc.api_create_endpoint) console.log(`   API: ${svc.api_create_endpoint}`);
  console.log();

  if (args.dryRun) {
    console.log("   [DRY RUN] Would:");
    console.log(`   1. Login via ${svc.sign_in_url}`);
    console.log(`   2. Navigate to ${svc.keys_page_url}`);
    console.log(`   3. ${svc.api_create_endpoint ? "Use API: " + svc.api_create_endpoint : "Use browser automation"}`);
    console.log(`   4. Save to ${args.saveTo}`);
    process.exit(0);
  }

  // ── Step 1: Login ──────────────────────────────────────────────────────
  console.log("1️⃣  Logging in...");
  try {
    execSync(
      `node ${path.join(DIR, "google-sso-login.js")} --port ${args.port} "${svc.sign_in_url}" "${svc.login_pattern}"`,
      { stdio: "inherit", timeout: 120000 }
    );
  } catch {
    console.error("   ❌ Login failed");
    process.exit(1);
  }

  // ── Step 2: Connect and navigate ───────────────────────────────────────
  console.log("\n2️⃣  Navigating to keys page...");
  const browserVer = JSON.parse(await httpGet(`http://localhost:${args.port}/json/version`));
  const cdp = new CDPClient(browserVer.webSocketDebuggerUrl);
  await cdp.connect();

  let targetId = null;
  let apiKey = null;

  try {
    const targets = JSON.parse(await httpGet(`http://localhost:${args.port}/json/list`));
    const existingTab = targets.find((t) => t.url.includes(svc.login_pattern) && t.type === "page");

    let sessionId;
    if (existingTab) {
      targetId = existingTab.id;
      ({ sessionId } = await cdp.send("Target.attachToTarget", { targetId, flatten: true }));
      await cdp.send("Page.navigate", { url: svc.keys_page_url }, sessionId);
    } else {
      ({ targetId } = await cdp.send("Target.createTarget", { url: svc.keys_page_url }));
      ({ sessionId } = await cdp.send("Target.attachToTarget", { targetId, flatten: true }));
    }
    await cdp.send("Runtime.enable", {}, sessionId);
    await sleep(5000);

    const pageUrl = await evalJS(cdp, sessionId, "window.location.href");
    console.log(`   ✅ On: ${pageUrl}\n`);

    // ── Step 3: Create key ───────────────────────────────────────────────
    if (svc.api_create_endpoint === "intercept_fetch") {
      console.log("3️⃣  Creating key (fetch intercept)...");
      apiKey = await createKeyViaIntercept(cdp, sessionId, svc, args);
    } else if (svc.api_create_endpoint) {
      console.log(`3️⃣  Creating key via API: ${svc.api_create_endpoint}`);
      console.log("   ⚠️  Direct API not yet implemented, using browser fallback");
      apiKey = await createKeyViaBrowser(cdp, sessionId, svc, args);
    } else {
      console.log("3️⃣  Creating key (browser)...");
      apiKey = await createKeyViaBrowser(cdp, sessionId, svc, args);
    }

    // ── Step 4: Save ─────────────────────────────────────────────────────
    if (apiKey) {
      console.log(`\n   ✅ Key: ${apiKey.substring(0, 10)}...${apiKey.substring(apiKey.length - 4)}`);

      // CSV log
      let existing = "";
      if (fs.existsSync(KEYS_OUTPUT)) existing = fs.readFileSync(KEYS_OUTPUT, "utf-8").trim();
      const header = "service,api_key,created_at";
      const row = `"${svc.service}","${apiKey}","${new Date().toISOString()}"`;
      fs.writeFileSync(KEYS_OUTPUT, (existing ? existing + "\n" : header + "\n") + row + "\n");
      console.log(`   Logged to ${KEYS_OUTPUT}`);

      // Storage backend
      saveKey(svc.service, apiKey, args.saveTo);

      // Update CSV
      svc.last_verified = new Date().toISOString().split("T")[0];
      saveCSV(services);
    } else {
      console.log("\n   ⚠️  Could not extract API key");
    }

  } finally {
    if (targetId) await cdp.send("Target.closeTarget", { targetId }).catch(() => {});
    cdp.close();
  }

  // ── Result ─────────────────────────────────────────────────────────────
  console.log("\n" + "─".repeat(50));
  if (apiKey) {
    console.log("✅ API KEY CREATED");
    console.log(`   Service: ${svc.service}`);
    console.log(`   Key: ${apiKey.substring(0, 10)}...${apiKey.substring(apiKey.length - 4)}`);
    console.log(`   Storage: ${args.saveTo}`);
  } else {
    console.log("❌ API KEY CREATION FAILED");
  }
  console.log("─".repeat(50) + "\n");

  process.exit(apiKey ? 0 : 1);
}

// ─── Strategy: Fetch Intercept ──────────────────────────────────────────────

async function createKeyViaIntercept(cdp, sessionId, svc, args) {
  // Build JS to extract key from response based on key_response_field
  const fieldPath = svc.key_response_field || "key";
  const extractJS = fieldPath.includes(".")
    ? `data.${fieldPath.replace(/\./g, "?.")}`  // e.g., data.key?.sensitive_id
    : `data.${fieldPath}`;

  // Intercept fetch to capture API key from response
  await evalJS(cdp, sessionId, `
    window.__capturedApiKey = null;
    const origFetch = window.fetch;
    window.fetch = async function(...args) {
      const resp = await origFetch.apply(this, args);
      const url = typeof args[0] === 'string' ? args[0] : args[0]?.url || '';
      if ((url.includes('key') || url.includes('token')) && resp.status < 300) {
        try {
          const clone = resp.clone();
          const data = await clone.json();
          // Try configured field path
          let key = ${extractJS};
          if (!key && Array.isArray(data.data)) key = data.data[0]?.${fieldPath.includes(".") ? fieldPath.replace(/\./g, "?.") : fieldPath};
          if (!key) key = data.exposed_secret_key || data.key || data.token || data.secret;
          if (key && typeof key === 'string' && key.length > 10) window.__capturedApiKey = key;
        } catch {}
      }
      return resp;
    };
  `);

  // Get selectors
  const selectors = await getSelectors(cdp, sessionId, svc, args);

  // Click create button
  console.log("   Clicking create button...");
  await clickButton(cdp, sessionId, selectors.createBtn, selectors.createBtnText);
  await sleep(2000);

  // Fill name
  if (selectors.nameInput) {
    const keyName = args.keyName || `auto-${Date.now()}`;
    await evalJS(cdp, sessionId, `document.querySelector(${JSON.stringify(selectors.nameInput)})?.focus()`);
    await sleep(200);
    for (const char of keyName) {
      await cdp.send("Input.dispatchKeyEvent", { type: "char", text: char }, sessionId);
      await sleep(30);
    }
    console.log(`   Name: ${keyName}`);
    await sleep(500);
  }

  // Click confirm
  console.log("   Clicking confirm...");
  await clickButton(cdp, sessionId, selectors.confirmBtn, selectors.confirmBtnText);
  console.log("   Submitted");

  await sleep(5000);
  return await evalJS(cdp, sessionId, "window.__capturedApiKey");
}

// ─── Strategy: Browser DOM ──────────────────────────────────────────────────

async function createKeyViaBrowser(cdp, sessionId, svc, args) {
  const selectors = await getSelectors(cdp, sessionId, svc, args);

  if (selectors.createBtn) {
    await evalJS(cdp, sessionId, `document.querySelector(${JSON.stringify(selectors.createBtn)})?.click()`);
    await sleep(2000);
  }

  if (selectors.nameInput) {
    const keyName = args.keyName || `auto-${Date.now()}`;
    await evalJS(cdp, sessionId, `document.querySelector(${JSON.stringify(selectors.nameInput)})?.focus()`);
    await sleep(200);
    for (const char of keyName) {
      await cdp.send("Input.dispatchKeyEvent", { type: "char", text: char }, sessionId);
      await sleep(30);
    }
    await sleep(500);
  }

  if (selectors.confirmBtn) {
    await evalJS(cdp, sessionId, `document.querySelector(${JSON.stringify(selectors.confirmBtn)})?.click()`);
    await sleep(5000);
  }

  // Extract from DOM
  if (selectors.keyDisplay) {
    const key = await evalJS(cdp, sessionId, `document.querySelector(${JSON.stringify(selectors.keyDisplay)})?.textContent?.trim()`);
    if (key) return key;
  }

  // Pattern-based extraction
  if (svc.key_pattern) {
    const key = await evalJS(cdp, sessionId, `
      (function() {
        const m = document.body.innerText.match(${svc.key_pattern});
        return m ? m[0] : null;
      })()
    `);
    if (key) return key;
  }

  return null;
}

// ─── Selector Resolution (cache → text → LLM) ──────────────────────────────

async function getSelectors(cdp, sessionId, svc, args) {
  // 1. Try CSS selectors from CSV
  if (svc.create_btn_selector) {
    const exists = await evalJS(cdp, sessionId, `!!document.querySelector(${JSON.stringify(svc.create_btn_selector)})`);
    if (exists) {
      console.log("   📋 Using cached CSS selectors");
      return {
        createBtn: svc.create_btn_selector,
        nameInput: svc.name_input_selector,
        confirmBtn: svc.confirm_btn_selector,
        keyDisplay: svc.key_display_selector,
      };
    }
    console.log("   ⚠️  Cached CSS selectors stale, trying text-based...");
  }

  // 2. Try text-based button matching from CSV
  if (svc.create_btn_text) {
    const found = await evalJS(cdp, sessionId, `
      (function() {
        const result = {};
        for (const b of document.querySelectorAll('button, a, [role="button"]')) {
          const t = (b.textContent || '').trim();
          ${svc.create_btn_text ? `if (t.includes(${JSON.stringify(svc.create_btn_text)})) result.createBtn = true;` : ""}
          ${svc.confirm_btn_text ? `if (t.includes(${JSON.stringify(svc.confirm_btn_text)})) result.confirmBtn = true;` : ""}
        }
        return JSON.stringify(result);
      })()
    `);
    const parsed = JSON.parse(found || "{}");
    if (parsed.createBtn) {
      console.log("   📋 Using text-based button matching");
      return {
        createBtn: svc.create_btn_selector || null,
        createBtnText: svc.create_btn_text,
        nameInput: svc.name_input_selector,
        confirmBtn: svc.confirm_btn_selector || null,
        confirmBtnText: svc.confirm_btn_text,
        keyDisplay: svc.key_display_selector,
      };
    }
  }

  // 3. LLM fallback
  if (!args.noLlm && args.llmBaseUrl && args.llmApiKey) {
    console.log("   🤖 Asking LLM for selectors...");
    const pageHtml = await evalJS(cdp, sessionId, "document.documentElement.outerHTML");
    const llmResp = await callLLM(args.llmBaseUrl, args.llmApiKey, args.llmModel,
      `HTML of API keys page (${svc.keys_page_url}):\n${pageHtml.substring(0, 15000)}\n\nReturn JSON with CSS selectors: {createBtn, nameInput, confirmBtn, keyDisplay}. JSON only.`
    );
    try {
      const jsonMatch = llmResp.match(/\{[\s\S]*\}/);
      const selectors = JSON.parse(jsonMatch ? jsonMatch[0] : llmResp);
      svc.create_btn_selector = selectors.createBtn || "";
      svc.name_input_selector = selectors.nameInput || "";
      svc.confirm_btn_selector = selectors.confirmBtn || "";
      svc.key_display_selector = selectors.keyDisplay || "";
      svc.last_verified = new Date().toISOString().split("T")[0];
      saveCSV(loadCSV().map((s) => (s.service === svc.service ? svc : s)));
      console.log("   ✅ Selectors saved to CSV");
      return selectors;
    } catch {
      console.error("   ❌ Failed to parse LLM response");
    }
  }

  console.error("   ❌ No selectors available");
  process.exit(1);
}

// Click a button by CSS selector or by text content
async function clickButton(cdp, sessionId, selector, text) {
  if (selector) {
    const exists = await evalJS(cdp, sessionId, `!!document.querySelector(${JSON.stringify(selector)})`);
    if (exists) {
      await evalJS(cdp, sessionId, `document.querySelector(${JSON.stringify(selector)}).click()`);
      return true;
    }
  }
  if (text) {
    const clicked = await evalJS(cdp, sessionId, `
      (function() {
        for (const b of document.querySelectorAll('button, a, [role="button"]')) {
          if ((b.textContent || '').trim().includes(${JSON.stringify(text)})) {
            b.click(); return true;
          }
        }
        return false;
      })()
    `);
    if (clicked) return true;
  }
  return false;
}

main().catch((err) => {
  console.error(`\n❌ Fatal error: ${err.message}`);
  process.exit(1);
});
