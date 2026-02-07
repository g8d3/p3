import { Polar } from '@polar-sh/sdk'

// Environment variables
const POLAR_ACCESS_TOKEN = process.env.POLAR_ACCESS_TOKEN
const POLAR_WEBHOOK_SECRET = process.env.POLAR_WEBHOOK_SECRET
const POLAR_MODE = process.env.POLAR_MODE || 'sandbox'

// Validate environment variables
if (!POLAR_ACCESS_TOKEN) {
  throw new Error('POLAR_ACCESS_TOKEN environment variable is required')
}

if (!POLAR_WEBHOOK_SECRET) {
  throw new Error('POLAR_WEBHOOK_SECRET environment variable is required')
}

// Initialize Polar SDK client
export const polarClient = new Polar({
  accessToken: POLAR_ACCESS_TOKEN,
  server: POLAR_MODE === 'production' ? 'production' : 'sandbox',
})

// Helper function to create a checkout session
export async function createCheckoutSession(params: {
  productId: string
  customerEmail?: string
  successUrl: string
  cancelUrl: string
  metadata?: Record<string, string>
}) {
  try {
    const checkout = await polarClient.checkouts.create({
      products: [params.productId],
      customerEmail: params.customerEmail,
      successUrl: params.successUrl,
      returnUrl: params.cancelUrl, // returnUrl is the cancel URL in our context
      metadata: params.metadata,
    })

    return {
      success: true,
      checkoutUrl: checkout.url,
      checkoutId: checkout.id,
    }
  } catch (error) {
    console.error('Error creating checkout session:', error)
    return {
      success: false,
      error: error instanceof Error ? error.message : 'Failed to create checkout session',
    }
  }
}

// Helper function to create a customer portal session
export async function createCustomerPortalSession(customerId: string, returnUrl: string) {
  try {
    const portalSession = await polarClient.customerSessions.create({
      customerId,
      returnUrl,
    })

    return {
      success: true,
      portalUrl: portalSession.customerPortalUrl,
    }
  } catch (error) {
    console.error('Error creating customer portal session:', error)
    return {
      success: false,
      error: error instanceof Error ? error.message : 'Failed to create customer portal session',
    }
  }
}

// Helper function to verify webhook signature
export function verifyWebhookSignature(payload: string, signature: string): boolean {
  try {
    const crypto = require('crypto')
    const hmac = crypto.createHmac('sha256', POLAR_WEBHOOK_SECRET)
    const expectedSignature = hmac.update(payload).digest('hex')
    
    // Compare signatures securely
    return crypto.timingSafeEqual(
      Buffer.from(signature, 'hex'),
      Buffer.from(expectedSignature, 'hex')
    )
  } catch (error) {
    console.error('Error verifying webhook signature:', error)
    return false
  }
}

// Export environment variables for use in other modules
export { POLAR_ACCESS_TOKEN, POLAR_WEBHOOK_SECRET, POLAR_MODE }