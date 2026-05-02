const Database = require('better-sqlite3');
const path = require('path');

const dbPath = path.join(__dirname, 'data', 'scraper.db');
const db = new Database(dbPath);

// Create tables
db.exec(`
  CREATE TABLE IF NOT EXISTS llms (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    provider TEXT NOT NULL,
    api_key TEXT NOT NULL,
    model TEXT NOT NULL,
    base_url TEXT
  );

  CREATE TABLE IF NOT EXISTS generated_codes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    html_hash TEXT NOT NULL,
    llm_id INTEGER NOT NULL,
    code TEXT NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (llm_id) REFERENCES llms (id)
  );

  CREATE TABLE IF NOT EXISTS runs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    code_id INTEGER NOT NULL,
    url TEXT NOT NULL,
    csv_path TEXT NOT NULL,
    status TEXT NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (code_id) REFERENCES generated_codes (id)
  );
`);

console.log('Database initialized successfully');

module.exports = db;