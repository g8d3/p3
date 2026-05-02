const { chromium } = require('playwright');
const fs = require('fs');

(async () => {
  const startTime = Date.now();
  const getElapsed = () => `[+${((Date.now() - startTime) / 1000).toFixed(1)}s]`;

  console.log(`${getElapsed()} 🚀 Initializing Browser...`);
  
  const browser = await chromium.launch({ headless: true });
  const context = await browser.newContext({
    userAgent: 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
    viewport: { width: 1280, height: 720 },
    recordVideo: { dir: 'tutorials/', size: { width: 1280, height: 720 } }
  });

  const page = await context.newPage();

  const showSubtitle = async (text, duration) => {
    console.log(`${getElapsed()} 💬 Subtitle: "${text}"`);
    await page.evaluate((msg) => {
      let el = document.getElementById('ai-sub') || document.createElement('div');
      el.id = 'ai-sub';
      Object.assign(el.style, {
        position: 'fixed', bottom: '40px', left: '50%', transform: 'translateX(-50%)',
        backgroundColor: 'rgba(15, 23, 42, 0.95)', color: '#00ffcc', padding: '12px 25px',
        borderRadius: '8px', fontSize: '22px', fontFamily: 'monospace', zIndex: '10000',
        textAlign: 'center', border: '1px solid #00ffcc', width: '75%', fontWeight: 'bold'
      });
      el.innerText = msg;
      if (!document.body.contains(el)) document.body.appendChild(el);
    }, text);
    
    const steps = Math.ceil(duration/1000);
    for(let i = steps; i > 0; i--) {
        process.stdout.write(`${getElapsed()} ...holding for ${i}s \r`);
        await page.waitForTimeout(1000);
    }
    process.stdout.write('\n');
  };

  try {
    // SCENE 1: GitHub
    console.log(`${getElapsed()} 🌐 Navigating to GitHub...`);
    await page.goto('https://github.com/theopensource-ai/OpenClaw', { waitUntil: 'load', timeout: 60000 });
    
    console.log(`${getElapsed()} 🔍 Searching for Repository Title...`);

    // UNIVERSAL SELECTOR: Target the repository link in the breadcrumb header
    const repoHeader = page.locator('div.AppHeader-context-full nav ol li:last-child a, #repository-container-header a').first();
    
    try {
      await repoHeader.waitFor({ state: 'visible', timeout: 10000 });
    } catch (e) {
      console.log(`${getElapsed()} ⚠️  Standard locator failed. Taking a debug screenshot...`);
      await page.screenshot({ path: 'debug_error.png' });
      // Fallback: Just use the document title if the element is being weird
      console.log(`${getElapsed()} 🔄 Falling back to generic header search...`);
    }

    await showSubtitle("Meet OpenClaw: The Open-Source AI Agent for coding.", 3000);
    
    // We attempt the highlight, but wrap it so it doesn't crash the script if element is missing
    await repoHeader.evaluate(el => {
      el.style.transition = "all 0.5s ease";
      el.style.color = "#00ffcc";
      el.style.fontSize = "1.5em";
      el.style.textShadow = "0 0 10px #00ffcc";
    }).catch(() => console.log(`${getElapsed()} ⚠️  Could not apply styles to header.`));

    // SCENE 2: Stripe
    console.log(`${getElapsed()} 🌐 Navigating to Stripe...`);
    await page.goto('https://stripe.com/en-us/payments', { waitUntil: 'domcontentloaded' });
    await showSubtitle("Step 1: Build your Micro-SaaS with AI Agents.", 3000);
    await showSubtitle("Step 2: Connect Stripe for automated revenue.", 3000);

    // SCENE 3: Terminal Simulation
    console.log(`${getElapsed()} 🖥️  Generating Virtual Terminal...`);
    await page.evaluate(() => {
        document.body.innerHTML = `
        <div style="background:#020617; color:#00ffcc; font-family:monospace; padding:60px; height:100vh; font-size:24px; display:flex; flex-direction:column; justify-content:center;">
            <div id="content"></div>
            <div style="margin-top:10px;">> <span id="cursor">█</span></div>
        </div>`;
    });

    const codeLines = [
        "Initializing OpenClaw Agent...",
        "Generating API endpoints...",
        "Connecting to Stripe Production...",
        "Deployment Complete: https://ai-startup.com",
        "STATUS: LIVE & MONETIZED"
    ];

    for (const line of codeLines) {
        console.log(`${getElapsed()} ⌨️  Agent Activity: ${line}`);
        await page.evaluate((l) => {
            const div = document.createElement('div');
            div.innerText = `> ${l}`;
            document.getElementById('content').appendChild(div);
        }, line);
        await page.waitForTimeout(1000);
    }

    await showSubtitle("The future of software is autonomous. Start now.", 4000);

  } catch (err) {
    console.error(`\n${getElapsed()} ❌ FATAL ERROR: ${err.message}`);
    await page.screenshot({ path: 'fatal_error.png' });
  } finally {
    console.log(`${getElapsed()} 💾 Closing and Saving Video...`);
    try {
        await context.close();
        await browser.close();
    } catch (e) {}
    console.log(`${getElapsed()} 🏁 Process Finished. Video is in /tutorials`);
  }
})();