import { NextRequest, NextResponse } from 'next/server';
import { getAgentReputation, getContractAddresses, createClients } from '@/lib/erc8004';
import { REPUTATION_REGISTRY_ABI } from '@/lib/contracts/erc8004-abis';
import { mainnet, base } from 'viem/chains';

// Default to mainnet if no chain specified
const DEFAULT_CHAIN_ID = mainnet.id;

export async function GET(request: NextRequest) {
  try {
    const { searchParams } = new URL(request.url);
    const agentId = searchParams.get('agentId');
    const chainId = parseInt(searchParams.get('chainId') || DEFAULT_CHAIN_ID.toString());

    if (!agentId) {
      return NextResponse.json(
        { error: 'agentId is required' },
        { status: 400 }
      );
    }

    if (!agentId.match(/^\d+$/)) {
      return NextResponse.json(
        { error: 'agentId must be a valid integer' },
        { status: 400 }
      );
    }

    const reputationData = await getAgentReputation(chainId, agentId);

    // Get detailed feedbacks if requested
    const includeFeedbacks = searchParams.get('includeFeedbacks') === 'true';
    let feedbacks = [];

    if (includeFeedbacks) {
      const { publicClient } = createClients(chainId);
      const addresses = getContractAddresses(chainId);
      const totalFeedbacks = parseInt(reputationData.totalFeedbacks);

      // Get up to 10 most recent feedbacks
      const feedbackCount = Math.min(totalFeedbacks, 10);
      
      for (let i = 0; i < feedbackCount; i++) {
        try {
          const feedback = await publicClient.readContract({
            address: addresses.reputationRegistry as `0x${string}`,
            abi: REPUTATION_REGISTRY_ABI,
            functionName: 'getFeedback',
            args: [BigInt(agentId), BigInt(i)]
          }) as [number, string, bigint];

          const [rating, feedbackText, timestamp] = feedback;
          
          feedbacks.push({
            rating,
            feedback: feedbackText,
            timestamp: timestamp.toString(),
            date: new Date(parseInt(timestamp.toString()) * 1000).toISOString()
          });
        } catch (error) {
          console.error(`Error fetching feedback ${i} for agent ${agentId}:`, error);
          // Continue with other feedbacks even if one fails
        }
      }
    }

    return NextResponse.json({
      success: true,
      agentId,
      reputationScore: reputationData.score,
      totalFeedbacks: reputationData.totalFeedbacks,
      feedbacks: includeFeedbacks ? feedbacks : undefined,
      chainId
    });
  } catch (error) {
    console.error('Error in GET /api/erc8004/reputation:', error);
    
    const errorMessage = error instanceof Error ? error.message : 'Unknown error occurred';
    
    return NextResponse.json(
      { 
        error: 'Failed to get reputation information',
        details: errorMessage 
      },
      { status: 500 }
    );
  }
}

export async function POST(request: NextRequest) {
  try {
    const body = await request.json();
    const agentId = body.agentId as string;
    const rating = body.rating as number;
    const feedback = body.feedback as string;
    const chainId = (body.chainId as number | undefined) ?? DEFAULT_CHAIN_ID;

    if (!agentId || rating === undefined || feedback === undefined) {
      return NextResponse.json(
        { error: 'agentId, rating, and feedback are required' },
        { status: 400 }
      );
    }

    // Validate inputs
    if (!agentId.match(/^\d+$/)) {
      return NextResponse.json(
        { error: 'agentId must be a valid integer' },
        { status: 400 }
      );
    }

    if (typeof rating !== 'number' || rating < 1 || rating > 5) {
      return NextResponse.json(
        { error: 'rating must be a number between 1 and 5' },
        { status: 400 }
      );
    }

    if (typeof feedback !== 'string' || feedback.length === 0 || feedback.length > 1000) {
      return NextResponse.json(
        { error: 'feedback must be a non-empty string with max 1000 characters' },
        { status: 400 }
      );
    }

    const { publicClient, walletClient } = createClients(chainId);
    const addresses = getContractAddresses(chainId);

    if (!walletClient) {
      return NextResponse.json(
        { error: 'Wallet client not configured for transaction submission' },
        { status: 500 }
      );
    }

    // Submit feedback to the reputation registry
    const { request } = await publicClient.simulateContract({
      address: addresses.reputationRegistry as `0x${string}`,
      abi: REPUTATION_REGISTRY_ABI,
      functionName: 'submitFeedback',
      args: [BigInt(agentId), rating, feedback],
      account: walletClient.account!
    });

    const transactionHash = await walletClient.writeContract(request);

    // Wait for transaction confirmation
    const receipt = await publicClient.waitForTransactionReceipt({ 
      hash: transactionHash 
    });

    return NextResponse.json({
      success: true,
      agentId,
      rating,
      feedback,
      transactionHash,
      blockNumber: receipt.blockNumber.toString(),
      chainId
    });
  } catch (error) {
    console.error('Error in POST /api/erc8004/reputation:', error);
    
    const errorMessage = error instanceof Error ? error.message : 'Unknown error occurred';
    
    return NextResponse.json(
      { 
        error: 'Failed to submit reputation feedback',
        details: errorMessage 
      },
      { status: 500 }
    );
  }
}