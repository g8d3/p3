const { chromium } = require('playwright');

const ARGS = process.argv.slice(2);
const CDP_URL = 'http://localhost:9222';

async function main() {
    if (ARGS.length === 0) {
        console.log('Usage:');
        console.log('  node x_poster.js "Tweet content..."');
        console.log('  Note: Ensure your Chrome is running with --remote-debugging-port=9222');
        return;
    }

    const tweetContent = ARGS[0];
    console.log(`Connecting to browser at ${CDP_URL} to post: "${tweetContent}"`);

    let browser;
    try {
        browser = await chromium.connectOverCDP(CDP_URL);
    } catch (err) {
        console.error(`Failed to connect to browser automatically: ${err.message}`);
        console.error('Make sure Chrome is running with: --remote-debugging-port=9222');
        process.exit(1);
    }

    // Use the first context (usually the default profile)
    const context = browser.contexts()[0];
    if (!context) {
        console.error('No browser context found.');
        await browser.close();
        process.exit(1);
    }

    const page = await context.newPage();

    try {
        console.log('Navigating to composer...');
        await page.goto('https://x.com/compose/post');

        // Wait for the editor to appear
        const editorSelector = '[data-testid="tweetTextarea_0"]';
        console.log('Waiting for editor...');
        await page.waitForSelector(editorSelector, { timeout: 15000 });

        // Type content
        await page.click(editorSelector);
        console.log('Typing content...');
        await page.keyboard.type(tweetContent);

        // Click Post button
        const postButtonSelector = '[data-testid="tweetButton"]';
        await page.waitForSelector(postButtonSelector);

        // Small delay to ensure button enabled state is active
        await page.waitForTimeout(500);

        console.log('Clicking post...');
        await page.click(postButtonSelector);

        // Wait for post to complete (indicated by dialog closing or URL change)
        await page.waitForTimeout(3000);

        console.log('Post submitted successfully!');

        // Cleanup: close the tab we opened (optional, based on preference)
        await page.close();

    } catch (e) {
        console.error('Failed to post:', e);
    } finally {
        // Disconnect from the browser (this does NOT close the actual browser window)
        await browser.close();
    }
}

main();
