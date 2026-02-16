/**
 * JWT token generation and verification utilities
 * Handles access tokens (15 min) and refresh tokens (7 days)
 */

import jwt from 'jsonwebtoken';
import crypto from 'crypto';

// JWT secret - use env var or generate a random one
const JWT_SECRET = process.env.JWT_SECRET || crypto.randomBytes(64).toString('hex');
const ACCESS_TOKEN_EXPIRY = '15m';
const REFRESH_TOKEN_EXPIRY = '7d';

/**
 * Generate an access token for a user
 * @param {Object} user - User object with id, email, displayName, planTier
 * @returns {string} JWT access token
 */
export function generateAccessToken(user) {
  const payload = {
    userId: user.id,
    email: user.email,
    displayName: user.display_name || user.displayName,
    planTier: user.plan_tier || user.planTier || 'free'
  };
  
  return jwt.sign(payload, JWT_SECRET, {
    expiresIn: ACCESS_TOKEN_EXPIRY,
    issuer: 'novaisabuilder-agent'
  });
}

/**
 * Generate a refresh token
 * @returns {Object} { token: plaintext token, hash: hashed token for storage }
 */
export function generateRefreshToken() {
  // Generate a random token
  const token = crypto.randomBytes(40).toString('hex');
  
  // Create a hash for storage (we only store the hash)
  const hash = crypto.createHash('sha256').update(token).digest('hex');
  
  return {
    token,
    hash
  };
}

/**
 * Verify an access token
 * @param {string} token - JWT token to verify
 * @returns {Object|null} Decoded payload or null if invalid
 */
export function verifyAccessToken(token) {
  try {
    const decoded = jwt.verify(token, JWT_SECRET, {
      issuer: 'novaisabuilder-agent'
    });
    return decoded;
  } catch (error) {
    return null;
  }
}

/**
 * Verify a refresh token hash
 * Creates a hash from the plaintext token and compares with stored hash
 * @param {string} token - Plaintext refresh token
 * @returns {string} Hash of the token for comparison
 */
export function hashRefreshToken(token) {
  return crypto.createHash('sha256').update(token).digest('hex');
}

/**
 * Decode an access token without verification (for inspection)
 * @param {string} token - JWT token to decode
 * @returns {Object|null} Decoded payload or null if malformed
 */
export function decodeAccessToken(token) {
  try {
    return jwt.decode(token);
  } catch (error) {
    return null;
  }
}

export default {
  generateAccessToken,
  generateRefreshToken,
  verifyAccessToken,
  hashRefreshToken,
  decodeAccessToken,
  JWT_SECRET
};
