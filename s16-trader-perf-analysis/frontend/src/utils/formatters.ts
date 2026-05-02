/**
 * Utility functions for formatting various data types in the frontend application.
 * Handles edge cases and provides user-friendly output.
 */

/**
 * Formats a number to a user-friendly string with locale-specific formatting.
 * @param value - The number to format
 * @param options - Intl.NumberFormat options
 * @returns Formatted string or 'N/A' if invalid
 */
export function formatNumber(value: number | null | undefined, options?: Intl.NumberFormatOptions): string {
  if (value === null || value === undefined || isNaN(value)) {
    return 'N/A';
  }
  return new Intl.NumberFormat('en-US', options).format(value);
}

/**
 * Formats a number as currency (USD by default).
 * @param value - The number to format
 * @param currency - Currency code (default: 'USD')
 * @returns Formatted currency string or 'N/A' if invalid
 */
export function formatCurrency(value: number | null | undefined, currency: string = 'USD'): string {
  return formatNumber(value, { style: 'currency', currency });
}

/**
 * Formats a number as a percentage.
 * @param value - The decimal value (e.g., 0.15 for 15%)
 * @param decimals - Number of decimal places (default: 2)
 * @returns Formatted percentage string or 'N/A' if invalid
 */
export function formatPercentage(value: number | null | undefined, decimals: number = 2): string {
  if (value === null || value === undefined || isNaN(value)) {
    return 'N/A';
  }
  return `${(value * 100).toFixed(decimals)}%`;
}

/**
 * Formats a date to a user-friendly string.
 * @param date - The date to format (Date object, string, or number)
 * @param options - Intl.DateTimeFormat options
 * @returns Formatted date string or 'Invalid Date' if invalid
 */
export function formatDate(date: Date | string | number | null | undefined, options?: Intl.DateTimeFormatOptions): string {
  if (!date) {
    return 'Invalid Date';
  }
  try {
    const d = new Date(date);
    if (isNaN(d.getTime())) {
      return 'Invalid Date';
    }
    return new Intl.DateTimeFormat('en-US', options).format(d);
  } catch {
    return 'Invalid Date';
  }
}

/**
 * Formats a blockchain address by truncating the middle for readability.
 * @param address - The address string
 * @param startChars - Number of characters to show at start (default: 6)
 * @param endChars - Number of characters to show at end (default: 4)
 * @returns Formatted address or 'Invalid Address' if invalid
 */
export function formatAddress(address: string | null | undefined, startChars: number = 6, endChars: number = 4): string {
  if (!address || typeof address !== 'string' || address.length < startChars + endChars) {
    return 'Invalid Address';
  }
  return `${address.slice(0, startChars)}...${address.slice(-endChars)}`;
}