import { NextRequest, NextResponse } from 'next/server';
import { createEscrow } from '@/lib/erc8004';
import { mainnet, base } from 'viem/chains';

// Default to mainnet if no chain specified
const DEFAULT_CHAIN_ID = mainnet.id;

export async function POST(request: NextRequest) {
  try {
    const { skillId, buyerAddress, amount, chainId = DEFAULT_CHAIN_ID } = await request.json();

    if (!skillId || !buyerAddress || !amount) {
      return NextResponse.json(
        { error: 'skillId, buyerAddress, and amount are required' },
        { status: 400 }
      );
    }

    // Validate inputs
    if (!skillId.match(/^\d+$/)) {
      return NextResponse.json(
        { error: 'skillId must be a valid integer' },
        { status: 400 }
      );
    }

    if (!buyerAddress.match(/^0x[a-fA-F0-9]{40}$/)) {
      return NextResponse.json(
        { error: 'Invalid buyerAddress format' },
        { status: 400 }
      );
    }

    const amountNum = parseFloat(amount);
    if (isNaN(amountNum) || amountNum <= 0) {
      return NextResponse.json(
        { error: 'amount must be a positive number' },
        { status: 400 }
      );
    }

    // Check if amount is within reasonable limits (max 100 ETH)
    if (amountNum > 100) {
      return NextResponse.json(
        { error: 'amount cannot exceed 100 ETH' },
        { status: 400 }
      );
    }

    // Validate chain
    if (![mainnet.id, base.id].includes(chainId)) {
      return NextResponse.json(
        { error: 'Unsupported chain ID' },
        { status: 400 }
      );
    }

    // Set escrow deadline to 30 days from now
    const deadline = Math.floor(Date.now() / 1000) + (30 * 24 * 60 * 60);

    // In a real implementation, you would:
    // 1. Get the skill details from your database to find the seller address
    // 2. Create a purchase record with PENDING status
    // For this example, we'll use a mock seller address
    
    // This would typically come from your skill database
    const mockSellerAddress = "0x742d35Cc6634C0532925a3b8D4E7E0E4e4e4e4e4";
    
    // Create escrow contract
    const escrowResult = await createEscrow(
      chainId,
      mockSellerAddress,
      amount,
      deadline
    );

    // Create database record (this is where you'd use Prisma)
    // const purchase = await prisma.purchase.create({
    //   data: {
    //     skillId: parseInt(skillId),
    //     buyerAddress,
    //     sellerAddress: mockSellerAddress,
    //     amount,
    //     erc8004EscrowId: escrowResult.escrowId,
    //     status: 'PENDING',
    //     createdAt: new Date(),
    //     updatedAt: new Date()
    //   }
    // });

    // Mock purchase record for now
    const mockPurchase = {
      id: Math.floor(Math.random() * 1000000),
      skillId: parseInt(skillId),
      buyerAddress,
      sellerAddress: mockSellerAddress,
      amount,
      erc8004EscrowId: escrowResult.escrowId,
      status: 'PENDING',
      createdAt: new Date().toISOString(),
      updatedAt: new Date().toISOString()
    };

    return NextResponse.json({
      success: true,
      purchase: mockPurchase,
      escrow: {
        escrowId: escrowResult.escrowId,
        transactionHash: escrowResult.transactionHash,
        deadline: deadline.toString(),
        amount
      },
      nextSteps: {
        waitForConfirmation: 'Wait for blockchain confirmation',
        completeTask: 'Once confirmed, the task can be completed',
        releasePayment: 'After task completion, release payment via confirm endpoint'
      },
      chainId
    });
  } catch (error) {
    console.error('Error in POST /api/payments/erc8004/initiate:', error);
    
    const errorMessage = error instanceof Error ? error.message : 'Unknown error occurred';
    
    return NextResponse.json(
      { 
        error: 'Failed to initiate escrow payment',
        details: errorMessage 
      },
      { status: 500 }
    );
  }
}