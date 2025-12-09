const { db, saveIdea } = require('../utils/db');
const { generateContent } = require('../generators/llm');
const { postTweet } = require('./poster');

function getDraftAssets() {
    return db.prepare("SELECT * FROM assets WHERE status = 'draft'").all();
}

async function runMarketing() {
    console.log("Running Marketing Loop...");
    const assets = getDraftAssets();

    if (assets.length === 0) {
        console.log("No draft assets found to market.");
        return;
    }

    // Pick one at random or first
    const asset = assets[0];
    console.log(`Selected asset for marketing: ${asset.name}`);

    try {
        // Generate Tweet
        const tweetContent = await generateContent(`
            Write a promotional tweet for a new product:
            Name: ${asset.name}
            Description: ${asset.description}
            
            Make it catchy, use 2 hashtags.
            Max 280 chars.
        `);

        // Post it
        await postTweet(tweetContent);

        console.log(`Successfully marketed: ${asset.name}`);

        // Update asset status to 'live' (simulated)
        db.prepare("UPDATE assets SET status = 'live' WHERE id = ?").run(asset.id);

    } catch (e) {
        console.error("Marketing loop failed:", e);
    }
}

if (require.main === module) {
    runMarketing();
}
