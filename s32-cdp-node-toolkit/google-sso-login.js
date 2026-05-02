#!/usr/bin/env node
/**
 * google-sso-login.js
 *
 * Automates signing into web apps using an already-signed-in Google account
 * via Chrome DevTools Protocol (CDP).
 *
 * Usage:
 *   node google-sso-login.js [options] <sign-in-url> <post-login-url-pattern>
 *
 * Options:
 *   --port <n>          CDP port (default: 9222)
 *   --timeout <ms>      Overall timeout in ms (default: 90000)
 *   --retries <n>       Button detection retries (default: 5)
 *   --llm-base-url <url>  Vision LLM URL (fallback for button detection)
 *   --llm-api-key <key>   Vision LLM API key
 *   --llm-model <model>   Vision model (default: gpt-4o-mini)
 *
 * Examples:
 *   node google-sso-login.js "https://elevenlabs.io/app/sign-in" "elevenlabs.io/app"
 *   node google-sso-login.js --port 9333 "https://app.example.com/login" "app.example.com/dashboard"
 */

const http = require("http");
const https = require("https");
const fs = require("fs");
const WebSocket = require("ws");

// ─── CLI Parsing ────────────────────────────────────────────────────────────

function parseArgs(argv) {
  const args = { port: 9222, timeout: 90000, retries: 5 };
  const positional = [];
  for (let i = 2; i < argv.length; i++) {
    if (argv[i] === "--port") args.port = Number(argv[++i]);
    else if (argv[i] === "--timeout") args.timeout = Number(argv[++i]);
    else if (argv[i] === "--retries") args.retries = Number(argv[++i]);
    else if (argv[i] === "--llm-base-url") args.llmBaseUrl = argv[++i];
    else if (argv[i] === "--llm-api-key") args.llmApiKey = argv[++i];
    else if (argv[i] === "--llm-model") args.llmModel = argv[++i];
    else positional.push(argv[i]);
  }
  args.signInUrl = positional[0];
  args.postLoginPattern = positional[1];
  args.llmBaseUrl = args.llmBaseUrl || process.env.LLM_BASE_URL;
  args.llmApiKey = args.llmApiKey || process.env.LLM_API_KEY;
  args.llmModel = args.llmModel || process.env.LLM_MODEL || "gpt-4o-mini";
  return args;
}

// ─── Timeouts ───────────────────────────────────────────────────────────────

const TIMEOUTS = {
  pageLoad: 15000,
  hydration: 10000,
  oauthPopup: 15000,
  oauthComplete: 45000,
  settle: 3000,
};

// ─── JS Expressions (compiled once) ─────────────────────────────────────────

const FIND_GOOGLE_BTN = `
  (function() {
    // Text-based search
    for (const el of document.querySelectorAll('button, a, [role="button"]')) {
      const t = (el.textContent || '').toLowerCase().trim();
      if (t.includes('sign in with google') || t.includes('continue with google') || t === 'google') {
        const r = el.getBoundingClientRect();
        return JSON.stringify({ x: r.x + r.width/2, y: r.y + r.height/2 });
      }
    }
    // Image-based search (buttons with Google logo, no text)
    for (const img of document.querySelectorAll('img[alt*="google" i], img[src*="google" i]')) {
      const btn = img.closest('button, a, [role="button"]');
      if (btn) {
        const r = btn.getBoundingClientRect();
        if (r.width > 0 && r.height > 0) {
          return JSON.stringify({ x: r.x + r.width/2, y: r.y + r.height/2 });
        }
      }
    }
    return null;
  })()
`;

const CLICK_ACCOUNT_OR_CONTINUE = `
  (function() {
    const items = document.querySelectorAll('[data-identifier], [data-email], li[role="link"]');
    if (items.length > 0) { items[0].click(); return; }
    for (const b of document.querySelectorAll('button')) {
      const t = (b.textContent || '').toLowerCase();
      if (t.includes('continue') || t.includes('allow') || t.includes('next') || t.includes('sign in')) {
        b.click(); return;
      }
    }
  })()
`;

