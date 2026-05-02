"use strict";
var __importDefault = (this && this.__importDefault) || function (mod) {
    return (mod && mod.__esModule) ? mod : { "default": mod };
};
Object.defineProperty(exports, "__esModule", { value: true });
const sqlite3_1 = __importDefault(require("sqlite3"));
const sqlite_1 = require("sqlite");
const uuid_1 = require("uuid");
class TableDataSource {
    constructor() {
        this.db = null;
    }
    async initialize() {
        if (!this.db) {
            this.db = await (0, sqlite_1.open)({
                filename: './data/data.db',
                driver: sqlite3_1.default.Database
            });
            await this.db.exec(`
        CREATE TABLE IF NOT EXISTS tables (
          id TEXT PRIMARY KEY,
          project_id TEXT NOT NULL,
          name TEXT NOT NULL,
          description TEXT,
          created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
          updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
          FOREIGN KEY (project_id) REFERENCES projects (id)
        )
      `);
        }
        return this.db;
    }
    async getByProjectId(projectId) {
        await this.initialize();
        const db = this.db;
        const rows = await db.all('SELECT * FROM tables WHERE project_id = ? ORDER BY created_at ASC', [projectId]);
        return rows.map(row => ({
            id: row.id,
            projectId: row.project_id,
            name: row.name,
            description: row.description,
            createdAt: new Date(row.created_at),
            updatedAt: new Date(row.updated_at)
        }));
    }
    async getById(id) {
        await this.initialize();
        const db = this.db;
        const row = await db.get('SELECT * FROM tables WHERE id = ?', [id]);
        if (!row)
            return null;
        return {
            id: row.id,
            projectId: row.project_id,
            name: row.name,
            description: row.description,
            createdAt: new Date(row.created_at),
            updatedAt: new Date(row.updated_at)
        };
    }
    async create(projectId, input) {
        await this.initialize();
        const db = this.db;
        const id = (0, uuid_1.v4)();
        const now = new Date().toISOString();
        await db.run('INSERT INTO tables (id, project_id, name, description, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?)', [id, projectId, input.name, input.description || null, now, now]);
        return {
            id,
            projectId,
            name: input.name,
            description: input.description,
            createdAt: new Date(now),
            updatedAt: new Date(now)
        };
    }
    async update(id, updates) {
        await this.initialize();
        const db = this.db;
        const existing = await this.getById(id);
        if (!existing)
            return null;
        const updateFields = [];
        const updateValues = [];
        if (updates.name !== undefined) {
            updateFields.push('name = ?');
            updateValues.push(updates.name);
            existing.name = updates.name;
        }
        if (updates.description !== undefined) {
            updateFields.push('description = ?');
            updateValues.push(updates.description);
            existing.description = updates.description;
        }
        if (updateFields.length > 0) {
            updateFields.push('updated_at = ?');
            updateValues.push(new Date().toISOString());
            updateValues.push(id);
            await db.run(`UPDATE tables SET ${updateFields.join(', ')} WHERE id = ?`, updateValues);
            existing.updatedAt = new Date();
        }
        return existing;
    }
    async delete(id) {
        await this.initialize();
        const db = this.db;
        const existing = await this.getById(id);
        if (!existing)
            return null;
        await db.run('DELETE FROM tables WHERE id = ?', [id]);
        return existing;
    }
}
exports.default = TableDataSource;
