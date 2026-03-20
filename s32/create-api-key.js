#!/usr/bin/env node
/**
 * create-api-key.js
 *
 * Automates API key creation on any web app that uses Google SSO.
 * Uses a hybrid approach: CSV cache for known selectors, LLM fallback for unknown sites.
 *
 * Usage:
 *   node create-api-key.js [options] <service-name-or-url>
 *
 * Options:
 *   --llm-base-url <url>   OpenAI-compatible API base URL
 *   --llm-api-key <key>    API key for the LLM provider
 *   --llm-model <model>    Model name (default: gpt-4o-mini)
 *   --port <n>             CDP port (default: 9222)
 *   --key-name <name>      Name for the API key (default: auto-generated)
 *   --no-llm               Skip LLM fallback, only use cache
 *
 * Environment variables (fallback if flags not set):
 *   LLM_BASE_URL, LLM_API_KEY, LLM_MODEL
 *
 * Examples:
 *   node create-api-key.js groq
 *   node create-api-key.js --llm-base-url https://api.groq.com/openai/v1 --llm-api-key gsk_xxx --llm-model llama-3.3-70b-versatile groq
 *   LLM_BASE_URL=https://api.groq.com/openai/v1 LLM_API_KEY=gsk_xxx node create-api-key.js mistral
 *
 * Service registry (built-in shortcuts):
 *   groq        → https://console.groq.com/keys
 *   mistral     → https://console.mistral.ai/api-keys
 *   cohere      → https://dashboard.cohere.com/api-keys
 *   openrouter  → https://openrouter.ai/settings/keys
 *   ai21        → https://studio.ai21.com/v2/account/api-keys
 *   deepseek    → https://platform.deepseek.com/api-keys
 *   huggingface → https://huggingface.co/settings/tokens
 *   elevenlabs  → https://elevenlabs.io/app/settings/api-keys
 *   openai      → https://platform.openai.com/api-keys
 *   anthropic   → https://console.anthropic.com/settings/keys
 */

const http = require("http");
const https = require("https");
const fs = require("fs");
const path = require("path");
const WebSocket = require("ws");

// ─── Service Registry ───────────────────────────────────────────────────────

const SERVICES = {
  groq: {
    signInUrl: "https://console.groq.com/login",
    keysUrl: "https://console.groq.com/keys",
    loginPattern: "console.groq.com",
    keyPattern: /^gsk_[A-Za-z0-9]+$/,
  },
  mistral: {
    signInUrl: "https://console.mistral.ai/login",
    keysUrl: "https://console.mistral.ai/api-keys",
    loginPattern: "console.mistral.ai",
    keyPattern: /^[A-Za-z0-9]{32,}$/,
  },
  cohere: {
    signInUrl: "https://dashboard.cohere.com/welcome/login",
    keysUrl: "https://dashboard.cohere.com/api-keys",
    loginPattern: "dashboard.cohere.com",
    keyPattern: /^[A-Za-z0-9]{40,}$/,
  },
  openrouter: {
    signInUrl: "https://openrouter.ai/login",
    keysUrl: "https://openrouter.ai/settings/keys",
    loginPattern: "openrouter.ai",
    keyPattern: /^sk-or-[A-Za-z0-9-]+$/,
  },
  ai21: {
    signInUrl: "https://studio.ai21.com/v2/login",
    keysUrl: "https://studio.ai21.com/v2/account/api-keys",
    loginPattern: "studio.ai21.com",
    keyPattern: /^[A-Za-z0-9]{32,}$/,
  },
  deepseek: {
    signInUrl: "https://platform.deepseek.com/login",
    keysUrl: "https://platform.deepseek.com/api-keys",
    loginPattern: "platform.deepseek.com",
    keyPattern: /^sk-[A-Za-z0-9]{32,}$/,
  },
  huggingface: {
    signInUrl: "https://huggingface.co/login",
    keysUrl: "https://huggingface.co/settings/tokens",
    loginPattern: "huggingface.co",
    keyPattern: /^hf_[A-Za-z0-9]{30,}$/,
  },
  elevenlabs: {
    signInUrl: "https://elevenlabs.io/app/sign-in",
    keysUrl: "https://elevenlabs.io/app/settings/api-keys",
    loginPattern: "elevenlabs.io/app",
    keyPattern: /^[A-Za-z0-9]{32,}$/,
  },
  openai: {
    signInUrl: "https://platform.openai.com/login",
    keysUrl: "https://platform.openai.com/api-keys",
    loginPattern: "platform.openai.com",
    keyPattern: /^sk-[A-Za-z0-9]{20,}$/,
  },
  anthropic: {
    signInUrl: "https://console.anthropic.com/login",
    keysUrl: "https://console.anthropic.com/settings/keys",
    loginPattern: "console.anthropic.com",
    keyPattern: /^sk-ant-[A-Za-z0-9-]{20,}$/,
  },
};

