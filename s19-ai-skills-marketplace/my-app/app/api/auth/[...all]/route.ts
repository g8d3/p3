import { auth } from "@/lib/auth"
import { NextRequest, NextResponse } from "next/server"

export async function GET(request: NextRequest) {
  const response = await auth.handler(request)
  return response
}

export async function POST(request: NextRequest) {
  const response = await auth.handler(request)
  return response
}
