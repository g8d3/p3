/**
 * StateManager - SQLite persistence layer for the autonomous agent
 * Handles database initialization, migrations, and CRUD operations
 * Supports multi-tenancy with user-scoped data
 */

import Database from 'better-sqlite3';
import { fileURLToPath } from 'url';
import { dirname, join } from 'path';
import { mkdirSync, existsSync } from 'fs';
import { config } from '../../config/defaults.js';
import { randomUUID } from 'crypto';

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);

class StateManager {
  constructor() {
    this.db = null;
    this.dbPath = config.paths.state;
    this.initialized = false;
  }

  /**
   * Initialize database connection and run schema migrations
   */
  init() {
    if (this.initialized && this.db) {
      return this;
    }

    // Ensure data directory exists
    const dbDir = dirname(this.dbPath);
    if (!existsSync(dbDir)) {
      mkdirSync(dbDir, { recursive: true });
    }

    // Create database connection
    this.db = new Database(this.dbPath);
    
    // Enable WAL mode for better concurrent performance
    this.db.pragma('journal_mode = WAL');
    
    // Run migrations
    this._runMigrations();
    
    // Ensure default user exists for backwards compatibility
    this._ensureDefaultUser();
    
    this.initialized = true;
    return this;
  }

  /**
   * Run all schema migrations
   */
  _runMigrations() {
    // Create migrations tracking table
    this.db.exec(`
      CREATE TABLE IF NOT EXISTS _migrations (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL UNIQUE,
        applied_at DATETIME DEFAULT CURRENT_TIMESTAMP
      )
    `);

    const appliedMigrations = this.db
      .prepare('SELECT name FROM _migrations')
      .all()
      .map(m => m.name);

    const migrations = this._getMigrations();

    for (const migration of migrations) {
      if (!appliedMigrations.includes(migration.name)) {
        this.db.exec(migration.sql);
        this.db.prepare('INSERT INTO _migrations (name) VALUES (?)').run(migration.name);
      }
    }
  }

  /**
   * Ensure default user exists for backwards compatibility
   */
  _ensureDefaultUser() {
    const existingUser = this.db
      .prepare('SELECT id FROM users WHERE id = ?')
      .get('default');
    
    if (!existingUser) {
      this.db.prepare(`
        INSERT INTO users (id, email, display_name, timezone, plan_tier)
        VALUES (?, ?, ?, ?, ?)
      `).run('default', 'default@system.local', 'Default User', 'UTC', 'free');
    }
  }

