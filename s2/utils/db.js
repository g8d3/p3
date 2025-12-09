const Database = require('better-sqlite3');
const path = require('path');

const dbPath = path.join(__dirname, '../data.db');
const db = new Database(dbPath, { verbose: null }); // Set verbose: console.log to see queries

// Initialize Schema
function initSchema() {
    db.exec(`
        CREATE TABLE IF NOT EXISTS ideas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            source TEXT NOT NULL,
            external_id TEXT UNIQUE, -- URL or ID to prevent duplicates
            title TEXT,
            content TEXT,
            score INTEGER,
            comments INTEGER,
            scraped_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            status TEXT DEFAULT 'new' -- new, approved, rejected, implemented
        );

        CREATE TABLE IF NOT EXISTS assets (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            type TEXT NOT NULL, -- product, micro-saas
            description TEXT,
            status TEXT DEFAULT 'draft', -- draft, live, sold
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        );
    `);
    console.log('Database initialized at', dbPath);
}

// Helper to save ideas
function saveIdea(idea) {
    const stmt = db.prepare(`
        INSERT INTO ideas (source, external_id, title, content, score, comments, scraped_at)
        VALUES (@source, @url, @title, @content, @score, @comments, @scraped_at)
        ON CONFLICT(external_id) DO UPDATE SET
            score = excluded.score,
            comments = excluded.comments,
            title = excluded.title
    `);
    return stmt.run(idea);
}

function getIdeas(status = 'new') {
    return db.prepare('SELECT * FROM ideas WHERE status = ? ORDER BY score DESC').all(status);
}

function updateIdeaStatus(id, status) {
    db.prepare('UPDATE ideas SET status = ? WHERE id = ?').run(status, id);
}

function saveAsset(asset) {
    const stmt = db.prepare(`
        INSERT INTO assets (name, type, description, status)
        VALUES (@name, @type, @description, @status)
    `);
    return stmt.run(asset);
}

module.exports = {
    db,
    initSchema,
    saveIdea,
    getIdeas,
    updateIdeaStatus,
    saveAsset
};
