import { randomBytes, createHash } from 'crypto'
import { prisma } from './prisma'
import { LicenseType } from '@prisma/client'

/**
 * Generate a unique license key using cryptographic random bytes
 * Format: XXXX-XXXX-XXXX-XXXX (16 characters in groups of 4)
 */
export function generateLicenseKey(): string {
  const bytes = randomBytes(8) // 8 bytes = 16 hex characters
  const hex = bytes.toString('hex').toUpperCase()
  
  // Format as XXXX-XXXX-XXXX-XXXX
  return [
    hex.slice(0, 4),
    hex.slice(4, 8),
    hex.slice(8, 12),
    hex.slice(12, 16)
  ].join('-')
}

/**
 * Generate a more secure license key with checksum
 * Format: XXXX-XXXX-XXXX-XXXX-XXXX (20 characters with checksum)
 */
export function generateSecureLicenseKey(): string {
  // Generate 16 random characters
  const randomPart = randomBytes(8).toString('hex').toUpperCase()
  
  // Create a checksum (first 4 characters of SHA256 hash)
  const checksum = createHash('sha256')
    .update(randomPart + process.env.LICENSE_SALT || 'default-salt')
    .digest('hex')
    .slice(0, 4)
    .toUpperCase()
  
  const fullKey = randomPart + checksum
  
  // Format as XXXX-XXXX-XXXX-XXXX-XXXX
  return [
    fullKey.slice(0, 4),
    fullKey.slice(4, 8),
    fullKey.slice(8, 12),
    fullKey.slice(12, 16),
    fullKey.slice(16, 20)
  ].join('-')
}

/**
 * Verify a license key and check its validity
 */
export async function verifyLicenseKey(licenseKey: string): Promise<{
  valid: boolean
  purchase?: any
  error?: string
}> {
  if (!licenseKey) {
    return { valid: false, error: 'License key is required' }
  }

  // Validate format
  const licenseKeyRegex = /^[A-F0-9]{4}-[A-F0-9]{4}-[A-F0-9]{4}-[A-F0-9]{4}(-[A-F0-9]{4})?$/
  if (!licenseKeyRegex.test(licenseKey)) {
    return { valid: false, error: 'Invalid license key format' }
  }

  try {
    // Find purchase by license key
    const purchase = await prisma.purchase.findUnique({
      where: { licenseKey },
      include: {
        skill: {
          select: {
            id: true,
            name: true,
            pricingType: true,
            sellerId: true,
          },
        },
        buyer: {
          select: {
            id: true,
            email: true,
            name: true,
          },
        },
      },
    })

    if (!purchase) {
      return { valid: false, error: 'License key not found' }
    }

    // Check payment status
    if (purchase.paymentStatus !== 'COMPLETED') {
      return { valid: false, error: 'License payment not completed' }
    }

    // Check expiration for subscriptions
    if (purchase.licenseType === LicenseType.SUBSCRIPTION && purchase.expiresAt) {
      const now = new Date()
      if (now > purchase.expiresAt) {
        return { valid: false, error: 'License has expired' }
      }
    }

    // Check usage quota for usage-based licenses
    if (purchase.licenseType === LicenseType.USAGE_BASED && purchase.usageQuota) {
      if (purchase.usageConsumed >= purchase.usageQuota) {
        return { valid: false, error: 'Usage quota exceeded' }
      }
    }

    // For secure license keys with checksum, verify the checksum
    if (licenseKey.length > 19) { // 20 chars including dashes
      const parts = licenseKey.split('-')
      if (parts.length === 5) {
        const randomPart = parts.slice(0, 4).join('')
        const providedChecksum = parts[4]
        
        const expectedChecksum = createHash('sha256')
          .update(randomPart + (process.env.LICENSE_SALT || 'default-salt'))
          .digest('hex')
          .slice(0, 4)
          .toUpperCase()
        
        if (providedChecksum !== expectedChecksum) {
          return { valid: false, error: 'Invalid license checksum' }
        }
      }
    }

    return { valid: true, purchase }
  } catch (error) {
    console.error('Error verifying license key:', error)
    return { valid: false, error: 'Internal verification error' }
  }
}

/**
 * Consume usage for a usage-based license
 */
export async function consumeUsage(licenseKey: string, amount: number = 1): Promise<{
  success: boolean
  remaining?: number
  error?: string
}> {
  const verification = await verifyLicenseKey(licenseKey)
  
  if (!verification.valid || !verification.purchase) {
    return { success: false, error: verification.error || 'Invalid license' }
  }

  const purchase = verification.purchase

  if (purchase.licenseType !== LicenseType.USAGE_BASED || !purchase.usageQuota) {
    return { success: false, error: 'License is not usage-based' }
  }

  const newUsageConsumed = purchase.usageConsumed + amount
  
  if (newUsageConsumed > purchase.usageQuota) {
    return { success: false, error: 'Insufficient usage quota' }
  }

  try {
    await prisma.purchase.update({
      where: { id: purchase.id },
      data: {
        usageConsumed: newUsageConsumed,
      },
    })

    return {
      success: true,
      remaining: purchase.usageQuota - newUsageConsumed,
    }
  } catch (error) {
    console.error('Error consuming usage:', error)
    return { success: false, error: 'Failed to update usage' }
  }
}

/**
 * Get license usage statistics
 */
export async function getLicenseStats(licenseKey: string): Promise<{
  totalQuota?: number
  consumed: number
  remaining?: number
  percentage?: number
  error?: string
}> {
  const verification = await verifyLicenseKey(licenseKey)
  
  if (!verification.valid || !verification.purchase) {
    return { consumed: 0, error: verification.error || 'Invalid license' }
  }

  const purchase = verification.purchase
  
  if (purchase.licenseType !== LicenseType.USAGE_BASED || !purchase.usageQuota) {
    return { 
      consumed: purchase.usageConsumed,
      error: 'License is not usage-based' 
    }
  }

  const remaining = purchase.usageQuota - purchase.usageConsumed
  const percentage = (purchase.usageConsumed / purchase.usageQuota) * 100

  return {
    totalQuota: purchase.usageQuota,
    consumed: purchase.usageConsumed,
    remaining,
    percentage,
  }
}

/**
 * Extend subscription expiration
 */
export async function extendSubscription(licenseKey: string, days: number): Promise<{
  success: boolean
  newExpirationDate?: Date
  error?: string
}> {
  const verification = await verifyLicenseKey(licenseKey)
  
  if (!verification.valid || !verification.purchase) {
    return { success: false, error: verification.error || 'Invalid license' }
  }

  const purchase = verification.purchase

  if (purchase.licenseType !== LicenseType.SUBSCRIPTION) {
    return { success: false, error: 'License is not a subscription' }
  }

  try {
    const currentExpiration = purchase.expiresAt || new Date()
    const newExpiration = new Date(currentExpiration)
    newExpiration.setDate(newExpiration.getDate() + days)

    await prisma.purchase.update({
      where: { id: purchase.id },
      data: {
        expiresAt: newExpiration,
      },
    })

    return {
      success: true,
      newExpirationDate: newExpiration,
    }
  } catch (error) {
    console.error('Error extending subscription:', error)
    return { success: false, error: 'Failed to extend subscription' }
  }
}