// ─── Config ─────────────────────────────────────────────────────────────────

const DIR = __dirname;
const CACHE_PATH = path.join(DIR, "api-keys-cache.csv");
const KEYS_PATH = path.join(DIR, "api-keys.csv");
const CDP_PORT = 9222;

// ─── CLI Parsing ────────────────────────────────────────────────────────────

function parseArgs(argv) {
  const args = { port: CDP_PORT, noLlm: false };
  const positional = [];
  for (let i = 2; i < argv.length; i++) {
    switch (argv[i]) {
      case "--llm-base-url": args.llmBaseUrl = argv[++i]; break;
      case "--llm-api-key": args.llmApiKey = argv[++i]; break;
      case "--llm-model": args.llmModel = argv[++i]; break;
      case "--port": args.port = Number(argv[++i]); break;
      case "--key-name": args.keyName = argv[++i]; break;
      case "--no-llm": args.noLlm = true; break;
      default: positional.push(argv[i]);
    }
  }
  args.service = positional[0];
  // Env fallbacks
  args.llmBaseUrl = args.llmBaseUrl || process.env.LLM_BASE_URL;
  args.llmApiKey = args.llmApiKey || process.env.LLM_API_KEY;
  args.llmModel = args.llmModel || process.env.LLM_MODEL || "gpt-4o-mini";
  return args;
}

// ─── CSV Cache ──────────────────────────────────────────────────────────────

function loadCache() {
  if (!fs.existsSync(CACHE_PATH)) return {};
  const lines = fs.readFileSync(CACHE_PATH, "utf-8").trim().split("\n");
  if (lines.length < 2) return {};
  const cache = {};
  for (let i = 1; i < lines.length; i++) {
    const cols = lines[i].match(/(".*?"|[^,]+)/g)?.map((c) => c.replace(/^"|"$/g, "")) || [];
    if (cols[0]) cache[cols[0]] = { createBtn: cols[1], nameInput: cols[2], confirmBtn: cols[3], keyDisplay: cols[4], lastVerified: cols[5] };
  }
  return cache;
}

function saveCache(cache) {
  const header = "service,create_btn_selector,name_input_selector,confirm_btn_selector,key_display_selector,last_verified";
  const rows = Object.entries(cache).map(([svc, v]) =>
    `"${svc}","${v.createBtn || ""}","${v.nameInput || ""}","${v.confirmBtn || ""}","${v.keyDisplay || ""}","${v.lastVerified || ""}"`
  );
  fs.writeFileSync(CACHE_PATH, [header, ...rows].join("\n") + "\n");
}

function saveApiKey(service, key) {
  const header = "service,api_key,created_at";
  let existing = "";
  if (fs.existsSync(KEYS_PATH)) existing = fs.readFileSync(KEYS_PATH, "utf-8").trim();
  const row = `"${service}","${key}","${new Date().toISOString()}"`;
  fs.writeFileSync(KEYS_PATH, (existing ? existing + "\n" : header + "\n") + row + "\n");
}

// ─── CDP (reused from google-sso-login.js) ──────────────────────────────────

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

// ─── LLM Integration ────────────────────────────────────────────────────────

async function callLLM(baseUrl, apiKey, model, prompt) {
  const url = new URL("/v1/chat/completions", baseUrl);
  const body = JSON.stringify({
    model,
    messages: [{ role: "user", content: prompt }],
    temperature: 0,
    max_tokens: 1000,
  });

  const proto = url.protocol === "https:" ? https : http;

  return new Promise((resolve, reject) => {
    const req = proto.request(url, {
      method: "POST",
      headers: { "Content-Type": "application/json", Authorization: `Bearer ${apiKey}` },
    }, (res) => {
      let data = "";
      res.on("data", (d) => (data += d));
      res.on("end", () => {
        try {
          const json = JSON.parse(data);
          resolve(json.choices?.[0]?.message?.content || "");
        } catch (e) { reject(new Error(`LLM response parse error: ${data.substring(0, 200)}`)); }
      });
    });
    req.on("error", reject);
    req.write(body);
    req.end();
  });
}

function buildLLMPrompt(pageHtml, pageUrl) {
  return `You are a CSS selector extraction assistant. Given the HTML of a web page, find selectors for creating an API key.

Page URL: ${pageUrl}

HTML (truncated):
${pageHtml.substring(0, 15000)}

Find and return ONLY a JSON object (no markdown, no explanation) with these fields:
{
  "createBtn": "CSS selector for the 'Create API Key' or 'Generate Key' or 'New Key' button",
  "nameInput": "CSS selector for the key name/description input field (empty string if none)",
  "confirmBtn": "CSS selector for the confirm/submit/create button in the dialog (empty string if no dialog)",
  "keyDisplay": "CSS selector where the generated API key is displayed after creation (empty string if unknown)"
}

Rules:
- Use specific, stable selectors (data-testid, id, or unique class combinations preferred)
- Avoid nth-child or positional selectors
- If multiple candidates, pick the most specific one
- Return valid JSON only`;
}

