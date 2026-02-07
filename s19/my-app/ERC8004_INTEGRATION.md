# ERC-8004 Trust Layer Integration

This document describes the ERC-8004 trust layer integration for the AI agent skills marketplace.

## Overview

ERC-8004 provides three registries for trustless agents:
1. **Identity Registry (ERC-721)** - Agent identity tokens
2. **Reputation Registry** - Feedback and ratings  
3. **Validation Registry** - Task validation and dispute resolution

## Files Created

### 1. lib/contracts/erc8004-abis.ts
Contains contract ABIs for all ERC-8004 registries and escrow contracts.

### 2. lib/erc8004.ts
Main library with helper functions:
- `registerAgentIdentity()` - Register new agent
- `getAgentReputation()` - Query reputation score
- `validateTask()` - Submit task validation
- `getIdentityMetadata()` - Get agent metadata URI
- `createEscrow()` - Create payment escrow
- `releaseEscrow()` - Release escrow funds

### 3. API Routes

#### /api/erc8004/identity
- **POST**: Register agent identity
  - Body: `{ metadataURI, walletAddress, chainId? }`
  - Response: `{ tokenId, transactionHash }`

- **GET**: Get identity information
  - Query: `address` OR `tokenId`, optional `chainId`
  - Response: `{ tokenId, metadataURI, owner, reputation }`

#### /api/erc8004/reputation  
- **GET**: Get reputation for agent
  - Query: `agentId`, optional `includeFeedbacks`, `chainId`
  - Response: `{ reputationScore, totalFeedbacks, feedbacks? }`

- **POST**: Submit reputation feedback
  - Body: `{ agentId, rating, feedback, chainId? }`
  - Response: `{ transactionHash, blockNumber }`

#### /api/payments/erc8004/initiate
- **POST**: Initiate escrow payment
  - Body: `{ skillId, buyerAddress, amount, chainId? }`
  - Response: `{ purchase, escrow, nextSteps }`

#### /api/payments/erc8004/confirm
- **POST**: Confirm escrow release or dispute
  - Body: `{ purchaseId, action, signature, chainId?, evidence? }`
  - Response: `{ purchase, transaction, escrowDetails }`

### 4. components/erc8004/agent-trust-badge.tsx
React component to display agent's ERC-8004 identity and reputation:
- Shows verification status
- Displays reputation score with color coding
- Provides detailed information on hover
- Links to blockchain explorer

## Configuration

### Environment Variables

```env
ERC8004_PRIVATE_KEY=0x...  # Private key for server-side transactions
```

### Contract Addresses

The contracts use mock addresses. Update these in `lib/erc8004.ts`:

```typescript
export const ERC8004_ADDRESSES = {
  mainnet: {
    identityRegistry: '0x...', // Actual deployed address
    reputationRegistry: '0x...',
    validationRegistry: '0x...',
    escrowContract: '0x...'
  },
  base: { ... },
  testnet: { ... }
};
```

## Usage Examples

### Register an Agent

```javascript
const response = await fetch('/api/erc8004/identity', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    metadataURI: 'https://api.example.com/agents/1',
    walletAddress: '0x742d35Cc6634C0532925a3b8D4E7E0E4e4e4e4e4',
    chainId: 1 // Ethereum mainnet
  })
});
```

### Get Agent Reputation

```javascript
const response = await fetch('/api/erc8004/reputation?agentId=123&includeFeedbacks=true');
const data = await response.json();
// { reputationScore: "85", totalFeedbacks: "12", feedbacks: [...] }
```

### Initiate Escrow Payment

```javascript
const response = await fetch('/api/payments/erc8004/initiate', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    skillId: '456',
    buyerAddress: '0x...',
    amount: '0.5',
    chainId: 1
  })
});
```

### Use Trust Badge Component

```jsx
import AgentTrustBadge from '@/components/erc8004/agent-trust-badge';

// Display by wallet address
<AgentTrustBadge agentAddress="0x..." showDetails={true} />

// Display by token ID
<AgentTrustBadge tokenId="123" chainId={8453} /> // Base network
```

## Database Integration

The current implementation uses mock data. To integrate with your database:

1. Uncomment Prisma imports in API routes
2. Replace mock operations with actual database queries
3. Update User, Skill, and Purchase models with ERC8004 fields:

```prisma
model User {
  id          String @id @default(cuid())
  address     String @unique
  erc8004Id   String? // ERC-8004 identity token ID
  reputation  Int     @default(0)
  createdAt   DateTime @default(now())
  updatedAt   DateTime @updatedAt
}

model Skill {
  id                String @id @default(cuid())
  name              String
  ownerAddress      String
  erc8004EscrowContract String? // Escrow contract address for this skill
  price             Float
  createdAt         DateTime @default(now())
  updatedAt         DateTime @updatedAt
}

model Purchase {
  id             String @id @default(cuid())
  skillId        String
  buyerAddress   String
  sellerAddress  String
  amount         Float
  erc8004EscrowId String  // Escrow transaction ID
  status         String   // PENDING, COMPLETED, DISPUTED, REFUNDED
  createdAt      DateTime @default(now())
  updatedAt      DateTime @updatedAt
}
```

## Security Considerations

1. **Signature Verification**: API routes verify signatures to ensure authorized actions
2. **Input Validation**: All inputs are validated before processing
3. **Rate Limiting**: Consider implementing rate limiting on API endpoints
4. **Private Key Security**: Server private key should be securely stored
5. **Smart Contract Audits**: Ensure deployed contracts are audited

## Testing

To test the integration:

1. Use the testnet contract addresses
2. Create test agents and verify identity registration
3. Test reputation feedback system
4. Verify escrow creation and release flows
5. Test dispute resolution process

## Deployment

1. Set `ERC8004_PRIVATE_KEY` environment variable
2. Update contract addresses to production values
3. Configure proper monitoring and logging
4. Set up blockchain indexing for historical data