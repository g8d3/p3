import { NextRequest, NextResponse } from 'next/server'
import { createCheckoutSession } from '../../../../../lib/polar'
import { prisma } from '../../../../../lib/prisma'
import { PaymentMethod } from '@prisma/client'

export async function POST(request: NextRequest) {
  try {
    const body = await request.json()
    const { skillId, successUrl, cancelUrl, buyerEmail } = body

    // Validate required fields
    if (!skillId || !successUrl || !cancelUrl) {
      return NextResponse.json(
        { error: 'Missing required fields: skillId, successUrl, cancelUrl' },
        { status: 400 }
      )
    }

    // Get skill details from database
    const skill = await prisma.skill.findUnique({
      where: { id: skillId },
      select: {
        id: true,
        name: true,
        price: true,
        currency: true,
        pricingType: true,
        sellerId: true,
      },
    })

    if (!skill) {
      return NextResponse.json(
        { error: 'Skill not found' },
        { status: 404 }
      )
    }

    // In a real implementation, you would need to:
    // 1. Create/get a Polar product for this skill
    // 2. Use the product ID for checkout creation
    
    // For now, assuming skill.id maps to a Polar product ID
    // In production, you should store polarProductId in the Skill model
    const polarProductId = skill.id // This should be skill.polarProductId in production

    // Create checkout session
    const checkoutResult = await createCheckoutSession({
      productId: polarProductId,
      customerEmail: buyerEmail,
      successUrl,
      cancelUrl,
      metadata: {
        skillId,
        buyerEmail: buyerEmail || '',
        pricingType: skill.pricingType,
      },
    })

    if (!checkoutResult.success) {
      return NextResponse.json(
        { error: checkoutResult.error },
        { status: 500 }
      )
    }

    // Create pending purchase record
    // Note: We need buyerId from the authenticated user
    // This should come from the session/auth context
    const buyerId = body.buyerId // This should come from auth session
    
    if (!buyerId) {
      return NextResponse.json(
        { error: 'Buyer authentication required' },
        { status: 401 }
      )
    }

    const purchase = await prisma.purchase.create({
      data: {
        paymentMethod: PaymentMethod.POLAR,
        paymentStatus: 'PENDING',
        polarCheckoutId: checkoutResult.checkoutId,
        pricePaid: skill.price,
        currency: skill.currency,
        licenseType: skill.pricingType === 'SUBSCRIPTION' ? 'SUBSCRIPTION' : 'PERPETUAL',
        skillId,
        buyerId,
      },
    })

    return NextResponse.json({
      success: true,
      checkoutUrl: checkoutResult.checkoutUrl,
      checkoutId: checkoutResult.checkoutId,
      purchaseId: purchase.id,
    })
  } catch (error) {
    console.error('Error creating checkout:', error)
    return NextResponse.json(
      { error: 'Internal server error' },
      { status: 500 }
    )
  }
}