import { NextRequest, NextResponse } from 'next/server';
import { registerAgentIdentity, getIdentityMetadata, getContractAddresses } from '@/lib/erc8004';
import { IDENTITY_REGISTRY_ABI } from '@/lib/contracts/erc8004-abis';
import { createPublicClient, http } from 'viem';
import { mainnet, base } from 'viem/chains';

// Default to mainnet if no chain specified
const DEFAULT_CHAIN_ID = mainnet.id;

export async function POST(request: NextRequest) {
  try {
    const { metadataURI, walletAddress, chainId = DEFAULT_CHAIN_ID } = await request.json();

    if (!metadataURI || !walletAddress) {
      return NextResponse.json(
        { error: 'metadataURI and walletAddress are required' },
        { status: 400 }
      );
    }

    // Validate addresses
    if (!walletAddress.match(/^0x[a-fA-F0-9]{40}$/)) {
      return NextResponse.json(
        { error: 'Invalid wallet address format' },
        { status: 400 }
      );
    }

    if (!metadataURI.startsWith('http') && !metadataURI.startsWith('ipfs://')) {
      return NextResponse.json(
        { error: 'metadataURI must be a valid HTTP or IPFS URI' },
        { status: 400 }
      );
    }

    const result = await registerAgentIdentity(chainId, metadataURI, walletAddress);

    return NextResponse.json({
      success: true,
      tokenId: result.tokenId,
      transactionHash: result.transactionHash,
      chainId
    });
  } catch (error) {
    console.error('Error in POST /api/erc8004/identity:', error);
    
    const errorMessage = error instanceof Error ? error.message : 'Unknown error occurred';
    
    return NextResponse.json(
      { 
        error: 'Failed to register agent identity',
        details: errorMessage 
      },
      { status: 500 }
    );
  }
}

export async function GET(request: NextRequest) {
  try {
    const { searchParams } = new URL(request.url);
    const address = searchParams.get('address');
    const tokenId = searchParams.get('tokenId');
    const chainId = parseInt(searchParams.get('chainId') || DEFAULT_CHAIN_ID.toString());

    if (!address && !tokenId) {
      return NextResponse.json(
        { error: 'Either address or tokenId must be provided' },
        { status: 400 }
      );
    }

    if (address && !address.match(/^0x[a-fA-F0-9]{40}$/)) {
      return NextResponse.json(
        { error: 'Invalid address format' },
        { status: 400 }
      );
    }

    const chain = chainId === base.id ? base : mainnet;
    const addresses = getContractAddresses(chainId);
    
    const publicClient = createPublicClient({
      chain,
      transport: http()
    });

    let targetTokenId: string;

    if (address) {
      // Get token ID by owner address
      targetTokenId = (await publicClient.readContract({
        address: addresses.identityRegistry as `0x${string}`,
        abi: IDENTITY_REGISTRY_ABI,
        functionName: 'getTokenIdByOwner',
        args: [address as `0x${string}`]
      }) as bigint).toString();
    } else {
      targetTokenId = tokenId!;
    }

    const identityData = await getIdentityMetadata(chainId, targetTokenId);

    // Get additional reputation data
    const { getAgentReputation } = await import('@/lib/erc8004');
    const reputationData = await getAgentReputation(chainId, targetTokenId);

    return NextResponse.json({
      success: true,
      tokenId: targetTokenId,
      metadataURI: identityData.metadataURI,
      owner: identityData.owner,
      reputation: reputationData,
      chainId
    });
  } catch (error) {
    console.error('Error in GET /api/erc8004/identity:', error);
    
    const errorMessage = error instanceof Error ? error.message : 'Unknown error occurred';
    
    return NextResponse.json(
      { 
        error: 'Failed to get identity information',
        details: errorMessage 
      },
      { status: 500 }
    );
  }
}