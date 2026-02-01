/**
 * Utility functions for validating various inputs in the frontend application.
 * Includes regex patterns and validation logic for trader addresses and other data.
 */

/**
 * Regex pattern for Ethereum-style addresses (42 characters, starts with 0x).
 */
const ETHEREUM_ADDRESS_REGEX = /^0x[a-fA-F0-9]{40}$/;

/**
 * Regex pattern for Solana addresses (32-44 characters, base58).
 */
const SOLANA_ADDRESS_REGEX = /^[1-9A-HJ-NP-Za-km-z]{32,44}$/;

/**
 * Regex pattern for email addresses.
 */
const EMAIL_REGEX = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

/**
 * Validates if a string is a valid trader address.
 * Supports Ethereum and Solana addresses.
 * @param address - The address string to validate
 * @returns True if valid, false otherwise
 */
export function isValidTraderAddress(address: string | null | undefined): boolean {
  if (!address || typeof address !== 'string') {
    return false;
  }
  return ETHEREUM_ADDRESS_REGEX.test(address) || SOLANA_ADDRESS_REGEX.test(address);
}

/**
 * Validates if a string is a valid email address.
 * @param email - The email string to validate
 * @returns True if valid, false otherwise
 */
export function isValidEmail(email: string | null | undefined): boolean {
  if (!email || typeof email !== 'string') {
    return false;
  }
  return EMAIL_REGEX.test(email);
}

/**
 * Validates if a value is a positive number.
 * @param value - The value to validate
 * @returns True if valid positive number, false otherwise
 */
export function isValidAmount(value: number | string | null | undefined): boolean {
  if (value === null || value === undefined) {
    return false;
  }
  const num = typeof value === 'string' ? parseFloat(value) : value;
  return !isNaN(num) && num > 0;
}

/**
 * Validates if a string is not empty and meets minimum length requirements.
 * @param value - The string to validate
 * @param minLength - Minimum length required (default: 1)
 * @returns True if valid, false otherwise
 */
export function isValidString(value: string | null | undefined, minLength: number = 1): boolean {
  return typeof value === 'string' && value.trim().length >= minLength;
}

/**
 * Validates if a date is valid and not in the future.
 * @param date - The date to validate
 * @returns True if valid and not future, false otherwise
 */
export function isValidPastDate(date: Date | string | number | null | undefined): boolean {
  if (!date) {
    return false;
  }
  try {
    const d = new Date(date);
    if (isNaN(d.getTime())) {
      return false;
    }
    return d <= new Date();
  } catch {
    return false;
  }
}