  /**
   * Get all migration definitions
   */
  _getMigrations() {
    return [
      {
        name: '001_create_agent_state',
        sql: `
          CREATE TABLE IF NOT EXISTS agent_state (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            key TEXT NOT NULL UNIQUE,
            value TEXT,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
          );
          CREATE INDEX IF NOT EXISTS idx_agent_state_key ON agent_state(key);
        `
      },
      {
        name: '002_create_content_items',
        sql: `
          CREATE TABLE IF NOT EXISTS content_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            type TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'draft',
            content TEXT NOT NULL,
            platform TEXT,
            posted_at DATETIME,
            external_id TEXT,
            engagement_metrics TEXT,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
          );
          CREATE INDEX IF NOT EXISTS idx_content_items_status ON content_items(status);
          CREATE INDEX IF NOT EXISTS idx_content_items_type ON content_items(type);
          CREATE INDEX IF NOT EXISTS idx_content_items_platform ON content_items(platform);
          CREATE INDEX IF NOT EXISTS idx_content_items_posted_at ON content_items(posted_at);
        `
      },
      {
        name: '003_create_scheduled_tasks',
        sql: `
          CREATE TABLE IF NOT EXISTS scheduled_tasks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            module TEXT NOT NULL,
            action TEXT NOT NULL,
            cron_expr TEXT NOT NULL,
            last_run DATETIME,
            next_run DATETIME,
            enabled INTEGER DEFAULT 1,
            config TEXT,
            UNIQUE(module, action)
          );
          CREATE INDEX IF NOT EXISTS idx_scheduled_tasks_next_run ON scheduled_tasks(next_run);
          CREATE INDEX IF NOT EXISTS idx_scheduled_tasks_enabled ON scheduled_tasks(enabled);
        `
      },
      {
        name: '004_create_rate_limits',
        sql: `
          CREATE TABLE IF NOT EXISTS rate_limits (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            action_type TEXT NOT NULL,
            window_start DATETIME NOT NULL,
            count INTEGER DEFAULT 0,
            max_count INTEGER NOT NULL,
            window_minutes INTEGER NOT NULL
          );
          CREATE INDEX IF NOT EXISTS idx_rate_limits_action_type ON rate_limits(action_type);
          CREATE INDEX IF NOT EXISTS idx_rate_limits_window_start ON rate_limits(window_start);
        `
      },
      {
        name: '005_create_approval_queue',
        sql: `
          CREATE TABLE IF NOT EXISTS approval_queue (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            action_type TEXT NOT NULL,
            action_data TEXT NOT NULL,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            status TEXT NOT NULL DEFAULT 'pending',
            reviewed_at DATETIME,
            reviewer_note TEXT
          );
          CREATE INDEX IF NOT EXISTS idx_approval_queue_status ON approval_queue(status);
          CREATE INDEX IF NOT EXISTS idx_approval_queue_created_at ON approval_queue(created_at);
        `
      },
      {
        name: '006_create_experiments',
        sql: `
          CREATE TABLE IF NOT EXISTS experiments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE,
            hypothesis TEXT,
            start_date DATETIME NOT NULL,
            end_date DATETIME,
            variants TEXT,
            results TEXT
          );
          CREATE INDEX IF NOT EXISTS idx_experiments_name ON experiments(name);
          CREATE INDEX IF NOT EXISTS idx_experiments_dates ON experiments(start_date, end_date);
        `
      },
      {
        name: '007_create_learnings',
        sql: `
          CREATE TABLE IF NOT EXISTS learnings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            category TEXT NOT NULL,
            insight TEXT NOT NULL,
            evidence TEXT,
            confidence REAL DEFAULT 0.5,
            applicable_to TEXT,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
          );
          CREATE INDEX IF NOT EXISTS idx_learnings_category ON learnings(category);
          CREATE INDEX IF NOT EXISTS idx_learnings_created_at ON learnings(created_at);
        `
      },
      {
        name: '008_create_action_log',
        sql: `
          CREATE TABLE IF NOT EXISTS action_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            module TEXT NOT NULL,
            action TEXT NOT NULL,
            params TEXT,
            result TEXT,
            error TEXT,
            duration_ms INTEGER
          );
          CREATE INDEX IF NOT EXISTS idx_action_log_timestamp ON action_log(timestamp);
          CREATE INDEX IF NOT EXISTS idx_action_log_module ON action_log(module);
          CREATE INDEX IF NOT EXISTS idx_action_log_action ON action_log(action);
        `
      },
      {
        name: '009_create_users',
        sql: `
          CREATE TABLE IF NOT EXISTS users (
            id TEXT PRIMARY KEY,
            email TEXT UNIQUE NOT NULL,
            password_hash TEXT,
            display_name TEXT,
            timezone TEXT DEFAULT 'UTC',
            plan_tier TEXT DEFAULT 'free',
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
          );
          CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);
          CREATE INDEX IF NOT EXISTS idx_users_plan_tier ON users(plan_tier);
        `
      },
      {
        name: '010_create_sessions',
        sql: `
          CREATE TABLE IF NOT EXISTS sessions (
            id TEXT PRIMARY KEY,
            user_id TEXT NOT NULL,
            refresh_token_hash TEXT UNIQUE NOT NULL,
            expires_at DATETIME NOT NULL,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
          );
          CREATE INDEX IF NOT EXISTS idx_sessions_user_id ON sessions(user_id);
          CREATE INDEX IF NOT EXISTS idx_sessions_expires_at ON sessions(expires_at);
        `
      },
      {
        name: '011_create_ai_commands',
        sql: `
          CREATE TABLE IF NOT EXISTS ai_commands (
            id TEXT PRIMARY KEY,
            user_id TEXT NOT NULL,
            input TEXT NOT NULL,
            parsed_intent TEXT,
            executed_actions TEXT,
            user_feedback TEXT,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
          );
          CREATE INDEX IF NOT EXISTS idx_ai_commands_user_id ON ai_commands(user_id);
          CREATE INDEX IF NOT EXISTS idx_ai_commands_created_at ON ai_commands(created_at);
        `
      },
      {
        name: '012_create_content_bookmarks',
        sql: `
          CREATE TABLE IF NOT EXISTS content_bookmarks (
            id TEXT PRIMARY KEY,
            user_id TEXT NOT NULL,
            x_tweet_id TEXT,
            text TEXT,
            author TEXT,
            author_handle TEXT,
            url TEXT,
            pulled_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            used_as_source INTEGER DEFAULT 0,
            tags TEXT,
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
          );
          CREATE INDEX IF NOT EXISTS idx_content_bookmarks_user_id ON content_bookmarks(user_id);
          CREATE INDEX IF NOT EXISTS idx_content_bookmarks_x_tweet_id ON content_bookmarks(x_tweet_id);
          CREATE INDEX IF NOT EXISTS idx_content_bookmarks_used_as_source ON content_bookmarks(used_as_source);
        `
      },
      {
        name: '013_add_user_id_to_existing_tables',
        sql: `
          -- Add user_id to content_items
          ALTER TABLE content_items ADD COLUMN user_id TEXT REFERENCES users(id);
          CREATE INDEX IF NOT EXISTS idx_content_items_user_id ON content_items(user_id);

          -- Add user_id to rate_limits
          ALTER TABLE rate_limits ADD COLUMN user_id TEXT REFERENCES users(id);
          CREATE INDEX IF NOT EXISTS idx_rate_limits_user_id ON rate_limits(user_id);

          -- Add user_id to approval_queue
          ALTER TABLE approval_queue ADD COLUMN user_id TEXT REFERENCES users(id);
          CREATE INDEX IF NOT EXISTS idx_approval_queue_user_id ON approval_queue(user_id);

          -- Add user_id to experiments
          ALTER TABLE experiments ADD COLUMN user_id TEXT REFERENCES users(id);
          CREATE INDEX IF NOT EXISTS idx_experiments_user_id ON experiments(user_id);

          -- Add user_id to learnings
          ALTER TABLE learnings ADD COLUMN user_id TEXT REFERENCES users(id);
          CREATE INDEX IF NOT EXISTS idx_learnings_user_id ON learnings(user_id);

          -- Add user_id to action_log
          ALTER TABLE action_log ADD COLUMN user_id TEXT REFERENCES users(id);
          CREATE INDEX IF NOT EXISTS idx_action_log_user_id ON action_log(user_id);

          -- Add user_id to agent_state and create new composite unique index
          ALTER TABLE agent_state ADD COLUMN user_id TEXT REFERENCES users(id);
          CREATE INDEX IF NOT EXISTS idx_agent_state_user_id ON agent_state(user_id);
        `
      },
      {
        name: '014_replace_scheduled_tasks_schema',
        sql: `
          -- Rename old table
          ALTER TABLE scheduled_tasks RENAME TO scheduled_tasks_old;

          -- Create new scheduled_tasks table with user-scoped schema
          CREATE TABLE scheduled_tasks (
            id TEXT PRIMARY KEY,
            user_id TEXT NOT NULL,
            task_type TEXT NOT NULL,
            schedule_type TEXT NOT NULL,
            schedule_config TEXT NOT NULL,
            schedule_description TEXT,
            is_active INTEGER DEFAULT 1,
            next_run_at DATETIME,
            last_run_at DATETIME,
            payload TEXT,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
          );
          CREATE INDEX IF NOT EXISTS idx_scheduled_tasks_user_id ON scheduled_tasks(user_id);
          CREATE INDEX IF NOT EXISTS idx_scheduled_tasks_task_type ON scheduled_tasks(task_type);
          CREATE INDEX IF NOT EXISTS idx_scheduled_tasks_next_run_at ON scheduled_tasks(next_run_at);
          CREATE INDEX IF NOT EXISTS idx_scheduled_tasks_is_active ON scheduled_tasks(is_active);

          -- Drop old table (data migration would need to be handled separately if needed)
          DROP TABLE scheduled_tasks_old;
        `
      }
    ];
  }

