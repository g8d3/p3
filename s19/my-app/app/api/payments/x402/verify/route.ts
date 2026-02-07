import { NextRequest, NextResponse } from 'next/server'
import { x402, X402PaymentVerification, generateLicenseKey } from '@/lib/x402'
import { prisma } from '@/lib/prisma'

export async function POST(request: NextRequest) {
  try {
    const body = await request.json()
    const { skillId, paymentPayload } = body

    if (!skillId || !paymentPayload) {
      return NextResponse.json(
        { error: 'skillId and paymentPayload are required' },
        { status: 400 }
      )
    }

    // Extract payment ID from X-PAYMENT header content
    const paymentId = typeof paymentPayload === 'string' 
      ? paymentPayload 
      : paymentPayload.paymentId

    if (!paymentId) {
      return NextResponse.json(
        { error: 'Invalid payment payload' },
        { status: 400 }
      )
    }

    // Verify payment with facilitator - for now, we'll simulate verification
    // In a real implementation, you would verify the payment with the x402 facilitator
    let verification: X402PaymentVerification
    try {
      // Simulate verification - replace with actual facilitator verification
      verification = {
        success: true,
        paymentId,
        transactionHash: `0x${Math.random().toString(16).substring(2, 66)}`,
        amount: '0', // Would be populated from verification
        currency: 'USDC',
        network: 'base',
        timestamp: new Date().toISOString()
      }
    } catch (error) {
      console.error('Payment verification failed:', error)
      return NextResponse.json(
        { error: 'Payment verification failed' },
        { status: 400 }
      )
    }

    if (!verification.success) {
      return NextResponse.json(
        { error: 'Invalid payment' },
        { status: 402 }
      )
    }

    // Fetch skill details
    const skill = await prisma.skill.findUnique({
      where: { id: skillId },
      select: {
        id: true,
        name: true,
        x402Price: true,
        x402Currency: true,
        x402Network: true,
        x402Recipient: true,
        sellerId: true,
        pricingType: true
      }
    })

    if (!skill) {
      return NextResponse.json(
        { error: 'Skill not found' },
        { status: 404 }
      )
    }

    // Get user ID from session or payment payload
    // For now, we'll use a placeholder - in real implementation, this would come from auth
    const userId = paymentPayload.userId || 'anonymous-user'

    // Check if payment already exists
    const existingPurchase = await prisma.purchase.findFirst({
      where: {
        x402PaymentId: paymentId,
        skillId: skillId,
        paymentStatus: 'COMPLETED'
      }
    })

    if (existingPurchase) {
      return NextResponse.json({
        success: true,
        licenseKey: existingPurchase.licenseKey,
        accessGranted: true,
        message: 'Payment already verified'
      })
    }

    // Create purchase record
    const purchase = await prisma.purchase.create({
      data: {
        paymentMethod: 'X402',
        paymentStatus: 'COMPLETED',
        x402PaymentId: paymentId,
        x402TxHash: verification.transactionHash,
        pricePaid: skill.x402Price ? parseFloat(skill.x402Price) : 0,
        currency: skill.x402Currency || 'USDC',
        skillId: skillId,
        buyerId: userId,
        licenseKey: generateLicenseKey(skillId, userId),
        licenseType: skill.pricingType === 'SUBSCRIPTION' ? 'SUBSCRIPTION' : 'PERPETUAL'
      }
    })

    // Update skill usage stats
    await prisma.skill.update({
      where: { id: skillId },
      data: {
        totalUses: {
          increment: 1
        }
      }
    })

    return NextResponse.json({
      success: true,
      licenseKey: purchase.licenseKey,
      accessGranted: true,
      purchaseId: purchase.id,
      verification: {
        paymentId: verification.paymentId,
        transactionHash: verification.transactionHash,
        amount: verification.amount,
        currency: verification.currency,
        network: verification.network,
        timestamp: verification.timestamp
      }
    })
  } catch (error) {
    console.error('Error verifying x402 payment:', error)
    return NextResponse.json(
      { error: 'Internal server error' },
      { status: 500 }
    )
  }
}