import { NextRequest, NextResponse } from 'next/server'
import { x402, X402PaymentVerification } from '@/lib/x402'

export async function GET(request: NextRequest) {
  try {
    // Get X-PAYMENT header
    const paymentHeader = request.headers.get('X-PAYMENT')

    if (!paymentHeader) {
      // Return 402 with payment requirements
      return NextResponse.json(
        {
          error: 'Payment required',
          message: 'This resource requires payment via x402 protocol',
          code: 'PAYMENT_REQUIRED'
        },
        { 
          status: 402,
          headers: {
            'Content-Type': 'application/json'
          }
        }
      )
    }

    // Extract payment ID from header
    const paymentId = typeof paymentHeader === 'string' ? paymentHeader : null

    if (!paymentId) {
      return NextResponse.json(
        { error: 'Invalid payment header' },
        { status: 400 }
      )
    }

    // Verify payment with facilitator - for now, we'll simulate verification
    let verification: X402PaymentVerification
    try {
      // Simulate verification - replace with actual facilitator verification
      verification = {
        success: true,
        paymentId,
        transactionHash: `0x${Math.random().toString(16).substring(2, 66)}`,
        amount: '0', // Would be populated from verification
        currency: 'USDC',
        network: 'base',
        timestamp: new Date().toISOString()
      }
    } catch (error) {
      console.error('Payment verification failed:', error)
      return NextResponse.json(
        { error: 'Payment verification failed' },
        { status: 402 }
      )
    }

    if (!verification.success) {
      return NextResponse.json(
        { 
          error: 'Invalid or expired payment',
          code: 'PAYMENT_INVALID'
        },
        { status: 402 }
      )
    }

    // Payment is valid - return success response
    // In a real implementation, this would return the actual resource
    return NextResponse.json({
      success: true,
      message: 'Payment verified - access granted',
      payment: {
        paymentId: verification.paymentId,
        transactionHash: verification.transactionHash,
        amount: verification.amount,
        currency: verification.currency,
        network: verification.network,
        timestamp: verification.timestamp
      },
      // Placeholder for actual resource data
      resource: {
        type: 'api_access',
        permissions: ['read', 'write'],
        expiresAt: null // Or set expiry based on payment type
      }
    })
  } catch (error) {
    console.error('Error in x402 middleware:', error)
    return NextResponse.json(
      { error: 'Internal server error' },
      { status: 500 }
    )
  }
}