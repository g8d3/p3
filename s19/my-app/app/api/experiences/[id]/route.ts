import { NextRequest, NextResponse } from 'next/server'
import { prisma } from '@/lib/prisma'
import { auth } from '@/lib/auth'
import { z } from 'zod'

export async function GET(
  request: NextRequest,
  { params }: { params: Promise<{ id: string }> }
) {
  try {
    const { id } = await params

    const experience = await prisma.experience.findUnique({
      where: { id },
      include: {
        author: {
          select: {
            id: true,
            name: true,
            type: true,
            reputation: true,
            image: true,
            bio: true
          }
        },
        skill: {
          select: {
            id: true,
            name: true,
            slug: true,
            category: true,
            sellerId: true
          }
        },
        purchase: {
          select: {
            id: true,
            pricePaid: true,
            currency: true,
            paymentMethod: true,
            createdAt: true
          }
        }
      }
    })

    if (!experience) {
      return NextResponse.json(
        { error: 'Experience not found' },
        { status: 404 }
      )
    }

    return NextResponse.json(experience)
  } catch (error) {
    console.error('Error fetching experience:', error)
    return NextResponse.json(
      { error: 'Failed to fetch experience' },
      { status: 500 }
    )
  }
}

export async function PATCH(
  request: NextRequest,
  { params }: { params: Promise<{ id: string }> }
) {
  try {
    const { id } = await params
    
    const session = await auth.api.getSession({
      headers: request.headers,
    })
    
    if (!session?.user) {
      return NextResponse.json(
        { error: 'Unauthorized' },
        { status: 401 }
      )
    }
    
    const userId = session.user.id
    const body = await request.json()
    
    // Check if experience exists and user is the author
    const existingExperience = await prisma.experience.findUnique({
      where: { id },
      select: { authorId: true, skillId: true }
    })
    
    if (!existingExperience) {
      return NextResponse.json(
        { error: 'Experience not found' },
        { status: 404 }
      )
    }
    
    if (existingExperience.authorId !== userId) {
      return NextResponse.json(
        { error: 'Only the author can update this experience' },
        { status: 403 }
      )
    }

    const UpdateSchema = z.object({
      rating: z.number().min(1).max(5).optional(),
      title: z.string().optional(),
      content: z.string().min(10).optional(),
      successRate: z.number().min(0).max(100).optional(),
      avgLatencyMs: z.number().min(0).optional(),
      costEfficiency: z.number().min(1).max(5).optional(),
      easeOfIntegration: z.number().min(1).max(5).optional(),
      documentationQuality: z.number().min(1).max(5).optional(),
      supportQuality: z.number().min(1).max(5).optional(),
      useCase: z.enum(['PRODUCTION', 'DEVELOPMENT', 'RESEARCH', 'PERSONAL', 'ENTERPRISE', 'PROTOTYPING']).optional(),
      workloadSize: z.enum(['SMALL', 'MEDIUM', 'LARGE', 'ENTERPRISE']).optional(),
      buyerType: z.enum(['HUMAN', 'AGENT']).optional(),
      attachments: z.any().optional()
    })

    const validatedData = UpdateSchema.parse(body)

    const experience = await prisma.experience.update({
      where: { id },
      data: {
        ...validatedData,
        attachments: validatedData.attachments || undefined
      },
      include: {
        author: {
          select: {
            id: true,
            name: true,
            type: true,
            reputation: true,
            image: true
          }
        },
        skill: {
          select: {
            id: true,
            name: true,
            slug: true
          }
        }
      }
    })

    // Update skill rating stats
    await updateSkillRatingStats(existingExperience.skillId)

    return NextResponse.json(experience)
  } catch (error) {
    console.error('Error updating experience:', error)
    return NextResponse.json(
      { error: 'Failed to update experience' },
      { status: 500 }
    )
  }
}

export async function DELETE(
  request: NextRequest,
  { params }: { params: Promise<{ id: string }> }
) {
  try {
    const { id } = await params
    
    const session = await auth.api.getSession({
      headers: request.headers,
    })
    
    if (!session?.user) {
      return NextResponse.json(
        { error: 'Unauthorized' },
        { status: 401 }
      )
    }
    
    const userId = session.user.id
    const isAdmin = session.user.role === 'ADMIN' // Assuming role field exists
    
    // Check if experience exists
    const existingExperience = await prisma.experience.findUnique({
      where: { id },
      select: { authorId: true, skillId: true }
    })
    
    if (!existingExperience) {
      return NextResponse.json(
        { error: 'Experience not found' },
        { status: 404 }
      )
    }
    
    if (existingExperience.authorId !== userId && !isAdmin) {
      return NextResponse.json(
        { error: 'Only the author or admin can delete this experience' },
        { status: 403 }
      )
    }

    await prisma.experience.delete({
      where: { id }
    })

    // Update skill rating stats
    await updateSkillRatingStats(existingExperience.skillId)

    return NextResponse.json({ message: 'Experience deleted successfully' })
  } catch (error) {
    console.error('Error deleting experience:', error)
    return NextResponse.json(
      { error: 'Failed to delete experience' },
      { status: 500 }
    )
  }
}

async function updateSkillRatingStats(skillId: string) {
  const stats = await prisma.experience.aggregate({
    where: { skillId },
    _avg: { rating: true },
    _count: { rating: true }
  })

  await prisma.skill.update({
    where: { id: skillId },
    data: {
      avgRating: stats._avg.rating || 0,
      reviewCount: stats._count.rating
    }
  })
}