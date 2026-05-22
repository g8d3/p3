/**
 * Episodic memory - stores agent sessions and task history.
 * 
 * Uses SQLite for persistence:
 *   - sessions: agent conversation history
 *   - tasks: task execution records
 *   - events: key events during execution
 * 
 * Efficient storage: only stores compressed summaries of old sessions,
 * full context of recent sessions.
 */

import Database from 'better-sqlite3';
import { join } from 'node:path';
import { mkdirSync, existsSync } from 'node:fs';

export interface SessionRecord {
  id: string;
  agentId: string;
  startedAt: number;
  endedAt?: number;
  taskCount: number;
  tokenCount: number;
  status: 'active' | 'completed' | 'abandoned';
  summary?: string;
}

export interface EventRecord {
  id: string;
  sessionId: string;
  timestamp: number;
  type: 'task_start' | 'task_end' | 'context_compression' | 'error' | 'milestone';
  data: string;
}

export class EpisodicMemory {
  private db: Database.Database;

  constructor(dataDir: string = './data') {
    if (!existsSync(dataDir)) {
      mkdirSync(dataDir, { recursive: true });
    }
    
    const dbPath = join(dataDir, 'episodic.db');
    this.db = new Database(dbPath);
    this.db.pragma('journal_mode = WAL');
    this.db.pragma('synchronous = NORMAL');
    this.initSchema();
  }

  private initSchema(): void {
    this.db.exec(`
      CREATE TABLE IF NOT EXISTS sessions (
        id TEXT PRIMARY KEY,
        agent_id TEXT NOT NULL,
        started_at INTEGER NOT NULL,
        ended_at INTEGER,
        task_count INTEGER DEFAULT 0,
        token_count INTEGER DEFAULT 0,
        status TEXT DEFAULT 'active',
        summary TEXT
      );
      
      CREATE TABLE IF NOT EXISTS events (
        id TEXT PRIMARY KEY,
        session_id TEXT NOT NULL,
        timestamp INTEGER NOT NULL,
        type TEXT NOT NULL,
        data TEXT DEFAULT '{}',
        FOREIGN KEY (session_id) REFERENCES sessions(id)
      );
      
      CREATE INDEX IF NOT EXISTS idx_events_session ON events(session_id);
      CREATE INDEX IF NOT EXISTS idx_events_type ON events(type);
      CREATE INDEX IF NOT EXISTS idx_sessions_agent ON sessions(agent_id);
      CREATE INDEX IF NOT EXISTS idx_sessions_status ON sessions(status);
    `);
  }

  createSession(agentId: string): string {
    const id = `session-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;
    const stmt = this.db.prepare(
      'INSERT INTO sessions (id, agent_id, started_at, status) VALUES (?, ?, ?, ?)'
    );
    stmt.run(id, agentId, Date.now(), 'active');
    return id;
  }

  endSession(sessionId: string, summary?: string): void {
    const stmt = this.db.prepare(
      'UPDATE sessions SET ended_at = ?, status = ?, summary = ? WHERE id = ?'
    );
    stmt.run(Date.now(), 'completed', summary ?? null, sessionId);
  }

  recordEvent(sessionId: string, type: EventRecord['type'], data: Record<string, unknown>): void {
    const id = `evt-${Date.now()}-${Math.random().toString(36).slice(2, 6)}`;
    const stmt = this.db.prepare(
      'INSERT INTO events (id, session_id, timestamp, type, data) VALUES (?, ?, ?, ?, ?)'
    );
    stmt.run(id, sessionId, Date.now(), type, JSON.stringify(data));
  }

  updateTokenCount(sessionId: string, tokens: number): void {
    const stmt = this.db.prepare(
      'UPDATE sessions SET token_count = token_count + ?, task_count = task_count + 1 WHERE id = ?'
    );
    stmt.run(tokens, sessionId);
  }

  getRecentSessions(agentId: string, limit = 10): SessionRecord[] {
    const stmt = this.db.prepare(
      'SELECT * FROM sessions WHERE agent_id = ? ORDER BY started_at DESC LIMIT ?'
    );
    return stmt.all(agentId, limit) as SessionRecord[];
  }

  getAgentStats(agentId: string): { totalSessions: number; totalTasks: number; totalTokens: number } {
    const stmt = this.db.prepare(
      'SELECT COUNT(*) as totalSessions, SUM(task_count) as totalTasks, SUM(token_count) as totalTokens FROM sessions WHERE agent_id = ?'
    );
    return stmt.get(agentId) as any;
  }

  close(): void {
    this.db.close();
  }
}
