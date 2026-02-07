import { NextRequest, NextResponse } from 'next/server';
import { releaseEscrow, validateTask, getEscrowDetails } from '@/lib/erc8004';
import { mainnet, base } from 'viem/chains';
import { verifyMessage } from 'viem';

// Default to mainnet if no chain specified
const DEFAULT_CHAIN_ID = mainnet.id;

export async function POST(request: NextRequest) {
  try {
    const { purchaseId, action, signature, chainId = DEFAULT_CHAIN_ID, evidence } = await request.json();

    if (!purchaseId || !action || !signature) {
      return NextResponse.json(
        { error: 'purchaseId, action, and signature are required' },
        { status: 400 }
      );
    }

    // Validate action
    const validActions = ['release', 'dispute', 'refund'];
    if (!validActions.includes(action)) {
      return NextResponse.json(
        { error: `action must be one of: ${validActions.join(', ')}` },
        { status: 400 }
      );
    }

    // Validate purchase ID
    if (!purchaseId.match(/^\d+$/)) {
      return NextResponse.json(
        { error: 'purchaseId must be a valid integer' },
        { status: 400 }
      );
    }

    // Validate signature format
    if (!signature.match(/^0x[a-fA-F0-9]{130}$/)) {
      return NextResponse.json(
        { error: 'Invalid signature format' },
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

    // In a real implementation, you would:
    // 1. Get the purchase record from your database
    // 2. Verify the signature belongs to the buyer or seller
    // 3. Check current status and permissions
    // For this example, we'll use mock data
    
    // Mock purchase record
    const mockPurchase = {
      id: parseInt(purchaseId),
      skillId: 1,
      buyerAddress: "0x742d35Cc6634C0532925a3b8D4E7E0E4e4e4e4e4",
      sellerAddress: "0x8765432109876543210987654321098765432109",
      amount: "0.1",
      erc8004EscrowId: "12345",
      status: 'PENDING',
      createdAt: new Date().toISOString(),
      updatedAt: new Date().toISOString()
    };

    // Verify signature
    const message = JSON.stringify({
      purchaseId,
      action,
      timestamp: Math.floor(Date.now() / 1000)
    });

    // This is a simplified signature verification
    // In production, you'd want to include more details and timestamp
    let recoveredAddress: string | null;
    try {
      recoveredAddress = verifyMessage({
        message,
        signature: signature as `0x${string}`
      });
    } catch (error) {
      return NextResponse.json(
        { error: 'Invalid signature' },
        { status: 400 }
      );
    }

    // Check if signer is authorized (buyer or seller)
    const isBuyer = recoveredAddress?.toLowerCase() === mockPurchase.buyerAddress.toLowerCase();
    const isSeller = recoveredAddress?.toLowerCase() === mockPurchase.sellerAddress.toLowerCase();

    if (!isBuyer && !isSeller) {
      return NextResponse.json(
        { error: 'Signature does not match buyer or seller address' },
        { status: 403 }
      );
    }

    // Get current escrow details
    const escrowDetails = await getEscrowDetails(chainId, mockPurchase.erc8004EscrowId);

    let result;
    let newStatus;

    switch (action) {
      case 'release':
        // Only buyer can release funds (or seller if task is validated)
        if (!isBuyer) {
          return NextResponse.json(
            { error: 'Only buyer can release funds' },
            { status: 403 }
          );
        }

        if (escrowDetails.released) {
          return NextResponse.json(
            { error: 'Escrow already released' },
            { status: 400 }
          );
        }

        result = await releaseEscrow(chainId, mockPurchase.erc8004EscrowId);
        newStatus = 'COMPLETED';
        break;

      case 'dispute':
        // Only buyer can raise dispute
        if (!isBuyer) {
          return NextResponse.json(
            { error: 'Only buyer can raise dispute' },
            { status: 403 }
          );
        }

        if (!evidence) {
          return NextResponse.json(
            { error: 'evidence is required for dispute' },
            { status: 400 }
          );
        }

        result = await validateTask(
          chainId,
          mockPurchase.erc8004EscrowId,
          false, // Mark as invalid (disputed)
          evidence
        );
        newStatus = 'DISPUTED';
        break;

      case 'refund':
        // Only seller can refund or buyer after dispute validation
        if (!isSeller) {
          return NextResponse.json(
            { error: 'Only seller can refund' },
            { status: 403 }
          );
        }

        if (escrowDetails.released) {
          return NextResponse.json(
            { error: 'Cannot refund: escrow already released' },
            { status: 400 }
          );
        }

        // In a real implementation, you'd call refundBuyer function
        // For now, we'll simulate it
        result = { transactionHash: '0xmockrefundhash' };
        newStatus = 'REFUNDED';
        break;

      default:
        return NextResponse.json(
          { error: 'Invalid action' },
          { status: 400 }
        );
    }

    // Update database record
    // await prisma.purchase.update({
    //   where: { id: parseInt(purchaseId) },
    //   data: {
    //     status: newStatus,
    //     updatedAt: new Date()
    //   }
    // });

    const updatedPurchase = {
      ...mockPurchase,
      status: newStatus,
      updatedAt: new Date().toISOString()
    };

    return NextResponse.json({
      success: true,
      purchase: updatedPurchase,
      transaction: {
        hash: result.transactionHash,
        action
      },
      escrowDetails: {
        released: escrowDetails.released,
        amount: escrowDetails.amount,
        deadline: escrowDetails.deadline
      },
      chainId
    });
  } catch (error) {
    console.error('Error in POST /api/payments/erc8004/confirm:', error);
    
    const errorMessage = error instanceof Error ? error.message : 'Unknown error occurred';
    
    return NextResponse.json(
      { 
        error: 'Failed to confirm payment action',
        details: errorMessage 
      },
      { status: 500 }
    );
  }
}