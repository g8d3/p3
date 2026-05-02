import { NextRequest, NextResponse } from 'next/server'
import { prisma } from '@/lib/prisma'
import { auth } from '@/lib/auth'

export async function POST(
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
        { error: 'Authentication required' },
        { status: 401 }
      )
    }
    
    const userId = session.user.id
    
    if (!userId) {
      return NextResponse.json(
        { error: 'Authentication required' },
        { status: 401 }
      )
    }

    // Check if experience exists
    const experience = await prisma.experience.findUnique({
      where: { id },
      select: { id: true, helpfulCount: true }
    })
    
    if (!experience) {
      return NextResponse.json(
        { error: 'Experience not found' },
        { status: 404 }
      )
    }

    // TODO: Implement proper tracking of helpful votes to prevent duplicate votes
    // For now, we'll just increment the counter
    // In a real implementation, you'd have a separate table to track who voted
    
    const updatedExperience = await prisma.experience.update({
      where: { id },
      data: {
        helpfulCount: {
          increment: 1
        }
      },
      select: {
        id: true,
        helpfulCount: true,
        unhelpfulCount: true
      }
    })

    return NextResponse.json({
      message: 'Marked as helpful',
      helpfulCount: updatedExperience.helpfulCount,
      unhelpfulCount: updatedExperience.unhelpfulCount
    })
  } catch (error) {
    console.error('Error marking experience as helpful:', error)
    return NextResponse.json(
      { error: 'Failed to mark as helpful' },
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
        { error: 'Authentication required' },
        { status: 401 }
      )
    }
    
    const userId = session.user.id
    
    if (!userId) {
      return NextResponse.json(
        { error: 'Authentication required' },
        { status: 401 }
      )
    }

    // Check if experience exists
    const experience = await prisma.experience.findUnique({
      where: { id },
      select: { id: true, helpfulCount: true }
    })
    
    if (!experience) {
      return NextResponse.json(
        { error: 'Experience not found' },
        { status: 404 }
      )
    }

    // TODO: Implement proper tracking of helpful votes to prevent duplicate votes
    // For now, we'll just decrement the counter if it's greater than 0
    // In a real implementation, you'd check if the user actually voted first
    
    const updatedExperience = await prisma.experience.update({
      where: { id },
      data: {
        helpfulCount: {
          decrement: experience.helpfulCount > 0 ? 1 : 0
        }
      },
      select: {
        id: true,
        helpfulCount: true,
        unhelpfulCount: true
      }
    })

    return NextResponse.json({
      message: 'Helpful mark removed',
      helpfulCount: updatedExperience.helpfulCount,
      unhelpfulCount: updatedExperience.unhelpfulCount
    })
  } catch (error) {
    console.error('Error removing helpful mark:', error)
    return NextResponse.json(
      { error: 'Failed to remove helpful mark' },
      { status: 500 }
    )
  }
}