  // ===========================================
  // Core Methods
  // ===========================================

  /**
   * Get a value from agent_state (user-scoped)
   * @param {string} key - The key to retrieve
   * @param {string} userId - User ID (defaults to 'default')
   * @returns {*} The parsed value or null if not found
   */
  get(key, userId = 'default') {
    this._ensureInitialized();
    const row = this.db.prepare('SELECT value FROM agent_state WHERE key = ? AND user_id = ?').get(key, userId);
    if (!row) return null;
    try {
      return JSON.parse(row.value);
    } catch {
      return row.value;
    }
  }

  /**
   * Set a value in agent_state (user-scoped)
   * @param {string} key - The key to set
   * @param {*} value - The value to store (will be JSON stringified)
   * @param {string} userId - User ID (defaults to 'default')
   */
  set(key, value, userId = 'default') {
    this._ensureInitialized();
    const jsonValue = typeof value === 'string' ? value : JSON.stringify(value);
    this.db.prepare(`
      INSERT INTO agent_state (key, value, user_id, updated_at) 
      VALUES (?, ?, ?, CURRENT_TIMESTAMP)
      ON CONFLICT(key) DO UPDATE SET 
        value = excluded.value,
        user_id = excluded.user_id,
        updated_at = CURRENT_TIMESTAMP
    `).run(key, jsonValue, userId);
    return this;
  }

