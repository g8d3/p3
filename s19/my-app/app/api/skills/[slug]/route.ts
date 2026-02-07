import { NextRequest, NextResponse } from 'next/server'
import { prisma } from '@/lib/prisma'
import { auth } from '@/lib/auth'
import { z } from 'zod'

// Update skill schema
const updateSkillSchema = z.object({
  name: z.string().min(1).max(100).optional(),
  description: z.string().min(1).max(5000).optional(),
  shortDesc: z.string().min(1).max(200).optional(),
  category: z.enum(['DATA_PROCESSING', 'NLP', 'VISION', 'AUTOMATION', 'ANALYTICS', 'COMMUNICATION', 'CREATIVE', 'RESEARCH', 'DEV_TOOLS', 'FINANCE', 'OTHER']).optional(),
  subcategory: z.string().optional(),
  tags: z.array(z.string()).optional(),
  integrationType: z.enum(['API', 'MCP', 'WEBSOCKET', 'SDK', 'WEBHOOK', 'GRAPHQL', 'LIBRARY']).optional(),
  inputSchema: z.any().optional(),
  outputSchema: z.any().optional(),
  endpointUrl: z.string().url().optional(),
  documentation: z.string().optional(),
  examples: z.any().optional(),
  pricingType: z.enum(['ONE_TIME', 'SUBSCRIPTION', 'USAGE_BASED', 'FREE']).optional(),
  price: z.coerce.number().min(0).optional(),
  currency: z.string().optional(),
  x402Price: z.string().optional(),
  x402Currency: z.string().optional(),
  x402Network: z.string().optional(),
  x402Recipient: z.string().optional(),
  erc8004EscrowContract: z.string().optional(),
  version: z.string().optional(),
})

export async function GET(
  request: NextRequest,
  { params }: { params: Promise<{ slug: string }> }
) {
  try {
    const skill = await prisma.skill.findUnique({
      where: { 
        slug: (await params).slug,
        isPublished: true
      },
      include: {
        seller: {
          select: {
            id: true,
            name: true,
            email: true,
            type: true,
            reputation: true,
            image: true,
            bio: true,
          }
        },
        experiences: {
          include: {
            author: {
              select: {
                id: true,
                name: true,
                type: true,
                image: true,
              }
            }
          },
          orderBy: {
            createdAt: 'desc'
          },
          take: 10
        }
      }
    })
    
    if (!skill) {
      return NextResponse.json(
        { error: 'Skill not found' },
        { status: 404 }
      )
    }
    
    return NextResponse.json(skill)
  } catch (error) {
    console.error('Error fetching skill:', error)
    return NextResponse.json(
      { error: 'Failed to fetch skill' },
      { status: 500 }
    )
  }
}

export async function PATCH(
  request: NextRequest,
  { params }: { params: Promise<{ slug: string }> }
) {
  try {
    const session = await auth.api.getSession({
      headers: request.headers,
    })
    
    if (!session?.user) {
      return NextResponse.json(
        { error: 'Unauthorized' },
        { status: 401 }
      )
    }
    
    // Get the skill first to check ownership
    const existingSkill = await prisma.skill.findUnique({
      where: { slug: (await params).slug }
    })
    
    if (!existingSkill) {
      return NextResponse.json(
        { error: 'Skill not found' },
        { status: 404 }
      )
    }
    
    if (existingSkill.sellerId !== session.user.id) {
      return NextResponse.json(
        { error: 'Forbidden - Only the seller can update this skill' },
        { status: 403 }
      )
    }
    
    const body = await request.json()
    const validatedData = updateSkillSchema.parse(body)
    
    const skill = await prisma.skill.update({
      where: { slug: (await params).slug },
      data: validatedData,
      include: {
        seller: {
          select: {
            id: true,
            name: true,
            email: true,
            type: true,
            reputation: true,
            image: true,
          }
        }
      }
    })
    
    return NextResponse.json(skill)
  } catch (error) {
    console.error('Error updating skill:', error)
    return NextResponse.json(
      { error: 'Failed to update skill' },
      { status: 500 }
    )
  }
}

export async function DELETE(
  request: NextRequest,
  { params }: { params: Promise<{ slug: string }> }
) {
  try {
    const session = await auth.api.getSession({
      headers: request.headers,
    })
    
    if (!session?.user) {
      return NextResponse.json(
        { error: 'Unauthorized' },
        { status: 401 }
      )
    }
    
    // Get the skill first to check ownership
    const existingSkill = await prisma.skill.findUnique({
      where: { slug: (await params).slug }
    })
    
    if (!existingSkill) {
      return NextResponse.json(
        { error: 'Skill not found' },
        { status: 404 }
      )
    }
    
    if (existingSkill.sellerId !== session.user.id) {
      return NextResponse.json(
        { error: 'Forbidden - Only the seller can delete this skill' },
        { status: 403 }
      )
    }
    
    // Soft delete by setting isPublished to false
    await prisma.skill.update({
      where: { slug: (await params).slug },
      data: { isPublished: false }
    })
    
    return NextResponse.json({ message: 'Skill deleted successfully' })
  } catch (error) {
    console.error('Error deleting skill:', error)
    return NextResponse.json(
      { error: 'Failed to delete skill' },
      { status: 500 }
    )
  }
}