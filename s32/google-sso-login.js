#!/usr/bin/env node
/**
 * google-sso-login.js
 *
 * Automates signing into web apps using an already-signed-in Google account
 * via Chrome DevTools Protocol (CDP) on port 9222.
 *
 * Usage:
 *   node google-sso-login.js <sign-in-url> <post-login-url-pattern>
 *
 * Examples:
 *   node google-sso-login.js "https://elevenlabs.io/app/sign-in" "elevenlabs.io/app"
 *   node google-sso-login.js "https://app.example.com/login" "app.example.com/dashboard"
 */

const http = require("http");
const WebSocket = require("ws");

const CDP_PORT = 9222;
const TIMEOUTS = {
  pageLoad: 15000,
  oauthPopup: 15000,
  oauthComplete: 45000,
  settle: 3000,
};

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

  send(method, params = {}, sessionId = undefined) {
    return new Promise((resolve, reject) => {
      const id = ++this.id;
      this.callbacks.set(id, { resolve, reject });
      const msg = { id, method, params };
      if (sessionId) msg.sessionId = sessionId;
      this.ws.send(JSON.stringify(msg));
    });
  }

  on(event, callback) {
    if (!this.events.has(event)) this.events.set(event, []);
    this.events.get(event).push(callback);
  }

  off(event, callback) {
    if (!this.events.has(event)) return;
    this.events.set(
      event,
      this.events.get(event).filter((cb) => cb !== callback)
    );
  }

  close() {
    if (this.ws) this.ws.close();
  }
}

// ─── Helpers ────────────────────────────────────────────────────────────────

const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