  /**
   * Delete a key from agent_state (user-scoped)
   * @param {string} key - The key to delete
   * @param {string} userId - User ID (defaults to 'default')
   */
  delete(key, userId = 'default') {
    this._ensureInitialized();
    this.db.prepare('DELETE FROM agent_state WHERE key = ? AND user_id = ?').run(key, userId);
    return this;
  }

  /**
   * Execute a raw SQL query
   * @param {string} sql - SQL query
   * @param {Array} params - Query parameters
   * @returns {Array|Object} Query results
   */
  query(sql, params = []) {
    this._ensureInitialized();
    
    // Determine if this is a SELECT query
    const isSelect = sql.trim().toUpperCase().startsWith('SELECT');
    
    if (isSelect) {
      return this.db.prepare(sql).all(...params);
    } else {
      return this.db.prepare(sql).run(...params);
    }
  }

  /**
   * Execute a SQL statement and return the first row
   * @param {string} sql - SQL query
   * @param {Array} params - Query parameters
   * @returns {Object|undefined} First row or undefined
   */
  queryOne(sql, params = []) {
    this._ensureInitialized();
    return this.db.prepare(sql).get(...params);
  }

  /**
   * Execute multiple statements in a transaction
   * @param {Function} fn - Function containing database operations
   * @returns {*} The return value of fn
   */
  transaction(fn) {
    this._ensureInitialized();
    return this.db.transaction(fn)();
  }

  /**
   * Close the database connection
   */
  close() {
    if (this.db) {
      this.db.close();
      this.db = null;
      this.initialized = false;
    }
  }

  // ===========================================
  // User Management Methods
  // ===========================================

  /**
   * Create a new user
   * @param {Object} data - User data
   * @returns {Object} The created user
   */
  createUser(data) {
    this._ensureInitialized();
    const id = data.id || randomUUID();
    const { email, passwordHash, displayName, timezone = 'UTC', planTier = 'free' } = data;
    
    this.db.prepare(`
      INSERT INTO users (id, email, password_hash, display_name, timezone, plan_tier)
      VALUES (?, ?, ?, ?, ?, ?)
    `).run(id, email, passwordHash, displayName, timezone, planTier);
    
    return this.getUserById(id);
  }

  /**
   * Get user by email
   * @param {string} email - User email
   * @returns {Object|undefined} User object or undefined
   */
  getUserByEmail(email) {
    this._ensureInitialized();
    return this.db.prepare('SELECT * FROM users WHERE email = ?').get(email);
  }

  /**
   * Get user by ID
   * @param {string} id - User ID
   * @returns {Object|undefined} User object or undefined
   */
  getUserById(id) {
    this._ensureInitialized();
    return this.db.prepare('SELECT * FROM users WHERE id = ?').get(id);
  }

  /**
   * Update user
   * @param {string} id - User ID
   * @param {Object} data - Fields to update
   * @returns {Object|undefined} Updated user or undefined
   */
  updateUser(id, data) {
    this._ensureInitialized();
    const allowedFields = ['email', 'password_hash', 'display_name', 'timezone', 'plan_tier'];
    const updates = [];
    const values = [];
    
    for (const [key, value] of Object.entries(data)) {
      const dbKey = key.replace(/([A-Z])/g, '_$1').toLowerCase(); // camelCase to snake_case
      if (allowedFields.includes(dbKey)) {
        updates.push(`${dbKey} = ?`);
        values.push(value);
      }
    }
    
    if (updates.length === 0) return this.getUserById(id);
    
    values.push(id);
    this.db.prepare(`UPDATE users SET ${updates.join(', ')}, updated_at = CURRENT_TIMESTAMP WHERE id = ?`).run(...values);
    
    return this.getUserById(id);
  }

  /**
   * Delete user and all associated data
   * @param {string} id - User ID
   * @returns {boolean} True if deleted
   */
  deleteUser(id) {
    this._ensureInitialized();
    const result = this.db.prepare('DELETE FROM users WHERE id = ?').run(id);
    return result.changes > 0;
  }

  // ===========================================
  // Session Management Methods
  // ===========================================

