import { NextRequest, NextResponse } from 'next/server'
import { prisma } from '@/lib/prisma'

export async function GET(request: NextRequest) {
  try {
    // Get all categories with skill counts
    const categories = await prisma.skill.groupBy({
      by: ['category'],
      where: {
        isPublished: true
      },
      _count: {
        id: true
      }
    })
    
    // Format the response
    const formattedCategories = categories.map((item: any) => ({
      category: item.category,
      count: item._count.id
    }))
    
    // Sort by count (descending) and then by category name
    formattedCategories.sort((a: any, b: any) => {
      if (b.count !== a.count) {
        return b.count - a.count
      }
      return a.category.localeCompare(b.category)
    })
    
    return NextResponse.json({
      categories: formattedCategories,
      total: formattedCategories.reduce((sum: number, cat: any) => sum + cat.count, 0)
    })
  } catch (error) {
    console.error('Error fetching categories:', error)
    return NextResponse.json(
      { error: 'Failed to fetch categories' },
      { status: 500 }
    )
  }
}