function withTimeout(promise, ms, label = "Operation") {
  return Promise.race([
    promise,
    sleep(ms).then(() => {
      throw new Error(`${label} timed out after ${ms}ms`);
    }),
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

// ─── Main ───────────────────────────────────────────────────────────────────

async function main() {
  const signInUrl = process.argv[2];
  const postLoginPattern = process.argv[3];

  if (!signInUrl || !postLoginPattern) {
    console.error(
      'Usage: node google-sso-login.js <sign-in-url> <post-login-url-pattern>\n' +
      'Example: node google-sso-login.js "https://elevenlabs.io/app/sign-in" "elevenlabs.io/app"'
    );
    process.exit(1);
  }

  console.log(`\n🔐 Google SSO Auto-Login`);
  console.log(`   Sign-in URL:  ${signInUrl}`);
  console.log(`   Expect after: ${postLoginPattern}\n`);

  // ── Step 1: Connect to browser ──────────────────────────────────────────
  console.log("1️⃣  Connecting to Chrome via CDP...");
  const browserVer = JSON.parse(await httpGet(`http://localhost:${CDP_PORT}/json/version`));
  const cdp = new CDPClient(browserVer.webSocketDebuggerUrl);
  await cdp.connect();
  console.log("   ✅ Connected\n");

  // ── Step 2: Open sign-in page ───────────────────────────────────────────
  console.log("2️⃣  Opening sign-in page...");
  const { targetId } = await cdp.send("Target.createTarget", { url: signInUrl });
  const { sessionId } = await cdp.send("Target.attachToTarget", { targetId, flatten: true });
  await cdp.send("Page.enable", {}, sessionId);
  await cdp.send("Runtime.enable", {}, sessionId);
  await cdp.send("DOM.enable", {}, sessionId);

  // Wait for load
  await withTimeout(
    new Promise((resolve) => {
      const handler = () => { cdp.off("Page.loadEventFired", handler); resolve(); };
      cdp.on("Page.loadEventFired", handler);
      setTimeout(resolve, TIMEOUTS.pageLoad);
    }),
    TIMEOUTS.pageLoad + 2000,
    "Page load"
  );
  await sleep(3000); // Next.js hydration

  const pageUrl = await evalJS(cdp, sessionId, "window.location.href");
  console.log(`   ✅ Loaded: ${pageUrl}\n`);

  // Check if already logged in (page redirected away from sign-in)
  if (!pageUrl.includes("sign-in") && pageUrl.includes(postLoginPattern)) {
    console.log("─".repeat(50));
    console.log("✅ ALREADY LOGGED IN");
    console.log(`   ${pageUrl}`);
    console.log("─".repeat(50) + "\n");
    cdp.close();
    process.exit(0);
  }

  // ── Step 3: Grant popup permission ──────────────────────────────────────
  // This prevents Chrome from blocking the Google OAuth popup
  console.log("3️⃣  Granting popup permission...");
  const origin = new URL(signInUrl).origin;
  await cdp.send("Browser.grantPermissions", {
    permissions: ["windowManagement"],
    origin,
  });
  console.log("   ✅ Popups allowed for", origin, "\n");

  // ── Step 4: Click "Sign in with Google" via real mouse events ───────────
  console.log("4️⃣  Clicking Google sign-in button...");

  // Find button position (retry up to 5 times for Next.js hydration)
  let posResult = null;
  for (let i = 0; i < 5; i++) {
    posResult = await evalJS(
      cdp,
      sessionId,
      `
      (function() {
        const patterns = ['sign in with google', 'continue with google'];
        for (const el of document.querySelectorAll('button, a, [role="button"]')) {
          const text = (el.textContent || '').toLowerCase().trim();
          for (const p of patterns) {
            if (text.includes(p)) {
              const r = el.getBoundingClientRect();
              return JSON.stringify({ x: r.x + r.width/2, y: r.y + r.height/2 });
            }
          }
        }
        return null;
      })()
      `
    );
    if (posResult) break;
    console.log(`   Retry ${i + 1}/5...`);
    await sleep(2000);
  }

  if (!posResult) {
    console.error("   ❌ Google sign-in button not found");
    cdp.close();
    process.exit(1);
  }

  const pos = JSON.parse(posResult);

  // Real mouse click (bypasses popup blocker unlike Runtime.evaluate .click())
  await cdp.send("Input.dispatchMouseEvent", { type: "mousePressed", x: pos.x, y: pos.y, button: "left", clickCount: 1 }, sessionId);
  await cdp.send("Input.dispatchMouseEvent", { type: "mouseReleased", x: pos.x, y: pos.y, button: "left", clickCount: 1 }, sessionId);
  console.log("   ✅ Clicked\n");

  // ── Step 5: Wait for OAuth popup ────────────────────────────────────────
  console.log("5️⃣  Waiting for OAuth popup...");

  // Record existing page targets
  const { targetInfos: beforeTargets } = await cdp.send("Target.getTargets");
  const beforePageIds = new Set(beforeTargets.filter((t) => t.type === "page").map((t) => t.targetId));

  // Poll for new page target
  let oauthTargetId = null;
  let oauthUrl = null;

  await withTimeout(
    new Promise((resolve) => {
      const poll = setInterval(async () => {
        try {
          const { targetInfos } = await cdp.send("Target.getTargets");
          const newPages = targetInfos.filter(
            (t) => t.type === "page" && !beforePageIds.has(t.targetId) && t.url && !t.url.startsWith("chrome://")
          );
          if (newPages.length > 0) {
            clearInterval(poll);
            oauthTargetId = newPages[0].targetId;
            oauthUrl = newPages[0].url;
            resolve();
          }
        } catch {}
      }, 300);
    }),
    TIMEOUTS.oauthPopup,
    "OAuth popup detection"
  );

  console.log(`   ✅ Popup opened: ${oauthUrl.substring(0, 80)}...\n`);

  // Attach to popup
  const { sessionId: oauthSid } = await cdp.send("Target.attachToTarget", { targetId: oauthTargetId, flatten: true });
  await cdp.send("Runtime.enable", {}, oauthSid);

  // ── Step 6: Handle Google account selection ─────────────────────────────
  console.log("6️⃣  Processing Google authorization...");

  for (let attempt = 0; attempt < 5; attempt++) {
    await sleep(3000);

    let url;
    try {
      url = await evalJS(cdp, oauthSid, "window.location.href");
    } catch (e) {
      // Session lost during cross-origin navigation — popup is processing auth
      console.log("   Session detached — popup processing auth\n");
      break;
    }
    console.log(`   [${attempt + 1}] ${url.substring(0, 100)}`);

    // If we've left Google, the auth is processing
    if (!url.includes("accounts.google.com")) {
      console.log("   ✅ Left Google — auth processing\n");
      break;
    }

    // Handle account chooser / consent screen
    try {
      await evalJS(
        cdp,
        oauthSid,
        `
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
        `
      );
    } catch {
      // Session may be detaching
      break;
    }
  }

  // ── Step 7: Wait for popup to close ─────────────────────────────────────
  // The Firebase auth handler processes the code, sends result to opener, then closes
  console.log("7️⃣  Waiting for OAuth popup to close...");

  await withTimeout(
    new Promise((resolve) => {
      const poll = setInterval(async () => {
        try {
          const { targetInfos } = await cdp.send("Target.getTargets");
          const t = targetInfos.find((t) => t.targetId === oauthTargetId);
          if (!t || !t.attached) {
            clearInterval(poll);
            resolve();
          }
        } catch {}
      }, 500);
    }),
    TIMEOUTS.oauthComplete,
    "Popup close"
  );

  console.log("   ✅ Popup closed\n");

  // ── Step 8: Verify login ────────────────────────────────────────────────
  console.log("8️⃣  Verifying login...");
  await sleep(TIMEOUTS.settle);

  let finalUrl = await evalJS(cdp, sessionId, "window.location.href");
  console.log(`   URL: ${finalUrl}`);

  // If still on sign-in, try navigating to the app
  if (!finalUrl.includes(postLoginPattern) || finalUrl.includes("sign-in")) {
    console.log("   Navigating to app...");
    await cdp.send("Page.navigate", { url: `https://${postLoginPattern}` }, sessionId);
    await sleep(5000);
    finalUrl = await evalJS(cdp, sessionId, "window.location.href");
    console.log(`   URL: ${finalUrl}`);
  }

  const loginSuccess = finalUrl.includes(postLoginPattern) && !finalUrl.includes("sign-in");

  // Content verification
  const verResult = await evalJS(
    cdp,
    sessionId,
    `
    (function() {
      const body = (document.body?.innerText || '').toLowerCase();
      return JSON.stringify({
        hasSignOut: body.includes('sign out') || body.includes('log out'),
        noSignInForm: !document.querySelector('input[type="email"], input[name="email"]'),
      });
    })()
    `
  );

  let ver;
  try { ver = JSON.parse(verResult); } catch { ver = {}; }

  console.log(`   URL matches:      ${loginSuccess ? "✅" : "❌"}`);
  console.log(`   Has sign-out:     ${ver.hasSignOut ? "✅" : "❌"}`);
  console.log(`   No sign-in form:  ${ver.noSignInForm ? "✅" : "❌"}`);

  // ── Result ──────────────────────────────────────────────────────────────
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

  cdp.close();
  process.exit(loginSuccess ? 0 : 1);
}

main().catch((err) => {
  console.error(`\n❌ Fatal error: ${err.message}`);
  process.exit(1);
});
