import config from '../../config/defaults.js';

/**
 * Approval - Approval queue system for actions requiring human approval
 * Uses StateManager approval_queue table for persistence
 */
export class Approval {
  constructor(stateManager, logger = console) {
    this.stateManager = stateManager;
    this.logger = logger;
    this.requireApproval = config.safety.requireApproval;
    this.timeoutHours = config.safety.approvalTimeoutHours;
  }

  /**
   * Get the table name for approval queue
   */
  getTableName() {
    return 'approval_queue';
  }

  /**
   * Ensure the approval queue table exists
   */
  async ensureTable() {
    const sql = `
      CREATE TABLE IF NOT EXISTS ${this.getTableName()} (
        id TEXT PRIMARY KEY,
        action_type TEXT NOT NULL,
        action_data TEXT NOT NULL,
        status TEXT DEFAULT 'pending',
        created_at INTEGER NOT NULL,
        expires_at INTEGER NOT NULL,
        approved_at INTEGER,
        approved_by TEXT,
        approval_note TEXT,
        rejected_at INTEGER,
        rejected_by TEXT,
        rejection_note TEXT
      )
    `;
    await this.stateManager.run(sql);
    
    // Create index for faster pending queries
    await this.stateManager.run(`
      CREATE INDEX IF NOT EXISTS idx_approval_status 
      ON ${this.getTableName()}(status, expires_at)
    `);
  }

