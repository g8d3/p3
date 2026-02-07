import { NextRequest, NextResponse } from 'next/server'
import { prisma } from '@/lib/prisma'
import { z } from 'zod'

// Query schema for featured skills
const querySchema = z.object({
  limit: z.coerce.number().min(1).max(50).default(10),
  category: z.enum(['DATA_PROCESSING', 'NLP', 'VISION', 'AUTOMATION', 'ANALYTICS', 'COMMUNICATION', 'CREATIVE', 'RESEARCH', 'DEV_TOOLS', 'FINANCE', 'OTHER']).optional(),
})

export async function GET(request: NextRequest) {
  try {
    const { searchParams } = new URL(request.url)
    const query = querySchema.parse(Object.fromEntries(searchParams))
    
    const where: any = {
      isPublished: true,
    }
    
    // Apply category filter if provided
    if (query.category) {
      where.category = query.category
    }
    
    // Get featured skills based on multiple factors
    // We'll use a scoring system that considers rating, usage, and recency
    const featuredSkills = await prisma.skill.findMany({
      where,
      include: {
        seller: {
          select: {
            id: true,
            name: true,
            type: true,
            reputation: true,
            image: true,
          }
        }
      },
      orderBy: [
        { avgRating: 'desc' },
        { totalUses: 'desc' },
        { reviewCount: 'desc' },
        { createdAt: 'desc' }
      ],
      take: query.limit,
    })
    
    // Calculate a featured score for each skill
    const skillsWithScore = featuredSkills.map((skill: any) => {
      // Score based on rating (40%), usage (30%), reviews (20%), recency (10%)
      const ratingScore = (skill.avgRating / 5) * 0.4
      const usageScore = Math.min(skill.totalUses / 1000, 1) * 0.3 // Cap at 1000 uses
      const reviewScore = Math.min(skill.reviewCount / 50, 1) * 0.2 // Cap at 50 reviews
      const recencyScore = skill.createdAt > new Date(Date.now() - 30 * 24 * 60 * 60 * 1000) ? 0.1 : 0.05 // Newer gets bonus
      
      return {
        ...skill,
        featuredScore: ratingScore + usageScore + reviewScore + recencyScore
      }
    })
    
    // Sort by featured score
    skillsWithScore.sort((a: any, b: any) => b.featuredScore - a.featuredScore)
    
    return NextResponse.json({
      featuredSkills: skillsWithScore,
      meta: {
        limit: query.limit,
        category: query.category,
        total: skillsWithScore.length
      }
    })
  } catch (error) {
    console.error('Error fetching featured skills:', error)
    return NextResponse.json(
      { error: 'Failed to fetch featured skills' },
      { status: 500 }
    )
  }
}