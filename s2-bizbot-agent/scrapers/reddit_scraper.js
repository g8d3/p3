const { connectToBrowser } = require('./common');

async function scrapeReddit(subreddit = 'sidehustle') {
    const url = `https://www.reddit.com/r/${subreddit}/top/?t=week`;
    console.log(`Scraping ${url}...`);

    const { browser, context } = await connectToBrowser();
    const page = await context.newPage();

    const results = [];

    try {
        await page.goto(url, { waitUntil: 'domcontentloaded' });

        // Wait for post list
        await page.waitForSelector('shreddit-post', { timeout: 10000 }).catch(() => console.log("Timeout waiting for shreddit-post"));

        // New Reddit uses <shreddit-post> tags
        const posts = await page.$$('shreddit-post');

        console.log(`Found ${posts.length} posts. processing top 10...`);

        for (let i = 0; i < Math.min(posts.length, 10); i++) {
            const post = posts[i];
            const title = await post.getAttribute('post-title');
            const score = await post.getAttribute('score');
            const commentCount = await post.getAttribute('comment-count');
            const permalink = await post.getAttribute('permalink');

            // Sometimes content is not in the list view, we might need to click? 
            // For now, let's just get the title as it's the main idea source.

            if (title) {
                const idea = {
                    source: 'reddit',
                    subreddit,
                    title,
                    content: '', // content extraction to be added if needed
                    score: parseInt(score || '0'),
                    comments: parseInt(commentCount || '0'),
                    url: `https://www.reddit.com${permalink}`,
                    scraped_at: new Date().toISOString()
                };

                try {
                    require('../utils/db').saveIdea(idea);
                } catch (dbErr) {
                    console.error('Failed to save to DB:', dbErr);
                }
                results.push(idea);
            }
        }

    } catch (e) {
        console.error('Error scraping Reddit:', e);
    } finally {
        await page.close();
        // Only close browser if we launched it? 
        // connectToBrowser returns a browser object. 
        // If it's connected over CDP, closing it might disconnect properly or close the chrome. 
        // playwright.connectOverCDP().close() disconnects.
        await browser.close();
    }

    return results;
}

if (require.main === module) {
    (async () => {
        require('../utils/db').initSchema();
        const data = await scrapeReddit();
        console.log(`Scraped and saved ${data.length} items from Reddit.`);
    })();
}

module.exports = { scrapeReddit };
