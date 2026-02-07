import { createPublicClient, createWalletClient, http, parseEther, formatEther } from 'viem';
import { mainnet, base, baseSepolia } from 'viem/chains';
import { privateKeyToAccount } from 'viem/accounts';
import {
  IDENTITY_REGISTRY_ABI,
  REPUTATION_REGISTRY_ABI,
  VALIDATION_REGISTRY_ABI,
  ESCROW_CONTRACT_ABI
} from './contracts/erc8004-abis';

// Contract addresses (these would be the actual deployed addresses)
export const ERC8004_ADDRESSES = {
  mainnet: {
    identityRegistry: '0x1234567890123456789012345678901234567890',
    reputationRegistry: '0x2345678901234567890123456789012345678901',
    validationRegistry: '0x3456789012345678901234567890123456789012',
    escrowContract: '0x4567890123456789012345678901234567890123'
  },
  base: {
    identityRegistry: '0x5432109876543210987654321098765432109876',
    reputationRegistry: '0x6543210987654321098765432109876543210987',
    validationRegistry: '0x7654321098765432109876543210987654321098',
    escrowContract: '0x8765432109876543210987654321098765432109'
  },
  testnet: {
    identityRegistry: '0x9876543210987654321098765432109876543210',
    reputationRegistry: '0x0987654321098765432109876543210987654321',
    validationRegistry: '0x2109876543210987654321098765432109876543',
    escrowContract: '0x3210987654321098765432109876543210987654'
  }
};

export const SUPPORTED_CHAINS = {
  mainnet,
  base,
  testnet: baseSepolia
};

// Create clients based on network
export function createClients(chainId: number) {
  const chain = Object.values(SUPPORTED_CHAINS).find(c => c.id === chainId) || mainnet;
  
  const publicClient = createPublicClient({
    chain,
    transport: http()
  });

  // Note: In production, you'd use proper wallet integration via wagmi
  // This is for server-side operations with a private key
  const walletClient = process.env.ERC8004_PRIVATE_KEY 
    ? createWalletClient({
        chain,
        transport: http(),
        account: privateKeyToAccount(process.env.ERC8004_PRIVATE_KEY as `0x${string}`)
      })
    : null;

  return { publicClient, walletClient };
}

// Helper function to get contract addresses for a network
export function getContractAddresses(chainId: number) {
  if (chainId === mainnet.id) return ERC8004_ADDRESSES.mainnet;
  if (chainId === base.id) return ERC8004_ADDRESSES.base;
  return ERC8004_ADDRESSES.testnet;
}

// Register a new agent identity
export async function registerAgentIdentity(
  chainId: number,
  metadataURI: string,
  ownerAddress: string
): Promise<{ tokenId: string; transactionHash: string }> {
  const { publicClient, walletClient } = createClients(chainId);
  const addresses = getContractAddresses(chainId);

  if (!walletClient) {
    throw new Error('Wallet client not configured');
  }

    try {
      const { request } = await publicClient.simulateContract({
        address: addresses.identityRegistry as `0x${string}`,
        abi: IDENTITY_REGISTRY_ABI,
        functionName: 'registerIdentity',
        args: [metadataURI, ownerAddress as `0x${string}`],
        account: walletClient.account!
      });

      const hash = await walletClient.writeContract(request);
    
    // Wait for transaction receipt and get token ID from events
    const receipt = await publicClient.waitForTransactionReceipt({ hash });
    
    // Parse logs to get tokenId (this would depend on actual contract event structure)
    let tokenId = '0';
    if (receipt.logs.length > 0) {
      // Assuming the token ID is emitted in an event
      // This would need to be adjusted based on actual contract implementation
      const log = receipt.logs[0];
      tokenId = (log.data || '0').slice(-10); // Simplified extraction
    }

    return { tokenId, transactionHash: hash };
  } catch (error) {
    console.error('Error registering agent identity:', error);
    throw error;
  }
}

// Get agent reputation score
export async function getAgentReputation(
  chainId: number,
  agentId: string
): Promise<{ score: string; totalFeedbacks: string }> {
  const { publicClient } = createClients(chainId);
  const addresses = getContractAddresses(chainId);

  try {
    const [score, totalFeedbacks] = await Promise.all([
      publicClient.readContract({
        address: addresses.reputationRegistry as `0x${string}`,
        abi: REPUTATION_REGISTRY_ABI,
        functionName: 'getReputationScore',
        args: [BigInt(agentId)]
      }) as Promise<bigint>,
      publicClient.readContract({
        address: addresses.reputationRegistry as `0x${string}`,
        abi: REPUTATION_REGISTRY_ABI,
        functionName: 'getTotalFeedbacks',
        args: [BigInt(agentId)]
      }) as Promise<bigint>
    ]);

    return {
      score: score.toString(),
      totalFeedbacks: totalFeedbacks.toString()
    };
  } catch (error) {
    console.error('Error getting agent reputation:', error);
    throw error;
  }
}

