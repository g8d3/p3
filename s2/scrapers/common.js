const { chromium } = require('playwright');

const CDP_URL = 'http://localhost:9222';

async function connectToBrowser() {
    try {
        console.log(`Connecting to browser at ${CDP_URL}...`);
        const browser = await chromium.connectOverCDP(CDP_URL);
        const context = browser.contexts()[0];
        if (!context) {
            throw new Error('No browser context found.');
        }
        return { browser, context };
    } catch (err) {
        console.log(`Could not connect to existing browser: ${err.message}`);
        console.log('Falling back to launching new browser (headless)...');
        const browser = await chromium.launch();
        const context = await browser.newContext();
        return { browser, context };
    }
}

module.exports = { connectToBrowser };
