/**
 * Password hashing utilities using bcrypt
 * Provides secure password hashing and verification
 */

import bcrypt from 'bcrypt';

const SALT_ROUNDS = 12;

/**
 * Hash a plaintext password
 * @param {string} password - Plaintext password to hash
 * @returns {Promise<string>} Bcrypt hash of the password
 */
export async function hash(password) {
  return bcrypt.hash(password, SALT_ROUNDS);
}

/**
 * Verify a password against a hash
 * @param {string} password - Plaintext password to verify
 * @param {string} hash - Bcrypt hash to compare against
 * @returns {Promise<boolean>} True if password matches hash
 */
export async function verify(password, hash) {
  return bcrypt.compare(password, hash);
}

export default {
  hash,
  verify
};
