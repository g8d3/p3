'use client';

import { useState, useEffect } from 'react';
import { Badge, CheckCircle, AlertCircle, Star, Shield, ExternalLink } from 'lucide-react';
import { useAccount } from 'wagmi';

interface AgentTrustBadgeProps {
  agentAddress?: string;
  tokenId?: string;
  showDetails?: boolean;
  className?: string;
  chainId?: number;
}

interface TrustData {
  tokenId: string;
  metadataURI: string;
  owner: string;
  reputation: {
    score: string;
    totalFeedbacks: string;
  };
  verified: boolean;
  registrationDate?: string;
}

export default function AgentTrustBadge({
  agentAddress,
  tokenId,
  showDetails = false,
  className = '',
  chainId = 1 // Default to mainnet
}: AgentTrustBadgeProps) {
  const [trustData, setTrustData] = useState<TrustData | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const { address: connectedAddress } = useAccount();

  useEffect(() => {
    const fetchTrustData = async () => {
      if (!agentAddress && !tokenId) return;

      setLoading(true);
      setError(null);

      try {
        const params = new URLSearchParams({
          chainId: chainId.toString()
        });

        if (agentAddress) {
          params.append('address', agentAddress);
        } else {
          params.append('tokenId', tokenId!);
        }

        const response = await fetch(`/api/erc8004/identity?${params}`);
        
        if (!response.ok) {
          throw new Error('Failed to fetch trust data');
        }

        const data = await response.json();
        
        if (data.success) {
          // Determine verification status (this could be enhanced based on your verification logic)
          const verified = parseInt(data.reputation.totalFeedbacks) > 0 && 
                          parseInt(data.reputation.score) > 70;

          setTrustData({
            tokenId: data.tokenId,
            metadataURI: data.metadataURI,
            owner: data.owner,
            reputation: data.reputation,
            verified
          });
        } else {
          setError(data.error || 'Failed to load trust data');
        }
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Unknown error');
      } finally {
        setLoading(false);
      }
    };

    fetchTrustData();
  }, [agentAddress, tokenId, chainId]);

  const getReputationColor = (score: string) => {
    const scoreNum = parseInt(score);
    if (scoreNum >= 90) return 'text-green-600 bg-green-50';
    if (scoreNum >= 70) return 'text-blue-600 bg-blue-50';
    if (scoreNum >= 50) return 'text-yellow-600 bg-yellow-50';
    return 'text-red-600 bg-red-50';
  };

  const getReputationLabel = (score: string) => {
    const scoreNum = parseInt(score);
    if (scoreNum >= 90) return 'Excellent';
    if (scoreNum >= 70) return 'Good';
    if (scoreNum >= 50) return 'Average';
    return 'Poor';
  };

  const formatChainName = (id: number) => {
    switch (id) {
      case 1: return 'Ethereum';
      case 8453: return 'Base';
      case 84532: return 'Base Sepolia';
      default: return 'Unknown';
    }
  };

  if (loading) {
    return (
      <div className={`inline-flex items-center space-x-2 ${className}`}>
        <div className="animate-pulse flex items-center space-x-2">
          <div className="h-4 w-4 bg-gray-200 rounded"></div>
          <div className="h-4 w-20 bg-gray-200 rounded"></div>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className={`inline-flex items-center space-x-2 ${className}`}>
        <AlertCircle className="h-4 w-4 text-red-500" />
        <span className="text-sm text-red-600">Trust data unavailable</span>
      </div>
    );
  }

  if (!trustData) {
    return (
      <div className={`inline-flex items-center space-x-2 ${className}`}>
        <Shield className="h-4 w-4 text-gray-400" />
        <span className="text-sm text-gray-500">No identity registered</span>
      </div>
    );
  }

  const reputationColor = getReputationColor(trustData.reputation.score);
  const reputationLabel = getReputationLabel(trustData.reputation.score);

  return (
    <div className={`inline-flex items-center space-x-2 ${className}`}>
      {/* Verification Badge */}
      {trustData.verified && (
        <div className="flex items-center space-x-1">
          <CheckCircle className="h-4 w-4 text-green-600" />
          <span className="text-xs font-medium text-green-600">Verified</span>
        </div>
      )}

      {/* Reputation Score */}
      <div className={`flex items-center space-x-1 px-2 py-1 rounded-full ${reputationColor}`}>
        <Star className="h-3 w-3 fill-current" />
        <span className="text-xs font-medium">{trustData.reputation.score}</span>
        <span className="text-xs">({reputationLabel})</span>
      </div>

      {/* ERC-8004 Badge */}
      <Badge variant="secondary" className="text-xs">
        ERC-8004
      </Badge>

      {/* Network Badge */}
      <Badge variant="outline" className="text-xs">
        {formatChainName(chainId)}
      </Badge>

      {/* Details Toggle */}
      {showDetails && (
        <div className="group relative">
          <ExternalLink className="h-3 w-3 text-gray-400 cursor-help" />
          
          {/* Tooltip with additional details */}
          <div className="absolute bottom-full right-0 mb-2 hidden w-64 rounded-lg bg-white p-3 text-xs shadow-lg border group-hover:block z-50">
            <div className="space-y-2">
              <div className="flex justify-between">
                <span className="font-medium">Agent ID:</span>
                <span className="font-mono">{trustData.tokenId}</span>
              </div>
              <div className="flex justify-between">
                <span className="font-medium">Total Reviews:</span>
                <span>{trustData.reputation.totalFeedbacks}</span>
              </div>
              <div className="flex justify-between">
                <span className="font-medium">Verified:</span>
                <span>{trustData.verified ? 'Yes' : 'No'}</span>
              </div>
              <div className="flex justify-between">
                <span className="font-medium">Network:</span>
                <span>{formatChainName(chainId)}</span>
              </div>
              
              {/* Link to blockchain explorer */}
              <a
                href={`https://etherscan.io/token/${chainId === 8453 ? '0x5432109876543210987654321098765432109876' : '0x1234567890123456789012345678901234567890'}?a=${trustData.tokenId}`}
                target="_blank"
                rel="noopener noreferrer"
                className="text-blue-600 hover:underline block text-center mt-2 pt-2 border-t"
              >
                View on Explorer
              </a>
            </div>
          </div>
        </div>
      )}

      {/* Show if this is the current user */}
      {connectedAddress && connectedAddress.toLowerCase() === trustData.owner.toLowerCase() && (
        <Badge variant="outline" className="text-xs bg-purple-50 text-purple-600">
          You
        </Badge>
      )}
    </div>
  );
}