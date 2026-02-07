import { NextRequest, NextResponse } from 'next/server'
import { X402PaymentGenerator, X402PaymentRequirements } from '@/lib/x402'
import { prisma } from '@/lib/prisma'

export async function GET(request: NextRequest) {
  try {
    const { searchParams } = new URL(request.url)
    const skillId = searchParams.get('skillId')

    if (!skillId) {
      return NextResponse.json(
        { error: 'skillId is required' },
        { status: 400 }
      )
    }

    // Fetch skill from database
    const skill = await prisma.skill.findUnique({
      where: { id: skillId },
      select: {
        id: true,
        name: true,
        x402Price: true,
        x402Currency: true,
        x402Network: true,
        x402Recipient: true,
        isPublished: true
      }
    })

    if (!skill) {
      return NextResponse.json(
        { error: 'Skill not found' },
        { status: 404 }
      )
    }

    if (!skill.isPublished) {
      return NextResponse.json(
        { error: 'Skill is not published' },
        { status: 403 }
      )
    }

    if (!skill.x402Price || !skill.x402Currency || !skill.x402Network || !skill.x402Recipient) {
      return NextResponse.json(
        { error: 'Skill does not support x402 payments' },
        { status: 400 }
      )
    }

    // Generate payment requirements
    const requirements = X402PaymentGenerator.generateRequirements({
      x402Price: skill.x402Price,
      x402Currency: skill.x402Currency,
      x402Network: skill.x402Network,
      x402Recipient: skill.x402Recipient
    })

    // Validate requirements
    if (!X402PaymentGenerator.validateRequirements(requirements)) {
      return NextResponse.json(
        { error: 'Invalid payment configuration' },
        { status: 500 }
      )
    }

    // Get additional network and currency info
    const networkConfig = X402PaymentGenerator.getNetworkConfig(requirements.network)
    const currencyConfig = X402PaymentGenerator.getCurrencyConfig(requirements.currency, requirements.network)

    return NextResponse.json({
      requirements: {
        ...requirements,
        skillId: skill.id,
        skillName: skill.name
      },
      network: networkConfig,
      currency: currencyConfig
    })
  } catch (error) {
    console.error('Error fetching x402 requirements:', error)
    return NextResponse.json(
      { error: 'Internal server error' },
      { status: 500 }
    )
  }
}