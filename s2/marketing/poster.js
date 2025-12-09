const { connectToBrowser } = require('../scrapers/common');

async function postTweet(content) {
    if (!content) {
        throw new Error("Content is empty");
    }

    console.log(`Marketing: Posting tweet: "${content}"`);

    // Safety check for MVP: just log if we are in test mode or if browser fails
    // But we want to prove the loop, so let's try to post.

    const { browser, context } = await connectToBrowser();
    const page = await context.newPage();

    try {
        await page.goto('https://x.com/compose/post', { waitUntil: 'domcontentloaded' });

        const editorSelector = '[data-testid="tweetTextarea_0"]';
        console.log('Waiting for editor...');

        try {
            await page.waitForSelector(editorSelector, { timeout: 10000 });
        } catch (e) {
            console.error("Could not find tweet editor. Are you logged in?");
            throw new Error("Not logged in or UI changed");
        }

        await page.click(editorSelector);
        await page.keyboard.type(content);

        // Wait a bit
        await page.waitForTimeout(1000);

        const postButtonSelector = '[data-testid="tweetButton"]';
        // Verify it's enabled?
        await page.click(postButtonSelector);
        console.log("Clicked post button.");

        await page.waitForTimeout(3000); // Wait for post to send

    } catch (e) {
        console.error("Failed to post tweet:", e.message);
        throw e;
    } finally {
        await page.close();
        await browser.close();
    }
}

module.exports = { postTweet };
