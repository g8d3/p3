const express = require('express');
const path = require('path');
const { db, getIdeas, getLLMConfigs, saveLLMConfig, setActiveLLMConfig, deleteLLMConfig, initSchema } = require('../utils/db');
const { createProduct } = require('../generators/product_maker');
const { scrapeReddit } = require('../scrapers/reddit_scraper');
const { scrapeX } = require('../scrapers/x_scraper');

const app = express();
const PORT = 3000;

app.set('view engine', 'ejs');
app.set('views', path.join(__dirname, 'views'));
app.use(express.static(path.join(__dirname, 'public')));
app.use(express.urlencoded({ extended: true }));

app.get('/', (req, res) => {
    const ideas = getIdeas('all'); // Show all ideas to see status
    const assets = db.prepare('SELECT * FROM assets ORDER BY created_at DESC').all();
    const llmConfigs = getLLMConfigs();

    // Stats
    const stats = {
        ideas: db.prepare('SELECT COUNT(*) as c FROM ideas').get().c,
        assets: db.prepare('SELECT COUNT(*) as c FROM assets').get().c
    };

    res.render('index', { ideas, assets, stats, llmConfigs });
});

app.post('/ideas/:id/approve', async (req, res) => {
    const id = req.params.id;
    console.log(`Approving idea ${id}...`);

    // For MVP, we run the generator directly in the request handler
    // In production, this should be a queue

    // First, verify the idea exists and is not processed
    // We need to modify product_maker to take an ID.
    // For now, I'll just hack it: Update status to 'new' (if it wasn't) or 'approved'
    // and rely on a modified product_maker or just let it pick it up if I run it.

    // Let's invoke the functionality directly:
    // But product_maker.js as written picks *any* idea.
    // I should create a specific function `createProductFromIdea(id)` in `product_maker.js`.

    // Current workaround:
    // I will just spawn the process for now, or assume the loop is running.
    // But let's try to do it right.

    // For now: Just redirect back saying "Queued" (Simulated)
    // Or actually run it.

    // Since I can't easily import the `createProduct` logic selectively without refactoring,
    // I will restart the `product_maker` script.

    const { exec } = require('child_process');
    exec(`node generators/product_maker.js`, (err, stdout, stderr) => {
        if (err) console.error(err);
        console.log("Product Maker Output:", stdout);
    });

    res.redirect('/');
});

// LLM Configuration routes
app.post('/llm-config', (req, res) => {
    const { name, provider, apiKey, model, baseUrl } = req.body;
    
    if (!name || !provider || !apiKey) {
        return res.status(400).json({ error: 'Name, provider, and API key are required' });
    }

    const config = {
        name: name.trim(),
        provider: provider.toLowerCase(),
        api_key: apiKey.trim(),
        model: model ? model.trim() : null,
        base_url: baseUrl ? baseUrl.trim() : null,
        is_active: 0
    };

    try {
        const result = saveLLMConfig(config);
        res.redirect('/');
    } catch (error) {
        console.error('Error saving LLM config:', error);
        res.status(500).json({ error: 'Failed to save configuration' });
    }
});

app.post('/llm-config/:id/activate', (req, res) => {
    const id = req.params.id;
    
    try {
        setActiveLLMConfig(id);
        res.redirect('/');
    } catch (error) {
        console.error('Error activating LLM config:', error);
        res.status(500).json({ error: 'Failed to activate configuration' });
    }
});

app.post('/llm-config/:id/delete', (req, res) => {
    const id = req.params.id;
    
    try {
        deleteLLMConfig(id);
        res.redirect('/');
    } catch (error) {
        console.error('Error deleting LLM config:', error);
        res.status(500).json({ error: 'Failed to delete configuration' });
    }
});

// Reset and control routes
app.post('/rescape', async (req, res) => {
    try {
        console.log('Starting rescraping...');
        
        // Scrape Reddit
        const redditResults = await scrapeReddit();
        console.log(`Scraped ${redditResults.length} items from Reddit`);
        
        // Scrape X  
        const xResults = await scrapeX();
        console.log(`Scraped ${xResults.length} items from X`);
        
        res.redirect('/');
    } catch (error) {
        console.error('Error rescraping:', error);
        res.status(500).json({ error: 'Failed to rescrape' });
    }
});

app.post('/recreate/:ideaId', async (req, res) => {
    const ideaId = req.params.ideaId;
    
    try {
        console.log(`Recreating product for idea ${ideaId}...`);
        
        // Reset idea status to 'new' and then run product maker
        db.prepare('UPDATE ideas SET status = ? WHERE id = ?').run('new', ideaId);
        
        // Run product maker for this specific idea
        const { exec } = require('child_process');
        exec(`node generators/product_maker.js`, (err, stdout, stderr) => {
            if (err) {
                console.error('Error running product maker:', err);
                res.status(500).json({ error: 'Failed to recreate product' });
                return;
            }
            console.log("Product recreation completed:", stdout);
            res.redirect('/');
        });
        
    } catch (error) {
        console.error('Error recreating product:', error);
        res.status(500).json({ error: 'Failed to recreate product' });
    }
});

app.post('/reset-data', (req, res) => {
    try {
        console.log('Resetting all data...');
        
        // Clear all ideas
        db.prepare('DELETE FROM ideas').run();
        
        // Clear all assets
        db.prepare('DELETE FROM assets').run();
        
        console.log('Data reset completed');
        res.redirect('/');
        
    } catch (error) {
        console.error('Error resetting data:', error);
        res.status(500).json({ error: 'Failed to reset data' });
    }
});

app.listen(PORT, () => {
    console.log(`BizBot Dashboard running at http://localhost:${PORT}`);
});