  /**
   * Create a new session
   * @param {string} userId - User ID
   * @param {string} refreshTokenHash - Hashed refresh token
   * @param {string|Date} expiresAt - Expiration timestamp
   * @returns {Object} The created session
   */
  createSession(userId, refreshTokenHash, expiresAt) {
    this._ensureInitialized();
    const id = randomUUID();
    const expiresAtStr = typeof expiresAt === 'string' ? expiresAt : expiresAt.toISOString();
    
    this.db.prepare(`
      INSERT INTO sessions (id, user_id, refresh_token_hash, expires_at)
      VALUES (?, ?, ?, ?)
    `).run(id, userId, refreshTokenHash, expiresAtStr);
    
    return this.db.prepare('SELECT * FROM sessions WHERE id = ?').get(id);
  }

  /**
   * Get session by refresh token hash
   * @param {string} tokenHash - Hashed refresh token
   * @returns {Object|undefined} Session object or undefined
   */
  getSessionByToken(tokenHash) {
    this._ensureInitialized();
    return this.db.prepare(`
      SELECT s.*, u.email, u.display_name, u.timezone, u.plan_tier
      FROM sessions s
      JOIN users u ON s.user_id = u.id
      WHERE s.refresh_token_hash = ? AND s.expires_at > CURRENT_TIMESTAMP
    `).get(tokenHash);
  }

  /**
   * Delete session by token hash
   * @param {string} tokenHash - Hashed refresh token
   * @returns {boolean} True if deleted
   */
  deleteSession(tokenHash) {
    this._ensureInitialized();
    const result = this.db.prepare('DELETE FROM sessions WHERE refresh_token_hash = ?').run(tokenHash);
    return result.changes > 0;
  }

  /**
   * Delete all sessions for a user
   * @param {string} userId - User ID
   * @returns {number} Number of sessions deleted
   */
  deleteUserSessions(userId) {
    this._ensureInitialized();
    const result = this.db.prepare('DELETE FROM sessions WHERE user_id = ?').run(userId);
    return result.changes;
  }

  /**
   * Clean up expired sessions
   * @returns {number} Number of sessions cleaned
   */
  cleanupExpiredSessions() {
    this._ensureInitialized();
    const result = this.db.prepare('DELETE FROM sessions WHERE expires_at <= CURRENT_TIMESTAMP').run();
    return result.changes;
  }

  // ===========================================
  // Content Items Helpers (User-Scoped)
  // ===========================================

  /**
   * Create a new content item (user-scoped)
   */
  createContentItem({ type, content, status = 'draft', platform = null, userId = 'default' }) {
    return this.query(
      `INSERT INTO content_items (type, status, content, platform, user_id) VALUES (?, ?, ?, ?, ?)`,
      [type, status, content, platform, userId]
    );
  }

  /**
   * Get content items for a user
   * @param {string} userId - User ID
   * @param {Object} filters - Optional filters
   * @returns {Array} Content items
   */
  getUserContentItems(userId, filters = {}) {
    this._ensureInitialized();
    let sql = 'SELECT * FROM content_items WHERE user_id = ?';
    const params = [userId];
    
    if (filters.status) {
      sql += ' AND status = ?';
      params.push(filters.status);
    }
    if (filters.type) {
      sql += ' AND type = ?';
      params.push(filters.type);
    }
    if (filters.platform) {
      sql += ' AND platform = ?';
      params.push(filters.platform);
    }
    
    sql += ' ORDER BY created_at DESC';
    
    if (filters.limit) {
      sql += ' LIMIT ?';
      params.push(filters.limit);
    }
    
    return this.db.prepare(sql).all(...params);
  }

  /**
   * Get content items by status
   */
  getContentItemsByStatus(status, limit = 100, userId = null) {
    let sql = `SELECT * FROM content_items WHERE status = ?`;
    const params = [status];
    
    if (userId) {
      sql += ` AND user_id = ?`;
      params.push(userId);
    }
    
    sql += ` ORDER BY created_at DESC LIMIT ?`;
    params.push(limit);
    
    return this.query(sql, params);
  }

  /**
   * Update content item status
   */
  updateContentItemStatus(id, status, externalId = null, engagementMetrics = null) {
    const postedAt = status === 'posted' ? new Date().toISOString() : null;
    return this.query(
      `UPDATE content_items 
       SET status = ?, posted_at = ?, external_id = ?, engagement_metrics = ?
       WHERE id = ?`,
      [status, postedAt, externalId, engagementMetrics ? JSON.stringify(engagementMetrics) : null, id]
    );
  }

  // ===========================================
  // Scheduled Tasks Helpers (User-Scoped)
  // ===========================================

