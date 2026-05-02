#!/usr/bin/env node
/**
 * logout-app.js
 *
 * Clears auth state for a web app by clearing cookies, localStorage,
 * sessionStorage, and IndexedDB for the given origin.
 *
 * Usage:
 *   node logout-app.js <origin-or-url>
 *
 * Examples:
 *   node logout-app.js https://elevenlabs.io
 *   node logout-app.js app.example.com
 */

const http = require("http");
const WebSocket = require("ws");

const CDP_PORT = 9222;

function httpGet(url) {
  return new Promise((resolve, reject) => {
    http.get(url, (res) => {
      let b = "";
      res.on("data", (d) => (b += d));
      res.on("end", () => resolve(b));
    }).on("error", reject);
  });
}

async function main() {
  let origin = process.argv[2];
  if (!origin) {
    console.error("Usage: node logout-app.js <origin-or-url>");
    console.error('Example: node logout-app.js https://elevenlabs.io');
    process.exit(1);
  }

  // Normalize: add protocol if missing
  if (!origin.startsWith("http")) origin = `https://${origin}`;
  const urlObj = new URL(origin);
  const originStr = urlObj.origin;

  console.log(`\n🔓 Logging out: ${originStr}\n`);

  const ver = JSON.parse(await httpGet(`http://localhost:${CDP_PORT}/json/version`));
  const ws = new WebSocket(ver.webSocketDebuggerUrl);
  await new Promise((r) => ws.on("open", r));

  let id = 0;
  const cbs = new Map();
  ws.on("message", (d) => {
    const m = JSON.parse(d.toString());
    if (m.id && cbs.has(m.id)) {
      const c = cbs.get(m.id);
      cbs.delete(m.id);
      m.error ? c.reject(new Error(m.error.message)) : c.resolve(m.result);
    }
  });

  function send(method, params = {}, sid) {
    return new Promise((resolve, reject) => {
      const i = ++id;
      cbs.set(i, { resolve, reject });
      const msg = { id: i, method, params };
      if (sid) msg.sessionId = sid;
      ws.send(JSON.stringify(msg));
    });
  }

  // 1. Open a tab on the origin to clear site-specific storage
  const { targetId } = await send("Target.createTarget", { url: originStr });
  const { sessionId } = await send("Target.attachToTarget", { targetId, flatten: true });
  await send("Runtime.enable", {}, sessionId);
  await send("Network.enable", {}, sessionId);

  // Wait for page load
  await new Promise((r) => setTimeout(r, 3000));

  // 2. Clear cookies for this origin
  await send("Network.clearBrowserCookies", {}, sessionId);
  console.log("   Cleared cookies");

  // 3. Clear localStorage, sessionStorage, IndexedDB
  await send(
    "Runtime.evaluate",
    {
      expression: `
      (async function() {
        let cleared = [];
        
        // localStorage
        try { localStorage.clear(); cleared.push('localStorage'); } catch {}
        
        // sessionStorage
        try { sessionStorage.clear(); cleared.push('sessionStorage'); } catch {}
        
        // IndexedDB
        try {
          if (indexedDB.databases) {
            const dbs = await indexedDB.databases();
            for (const db of dbs) {
              indexedDB.deleteDatabase(db.name);
            }
            cleared.push('IndexedDB(' + dbs.length + ' dbs)');
          }
        } catch {}
        
        // Service worker caches
        try {
          if (caches && caches.keys) {
            const keys = await caches.keys();
            for (const k of keys) await caches.delete(k);
            if (keys.length) cleared.push('caches(' + keys.length + ')');
          }
        } catch {}
        
        return cleared.join(', ') || 'nothing to clear';
      })()
    `,
      returnByValue: true,
      awaitPromise: true,
    },
    sessionId
  ).then((r) => console.log(`   Cleared storage: ${r.result?.value}`));

  // 4. Try Firebase sign-out if available
  const fbResult = await send(
    "Runtime.evaluate",
    {
      expression: `
      (async function() {
        try {
          // Try to get Firebase auth instance
          const { getAuth, signOut } = await import('firebase/auth');
          const auth = getAuth();
          await signOut(auth);
          return 'firebase-signout';
        } catch {
          return 'no-firebase';
        }
      })()
    `,
      returnByValue: true,
      awaitPromise: true,
    },
    sessionId
  ).then((r) => r.result?.value);
  console.log(`   Firebase: ${fbResult}`);

  // 5. Close the tab
  await send("Target.closeTarget", { targetId });

  console.log("\n✅ Logout complete\n");
  ws.close();
}

main().catch((err) => {
  console.error(`\n❌ Error: ${err.message}`);
  process.exit(1);
});