  /**
   * Generate a unique ID for approval requests
   */
  generateId() {
    return `apr_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
  }

  /**
   * Request approval for an action
   * @param {string} actionType - Type of action requiring approval
   * @param {object} actionData - Data describing the action
   * @returns {Promise<{id: string, requiresApproval: boolean}>}
   */
  async requestApproval(actionType, actionData) {
    // Check if approval is required
    if (!this.requireApproval) {
      return {
        id: null,
        requiresApproval: false,
        message: 'Approval not required'
      };
    }

    await this.ensureTable();

    const id = this.generateId();
    const now = Date.now();
    const expiresAt = now + (this.timeoutHours * 60 * 60 * 1000);

    const sql = `
      INSERT INTO ${this.getTableName()} 
      (id, action_type, action_data, status, created_at, expires_at)
      VALUES (?, ?, ?, 'pending', ?, ?)
    `;

    await this.stateManager.run(sql, [
      id,
      actionType,
      JSON.stringify(actionData),
      now,
      expiresAt
    ]);

    this.logger.log(`[APPROVAL] New approval request: ${id}`);
    this.logger.log(`[APPROVAL] Type: ${actionType}, Expires: ${new Date(expiresAt).toISOString()}`);

    return {
      id,
      requiresApproval: true,
      expiresAt,
      message: `Approval request created. ID: ${id}`
    };
  }

  /**
   * Get all pending approval requests (excluding expired)
   * @returns {Promise<Array>} - Array of pending approval requests
   */
  async getPending() {
    await this.ensureTable();

    const now = Date.now();
    const sql = `
      SELECT id, action_type, action_data, created_at, expires_at
      FROM ${this.getTableName()}
      WHERE status = 'pending' AND expires_at > ?
      ORDER BY created_at DESC
    `;

    const rows = await this.stateManager.query(sql, [now]);
    
    return rows.map(row => ({
      id: row.id,
      actionType: row.action_type,
      actionData: JSON.parse(row.action_data),
      createdAt: row.created_at,
      expiresAt: row.expires_at,
      createdAtISO: new Date(row.created_at).toISOString(),
      expiresAtISO: new Date(row.expires_at).toISOString()
    }));
  }

  /**
   * Get all approval requests (any status)
   * @param {string} status - Optional status filter ('pending', 'approved', 'rejected', 'expired')
   * @returns {Promise<Array>}
   */
  async getAll(status = null) {
    await this.ensureTable();

    let sql = `SELECT * FROM ${this.getTableName()}`;
    const params = [];

    if (status) {
      sql += ` WHERE status = ?`;
      params.push(status);
    }

    sql += ` ORDER BY created_at DESC`;

    const rows = await this.stateManager.query(sql, params);
    return rows.map(row => ({
      id: row.id,
      actionType: row.action_type,
      actionData: JSON.parse(row.action_data),
      status: row.status,
      createdAt: row.created_at,
      expiresAt: row.expires_at,
      approvedAt: row.approved_at,
      approvedBy: row.approved_by,
      approvalNote: row.approval_note,
      rejectedAt: row.rejected_at,
      rejectedBy: row.rejected_by,
      rejectionNote: row.rejection_note
    }));
  }

  /**
   * Approve a pending request
   * @param {string} id - Approval request ID
   * @param {string} note - Optional approval note
   * @param {string} approvedBy - Identifier of who approved
   * @returns {Promise<{success: boolean, message: string}>}
   */
  async approve(id, note = '', approvedBy = 'system') {
    await this.ensureTable();

    const now = Date.now();

    // Check if request exists and is pending
    const checkSql = `SELECT * FROM ${this.getTableName()} WHERE id = ?`;
    const rows = await this.stateManager.query(checkSql, [id]);

    if (rows.length === 0) {
      return { success: false, message: 'Approval request not found' };
    }

    const request = rows[0];
    if (request.status !== 'pending') {
      return { success: false, message: `Request already ${request.status}` };
    }

    if (request.expires_at < now) {
      // Mark as expired
      await this.stateManager.run(
        `UPDATE ${this.getTableName()} SET status = 'expired' WHERE id = ?`,
        [id]
      );
      return { success: false, message: 'Request has expired' };
    }

    // Approve the request
    const updateSql = `
      UPDATE ${this.getTableName()} 
      SET status = 'approved', 
          approved_at = ?, 
          approved_by = ?, 
          approval_note = ?
      WHERE id = ?
    `;

    await this.stateManager.run(updateSql, [now, approvedBy, note, id]);

    this.logger.log(`[APPROVAL] Approved: ${id} by ${approvedBy}`);
    if (note) {
      this.logger.log(`[APPROVAL] Note: ${note}`);
    }

    return { success: true, message: 'Request approved' };
  }

  /**
   * Reject a pending request
   * @param {string} id - Approval request ID
   * @param {string} note - Rejection reason/note
   * @param {string} rejectedBy - Identifier of who rejected
   * @returns {Promise<{success: boolean, message: string}>}
   */
  async reject(id, note = '', rejectedBy = 'system') {
    await this.ensureTable();

    const now = Date.now();

    // Check if request exists and is pending
    const checkSql = `SELECT * FROM ${this.getTableName()} WHERE id = ?`;
    const rows = await this.stateManager.query(checkSql, [id]);

    if (rows.length === 0) {
      return { success: false, message: 'Approval request not found' };
    }

    const request = rows[0];
    if (request.status !== 'pending') {
      return { success: false, message: `Request already ${request.status}` };
    }

    // Reject the request
    const updateSql = `
      UPDATE ${this.getTableName()} 
      SET status = 'rejected', 
          rejected_at = ?, 
          rejected_by = ?, 
          rejection_note = ?
      WHERE id = ?
    `;

    await this.stateManager.run(updateSql, [now, rejectedBy, note, id]);

    this.logger.log(`[APPROVAL] Rejected: ${id} by ${rejectedBy}`);
    if (note) {
      this.logger.log(`[APPROVAL] Reason: ${note}`);
    }

    return { success: true, message: 'Request rejected' };
  }

  /**
   * Check if a request has been approved
   * @param {string} id - Approval request ID
   * @returns {Promise<{approved: boolean, status: string, data?: object}>}
   */
  async isApproved(id) {
    await this.ensureTable();

    const sql = `SELECT * FROM ${this.getTableName()} WHERE id = ?`;
    const rows = await this.stateManager.query(sql, [id]);

    if (rows.length === 0) {
      return { approved: false, status: 'not_found' };
    }

    const request = rows[0];
    const now = Date.now();

    // Check if expired
    if (request.status === 'pending' && request.expires_at < now) {
      await this.stateManager.run(
        `UPDATE ${this.getTableName()} SET status = 'expired' WHERE id = ?`,
        [id]
      );
      return { approved: false, status: 'expired' };
    }

    return {
      approved: request.status === 'approved',
      status: request.status,
      data: {
        actionType: request.action_type,
        actionData: JSON.parse(request.action_data),
        approvedAt: request.approved_at,
        approvedBy: request.approved_by,
        approvalNote: request.approval_note
      }
    };
  }

  /**
   * Clean up expired approval requests
   * @returns {Promise<number>} - Number of expired requests cleaned
   */
  async cleanupExpired() {
    await this.ensureTable();

    const now = Date.now();
    const sql = `
      UPDATE ${this.getTableName()} 
      SET status = 'expired' 
      WHERE status = 'pending' AND expires_at < ?
    `;

    const result = await this.stateManager.run(sql, [now]);
    const count = result.changes || 0;

    if (count > 0) {
      this.logger.log(`[APPROVAL] Cleaned up ${count} expired requests`);
    }

    return count;
  }

  /**
   * Delete old processed requests (approved/rejected/expired)
   * @param {number} olderThanHours - Delete requests older than this many hours
   * @returns {Promise<number>} - Number of deleted requests
   */
  async deleteOldRequests(olderThanHours = 168) { // Default: 7 days
    await this.ensureTable();

    const cutoff = Date.now() - (olderThanHours * 60 * 60 * 1000);
    const sql = `
      DELETE FROM ${this.getTableName()} 
      WHERE status IN ('approved', 'rejected', 'expired') 
      AND created_at < ?
    `;

    const result = await this.stateManager.run(sql, [cutoff]);
    const count = result.changes || 0;

    if (count > 0) {
      this.logger.log(`[APPROVAL] Deleted ${count} old requests`);
    }

    return count;
  }
}

export default Approval;