const VERIFY_LOGIN = `
  (function() {
    const body = (document.body?.innerText || '').toLowerCase();
    return JSON.stringify({
      hasSignOut: body.includes('sign out') || body.includes('log out'),
      noSignInForm: !document.querySelector('input[type="email"], input[name="email"]'),
    });
  })()
`;

// ─── CDP Client ─────────────────────────────────────────────────────────────

class CDPClient {
  constructor(wsUrl) {
    this.wsUrl = wsUrl;
    this.ws = null;
    this.id = 0;
    this.callbacks = new Map();
    this.events = new Map();
  }

  async connect() {
    return new Promise((resolve, reject) => {
      this.ws = new WebSocket(this.wsUrl);
      this.ws.on("open", resolve);
      this.ws.on("error", reject);
      this.ws.on("message", (data) => {
        const msg = JSON.parse(data.toString());
        if (msg.id && this.callbacks.has(msg.id)) {
          const cb = this.callbacks.get(msg.id);
          this.callbacks.delete(msg.id);
          if (msg.error) cb.reject(new Error(msg.error.message));
          else cb.resolve(msg.result);
        }
        if (msg.method && this.events.has(msg.method)) {
          for (const cb of this.events.get(msg.method)) cb(msg.params);
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

  on(event, cb) {
    if (!this.events.has(event)) this.events.set(event, []);
    this.events.get(event).push(cb);
  }

  off(event, cb) {
    if (!this.events.has(event)) return;
    this.events.set(event, this.events.get(event).filter((x) => x !== cb));
  }

  close() {
    if (this.ws) {
      try { this.ws.close(); } catch {}
    }
  }
}

// ─── Helpers ────────────────────────────────────────────────────────────────

const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

/** Race a promise against a timeout. Cleans up the losing side. */
function withTimeout(promise, ms, label = "Operation") {
  let timer;
  const timeout = new Promise((_, reject) => {
    timer = setTimeout(() => reject(new Error(`${label} timed out after ${ms}ms`)), ms);
  });
  return Promise.race([
    promise.finally(() => clearTimeout(timer)),
    timeout.finally(() => clearTimeout(timer)),
  ]);
}

function httpGet(url) {
  return new Promise((resolve, reject) => {
    http.get(url, (res) => {
      let b = "";
      res.on("data", (d) => (b += d));
      res.on("end", () => resolve(b));
    }).on("error", reject);
  });
}

async function evalJS(cdp, sessionId, expression) {
  const result = await cdp.send(
    "Runtime.evaluate",
    { expression, returnByValue: true, awaitPromise: true },
    sessionId
  );
  if (result.exceptionDetails) {
    throw new Error(
      result.exceptionDetails.text ||
        result.exceptionDetails.exception?.description
    );
  }
  return result.result?.value;
}

/** Use vision LLM to find Google sign-in button via screenshot */
async function findGoogleBtnViaVision(cdp, sessionId, llmBaseUrl, llmApiKey, llmModel) {
  // Take screenshot
  const screenshot = await cdp.send("Page.captureScreenshot", { format: "png" }, sessionId);
  const imageBase64 = screenshot.data;

  // Call vision LLM
  const url = new URL("/v1/chat/completions", llmBaseUrl);
  const body = JSON.stringify({
    model: llmModel,
    messages: [{
      role: "user",
      content: [
        { type: "text", text: 'This is a screenshot of a web login page (1280x720 viewport). Find the "Sign in with Google" or "Continue with Google" button. It usually has a Google "G" logo. Return ONLY a JSON object: {"x": <center_x>, "y": <center_y>, "found": true} or {"found": false}. Be precise with coordinates.' },
        { type: "image_url", image_url: { url: `data:image/png;base64,${imageBase64}` } }
      ]
    }],
    max_tokens: 100,
    temperature: 0,
  });

  const proto = url.protocol === "https:" ? https : http;
  const response = await new Promise((resolve, reject) => {
    const req = proto.request(url, {
      method: "POST",
      headers: { "Content-Type": "application/json", Authorization: `Bearer ${llmApiKey}` },
    }, (res) => {
      let data = "";
      res.on("data", (d) => (data += d));
      res.on("end", () => {
        try { resolve(JSON.parse(data).choices?.[0]?.message?.content || ""); }
        catch { reject(new Error(`Vision LLM error: ${data.substring(0, 200)}`)); }
      });
    });
    req.on("error", reject);
    req.write(body);
    req.end();
  });

  // Parse coordinates from response
  const jsonMatch = response.match(/\{[\s\S]*?\}/);
  if (!jsonMatch) return null;
  const parsed = JSON.parse(jsonMatch[0]);
  if (!parsed.found) return null;
  return { x: parsed.x, y: parsed.y };
}

/** Poll for a value with exponential backoff (200ms → 400ms → 800ms, capped at 2s) */
async function pollUntil(fn, { timeoutMs, label, intervalMs = 300 } = {}) {
  return withTimeout(
    new Promise((resolve, reject) => {
      const poll = setInterval(async () => {
        try {
          const val = await fn();
          if (val) { clearInterval(poll); resolve(val); }
        } catch (e) { clearInterval(poll); reject(e); }
      }, intervalMs);
    }),
    timeoutMs,
    label
  );
}

// ─── Main ───────────────────────────────────────────────────────────────────

async function main() {
  const args = parseArgs(process.argv);

  if (!args.signInUrl || !args.postLoginPattern) {
    console.error(
      "Usage: node google-sso-login.js [options] <sign-in-url> <post-login-url-pattern>\n" +
      'Example: node google-sso-login.js "https://elevenlabs.io/app/sign-in" "elevenlabs.io/app"'
    );
    process.exit(1);
  }

  const { signInUrl, postLoginPattern } = args;
  console.log(`\n🔐 Google SSO Auto-Login`);
  console.log(`   Sign-in URL:  ${signInUrl}`);
  console.log(`   Expect after: ${postLoginPattern}`);
  console.log(`   CDP port:     ${args.port}\n`);

  // ── Connect ───────────────────────────────────────────────────────────
  console.log("1️⃣  Connecting to Chrome via CDP...");
  const browserVer = JSON.parse(await httpGet(`http://localhost:${args.port}/json/version`));
  const cdp = new CDPClient(browserVer.webSocketDebuggerUrl);
  await cdp.connect();
  console.log("   ✅ Connected\n");

  let targetId = null;
  let loginSuccess = false;
  let finalUrl = null;

  try {
    // ── Open sign-in page ───────────────────────────────────────────────
    console.log("2️⃣  Opening sign-in page...");
    ({ targetId } = await cdp.send("Target.createTarget", { url: signInUrl }));
    const { sessionId } = await cdp.send("Target.attachToTarget", { targetId, flatten: true });
    await cdp.send("Page.enable", {}, sessionId);
    await cdp.send("Runtime.enable", {}, sessionId);

    // Wait for page load event
    await withTimeout(
      new Promise((resolve) => {
        const handler = () => { cdp.off("Page.loadEventFired", handler); resolve(); };
        cdp.on("Page.loadEventFired", handler);
        // Fallback: resolve after pageLoad even if event doesn't fire
        setTimeout(() => { cdp.off("Page.loadEventFired", handler); resolve(); }, TIMEOUTS.pageLoad);
      }),
      TIMEOUTS.pageLoad + 2000,
      "Page load"
    );

    // Wait for hydration: poll until buttons appear (up to 10s)
    console.log("   Waiting for page hydration...");
    await pollUntil(
      async () => {
        const count = await evalJS(cdp, sessionId, "document.querySelectorAll('button').length");
        return count > 0 ? true : null;
      },
      { timeoutMs: TIMEOUTS.hydration, label: "Page hydration", intervalMs: 500 }
    ).catch(() => console.log("   ⚠️  Hydration timeout, proceeding anyway"));

    const pageUrl = await evalJS(cdp, sessionId, "window.location.href");
    console.log(`   ✅ Loaded: ${pageUrl}\n`);

    // Check if already logged in
    if (!pageUrl.includes("sign-in") && pageUrl.includes(postLoginPattern)) {
      console.log("─".repeat(50));
      console.log("✅ ALREADY LOGGED IN");
      console.log(`   ${pageUrl}`);
      console.log("─".repeat(50) + "\n");
      loginSuccess = true;
      finalUrl = pageUrl;
      return;
    }

    // ── Grant popup permission ──────────────────────────────────────────
    console.log("3️⃣  Granting popup permission...");
    const origin = new URL(signInUrl).origin;
    await cdp.send("Browser.grantPermissions", { permissions: ["windowManagement"], origin });
    console.log(`   ✅ Popups allowed for ${origin}\n`);

    // ── Click Google sign-in button ─────────────────────────────────────
    console.log("4️⃣  Clicking Google sign-in button...");

    let posResult = null;
    for (let i = 0; i < args.retries; i++) {
      posResult = await evalJS(cdp, sessionId, FIND_GOOGLE_BTN);
      if (posResult) break;
      if (i < args.retries - 1) {
        console.log(`   Retry ${i + 1}/${args.retries}...`);
        await sleep(2000);
      }
    }

    if (!posResult) {
      // Fallback: vision LLM
      if (args.llmBaseUrl && args.llmApiKey) {
        console.log("   Text search failed, trying vision LLM...");
        const visionPos = await findGoogleBtnViaVision(cdp, sessionId, args.llmBaseUrl, args.llmApiKey, args.llmModel);
        if (visionPos) {
          posResult = JSON.stringify(visionPos);
          console.log(`   ✅ Vision found button at (${visionPos.x}, ${visionPos.y})`);
        }
      }
    }

    if (!posResult) {
      console.error("   ❌ Google sign-in button not found (text + vision)");
      process.exit(1);
    }

    const pos = JSON.parse(posResult);
    await cdp.send("Input.dispatchMouseEvent", { type: "mousePressed", x: pos.x, y: pos.y, button: "left", clickCount: 1 }, sessionId);
    await cdp.send("Input.dispatchMouseEvent", { type: "mouseReleased", x: pos.x, y: pos.y, button: "left", clickCount: 1 }, sessionId);
    console.log("   ✅ Clicked\n");

    // ── Wait for OAuth (popup or same-tab redirect) ──────────────────────
    console.log("5️⃣  Waiting for OAuth flow...");

    const { targetInfos: beforeTargets } = await cdp.send("Target.getTargets");
    const beforePageIds = new Set(beforeTargets.filter((t) => t.type === "page").map((t) => t.targetId));

    // Race: new popup target vs same-tab navigation
    let oauthTarget = null;
    let oauthSid = null;
    await cdp.send("Target.setDiscoverTargets", { discover: true });

    const popupPromise = pollUntil(
      async () => {
        const { targetInfos } = await cdp.send("Target.getTargets");
        const newPages = targetInfos.filter(
          (t) => t.type === "page" && !beforePageIds.has(t.targetId) && t.url && !t.url.startsWith("chrome://")
        );
        return newPages[0] || null;
      },
      { timeoutMs: TIMEOUTS.oauthPopup, label: "OAuth popup", intervalMs: 500 }
    ).catch(() => null);

    const redirectPromise = pollUntil(
      async () => {
        try {
          const url = await evalJS(cdp, sessionId, "window.location.href");
          if (url.includes("accounts.google.com") || url.includes("auth")) return url;
        } catch {}
        return null;
      },
      { timeoutMs: TIMEOUTS.oauthPopup, label: "OAuth redirect", intervalMs: 500 }
    ).catch(() => null);

    const [popup, redirect] = await Promise.all([popupPromise, redirectPromise]);

    if (popup) {
      // Popup flow
      oauthTarget = popup;
      console.log(`   ✅ Popup opened: ${popup.url.substring(0, 80)}...\n`);
      ({ sessionId: oauthSid } = await cdp.send("Target.attachToTarget", { targetId: popup.targetId, flatten: true }));
      await cdp.send("Runtime.enable", {}, oauthSid);
    } else if (redirect) {
      // Same-tab redirect flow
      console.log(`   ✅ Redirected to: ${redirect.substring(0, 80)}...\n`);
      oauthSid = sessionId; // Use same session
    } else {
      console.error("   ❌ No OAuth flow detected");
      process.exit(1);
    }

    // ── Handle Google account selection ─────────────────────────────────
    console.log("6️⃣  Processing Google authorization...");

    for (let attempt = 0; attempt < 5; attempt++) {
      await sleep(3000);

      let url;
      try {
        url = await evalJS(cdp, oauthSid, "window.location.href");
      } catch {
        console.log("   Session detached — popup processing auth\n");
        break;
      }
      console.log(`   [${attempt + 1}] ${url.substring(0, 100)}`);

      if (!url.includes("accounts.google.com")) {
        console.log("   ✅ Left Google — auth processing\n");
        break;
      }

      try {
        await evalJS(cdp, oauthSid, CLICK_ACCOUNT_OR_CONTINUE);
      } catch {
        break;
      }
    }

    // ── Wait for auth to complete ────────────────────────────────────────
    if (oauthTarget) {
      // Popup flow: wait for popup to close
      console.log("7️⃣  Waiting for OAuth popup to close...");
      await pollUntil(
        async () => {
          const { targetInfos } = await cdp.send("Target.getTargets");
          const t = targetInfos.find((t) => t.targetId === oauthTarget.targetId);
          return (!t || !t.attached) ? true : null;
        },
        { timeoutMs: TIMEOUTS.oauthComplete, label: "Popup close", intervalMs: 500 }
      );
      console.log("   ✅ Popup closed\n");
    } else {
      // Same-tab flow: wait for redirect back to app
      console.log("7️⃣  Waiting for auth redirect...");
      await pollUntil(
        async () => {
          try {
            const url = await evalJS(cdp, sessionId, "window.location.href");
            return url.includes(postLoginPattern) ? true : null;
          } catch { return null; }
        },
        { timeoutMs: TIMEOUTS.oauthComplete, label: "Auth redirect", intervalMs: 500 }
      ).catch(() => console.log("   ⚠️  Redirect timeout, checking anyway"));
      console.log("   ✅ Auth complete\n");
    }

    // ── Verify login ────────────────────────────────────────────────────
    console.log("8️⃣  Verifying login...");
    await sleep(TIMEOUTS.settle);

    finalUrl = await evalJS(cdp, sessionId, "window.location.href");
    console.log(`   URL: ${finalUrl}`);

    // If still on sign-in, try navigating to the app
    if (!finalUrl.includes(postLoginPattern) || finalUrl.includes("sign-in")) {
      const appUrl = postLoginPattern.startsWith("http") ? postLoginPattern : `https://${postLoginPattern}`;
      console.log("   Navigating to app...");
      await cdp.send("Page.navigate", { url: appUrl }, sessionId);
      await sleep(5000);
      finalUrl = await evalJS(cdp, sessionId, "window.location.href");
      console.log(`   URL: ${finalUrl}`);
    }

    loginSuccess = finalUrl.includes(postLoginPattern) && !finalUrl.includes("sign-in");

    // Content verification
    let ver = {};
    try { ver = JSON.parse(await evalJS(cdp, sessionId, VERIFY_LOGIN)); } catch {}

    console.log(`   URL matches:      ${loginSuccess ? "✅" : "❌"}`);
    console.log(`   Has sign-out:     ${ver.hasSignOut ? "✅" : "❌"}`);
    console.log(`   No sign-in form:  ${ver.noSignInForm ? "✅" : "❌"}`);

  } finally {
    // ── Cleanup (always runs) ───────────────────────────────────────────
    if (targetId) {
      await cdp.send("Target.closeTarget", { targetId }).catch(() => {});
    }
    cdp.close();
  }

  // ── Result ────────────────────────────────────────────────────────────
  console.log("\n" + "─".repeat(50));
  if (loginSuccess) {
    console.log("✅ LOGIN SUCCESSFUL");
    console.log(`   ${finalUrl}`);
  } else {
    console.log("❌ LOGIN FAILED");
    console.log(`   Expected: ${postLoginPattern}`);
    console.log(`   Got:      ${finalUrl}`);
  }
  console.log("─".repeat(50) + "\n");

  process.exit(loginSuccess ? 0 : 1);
}

main().catch((err) => {
  console.error(`\n❌ Fatal error: ${err.message}`);
  process.exit(1);
});
