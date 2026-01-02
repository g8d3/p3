const { chromium } = require('playwright');

(async () => {
  // 1. Connect to the existing instance on port 9222
  const browser = await chromium.connectOverCDP('http://localhost:9222');

  // 2. Get the default context (CDP usually uses the existing one)
  const defaultContext = browser.contexts()[0];

  // 3. Open a new tab (page)
  const newPage = await defaultContext.newPage();

  // 4. Navigate and perform actions
  await newPage.goto('https://www.wikipedia.org');
  console.log('New tab opened and navigated!');

  // Note: Do not use browser.close() unless you want to kill the entire app.
  // Use newPage.close() to just close the tab you created.
})();