/**
 * Authentication API Routes
 * Provides endpoints for user registration, login, token refresh, and logout
 */

import { Router } from 'express';
import crypto from 'crypto';
import { stateManager } from '../infrastructure/state.js';
import { hash as hashPassword, verify as verifyPassword } from './password.js';
import { 
  generateAccessToken, 
  generateRefreshToken, 
  hashRefreshToken,
  verifyAccessToken 
} from './jwt.js';
import { authMiddleware, optionalAuth } from './middleware.js';
import logger from '../infrastructure/logger.js';

const log = logger.module('auth');

/**
 * Create auth router
 * @returns {Router}
 */
export function createAuthRouter() {
  const router = Router();

  /**
   * POST /auth/register - Register a new user
   * Body: { email, password, displayName }
   */
  router.post('/register', async (req, res) => {
    try {
      const { email, password, displayName } = req.body;
      
      // Validation
      if (!email || !password) {
        return res.status(400).json({
          success: false,
          error: 'Email and password are required'
        });
      }
      
      if (password.length < 8) {
        return res.status(400).json({
          success: false,
          error: 'Password must be at least 8 characters'
        });
      }
      
      // Check if user already exists
      const existingUser = stateManager.queryOne(
        'SELECT id FROM users WHERE email = ?',
        [email.toLowerCase()]
      );
      
      if (existingUser) {
        return res.status(409).json({
          success: false,
          error: 'An account with this email already exists'
        });
      }
      
      // Hash password
      const passwordHash = await hashPassword(password);
      
      // Generate user ID
      const userId = crypto.randomUUID();
      
      // Create user
      stateManager.query(
        `INSERT INTO users (id, email, password_hash, display_name, timezone, plan_tier)
         VALUES (?, ?, ?, ?, ?, ?)`,
        [userId, email.toLowerCase(), passwordHash, displayName || null, 'UTC', 'free']
      );
      
      // Generate tokens
      const accessToken = generateAccessToken({
        id: userId,
        email: email.toLowerCase(),
        displayName: displayName || null,
        planTier: 'free'
      });
      
      const { token: refreshToken, hash: refreshTokenHash } = generateRefreshToken();
      
      // Store refresh token
      const sessionId = crypto.randomUUID();
      const expiresAt = new Date(Date.now() + 7 * 24 * 60 * 60 * 1000); // 7 days
      
      stateManager.query(
        `INSERT INTO sessions (id, user_id, refresh_token_hash, expires_at)
         VALUES (?, ?, ?, ?)`,
        [sessionId, userId, refreshTokenHash, expiresAt.toISOString()]
      );
      
      log.info(`User registered: ${email}`);
      
      res.status(201).json({
        success: true,
        data: {
          accessToken,
          refreshToken,
          user: {
            id: userId,
            email: email.toLowerCase(),
            displayName: displayName || null,
            timezone: 'UTC',
            planTier: 'free'
          }
        }
      });
    } catch (error) {
      log.error(`Registration error: ${error.message}`);
      res.status(500).json({
        success: false,
        error: 'Registration failed'
      });
    }
  });

  /**
   * POST /auth/login - Login with email and password
   * Body: { email, password }
   */
  router.post('/login', async (req, res) => {
    try {
      const { email, password } = req.body;
      
      if (!email || !password) {
        return res.status(400).json({
          success: false,
          error: 'Email and password are required'
        });
      }
      
      // Find user
      const user = stateManager.queryOne(
        'SELECT * FROM users WHERE email = ?',
        [email.toLowerCase()]
      );
      
      if (!user) {
        return res.status(401).json({
          success: false,
          error: 'Invalid email or password'
        });
      }
      
      // Verify password
      const validPassword = await verifyPassword(password, user.password_hash);
      
      if (!validPassword) {
        return res.status(401).json({
          success: false,
          error: 'Invalid email or password'
        });
      }
      
      // Generate tokens
      const accessToken = generateAccessToken({
        id: user.id,
        email: user.email,
        displayName: user.display_name,
        planTier: user.plan_tier
      });
      
      const { token: refreshToken, hash: refreshTokenHash } = generateRefreshToken();
      
      // Store refresh token
      const sessionId = crypto.randomUUID();
      const expiresAt = new Date(Date.now() + 7 * 24 * 60 * 60 * 1000); // 7 days
      
      stateManager.query(
        `INSERT INTO sessions (id, user_id, refresh_token_hash, expires_at)
         VALUES (?, ?, ?, ?)`,
        [sessionId, user.id, refreshTokenHash, expiresAt.toISOString()]
      );
      
      // Update user's updated_at
      stateManager.query(
        'UPDATE users SET updated_at = CURRENT_TIMESTAMP WHERE id = ?',
        [user.id]
      );
      
      log.info(`User logged in: ${email}`);
      
      res.json({
        success: true,
        data: {
          accessToken,
          refreshToken,
          user: {
            id: user.id,
            email: user.email,
            displayName: user.display_name,
            timezone: user.timezone,
            planTier: user.plan_tier
          }
        }
      });
    } catch (error) {
      log.error(`Login error: ${error.message}`);
      res.status(500).json({
        success: false,
        error: 'Login failed'
      });
    }
  });

  /**
   * POST /auth/refresh - Refresh access token
   * Body: { refreshToken }
   */
  router.post('/refresh', async (req, res) => {
    try {
      const { refreshToken } = req.body;
      
      if (!refreshToken) {
        return res.status(400).json({
          success: false,
          error: 'Refresh token is required'
        });
      }
      
      // Hash the provided token to find it in the database
      const tokenHash = hashRefreshToken(refreshToken);
      
      // Find the session
      const session = stateManager.queryOne(
        `SELECT s.*, u.id as user_id, u.email, u.display_name, u.timezone, u.plan_tier
         FROM sessions s
         JOIN users u ON s.user_id = u.id
         WHERE s.refresh_token_hash = ? AND s.expires_at > CURRENT_TIMESTAMP`,
        [tokenHash]
      );
      
      if (!session) {
        return res.status(401).json({
          success: false,
          error: 'Invalid or expired refresh token'
        });
      }
      
      // Delete the old session (refresh token rotation)
      stateManager.query('DELETE FROM sessions WHERE id = ?', [session.id]);
      
      // Generate new tokens
      const accessToken = generateAccessToken({
        id: session.user_id,
        email: session.email,
        displayName: session.display_name,
        planTier: session.plan_tier
      });
      
      const { token: newRefreshToken, hash: newRefreshTokenHash } = generateRefreshToken();
      
      // Store new refresh token
      const newSessionId = crypto.randomUUID();
      const expiresAt = new Date(Date.now() + 7 * 24 * 60 * 60 * 1000); // 7 days
      
      stateManager.query(
        `INSERT INTO sessions (id, user_id, refresh_token_hash, expires_at)
         VALUES (?, ?, ?, ?)`,
        [newSessionId, session.user_id, newRefreshTokenHash, expiresAt.toISOString()]
      );
      
      res.json({
        success: true,
        data: {
          accessToken,
          refreshToken: newRefreshToken
        }
      });
    } catch (error) {
      log.error(`Token refresh error: ${error.message}`);
      res.status(500).json({
        success: false,
        error: 'Token refresh failed'
      });
    }
  });

  /**
   * POST /auth/logout - Logout and invalidate refresh token
   * Body: { refreshToken }
   */
  router.post('/logout', async (req, res) => {
    try {
      const { refreshToken } = req.body;
      
      if (!refreshToken) {
        return res.status(400).json({
          success: false,
          error: 'Refresh token is required'
        });
      }
      
      // Hash the token to find and delete the session
      const tokenHash = hashRefreshToken(refreshToken);
      
      stateManager.query(
        'DELETE FROM sessions WHERE refresh_token_hash = ?',
        [tokenHash]
      );
      
      res.json({
        success: true,
        data: { message: 'Logged out successfully' }
      });
    } catch (error) {
      log.error(`Logout error: ${error.message}`);
      res.status(500).json({
        success: false,
        error: 'Logout failed'
      });
    }
  });

  /**
   * GET /auth/me - Get current user info
   * Requires authentication
   */
  router.get('/me', authMiddleware, (req, res) => {
    try {
      const user = stateManager.queryOne(
        'SELECT id, email, display_name, timezone, plan_tier, created_at FROM users WHERE id = ?',
        [req.user.id]
      );
      
      if (!user) {
        return res.status(404).json({
          success: false,
          error: 'User not found'
        });
      }
      
      res.json({
        success: true,
        data: {
          id: user.id,
          email: user.email,
          displayName: user.display_name,
          timezone: user.timezone,
          planTier: user.plan_tier,
          createdAt: user.created_at
        }
      });
    } catch (error) {
      log.error(`Get user error: ${error.message}`);
      res.status(500).json({
        success: false,
        error: 'Failed to get user info'
      });
    }
  });

  /**
   * DELETE /auth/sessions - Invalidate all sessions for current user
   * Requires authentication
   */
  router.delete('/sessions', authMiddleware, (req, res) => {
    try {
      stateManager.query(
        'DELETE FROM sessions WHERE user_id = ?',
        [req.user.id]
      );
      
      res.json({
        success: true,
        data: { message: 'All sessions invalidated' }
      });
    } catch (error) {
      log.error(`Session cleanup error: ${error.message}`);
      res.status(500).json({
        success: false,
        error: 'Failed to invalidate sessions'
      });
    }
  });

  return router;
}

export default createAuthRouter;