// Submit task validation
export async function validateTask(
  chainId: number,
  escrowId: string,
  isValid: boolean,
  evidence: string
): Promise<{ transactionHash: string }> {
  const { publicClient, walletClient } = createClients(chainId);
  const addresses = getContractAddresses(chainId);

  if (!walletClient) {
    throw new Error('Wallet client not configured');
  }

  try {
    const { request } = await publicClient.simulateContract({
      address: addresses.escrowContract as `0x${string}`,
      abi: ESCROW_CONTRACT_ABI,
      functionName: 'releaseFunds',
      args: [BigInt(escrowId)],
      account: walletClient.account!
    });

    const hash = await walletClient.writeContract(request);
    
    return { transactionHash: hash };
  } catch (error) {
    console.error('Error validating task:', error);
    throw error;
  }
}

// Get identity metadata URI
export async function getIdentityMetadata(
  chainId: number,
  tokenId: string
): Promise<{ metadataURI: string; owner: string }> {
  const { publicClient } = createClients(chainId);
  const addresses = getContractAddresses(chainId);

  try {
    const [metadataURI, owner] = await Promise.all([
      publicClient.readContract({
        address: addresses.identityRegistry as `0x${string}`,
        abi: IDENTITY_REGISTRY_ABI,
        functionName: 'tokenURI',
        args: [BigInt(tokenId)]
      }) as Promise<string>,
      publicClient.readContract({
        address: addresses.identityRegistry as `0x${string}`,
        abi: IDENTITY_REGISTRY_ABI,
        functionName: 'ownerOf',
        args: [BigInt(tokenId)]
      }) as Promise<`0x${string}`>
    ]);

    return {
      metadataURI: metadataURI as string,
      owner: owner as string
    };
  } catch (error) {
    console.error('Error getting identity metadata:', error);
    throw error;
  }
}

// Create escrow for payment
export async function createEscrow(
  chainId: number,
  sellerAddress: string,
  amount: string,
  deadline: number
): Promise<{ escrowId: string; transactionHash: string }> {
  const { publicClient, walletClient } = createClients(chainId);
  const addresses = getContractAddresses(chainId);

  if (!walletClient) {
    throw new Error('Wallet client not configured');
  }

  try {
    const amountInWei = parseEther(amount);
    
    const { request } = await publicClient.simulateContract({
      address: addresses.escrowContract as `0x${string}`,
      abi: ESCROW_CONTRACT_ABI,
      functionName: 'createEscrow',
      args: [sellerAddress as `0x${string}`, amountInWei, BigInt(deadline)],
      value: amountInWei,
      account: walletClient.account
    });

    const hash = await walletClient.writeContract(request);
    
    // Wait for transaction receipt and get escrow ID
    const receipt = await publicClient.waitForTransactionReceipt({ hash });
    
    let escrowId = '0';
    if (receipt.logs.length > 0) {
      const log = receipt.logs[0];
      escrowId = (log.data || '0').slice(-10); // Simplified extraction
    }

    return { escrowId, transactionHash: hash };
  } catch (error) {
    console.error('Error creating escrow:', error);
    throw error;
  }
}

// Release escrow funds
export async function releaseEscrow(
  chainId: number,
  escrowId: string
): Promise<{ transactionHash: string }> {
  const { publicClient, walletClient } = createClients(chainId);
  const addresses = getContractAddresses(chainId);

  if (!walletClient) {
    throw new Error('Wallet client not configured');
  }

  try {
    const { request } = await publicClient.simulateContract({
      address: addresses.escrowContract as `0x${string}`,
      abi: ESCROW_CONTRACT_ABI,
      functionName: 'createEscrow',
      args: [sellerAddress as `0x${string}`, amountInWei, BigInt(deadline)],
      value: amountInWei,
      account: walletClient.account!
    });

    const hash = await walletClient.writeContract(request);
    
    return { transactionHash: hash };
  } catch (error) {
    console.error('Error releasing escrow:', error);
    throw error;
  }
}

// Get escrow details
export async function getEscrowDetails(
  chainId: number,
  escrowId: string
): Promise<{
  buyer: string;
  seller: string;
  amount: string;
  deadline: string;
  released: boolean;
}> {
  const { publicClient } = createClients(chainId);
  const addresses = getContractAddresses(chainId);

  try {
    const details = await publicClient.readContract({
      address: addresses.escrowContract as `0x${string}`,
      abi: ESCROW_CONTRACT_ABI,
      functionName: 'getEscrowDetails',
      args: [BigInt(escrowId)]
    }) as [`0x${string}`, `0x${string}`, bigint, bigint, boolean];

    const [buyer, seller, amount, deadline, released] = details as [
      string,
      string,
      bigint,
      bigint,
      boolean
    ];

    return {
      buyer,
      seller,
      amount: formatEther(amount),
      deadline: deadline.toString(),
      released
    };
  } catch (error) {
    console.error('Error getting escrow details:', error);
    throw error;
  }
}