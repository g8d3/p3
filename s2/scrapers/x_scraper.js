const { connectToBrowser } = require('./common');
const { saveIdea, initSchema } = require('../utils/db');

async function scrapeX(query = 'I need a tool for') {
    const url = `https://x.com/search?q=${encodeURIComponent(query)}&src=typed_query&f=live`;
    console.log(`Scraping X: ${url}...`);

    const { browser, context } = await connectToBrowser();
    const page = await context.newPage();

    const results = [];

    try {
        await page.goto(url, { waitUntil: 'domcontentloaded' });

        // Wait for timeline to load
        // X uses obscure class names, let's try to wait for 'article' which is usually a tweet
        try {
            await page.waitForSelector('article', { timeout: 10000 });
        } catch (e) {
            console.log("Timeout waiting for articles on X, maybe login needed or layout changed?");
            // If text 'Log in' is visible, we failed auth
            const loginText = await page.getByText('Log in to Twitter').count();
            if (loginText > 0) {
                console.error("X requires login. Ensure browser is logged in.");
                return [];
            }
        }

        const tweets = await page.$$('article');
        console.log(`Found ${tweets.length} tweets.`);

        for (let i = 0; i < Math.min(tweets.length, 10); i++) {
            const tweet = tweets[i];

            const textEl = await tweet.$('[data-testid="tweetText"]');
            const text = textEl ? await textEl.innerText() : '';

            // Get link (date element usually wraps the permalink)
            const timeEl = await tweet.$('time');
            const relativeLink = timeEl ? await timeEl.evaluate(el => el.closest('a').getAttribute('href')) : null;
            const link = relativeLink ? `https://x.com${relativeLink}` : '';

            // Get Metrics (this is hard due to dynamic classes, skipping for MVP unless easy)

            if (text) {
                const idea = {
                    source: 'x',
                    external_id: link || `x-${Date.now()}-${i}`,
                    title: text.substring(0, 100) + '...', // Use start of tweet as title
                    content: text,
                    score: 0,
                    comments: 0,
                    url: link,
                    scraped_at: new Date().toISOString()
                };

                try {
                    saveIdea(idea);
                    results.push(idea);
                } catch (dbErr) {
                    console.error('Failed to save to DB:', dbErr);
                }
            }
        }

    } catch (e) {
        console.error('Error scraping X:', e);
    } finally {
        await page.close();
        await browser.close();
    }

    return results;
}

if (require.main === module) {
    (async () => {
        initSchema();
        const data = await scrapeX();
        console.log(`Scraped and saved ${data.length} items from X.`);
    })();
}

module.exports = { scrapeX };
