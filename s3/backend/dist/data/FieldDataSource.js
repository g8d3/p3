"use strict";
var __importDefault = (this && this.__importDefault) || function (mod) {
    return (mod && mod.__esModule) ? mod : { "default": mod };
};
Object.defineProperty(exports, "__esModule", { value: true });
const sqlite3_1 = __importDefault(require("sqlite3"));
const sqlite_1 = require("sqlite");
class FieldDataSource {
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
        CREATE TABLE IF NOT EXISTS fields (
          id TEXT PRIMARY KEY,
          table_id TEXT NOT NULL,
          name TEXT NOT NULL,
          type TEXT NOT NULL,
          required BOOLEAN DEFAULT 0,
          description TEXT,
          default_value TEXT,
          created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
          updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
          FOREIGN KEY (table_id) REFERENCES tables (id)
        )
      `);
        }
        return this.db;
    }
    async getByTableId(tableId) {
        await this.initialize();
        const db = this.db;
        const rows = await db.all('SELECT * FROM fields WHERE table_id = ? ORDER BY created_at ASC', [tableId]);
        return rows.map(row => ({
            id: row.id,
            tableId: row.table_id,
            name: row.name,
            type: row.type,
            required: Boolean(row.required),
            description: row.description,
            defaultValue: row.default_value,
            createdAt: new Date(row.created_at),
            updatedAt: new Date(row.updated_at)
        }));
    }
}
exports.default = FieldDataSource;
