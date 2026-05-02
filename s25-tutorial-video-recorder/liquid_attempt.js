const { chromium } = require('playwright');
const fs = require('fs');
const path = require('path');

function logWithTimer(msg) {
    const now = Date.now();
    const hrtimeBigInt = process.hrtime.bigint;
    const seconds = Math.floor((now - Number(hrtimeBigInt)) / 1e9);
    console.log(`[${seconds.toFixed(1)}s] ${msg}`);
}

// Helper: Overlay function
async function showSubtitle(text, duration) {
    await page.setViewport({ width: 1280, height: 720 });
    // Wait until hero text appears
    await page.waitForSelector('h1', { timeout: 10000 });

    // Create overlay div
    const overlay = await page.$(
        `<div id="showSubtitleOverlay" style="
            position:fixed;top:0;left:0;width:100vw;height:100vh;
            z-index:9999;display:flex;align-items:center;justify-content:center;
            background:rgba(0,0,0,0.7);color:#00ffcc;font-family:monospace;font-size:2.4em;
            pointer-events:none;transition:opacity 0.3s;"
        >
            <span style="text-shadow: 0 0 8px #00ffcc;">${text}</span>
        </div>`
    );

    await overlay.fill(); // ensure it's rendered
    await page.evaluate(el => {
        const o = document.getElementById('showSubtitleOverlay');
        if (o) {
            o.style.opacity = '1';
            o.style.transition = 'opacity 0.3s';
            setTimeout(() => { o.style.opacity = '0'; }, duration * 1000);
        }
    }, overlay);

    // Apply overlay globally
    await page.evaluate(`
        () => {
            const el = document.createElement('style');
            el.textContent = \`#showSubtitleOverlay {position:fixed;top:0;left:0;width:100vw;height:100vh;z-index:9999;display:flex;align-items:center;justify-content:center;background:rgba(0,0,0,0.7);color:#00ffcc;font-family:monospace;font-size:2.4em;pointer-events:none;transition:opacity 0.3s;}
            #showSubtitleOverlay {opacity:0;}
            #showSubtitleOverlay span {text-shadow:0 0 8px #00ffcc;}
            document.body.appendChild(el);
            setTimeout(()=>{document.getElementById('showSubtitleOverlay').style.opacity='0';}, ${duration * 1000} * 1000);
        }
    `);
    // Or simpler: inject via page.evaluate to add class or style
    // For brevity, we'll just rely on inline style above.
}

// Main script
(async () => {
    let browser, context, page;
    let startTime = Date.now();

    try {
        browser = await chromium.launch({ headless: true, args: ['--no-sandbox', '--disable-setuid-sandbox'] });
        context = await browser.newContext({
            userAgent: 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36',
            viewport: { width: 1280, height: 720 }
        });
        page = await context.newPage();

        // Record video
        const videoPath = path.join(__dirname, '/tutorials/video_tutorial.mp4');
        const videoRec = await page.startRecord({ path: videoPath });
        console.log(`[Start] Recording video to ${videoPath}`);

        // Scene 1: Copilot trending repo
        logWithTimer('Scene 1: Navigating to trending AI repo...');
        await page.goto('https://github.com/features/copilot', { waitUntil: 'domcontentloaded' });
        await page.waitForSelector('h1', { timeout: 12000 });
        await showSubtitle('AI Copilot – Revolutionizing Coding', 2);
        await page.hover('h1'); // highlight header with neon glow (simulated via overlay)
        logWithTimer('Scene 1: Header highlighted.');

        // Scene 2: Stripe Payments page
        logWithTimer('Scene 2: Navigating to Stripe payments page...');
        await page.goto('https://stripe.com/en-us/payments', { waitUntil: 'domcontentloaded' });
        await showSubtitle('How to Monetize Your AI App', 2);
        logWithTimer('Scene 2: Subtitles shown.');

        // Scene 3: Virtual Terminal simulation
        logWithTimer('Scene 3: Wiping page and showing Virtual Terminal...');
        await page.clear();
        await page.setContent(`
            <html>
                <body>
                    <div id="terminal" style="font-family: monospace; font-size: 1.2em; border: 1px solid #444; padding: 20px; min-height: 600px;">
                        <div id="status" style="margin-bottom: 15px; color:#00ffcc;">Status: Idle</div>
                        <pre id="log"></pre>
                    </div>
                </body>
            </html>
        `, { waitable: true });
        // Simulate AI typing
        const logEl = document.getElementById('log');
        const messages = [
            'Cloning repo...',
            'Installing dependencies...',
            'Deploying to production...',
            'Status: Monetized.'
        ];
        let idx = 0;
        const interval = setInterval(async () => {
            if (idx < messages.length) {
                const msg = messages[idx++];
                const span = document.createElement('span');
                span.style.color = '#00ffcc';
                span.textContent = `[${idx * 0.5}s] ${msg}`;
                await logEl.appendChild(span);
                await new Promise(r => setTimeout(r, 800));
            } else {
                clearInterval(interval);
                await page.evaluate(() => {
                    document.getElementById('status').innerText = 'Status: Monetized.';
                });
            }
        }, 900);

        // Wait for all logs to finish
        await new Promise(resolve => setTimeout(resolve, 6500));

        logWithTimer('Scene 3: Virtual terminal simulated.');

    } catch (err) {
        logWithTimer(`Error encountered: ${err.message}`);
        // Take debug screenshot
        if (page) await page.screenshot({ path: path.join(__dirname, '/tutorials/debug_error.png') });
    } finally {
        // Clean exit
        if (context) await context.close();
        if (browser) await browser.close();
        logWithTimer('Script finished. Video saved to /tutorials/video_tutorial.mp4');
    }
})();