  /**
   * Create a new scheduled task
   * @param {Object} data - Task data
   * @returns {Object} Created task
   */
  createScheduledTask({ userId, taskType, scheduleType, scheduleConfig, scheduleDescription = null, payload = null, nextRunAt = null }) {
    this._ensureInitialized();
    const id = randomUUID();
    
    this.db.prepare(`
      INSERT INTO scheduled_tasks (id, user_id, task_type, schedule_type, schedule_config, schedule_description, payload, next_run_at)
      VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    `).run(id, userId, taskType, scheduleType, JSON.stringify(scheduleConfig), scheduleDescription, payload ? JSON.stringify(payload) : null, nextRunAt);
    
    return this.db.prepare('SELECT * FROM scheduled_tasks WHERE id = ?').get(id);
  }

  /**
   * Get tasks for a user
   * @param {string} userId - User ID
   * @returns {Array} Scheduled tasks
   */
  getUserTasks(userId) {
    this._ensureInitialized();
    return this.db.prepare('SELECT * FROM scheduled_tasks WHERE user_id = ? ORDER BY created_at DESC').all(userId);
  }

  /**
   * Get all active tasks
   */
  getActiveTasks() {
    return this.query(
      `SELECT * FROM scheduled_tasks WHERE is_active = 1`
    );
  }

  // Legacy method name alias
  getEnabledTasks() {
    return this.getActiveTasks();
  }

  /**
   * Get tasks due to run
   */
  getDueTasks() {
    return this.query(
      `SELECT * FROM scheduled_tasks 
       WHERE is_active = 1 AND (next_run_at IS NULL OR next_run_at <= CURRENT_TIMESTAMP)`
    );
  }

  /**
   * Update task run times
   */
  updateTaskRunTimes(id, lastRun, nextRun) {
    return this.query(
      `UPDATE scheduled_tasks SET last_run_at = ?, next_run_at = ? WHERE id = ?`,
      [lastRun, nextRun, id]
    );
  }

  /**
   * Update task active status
   */
  setTaskActive(id, isActive) {
    return this.query(
      `UPDATE scheduled_tasks SET is_active = ? WHERE id = ?`,
      [isActive ? 1 : 0, id]
    );
  }

  /**
   * Delete a scheduled task
   */
  deleteScheduledTask(id) {
    return this.query(`DELETE FROM scheduled_tasks WHERE id = ?`, [id]);
  }

  // ===========================================
  // Content Bookmarks Helpers
  // ===========================================

  /**
   * Create a content bookmark
   * @param {Object} data - Bookmark data
   * @returns {Object} Created bookmark
   */
  createContentBookmark({ userId, xTweetId, text, author, authorHandle, url, tags = null }) {
    this._ensureInitialized();
    const id = randomUUID();
    
    this.db.prepare(`
      INSERT INTO content_bookmarks (id, user_id, x_tweet_id, text, author, author_handle, url, tags)
      VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    `).run(id, userId, xTweetId, text, author, authorHandle, url, tags ? JSON.stringify(tags) : null);
    
    return this.db.prepare('SELECT * FROM content_bookmarks WHERE id = ?').get(id);
  }

  /**
   * Get bookmarks for a user
   * @param {string} userId - User ID
   * @param {Object} filters - Optional filters
   * @returns {Array} Bookmarks
   */
  getUserBookmarks(userId, filters = {}) {
    this._ensureInitialized();
    let sql = 'SELECT * FROM content_bookmarks WHERE user_id = ?';
    const params = [userId];
    
    if (filters.usedAsSource !== undefined) {
      sql += ' AND used_as_source = ?';
      params.push(filters.usedAsSource ? 1 : 0);
    }
    
    sql += ' ORDER BY pulled_at DESC';
    
    if (filters.limit) {
      sql += ' LIMIT ?';
      params.push(filters.limit);
    }
    
    return this.db.prepare(sql).all(...params);
  }

  /**
   * Mark bookmark as used as source
   */
  markBookmarkAsUsed(id) {
    return this.query(
      `UPDATE content_bookmarks SET used_as_source = 1 WHERE id = ?`,
      [id]
    );
  }

  /**
   * Delete a bookmark
   */
  deleteBookmark(id) {
    return this.query(`DELETE FROM content_bookmarks WHERE id = ?`, [id]);
  }

  // ===========================================
  // AI Commands Helpers
  // ===========================================

