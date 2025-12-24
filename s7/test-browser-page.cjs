const puppeteer = require('puppeteer-core');
const fs = require('fs');

async function testBrowserPage() {
  let browser;
  try {
    // Get WebSocket endpoint
    console.log('Getting CDP WebSocket endpoint...');
    const versionResponse = await fetch('http://localhost:9222/json/version');
    const versionData = await versionResponse.json();
    const wsEndpoint = versionData.webSocketDebuggerUrl;

    console.log('Connecting to browser via CDP...');
    browser = await puppeteer.connect({
      browserWSEndpoint: wsEndpoint,
      defaultViewport: { width: 1280, height: 1024 }
    });

    const page = await browser.newPage();

    // Capture console errors and warnings
    const consoleErrors = [];
    const consoleWarnings = [];

    // Function to log to file
    const logToFile = (level, message) => {
      const timestamp = new Date().toISOString();
      const logEntry = `[${timestamp}] [${level}] ${message}\n`;
      fs.appendFileSync('browser-console.log', logEntry);
    };

    page.on('console', (msg) => {
      const type = msg.type();
      const text = msg.text();

      // Filter out browser extension errors
      const isExtensionError = text.includes('ethereum') ||
                              text.includes('Cannot redefine property') ||
                              text.includes('MetaMask') ||
                              text.includes('extension');

      if (type === 'error') {
        if (!isExtensionError) {
          consoleErrors.push(text);
          console.error('CONSOLE ERROR:', text);
          logToFile('ERROR', `Browser Console Error: ${text}`);
        } else {
          console.warn('Ignoring browser extension error:', text);
          logToFile('INFO', `Ignored extension error: ${text}`);
        }
      } else if (type === 'warning') {
        consoleWarnings.push(text);
        console.warn('CONSOLE WARNING:', text);
        logToFile('WARN', `Browser Console Warning: ${text}`);
      } else if (type === 'log' || type === 'info') {
        logToFile('INFO', `Browser Console ${type}: ${text}`);
      }
    });

    page.on('pageerror', (error) => {
      // Filter out common browser extension errors that we can't fix
      const message = error.message;
      if (!message.includes('ethereum') && !message.includes('Cannot redefine property')) {
        consoleErrors.push(message);
        console.error('PAGE ERROR:', message);
        logToFile('ERROR', `Browser Page Error: ${message}`);
      } else {
        console.warn('Ignoring browser extension error:', message);
        logToFile('INFO', `Ignored extension page error: ${message}`);
      }
    });

    // Navigate to app
    console.log('Loading application at http://localhost:3000/...');
    await page.goto('http://localhost:3000/', { waitUntil: 'networkidle2', timeout: 10000 });

    // Wait for app to load
    await page.waitForSelector('body', { timeout: 5000 });

    // Check page title
    const title = await page.title();
    console.log('Page title:', title);

    if (!title.includes('AI Scraper')) {
      console.error('ERROR: Unexpected page title');
      process.exit(1);
    }

    // Check for login form
    const hasLoginForm = await page.$('#email') !== null;
    console.log('Login form found:', hasLoginForm);

    // Get page HTML to check for issues
    const bodyHtml = await page.evaluate(() => document.body.innerHTML.substring(0, 500));
    console.log('Page HTML preview:', bodyHtml.substring(0, 200) + '...');

    // Try to execute some JavaScript on the page
    try {
      const jsTest = await page.evaluate(() => {
        console.log('Testing JavaScript execution...');
        return 'JavaScript works';
      });
      console.log('JavaScript execution test:', jsTest);
    } catch (jsError) {
      console.error('JavaScript execution failed:', jsError.message);
      consoleErrors.push('JavaScript execution error: ' + jsError.message);
    }

    // Wait a bit for any async errors to appear
    await new Promise(resolve => setTimeout(resolve, 2000));

    // Report results
    if (consoleErrors.length > 0) {
      console.error(`FOUND ${consoleErrors.length} BROWSER CONSOLE ERRORS:`);
      consoleErrors.forEach((error, i) => console.error(`  ${i+1}. ${error}`));
      logToFile('ERROR', `Browser test FAILED: ${consoleErrors.length} console errors found`);
      console.error('\n❌ BROWSER HAS CONSOLE ERRORS THAT NEED TO BE FIXED');
      process.exit(1);
    }

    if (consoleWarnings.length > 0) {
      console.warn(`FOUND ${consoleWarnings.length} BROWSER CONSOLE WARNINGS:`);
      consoleWarnings.forEach((warning, i) => console.warn(`  ${i+1}. ${warning}`));
      logToFile('WARN', `Browser test completed with ${consoleWarnings.length} warnings`);
    }

    console.log('✅ Browser page loaded successfully with no console errors');
    logToFile('SUCCESS', 'Browser test PASSED: No console errors detected');
    process.exit(0);

  } catch (error) {
    console.error('Browser test failed:', error.message);
    process.exit(1);
  } finally {
    if (browser) {
      try {
        await browser.disconnect();
      } catch (e) {
        // Ignore disconnect errors
      }
    }
  }
}

testBrowserPage().catch(console.error);