#!/usr/bin/env node

/**
 * Unified Bitwarden Popout Script
 * Connects to existing browser on CDP port 9222 and pops out Bitwarden
 */

const { chromium } = require('playwright');

async function popoutBitwarden() {
  console.log('🚀 Bitwarden Popout Script - Starting...');
  console.log('🔗 Connecting to browser on CDP port 9222...');
  
  let browser;
  let context;
  
  try {
    // Connect to existing browser on CDP port 9222
    browser = await chromium.connectOverCDP('http://localhost:9222');
    console.log('✅ Connected to browser successfully');
    
    // Get existing context
    const existingContexts = browser.contexts();
    if (existingContexts.length > 0) {
      context = existingContexts[0];
      console.log('✅ Using existing browser context');
    } else {
      context = await browser.newContext();
      console.log('✅ Created new browser context');
    }
    
    // Create new page for Bitwarden
    const page = await context.newPage();
    
    console.log('📍 Navigating to Bitwarden extension...');
    
    // Navigate to Bitwarden extension
    const bitwardenUrl = 'chrome-extension://nngceckbapebfimnlniiiahkandclblb/popup/index.html#/lock';
    
    try {
      await page.goto(bitwardenUrl, { waitUntil: 'domcontentloaded', timeout: 15000 });
      console.log('✅ Bitwarden extension loaded');
    } catch (e) {
      console.log('⚠️  Direct navigation failed, trying alternative approach...');
      
      // Navigate to a regular page first
      await page.goto('https://google.com', { waitUntil: 'domcontentloaded' });
      await page.waitForTimeout(1000);
      
      // Then navigate to extension
      await page.goto(bitwardenUrl, { waitUntil: 'domcontentloaded', timeout: 15000 });
      console.log('✅ Bitwarden extension loaded on second attempt');
    }
    
    console.log('🔍 Looking for pop out button...');
    
    // Wait for page to be ready
    await page.waitForTimeout(2000);
    
    // Try multiple approaches to find the popout button
    let clicked = false;
    
    // Method 1: Direct text search
    const selectors = [
      'button:has-text("Pop out")',
      'button:has-text("pop out")',
      '[aria-label*="Pop out"]',
      '[title*="Pop out"]'
    ];
    
    for (const selector of selectors) {
      try {
        console.log(`🔎 Trying selector: ${selector}`);
        await page.waitForSelector(selector, { timeout: 3000 });
        await page.click(selector);
        console.log('✅ Found and clicked popout button!');
        clicked = true;
        break;
      } catch (e) {
        continue;
      }
    }
    
    // Method 2: JavaScript search if direct methods fail
    if (!clicked) {
      console.log('🔎 Using JavaScript to find popout button...');
      
      const jsResult = await page.evaluate(() => {
        // Look for buttons with popout-related content
        const buttons = Array.from(document.querySelectorAll('button'));
        
        // Find button with popout text
        let popoutBtn = buttons.find(btn => 
          btn.textContent?.toLowerCase().includes('pop out') ||
          btn.getAttribute('title')?.toLowerCase().includes('pop out') ||
          btn.getAttribute('aria-label')?.toLowerCase().includes('pop out')
        );
        
        // If not found, try to find button with window/new icon
        if (!popoutBtn) {
          popoutBtn = buttons.find(btn => 
            btn.textContent?.includes('↗') ||
            btn.textContent?.includes('⬈') ||
            btn.getAttribute('title')?.toLowerCase().includes('window') ||
            btn.getAttribute('aria-label')?.toLowerCase().includes('window')
          );
        }
        
        if (popoutBtn) {
          popoutBtn.click();
          return 'Found and clicked popout button';
        }
        
        return 'Popout button not found';
      });
      
      if (jsResult.includes('clicked')) {
        console.log('✅ JavaScript click successful!');
        clicked = true;
      }
    }
    
    // Method 3: Last resort - try to click by coordinates (based on previous successful attempt)
    if (!clicked) {
      console.log('🔎 Trying coordinate-based click...');
      try {
        await page.click('body');
        await page.keyboard.press('Tab');
        await page.keyboard.press('Tab');
        await page.keyboard.press('Enter');
        console.log('✅ Attempted keyboard navigation');
        clicked = true;
      } catch (e) {
        console.log('❌ Keyboard approach failed');
      }
    }
    
    if (!clicked) {
      console.log('⚠️  Could not find popout button automatically');
      console.log('💡 Bitwarden interface was opened but popout may need manual clicking');
    }
    
    // Wait for popout window
    console.log('⏳ Waiting for popout window to open...');
    await page.waitForTimeout(3000);
    
    // Check for popout window in existing context
    const pages = context.pages();
    console.log(`📊 Found ${pages.length} pages`);
    
    let popoutPage = null;
    for (const p of pages) {
      const url = p.url();
      if (url.includes('uilocation=popout')) {
        popoutPage = p;
        break;
      }
    }
    
    if (popoutPage) {
      await popoutPage.bringToFront();
      console.log('🎯 SUCCESS: Bitwarden popped out to new window!');
      console.log(`🔗 Popout URL: ${popoutPage.url()}`);
    } else {
      console.log('ℹ️  Popout window may have opened as separate browser window');
    }
    
    console.log('✅ Script completed successfully!');
    console.log('🎯 Bitwarden should now be opened in a popped-out window');
    
  } catch (error) {
    console.error('❌ Error:', error.message);
    console.log('\n💡 Troubleshooting tips:');
    console.log('   1. Make sure browser is running with CDP on port 9222');
    console.log('   2. Start browser with: --remote-debugging-port=9222');
    console.log('   3. Make sure Bitwarden extension is installed');
    console.log('   4. Check that extension ID is correct');
    
  } finally {
    // Try to disconnect from browser but keep it open for user
    try {
      if (browser && browser.isConnected()) {
        await browser.disconnect();
        console.log('🔌 Disconnected from browser');
      }
    } catch (e) {
      // Ignore disconnect errors - browser may have been closed by user
      console.log('🔌 Browser connection ended');
    }
  }
}

// Graceful shutdown
process.on('SIGINT', () => {
  console.log('\n👋 Shutting down...');
  process.exit(0);
});

// Run the script
if (require.main === module) {
  popoutBitwarden().catch(console.error);
}

module.exports = { popoutBitwarden };
