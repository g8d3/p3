import { NextRequest, NextResponse } from 'next/server'
import { prisma } from '@/lib/prisma'

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
    
    const verifiedOnly = searchParams.get('verifiedOnly') === 'true'
    const timeFrame = searchParams.get('timeFrame') // 'week', 'month', 'quarter', 'year', 'all'

    // Build date filter based on time frame
    let dateFilter = {}
    const now = new Date()
    
    switch (timeFrame) {
      case 'week':
        dateFilter = { gte: new Date(now.getTime() - 7 * 24 * 60 * 60 * 1000) }
        break
      case 'month':
        dateFilter = { gte: new Date(now.getTime() - 30 * 24 * 60 * 60 * 1000) }
        break
      case 'quarter':
        dateFilter = { gte: new Date(now.getTime() - 90 * 24 * 60 * 60 * 1000) }
        break
      case 'year':
        dateFilter = { gte: new Date(now.getTime() - 365 * 24 * 60 * 60 * 1000) }
        break
      default:
        dateFilter = {} // All time
    }

    const where = {
      skillId,
      ...(verifiedOnly && { isVerifiedPurchase: true }),
      ...(Object.keys(dateFilter).length > 0 && { createdAt: dateFilter })
    }

    // Basic aggregates
    const [
      basicStats,
      ratingDistribution,
      metricsAverages,
      useCaseBreakdown,
      buyerTypeBreakdown,
      workloadSizeBreakdown,
      timeSeriesData
    ] = await Promise.all([
      // Basic stats
      prisma.experience.aggregate({
        where,
        _avg: { rating: true },
        _count: { rating: true },
        _min: { rating: true },
        _max: { rating: true }
      }),

      // Rating distribution
      prisma.experience.groupBy({
        by: ['rating'],
        where,
        _count: { rating: true },
        orderBy: { rating: 'asc' }
      }),

      // Metrics averages for structured data
      prisma.experience.aggregate({
        where,
        _avg: {
          successRate: true,
          avgLatencyMs: true,
          costEfficiency: true,
          easeOfIntegration: true,
          documentationQuality: true,
          supportQuality: true
        },
        _count: {
          successRate: true,
          avgLatencyMs: true,
          costEfficiency: true,
          easeOfIntegration: true,
          documentationQuality: true,
          supportQuality: true
        }
      }),

      // Use case breakdown
      prisma.experience.groupBy({
        by: ['useCase'],
        where,
        _count: { useCase: true },
        _avg: { rating: true }
      }),

      // Buyer type breakdown
      prisma.experience.groupBy({
        by: ['buyerType'],
        where,
        _count: { buyerType: true },
        _avg: { rating: true }
      }),

      // Workload size breakdown
      prisma.experience.groupBy({
        by: ['workloadSize'],
        where,
        _count: { workloadSize: true },
        _avg: { rating: true }
      }),

      // Time series data (last 30 days)
      prisma.$queryRaw`
        SELECT 
          DATE_TRUNC('day', created_at) as date,
          COUNT(*) as count,
          AVG(rating) as avg_rating
        FROM experiences 
        WHERE skill_id = ${skillId}
          AND created_at >= ${new Date(now.getTime() - 30 * 24 * 60 * 60 * 1000)}
        GROUP BY DATE_TRUNC('day', created_at)
        ORDER BY date DESC
      `
    ])

    // Verification stats
    const verificationStats = await prisma.experience.groupBy({
      by: ['isVerifiedPurchase', 'isVerifiedUsage'],
      where: { skillId },
      _count: { id: true },
      _avg: { rating: true }
    })

    // Engagement stats
    const engagementStats = await prisma.experience.aggregate({
      where: { skillId },
      _avg: { helpfulCount: true, unhelpfulCount: true },
      _sum: { helpfulCount: true, unhelpfulCount: true }
    })

    // Format rating distribution
    const formattedRatingDistribution = ratingDistribution.map(item => ({
      rating: item.rating,
      count: item._count.rating,
      percentage: Math.round((item._count.rating / basicStats._count.rating) * 100)
    }))

    // Format use case breakdown
    const formattedUseCaseBreakdown = useCaseBreakdown.map(item => ({
      useCase: item.useCase,
      count: item._count.useCase,
      avgRating: Math.round((item._avg.rating || 0) * 100) / 100,
      percentage: Math.round((item._count.useCase / basicStats._count.rating) * 100)
    }))

    // Format buyer type breakdown
    const formattedBuyerTypeBreakdown = buyerTypeBreakdown.map(item => ({
      buyerType: item.buyerType,
      count: item._count.buyerType,
      avgRating: Math.round((item._avg.rating || 0) * 100) / 100,
      percentage: Math.round((item._count.buyerType / basicStats._count.rating) * 100)
    }))

    // Format workload size breakdown
    const formattedWorkloadSizeBreakdown = workloadSizeBreakdown.map(item => ({
      workloadSize: item.workloadSize,
      count: item._count.workloadSize,
      avgRating: Math.round((item._avg.rating || 0) * 100) / 100,
      percentage: Math.round((item._count.workloadSize / basicStats._count.rating) * 100)
    }))

    // Calculate metrics with non-null counts
    const metricsWithCounts = {
      successRate: {
        avg: Math.round((metricsAverages._avg.successRate || 0) * 100) / 100,
        count: metricsAverages._count.successRate
      },
      avgLatencyMs: {
        avg: Math.round(metricsAverages._avg.avgLatencyMs || 0),
        count: metricsAverages._count.avgLatencyMs
      },
      costEfficiency: {
        avg: Math.round((metricsAverages._avg.costEfficiency || 0) * 100) / 100,
        count: metricsAverages._count.costEfficiency
      },
      easeOfIntegration: {
        avg: Math.round((metricsAverages._avg.easeOfIntegration || 0) * 100) / 100,
        count: metricsAverages._count.easeOfIntegration
      },
      documentationQuality: {
        avg: Math.round((metricsAverages._avg.documentationQuality || 0) * 100) / 100,
        count: metricsAverages._count.documentationQuality
      },
      supportQuality: {
        avg: Math.round((metricsAverages._avg.supportQuality || 0) * 100) / 100,
        count: metricsAverages._count.supportQuality
      }
    }

    return NextResponse.json({
      summary: {
        totalReviews: basicStats._count.rating,
        avgRating: Math.round((basicStats._avg.rating || 0) * 100) / 100,
        minRating: basicStats._min.rating,
        maxRating: basicStats._max.rating
      },
      ratingDistribution: formattedRatingDistribution,
      metrics: metricsWithCounts,
      breakdowns: {
        useCases: formattedUseCaseBreakdown,
        buyerTypes: formattedBuyerTypeBreakdown,
        workloadSizes: formattedWorkloadSizeBreakdown
      },
      verification: verificationStats.map(item => ({
        isVerifiedPurchase: item.isVerifiedPurchase,
        isVerifiedUsage: item.isVerifiedUsage,
        count: item._count.id,
        avgRating: Math.round((item._avg.rating || 0) * 100) / 100
      })),
      engagement: {
        totalHelpful: engagementStats._sum.helpfulCount || 0,
        totalUnhelpful: engagementStats._sum.unhelpfulCount || 0,
        avgHelpfulPerReview: Math.round((engagementStats._avg.helpfulCount || 0) * 100) / 100,
        avgUnhelpfulPerReview: Math.round((engagementStats._avg.unhelpfulCount || 0) * 100) / 100
      },
      timeSeries: timeSeriesData.map((item: any) => ({
        date: item.date,
        count: parseInt(item.count),
        avgRating: Math.round((parseFloat(item.avg_rating) || 0) * 100) / 100
      }))
    })
  } catch (error) {
    console.error('Error fetching experience stats:', error)
    return NextResponse.json(
      { error: 'Failed to fetch experience statistics' },
      { status: 500 }
    )
  }
}