import { NextRequest, NextResponse } from 'next/server'
import { prisma } from '@/lib/prisma'
import { auth } from '@/lib/auth'

export async function POST(
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
        { error: 'Forbidden - Only the seller can publish this skill' },
        { status: 403 }
      )
    }
    
    // Toggle publish status
    const skill = await prisma.skill.update({
      where: { slug: (await params).slug },
      data: {
        isPublished: !existingSkill.isPublished
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
    
    return NextResponse.json({
      skill,
      message: skill.isPublished ? 'Skill published successfully' : 'Skill unpublished successfully'
    })
  } catch (error) {
    console.error('Error toggling publish status:', error)
    return NextResponse.json(
      { error: 'Failed to update publish status' },
      { status: 500 }
    )
  }
}