// ─── Main ───────────────────────────────────────────────────────────────────

async function main() {
  const args = parseArgs(process.argv);

  if (!args.service) {
    console.error(
      "Usage: node create-api-key.js [options] <service>\n" +
      `Services: ${Object.keys(SERVICES).join(", ")}\n` +
      "Or provide a full URL as the service argument."
    );
    process.exit(1);
  }

  // Resolve service config
  let svcConfig = SERVICES[args.service.toLowerCase()];
  if (!svcConfig && args.service.startsWith("http")) {
    const url = new URL(args.service);
    svcConfig = { keysUrl: args.service, loginPattern: url.hostname, signInUrl: `${url.origin}/login`, keyPattern: /[A-Za-z0-9]{20,}/ };
  }
  if (!svcConfig) {
    console.error(`Unknown service: ${args.service}`);
    console.error(`Available: ${Object.keys(SERVICES).join(", ")}`);
    process.exit(1);
  }

  const serviceName = args.service.toLowerCase();
  console.log(`\n🔑 API Key Creator: ${serviceName}`);
  console.log(`   Keys page: ${svcConfig.keysUrl}\n`);

  // ── Step 1: Login ──────────────────────────────────────────────────────
  console.log("1️⃣  Logging in...");
  const { execSync } = require("child_process");
  try {
    execSync(
      `node ${path.join(DIR, "google-sso-login.js")} --port ${args.port} "${svcConfig.signInUrl}" "${svcConfig.loginPattern}"`,
      { stdio: "inherit", timeout: 120000 }
    );
  } catch (e) {
    console.error("   ❌ Login failed");
    process.exit(1);
  }

  // ── Step 2: Connect to Chrome ──────────────────────────────────────────
  console.log("\n2️⃣  Connecting to Chrome...");
  const browserVer = JSON.parse(await httpGet(`http://localhost:${args.port}/json/version`));
  const cdp = new CDPClient(browserVer.webSocketDebuggerUrl);
  await cdp.connect();

  let targetId = null;
  let apiKey = null;

  try {
    // Find existing tab or create new one
    const targets = JSON.parse(await httpGet(`http://localhost:${args.port}/json/list`));
    const existingTab = targets.find((t) => t.url.includes(svcConfig.loginPattern) && t.type === "page");

    let sessionId;
    if (existingTab) {
      ({ sessionId } = await cdp.send("Target.attachToTarget", { targetId: existingTab.id, flatten: true }));
      targetId = existingTab.id;
      // Navigate to keys page
      await cdp.send("Page.navigate", { url: svcConfig.keysUrl }, sessionId);
    } else {
      ({ targetId } = await cdp.send("Target.createTarget", { url: svcConfig.keysUrl }));
      ({ sessionId } = await cdp.send("Target.attachToTarget", { targetId, flatten: true }));
    }
    await cdp.send("Runtime.enable", {}, sessionId);

    // Wait for page load
    await sleep(5000);
    const pageUrl = await evalJS(cdp, sessionId, "window.location.href");
    console.log(`   ✅ On: ${pageUrl}\n`);

    // ── Step 3: Get selectors (cache or LLM) ─────────────────────────────
    console.log("3️⃣  Finding API key creation flow...");

    const cache = loadCache();
    let selectors = cache[serviceName];

    if (selectors && selectors.createBtn) {
      console.log("   📋 Using cached selectors");
      // Verify the create button exists
      const btnExists = await evalJS(cdp, sessionId, `!!document.querySelector(${JSON.stringify(selectors.createBtn)})`);
      if (!btnExists) {
        console.log("   ⚠️  Cached selector no longer works, will re-analyze");
        selectors = null;
      }
    }

    if (!selectors && !args.noLlm) {
      if (!args.llmBaseUrl || !args.llmApiKey) {
        console.error("   ❌ No cached selectors and no LLM configured.");
        console.error("   Set --llm-base-url and --llm-api-key, or LLM_BASE_URL and LLM_API_KEY env vars.");
        process.exit(1);
      }

      console.log("   🤖 Asking LLM to analyze page...");
      const pageHtml = await evalJS(cdp, sessionId, "document.documentElement.outerHTML");
      const prompt = buildLLMPrompt(pageHtml, svcConfig.keysUrl);

      const llmResponse = await callLLM(args.llmBaseUrl, args.llmApiKey, args.llmModel, prompt);

      try {
        // Extract JSON from response (handle markdown wrapping)
        const jsonMatch = llmResponse.match(/\{[\s\S]*\}/);
        selectors = JSON.parse(jsonMatch ? jsonMatch[0] : llmResponse);
        selectors.lastVerified = new Date().toISOString().split("T")[0];
        cache[serviceName] = selectors;
        saveCache(cache);
        console.log("   ✅ LLM selectors saved to cache");
      } catch (e) {
        console.error(`   ❌ Failed to parse LLM response: ${llmResponse.substring(0, 200)}`);
        process.exit(1);
      }
    }

    if (!selectors) {
      console.error("   ❌ No selectors available. Run without --no-llm and configure LLM.");
      process.exit(1);
    }

    console.log(`   Create button: ${selectors.createBtn || "N/A"}`);
    console.log(`   Name input:    ${selectors.nameInput || "N/A"}`);
    console.log(`   Confirm:       ${selectors.confirmBtn || "N/A"}`);
    console.log(`   Key display:   ${selectors.keyDisplay || "N/A"}\n`);

    // ── Step 4: Click create button ──────────────────────────────────────
    console.log("4️⃣  Creating API key...");

    if (selectors.createBtn) {
      await evalJS(cdp, sessionId, `document.querySelector(${JSON.stringify(selectors.createBtn)})?.click()`);
      await sleep(2000);
    }

    // ── Step 5: Fill name if applicable ──────────────────────────────────
    if (selectors.nameInput) {
      const nameExists = await evalJS(cdp, sessionId, `!!document.querySelector(${JSON.stringify(selectors.nameInput)})`);
      if (nameExists) {
        const keyName = args.keyName || `auto-key-${Date.now()}`;
        await evalJS(cdp, sessionId, `
          const el = document.querySelector(${JSON.stringify(selectors.nameInput)});
          el.focus();
          el.value = ${JSON.stringify(keyName)};
          el.dispatchEvent(new Event('input', {bubbles: true}));
        `);
        console.log(`   Set key name: ${keyName}`);
        await sleep(500);
      }
    }

    // ── Step 6: Confirm ──────────────────────────────────────────────────
    if (selectors.confirmBtn) {
      await sleep(500);
      await evalJS(cdp, sessionId, `document.querySelector(${JSON.stringify(selectors.confirmBtn)})?.click()`);
      await sleep(3000);
    }

    // ── Step 7: Extract API key ──────────────────────────────────────────
    console.log("5️⃣  Extracting API key...");

    if (selectors.keyDisplay) {
      await sleep(2000);
      apiKey = await evalJS(cdp, sessionId, `
        const el = document.querySelector(${JSON.stringify(selectors.keyDisplay)});
        el ? el.textContent.trim() : null
      `);
    }

    // Fallback: scan page for key pattern
    if (!apiKey && svcConfig.keyPattern) {
      console.log("   Trying pattern-based extraction...");
      apiKey = await evalJS(cdp, sessionId, `
        (function() {
          const pattern = ${svcConfig.keyPattern.toString()};
          const allText = document.body.innerText;
          const match = allText.match(pattern);
          return match ? match[0] : null;
        })()
      `);
    }

    // Another fallback: check all code/pre elements
    if (!apiKey) {
      apiKey = await evalJS(cdp, sessionId, `
        (function() {
          for (const el of document.querySelectorAll('code, pre, [class*="key"], [class*="token"], input[readonly]')) {
            const text = el.textContent?.trim();
            if (text && text.length > 20 && /^[A-Za-z0-9_-]+$/.test(text)) return text;
          }
          return null;
        })()
      `);
    }

    if (apiKey) {
      console.log(`   ✅ Found key: ${apiKey.substring(0, 10)}...${apiKey.substring(apiKey.length - 4)}`);
      saveApiKey(serviceName, apiKey);
      console.log(`   ✅ Saved to ${KEYS_PATH}`);
    } else {
      console.log("   ⚠️  Could not extract API key. Check the page manually.");
    }

    // Update cache verification date
    if (cache[serviceName]) {
      cache[serviceName].lastVerified = new Date().toISOString().split("T")[0];
      saveCache(cache);
    }

  } finally {
    if (targetId) await cdp.send("Target.closeTarget", { targetId }).catch(() => {});
    cdp.close();
  }

  // ── Result ─────────────────────────────────────────────────────────────
  console.log("\n" + "─".repeat(50));
  if (apiKey) {
    console.log("✅ API KEY CREATED");
    console.log(`   Service: ${serviceName}`);
    console.log(`   Key: ${apiKey.substring(0, 10)}...${apiKey.substring(apiKey.length - 4)}`);
  } else {
    console.log("❌ API KEY CREATION FAILED");
    console.log("   Could not extract key from page.");
  }
  console.log("─".repeat(50) + "\n");

  process.exit(apiKey ? 0 : 1);
}

main().catch((err) => {
  console.error(`\n❌ Fatal error: ${err.message}`);
  process.exit(1);
});
