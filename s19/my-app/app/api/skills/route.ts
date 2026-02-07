import { NextRequest, NextResponse } from 'next/server'
import { prisma } from '@/lib/prisma'
import { auth } from '@/lib/auth'
import { z } from 'zod'
import slugify from 'slugify'

// Query schema for filtering
const querySchema = z.object({
  category: z.enum(['DATA_PROCESSING', 'NLP', 'VISION', 'AUTOMATION', 'ANALYTICS', 'COMMUNICATION', 'CREATIVE', 'RESEARCH', 'DEV_TOOLS', 'FINANCE', 'OTHER']).optional(),
  tags: z.string().optional(),
  minRating: z.coerce.number().min(0).max(5).optional(),
  maxPrice: z.coerce.number().min(0).optional(),
  integrationType: z.enum(['API', 'MCP', 'WEBSOCKET', 'SDK', 'WEBHOOK', 'GRAPHQL', 'LIBRARY']).optional(),
  sortBy: z.enum(['name', 'price', 'avgRating', 'totalUses', 'createdAt']).default('createdAt'),
  sortOrder: z.enum(['asc', 'desc']).default('desc'),
  page: z.coerce.number().min(1).default(1),
  limit: z.coerce.number().min(1).max(100).default(20),
})

// Create skill schema
const createSkillSchema = z.object({
  name: z.string().min(1).max(100),
  description: z.string().min(1).max(5000),
  shortDesc: z.string().min(1).max(200),
  category: z.enum(['DATA_PROCESSING', 'NLP', 'VISION', 'AUTOMATION', 'ANALYTICS', 'COMMUNICATION', 'CREATIVE', 'RESEARCH', 'DEV_TOOLS', 'FINANCE', 'OTHER']),
  subcategory: z.string().optional(),
  tags: z.array(z.string()).default([]),
  integrationType: z.enum(['API', 'MCP', 'WEBSOCKET', 'SDK', 'WEBHOOK', 'GRAPHQL', 'LIBRARY']),
  inputSchema: z.any().optional(),
  outputSchema: z.any().optional(),
  endpointUrl: z.string().url().optional(),
  documentation: z.string().optional(),
  examples: z.any().optional(),
  pricingType: z.enum(['ONE_TIME', 'SUBSCRIPTION', 'USAGE_BASED', 'FREE']),
  price: z.coerce.number().min(0),
  currency: z.string().default('USD'),
  x402Price: z.string().optional(),
  x402Currency: z.string().optional(),
  x402Network: z.string().optional(),
  x402Recipient: z.string().optional(),
  erc8004EscrowContract: z.string().optional(),
  version: z.string().default('1.0.0'),
})

export async function GET(request: NextRequest) {
  try {
    const { searchParams } = new URL(request.url)
    const query = querySchema.parse(Object.fromEntries(searchParams))
    
    const where: any = {
      isPublished: true,
    }
    
    // Apply filters
    if (query.category) {
      where.category = query.category
    }
    
    if (query.tags) {
      const tagArray = query.tags.split(',').map(tag => tag.trim())
      where.tags = {
        hasSome: tagArray
      }
    }
    
    if (query.minRating) {
      where.avgRating = {
        gte: query.minRating
      }
    }
    
    if (query.maxPrice) {
      where.price = {
        lte: query.maxPrice
      }
    }
    
    if (query.integrationType) {
      where.integrationType = query.integrationType
    }
    
    // Calculate pagination
    const skip = (query.page - 1) * query.limit
    
    // Get skills with seller info
    const [skills, total] = await Promise.all([
      prisma.skill.findMany({
        where,
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
        },
        orderBy: {
          [query.sortBy]: query.sortOrder
        },
        skip,
        take: query.limit,
      }),
      prisma.skill.count({ where })
    ])
    
    return NextResponse.json({
      skills,
      pagination: {
        page: query.page,
        limit: query.limit,
        total,
        pages: Math.ceil(total / query.limit),
      }
    })
  } catch (error) {
    console.error('Error fetching skills:', error)
    return NextResponse.json(
      { error: 'Failed to fetch skills' },
      { status: 500 }
    )
  }
}

export async function POST(request: NextRequest) {
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
    
    const body = await request.json()
    const validatedData = createSkillSchema.parse(body)
    
    // Generate slug from name
    const slug = slugify(validatedData.name, {
      lower: true,
      strict: true,
    })
    
    // Check if slug already exists
    const existingSkill = await prisma.skill.findUnique({
      where: { slug }
    })
    
    if (existingSkill) {
      return NextResponse.json(
        { error: 'Skill with this name already exists' },
        { status: 409 }
      )
    }
    
    const skill = await prisma.skill.create({
      data: {
        ...validatedData,
        slug,
        sellerId: session.user.id,
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
          }
        }
      }
    })
    
    return NextResponse.json(skill, { status: 201 })
  } catch (error) {
    console.error('Error creating skill:', error)
    return NextResponse.json(
      { error: 'Failed to create skill' },
      { status: 500 }
    )
  }
}