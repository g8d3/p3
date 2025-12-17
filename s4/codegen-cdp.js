const { chromium } = require('playwright');

(async () => {
  // 1. Connect to the running browser instance via CDP
  const browser = await chromium.connectOverCDP('http://localhost:9222');
  
  // 2. Get the default context and first page
  const defaultContext = browser.contexts()[0];
  const page = defaultContext.pages()[0];
  
  // You can navigate to a starting URL here if the page is not already open
  // await page.goto('https://example.com'); 
  
  // 3. Call page.pause() to open the Playwright Inspector (Codegen UI)
  console.log("Playwright is connected. Invoking Codegen Inspector with page.pause().");
  await page.pause();

  // The script will stay open until you close the Playwright Inspector or the browser
  
  // Optional: Add a cleanup function to close the connection after you're done
  // await browser.close();
})();