  /**
   * Log an AI command
   * @param {Object} data - Command data
   * @returns {Object} Created command record
   */
  logAICommand({ userId, input, parsedIntent = null, executedActions = null }) {
    this._ensureInitialized();
    const id = randomUUID();
    
    this.db.prepare(`
      INSERT INTO ai_commands (id, user_id, input, parsed_intent, executed_actions)
      VALUES (?, ?, ?, ?, ?)
    `).run(id, userId, input, parsedIntent ? JSON.stringify(parsedIntent) : null, executedActions ? JSON.stringify(executedActions) : null);
    
    return this.db.prepare('SELECT * FROM ai_commands WHERE id = ?').get(id);
  }

  /**
   * Update AI command with user feedback
   */
  updateAICommandFeedback(id, feedback) {
    return this.query(
      `UPDATE ai_commands SET user_feedback = ? WHERE id = ?`,
      [feedback, id]
    );
  }

  /**
   * Get AI commands for a user
   */
  getUserAICommands(userId, limit = 100) {
    return this.query(
      `SELECT * FROM ai_commands WHERE user_id = ? ORDER BY created_at DESC LIMIT ?`,
      [userId, limit]
    );
  }

  // ===========================================
  // Rate Limits Helpers (User-Scoped)
  // ===========================================

  /**
   * Check and increment rate limit (user-scoped)
   * @returns {boolean} True if action is allowed, false if rate limited
   */
  checkRateLimit(actionType, maxCount, windowMinutes, userId = 'default') {
    return this.transaction(() => {
      const now = new Date();
      const windowStart = new Date(now.getTime() - windowMinutes * 60 * 1000);

      // Clean up expired rate limits
      this.query(
        `DELETE FROM rate_limits WHERE window_start < ?`,
        [windowStart.toISOString()]
      );

      // Get current count for this action type and user in the window
      const row = this.queryOne(
        `SELECT SUM(count) as total FROM rate_limits 
         WHERE action_type = ? AND user_id = ? AND window_start >= ?`,
        [actionType, userId, windowStart.toISOString()]
      );

      const currentCount = row?.total || 0;

      if (currentCount >= maxCount) {
        return false;
      }

      // Increment the counter
      this.query(
        `INSERT INTO rate_limits (action_type, user_id, window_start, count, max_count, window_minutes)
         VALUES (?, ?, CURRENT_TIMESTAMP, 1, ?, ?)`,
        [actionType, userId, maxCount, windowMinutes]
      );

      return true;
    });
  }

  /**
   * Get remaining rate limit count (user-scoped)
   */
  getRemainingRateLimit(actionType, maxCount, windowMinutes, userId = 'default') {
    const now = new Date();
    const windowStart = new Date(now.getTime() - windowMinutes * 60 * 1000);

    const row = this.queryOne(
      `SELECT SUM(count) as total FROM rate_limits 
       WHERE action_type = ? AND user_id = ? AND window_start >= ?`,
      [actionType, userId, windowStart.toISOString()]
    );

    const currentCount = row?.total || 0;
    return Math.max(0, maxCount - currentCount);
  }

  // ===========================================
  // Approval Queue Helpers (User-Scoped)
  // ===========================================

  /**
   * Add item to approval queue (user-scoped)
   */
  addToApprovalQueue(actionType, actionData, userId = 'default') {
    return this.query(
      `INSERT INTO approval_queue (action_type, action_data, user_id) VALUES (?, ?, ?)`,
      [actionType, JSON.stringify(actionData), userId]
    );
  }

  /**
   * Get pending approvals
   */
  getPendingApprovals(limit = 100, userId = null) {
    let sql = `SELECT * FROM approval_queue WHERE status = 'pending'`;
    const params = [];
    
    if (userId) {
      sql += ` AND user_id = ?`;
      params.push(userId);
    }
    
    sql += ` ORDER BY created_at ASC LIMIT ?`;
    params.push(limit);
    
    return this.query(sql, params);
  }

  /**
   * Approve or reject an item
   */
  resolveApproval(id, approved, note = null) {
    const status = approved ? 'approved' : 'rejected';
    return this.query(
      `UPDATE approval_queue 
       SET status = ?, reviewed_at = CURRENT_TIMESTAMP, reviewer_note = ?
       WHERE id = ?`,
      [status, note, id]
    );
  }

  // ===========================================
  // Experiments Helpers (User-Scoped)
  // ===========================================

  /**
   * Create a new experiment (user-scoped)
   */
  createExperiment({ name, hypothesis, startDate, endDate, variants, userId = 'default' }) {
    return this.query(
      `INSERT INTO experiments (name, hypothesis, start_date, end_date, variants, user_id)
       VALUES (?, ?, ?, ?, ?, ?)`,
      [name, hypothesis, startDate, endDate, JSON.stringify(variants), userId]
    );
  }

