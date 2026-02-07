import { NextRequest, NextResponse } from 'next/server'
import { verifyWebhookSignature, polarClient } from '../../../../../lib/polar'
import { prisma } from '../../../../../lib/prisma'
import { PaymentStatus, LicenseType } from '@prisma/client'
import { generateLicenseKey } from '../../../../../lib/license'

// Webhook event types from Polar.sh
interface PolarWebhookEvent {
  type: string
  data: any
  created_at: string
  id: string
}

export async function POST(request: NextRequest) {
  try {
    const body = await request.text()
    const signature = request.headers.get('polar-signature')

    if (!signature) {
      console.error('Missing Polar signature header')
      return NextResponse.json(
        { error: 'Missing signature' },
        { status: 400 }
      )
    }

    // Verify webhook signature
    if (!verifyWebhookSignature(body, signature)) {
      console.error('Invalid webhook signature')
      return NextResponse.json(
        { error: 'Invalid signature' },
        { status: 401 }
      )
    }

    const event: PolarWebhookEvent = JSON.parse(body)
    console.log('Received Polar webhook event:', event.type)

    // Handle different event types
    // See: https://polar.sh/docs/integrate/webhooks#events
    switch (event.type) {
      case 'checkout.created':
        await handleCheckoutCreated(event.data)
        break

      case 'checkout.updated':
        await handleCheckoutUpdated(event.data)
        break

      case 'order.created':
        await handleOrderCreated(event.data)
        break

      case 'order.paid':
        await handleOrderPaid(event.data)
        break

      case 'subscription.active':
        await handleSubscriptionActive(event.data)
        break

      case 'subscription.cancelled':
        await handleSubscriptionCancelled(event.data)
        break

      default:
        console.log(`Unhandled webhook event type: ${event.type}`)
    }

    return NextResponse.json({ received: true })
  } catch (error) {
    console.error('Webhook processing error:', error)
    return NextResponse.json(
      { error: 'Webhook processing failed' },
      { status: 500 }
    )
  }
}

async function handleCheckoutCreated(data: any) {
  console.log('Checkout created:', data.id)
  
  // Update purchase record with checkout ID if it exists
  if (data.metadata?.skillId) {
    await prisma.purchase.updateMany({
      where: {
        polarCheckoutId: data.id,
      },
      data: {
        paymentStatus: PaymentStatus.PENDING,
      },
    })
  }
}

async function handleCheckoutUpdated(data: any) {
  console.log('Checkout updated (completed):', data.id)
  
  if (!data.metadata?.skillId) {
    console.error('Checkout completed without skill metadata')
    return
  }

  const skillId = data.metadata.skillId
  
  // Find the purchase record
  const purchase = await prisma.purchase.findFirst({
    where: {
      polarCheckoutId: data.id,
      skillId,
    },
    include: {
      skill: true,
    },
  })

  if (!purchase) {
    console.error('Purchase not found for checkout:', data.id)
    return
  }

  // Generate license key
  const licenseKey = generateLicenseKey()
  
  // Calculate expiration for subscriptions
  let expiresAt: Date | null = null
  if (purchase.skill.pricingType === 'SUBSCRIPTION') {
    // Set expiration to 1 year from now (adjust as needed)
    expiresAt = new Date()
    expiresAt.setFullYear(expiresAt.getFullYear() + 1)
  }

  // Update purchase record
  await prisma.purchase.update({
    where: { id: purchase.id },
    data: {
      paymentStatus: PaymentStatus.COMPLETED,
      polarOrderId: data.order_id,
      licenseKey,
      licenseType: purchase.skill.pricingType === 'SUBSCRIPTION' ? LicenseType.SUBSCRIPTION : LicenseType.PERPETUAL,
      expiresAt,
    },
  })

  console.log(`License generated for purchase ${purchase.id}: ${licenseKey}`)
}

async function handleOrderCreated(data: any) {
  console.log('Order created:', data.id)
  
  // Update purchase with order ID
  if (data.checkout_id) {
    await prisma.purchase.updateMany({
      where: {
        polarCheckoutId: data.checkout_id,
      },
      data: {
        polarOrderId: data.id,
      },
    })
  }
}

async function handleOrderPaid(data: any) {
  console.log('Order paid:', data.id)
  
  // Mark purchase as completed
  const purchase = await prisma.purchase.findFirst({
    where: {
      polarOrderId: data.id,
    },
  })

  if (purchase && purchase.paymentStatus !== PaymentStatus.COMPLETED) {
    const licenseKey = generateLicenseKey()
    
    await prisma.purchase.update({
      where: { id: purchase.id },
      data: {
        paymentStatus: PaymentStatus.COMPLETED,
        licenseKey,
      },
    })

    console.log(`License generated for order ${data.id}: ${licenseKey}`)
  }
}

async function handleSubscriptionActive(data: any) {
  console.log('Subscription activated:', data.id)
  
  // For subscription management, you might want to:
  // 1. Update the purchase record
  // 2. Extend the expiration date
  // 3. Send notifications
  
  // This would require linking subscriptions to purchases
  // You might store subscriptionId in the purchase record
}

async function handleSubscriptionCancelled(data: any) {
  console.log('Subscription cancelled:', data.id)
  
  // Handle subscription cancellation
  // 1. Update the purchase record
  // 2. Set appropriate expiration date
  // 3. Send notifications to the user
}