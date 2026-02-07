import { NextRequest, NextResponse } from 'next/server'
import { x402 } from '@/lib/x402'
import { prisma } from '@/lib/prisma'

export async function POST(request: NextRequest) {
  try {
    const body = await request.json()
    const { skillId, requirements } = body

    if (!skillId || !requirements) {
      return NextResponse.json(
        { error: 'skillId and requirements are required' },
        { status: 400 }
      )
    }

    // Validate skill exists
    const skill = await prisma.skill.findUnique({
      where: { id: skillId },
      select: {
        id: true,
        name: true,
        x402Price: true,
        x402Currency: true,
        x402Network: true,
        x402Recipient: true
      }
    })

    if (!skill) {
      return NextResponse.json(
        { error: 'Skill not found' },
        { status: 404 }
      )
    }

    // Create payment with x402 - for now, we'll simulate payment creation
    // In a real implementation, you would use the x402 SDK to create payments
    try {
      const paymentId = `payment_${Date.now()}_${Math.random().toString(36).substring(7)}`
      const transactionHash = `0x${Math.random().toString(16).substring(2, 66)}`
      
      return NextResponse.json({
        paymentId,
        transactionHash,
        messageToSign: `Sign to authorize payment for ${skill.name}`,
        status: 'pending'
      })
    } catch (error) {
      console.error('Error creating x402 payment:', error)
      return NextResponse.json(
        { error: 'Failed to create payment' },
        { status: 500 }
      )
    }
  } catch (error) {
    console.error('Error in x402 create:', error)
    return NextResponse.json(
      { error: 'Internal server error' },
      { status: 500 }
    )
  }
}