  /**
   * Get active experiments
   */
  getActiveExperiments(userId = null) {
    let sql = `SELECT * FROM experiments 
       WHERE start_date <= CURRENT_TIMESTAMP 
       AND (end_date IS NULL OR end_date >= CURRENT_TIMESTAMP)`;
    const params = [];
    
    if (userId) {
      sql += ` AND user_id = ?`;
      params.push(userId);
    }
    
    return this.query(sql, params);
  }

  /**
   * Update experiment results
   */
  updateExperimentResults(id, results) {
    return this.query(
      `UPDATE experiments SET results = ? WHERE id = ?`,
      [JSON.stringify(results), id]
    );
  }

  // ===========================================
  // Learnings Helpers (User-Scoped)
  // ===========================================

  /**
   * Add a learning (user-scoped)
   */
  addLearning({ category, insight, evidence = null, confidence = 0.5, applicableTo = null, userId = 'default' }) {
    return this.query(
      `INSERT INTO learnings (category, insight, evidence, confidence, applicable_to, user_id)
       VALUES (?, ?, ?, ?, ?, ?)`,
      [category, insight, evidence ? JSON.stringify(evidence) : null, confidence, 
       applicableTo ? JSON.stringify(applicableTo) : null, userId]
    );
  }

  /**
   * Get learnings by category
   */
  getLearningsByCategory(category, limit = 100, userId = null) {
    let sql = `SELECT * FROM learnings WHERE category = ?`;
    const params = [category];
    
    if (userId) {
      sql += ` AND user_id = ?`;
      params.push(userId);
    }
    
    sql += ` ORDER BY confidence DESC, created_at DESC LIMIT ?`;
    params.push(limit);
    
    return this.query(sql, params);
  }

  // ===========================================
  // Action Log Helpers (User-Scoped)
  // ===========================================

  /**
   * Log an action (user-scoped)
   */
  logAction({ module, action, params = null, result = null, error = null, durationMs = null, userId = 'default' }) {
    return this.query(
      `INSERT INTO action_log (module, action, params, result, error, duration_ms, user_id)
       VALUES (?, ?, ?, ?, ?, ?, ?)`,
      [module, action, params ? JSON.stringify(params) : null, result, error, durationMs, userId]
    );
  }

  /**
   * Get recent action logs
   */
  getRecentActions(limit = 100, module = null, userId = null) {
    let sql = `SELECT * FROM action_log WHERE 1=1`;
    const params = [];
    
    if (module) {
      sql += ` AND module = ?`;
      params.push(module);
    }
    
    if (userId) {
      sql += ` AND user_id = ?`;
      params.push(userId);
    }
    
    sql += ` ORDER BY timestamp DESC LIMIT ?`;
    params.push(limit);
    
    return this.query(sql, params);
  }

  // ===========================================
  // Utility Methods
  // ===========================================

  /**
   * Ensure database is initialized
   */
  _ensureInitialized() {
    if (!this.initialized || !this.db) {
      throw new Error('StateManager not initialized. Call init() first.');
    }
  }

  /**
   * Get database statistics
   */
  getStats() {
    this._ensureInitialized();
    const tables = [
      'users', 'sessions', 'agent_state', 'content_items', 'scheduled_tasks', 
      'rate_limits', 'approval_queue', 'experiments', 'learnings', 
      'action_log', 'ai_commands', 'content_bookmarks'
    ];
    
    const stats = {};
    for (const table of tables) {
      try {
        const row = this.queryOne(`SELECT COUNT(*) as count FROM ${table}`);
        stats[table] = row.count;
      } catch {
        stats[table] = 0;
      }
    }
    return stats;
  }

  /**
   * Clear all data from tables (use with caution)
   */
  clearAll() {
    this._ensureInitialized();
    return this.transaction(() => {
      this.query('DELETE FROM content_bookmarks');
      this.query('DELETE FROM ai_commands');
      this.query('DELETE FROM action_log');
      this.query('DELETE FROM learnings');
      this.query('DELETE FROM experiments');
      this.query('DELETE FROM approval_queue');
      this.query('DELETE FROM rate_limits');
      this.query('DELETE FROM scheduled_tasks');
      this.query('DELETE FROM content_items');
      this.query('DELETE FROM agent_state');
      this.query('DELETE FROM sessions');
      // Don't delete users by default - keep default user
    });
  }
}

// Export singleton instance
export const stateManager = new StateManager();
export default StateManager;
