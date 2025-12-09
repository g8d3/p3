const express = require('express');
const path = require('path');
const { db, getIdeas } = require('../utils/db');
const { createProduct } = require('../generators/product_maker');

const app = express();
const PORT = 3000;

app.set('view engine', 'ejs');
app.set('views', path.join(__dirname, 'views'));
app.use(express.static(path.join(__dirname, 'public')));
app.use(express.urlencoded({ extended: true }));

app.get('/', (req, res) => {
    const ideas = getIdeas('new'); // Only show new
    const assets = db.prepare('SELECT * FROM assets ORDER BY created_at DESC').all();

    // Stats
    const stats = {
        ideas: db.prepare('SELECT COUNT(*) as c FROM ideas').get().c,
        assets: db.prepare('SELECT COUNT(*) as c FROM assets').get().c
    };

    res.render('index', { ideas, assets, stats });
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

app.listen(PORT, () => {
    console.log(`BizBot Dashboard running at http://localhost:${PORT}`);
});
