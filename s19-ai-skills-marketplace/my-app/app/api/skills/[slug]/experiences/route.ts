import { NextRequest, NextResponse } from 'next/server'
import { prisma } from '@/lib/prisma'
import { auth } from '@/lib/auth'
import { z } from 'zod'

const QuerySchema = z.object({
  rating: z.string().optional().transform(val => val ? val.split(',').map(Number) : undefined),
  useCase: z.string().optional().transform(val => val ? val.split(',') : undefined),
  buyerType: z.string().optional().transform(val => val ? val.split(',') : undefined),
  workloadSize: z.string().optional().transform(val => val ? val.split(',') : undefined),
  verifiedOnly: z.string().optional().transform(val => val === 'true'),
  hasMetrics: z.string().optional().transform(val => val === 'true'),
  sortBy: z.enum(['newest', 'highest', 'lowest', 'helpful']).default('newest'),
  page: z.string().optional().transform(val => val ? parseInt(val) : 1),
  limit: z.string().optional().transform(val => val ? parseInt(val) : 10),
})

export async function GET(
  request: NextRequest,
  { params }: { params: Promise<{ slug: string }> }
) {
  try {
    const { slug } = await params
  const skill = await prisma.skill.findUnique({ where: { slug } })
  if (!skill) return NextResponse.json({ error: "Skill not found" }, { status: 404 })
  const skillId = skill.id
    const { searchParams } = new URL(request.url)
    
    const query = QuerySchema.parse(Object.fromEntries(searchParams))
    
    const where = {
      skillId,
      ...(query.rating && { rating: { in: query.rating } }),
      ...(query.useCase && { useCase: { in: query.useCase as any[] } }),
      ...(query.buyerType && { buyerType: { in: query.buyerType as any[] } }),
      ...(query.workloadSize && { workloadSize: { in: query.workloadSize as any[] } }),
      ...(query.verifiedOnly && { isVerifiedPurchase: true }),
      ...(query.hasMetrics && {
        OR: [
          { successRate: { not: null } },
          { avgLatencyMs: { not: null } },
          { costEfficiency: { not: null } },
          { easeOfIntegration: { not: null } },
          { documentationQuality: { not: null } },
          { supportQuality: { not: null } }
        ]
      })
    }

    const orderBy = []
    switch (query.sortBy) {
      case 'highest':
        orderBy.push({ rating: 'desc' })
        break
      case 'lowest':
        orderBy.push({ rating: 'asc' })
        break
      case 'helpful':
        orderBy.push({ helpfulCount: 'desc' })
        break
      case 'newest':
      default:
        orderBy.push({ createdAt: 'desc' })
        break
    }

    const skip = (query.page! - 1) * query.limit!

    const [experiences, total] = await Promise.all([
      prisma.experience.findMany({
        where,
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
        },
        orderBy,
        skip,
        take: query.limit!
      }),
      prisma.experience.count({ where })
    ])

    // Calculate aggregated metrics
    const aggregatedMetrics = await prisma.experience.aggregate({
      where: { skillId },
      _avg: {
        rating: true,
        successRate: true,
        avgLatencyMs: true,
        costEfficiency: true,
        easeOfIntegration: true,
        documentationQuality: true,
        supportQuality: true
      },
      _count: true
    })

    return NextResponse.json({
      experiences,
      pagination: {
        page: query.page,
        limit: query.limit,
        total,
        totalPages: Math.ceil(total / query.limit!)
      },
      aggregatedMetrics: {
        avgRating: aggregatedMetrics._avg.rating || 0,
        avgSuccessRate: aggregatedMetrics._avg.successRate || 0,
        avgLatencyMs: aggregatedMetrics._avg.avgLatencyMs || 0,
        avgCostEfficiency: aggregatedMetrics._avg.costEfficiency || 0,
        avgEaseOfIntegration: aggregatedMetrics._avg.easeOfIntegration || 0,
        avgDocumentationQuality: aggregatedMetrics._avg.documentationQuality || 0,
        avgSupportQuality: aggregatedMetrics._avg.supportQuality || 0,
        totalReviews: aggregatedMetrics._count
      }
    })
  } catch (error) {
    console.error('Error fetching experiences:', error)
    return NextResponse.json(
      { error: 'Failed to fetch experiences' },
      { status: 500 }
    )
  }
}

export async function POST(
  request: NextRequest,
  { params }: { params: Promise<{ slug: string }> }
) {
  try {
    const { slug } = await params
  const skill = await prisma.skill.findUnique({ where: { slug } })
  if (!skill) return NextResponse.json({ error: "Skill not found" }, { status: 404 })
  const skillId = skill.id
    
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
    
    // Verify user has purchased the skill
    const purchase = await prisma.purchase.findFirst({
      where: {
        buyerId: userId,
        skillId,
        paymentStatus: 'COMPLETED'
      }
    })
    
    if (!purchase) {
      return NextResponse.json(
        { error: 'Must purchase skill before leaving a review' },
        { status: 403 }
      )
    }
    
    // Check if user already reviewed
    const existingReview = await prisma.experience.findFirst({
      where: {
        skillId,
        authorId: userId,
        purchaseId: purchase.id
      }
    })
    
    if (existingReview) {
      return NextResponse.json(
        { error: 'You have already reviewed this skill' },
        { status: 409 }
      )
    }

    const CreateSchema = z.object({
      rating: z.number().min(1).max(5),
      title: z.string().optional(),
      content: z.string().min(10),
      successRate: z.number().min(0).max(100).optional(),
      avgLatencyMs: z.number().min(0).optional(),
      costEfficiency: z.number().min(1).max(5).optional(),
      easeOfIntegration: z.number().min(1).max(5).optional(),
      documentationQuality: z.number().min(1).max(5).optional(),
      supportQuality: z.number().min(1).max(5).optional(),
      useCase: z.enum(['PRODUCTION', 'DEVELOPMENT', 'RESEARCH', 'PERSONAL', 'ENTERPRISE', 'PROTOTYPING']),
      workloadSize: z.enum(['SMALL', 'MEDIUM', 'LARGE', 'ENTERPRISE']),
      buyerType: z.enum(['HUMAN', 'AGENT']),
      attachments: z.any().optional()
    })

    const validatedData = CreateSchema.parse(body)

    const experience = await prisma.experience.create({
      data: {
        ...validatedData,
        skillId,
        authorId: userId,
        purchaseId: purchase.id,
        isVerifiedPurchase: true,
        attachments: validatedData.attachments || null
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
    await updateSkillRatingStats(skillId)

    return NextResponse.json(experience, { status: 201 })
  } catch (error) {
    console.error('Error creating experience:', error)
    return NextResponse.json(
      { error: 'Failed to create experience' },
      { status: 500 }
    )
  }
}

async function updateSkillRatingStats(skillId: string) {
  const stats = await prisma.experience.aggregate({
    where: { skill.id },
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