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

        CREATE TABLE IF NOT EXISTS llm_configs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            provider TEXT NOT NULL, -- openai, anthropic, etc.
            api_key TEXT,
            model TEXT,
            base_url TEXT,
            is_active INTEGER DEFAULT 0, -- 0 or 1
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
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
    if (status === 'all') {
        return db.prepare('SELECT * FROM ideas ORDER BY scraped_at DESC').all();
    }
    return db.prepare('SELECT * FROM ideas WHERE status = ? ORDER BY scraped_at DESC').all(status);
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

// LLM Config functions
function saveLLMConfig(config) {
    const stmt = db.prepare(`
        INSERT INTO llm_configs (name, provider, api_key, model, base_url, is_active)
        VALUES (@name, @provider, @api_key, @model, @base_url, @is_active)
    `);
    return stmt.run(config);
}

function getLLMConfigs() {
    return db.prepare('SELECT * FROM llm_configs ORDER BY created_at DESC').all();
}

function getActiveLLMConfig() {
    return db.prepare('SELECT * FROM llm_configs WHERE is_active = 1 LIMIT 1').get();
}

function updateLLMConfig(id, config) {
    const stmt = db.prepare(`
        UPDATE llm_configs 
        SET name = @name, provider = @provider, api_key = @api_key, 
            model = @model, base_url = @base_url, is_active = @is_active,
            updated_at = CURRENT_TIMESTAMP
        WHERE id = @id
    `);
    return stmt.run({ ...config, id });
}

function setActiveLLMConfig(id) {
    // First, deactivate all configs
    db.prepare('UPDATE llm_configs SET is_active = 0').run();
    // Then activate the specified one
    return db.prepare('UPDATE llm_configs SET is_active = 1 WHERE id = ?').run(id);
}

function deleteLLMConfig(id) {
    return db.prepare('DELETE FROM llm_configs WHERE id = ?').run(id);
}

module.exports = {
    db,
    initSchema,
    saveIdea,
    getIdeas,
    updateIdeaStatus,
    saveAsset,
    saveLLMConfig,
    getLLMConfigs,
    getActiveLLMConfig,
    updateLLMConfig,
    setActiveLLMConfig,
    deleteLLMConfig
};
