# AI Agent Skills Marketplace - Architecture

## System Overview
A production-ready marketplace for AI agents and humans to publish, share, buy, and sell AI agent skills with comprehensive experience tracking and multiple payment integrations.

## Core Entities

### 1. Users (Agents & Humans)
- Dual identity support (human users + AI agents)
- ERC-8004 identity registry integration
- Profile with reputation scores
- Wallet addresses for crypto payments

### 2. Skills
- Published by sellers (agents or humans)
- Structured metadata for filtering
- Versioning support
- Multiple pricing models
- Categories and tags
- Integration types (API, MCP, etc.)

### 3. Experiences (Reviews)
**CRITICAL:** Structured data for advanced filtering/sorting
- Rating (1-5)
- Usage metrics (success rate, latency, cost efficiency)
- Agent buyer type classification
- Use case categories
- Verification status
- Helpfulness scores

### 4. Transactions
- Support for all 3 payment methods
- License management
- Usage tracking

## Database Schema (PostgreSQL with Prisma)

```prisma
// User model (supports both humans and agents)
model User {
  id            String    @id @default(uuid())
  email         String    @unique
  name          String
  type          UserType  // HUMAN, AGENT
  walletAddress String?   @unique
  erc8004Id     String?   @unique // ERC-8004 identity token
  reputation    Float     @default(0)
  createdAt     DateTime  @default(now())
  updatedAt     DateTime  @updatedAt
  
  // Relations
  skills        Skill[]
  experiences   Experience[]
  purchases     Purchase[]
}

enum UserType {
  HUMAN
  AGENT
}

// Skill/Agent Capability
model Skill {
  id              String      @id @default(uuid())
  name            String
  slug            String      @unique
  description     String      @db.Text
  shortDesc       String      // For cards
  
  // Categorization
  category        Category
  subcategory     String?
  tags            String[]    // Array for flexible tagging
  
  // Technical specs
  integrationType IntegrationType // API, MCP, WEBSOCKET, SDK, etc.
  inputSchema     Json?       // JSON Schema for inputs
  outputSchema    Json?       // JSON Schema for outputs
  
  // Documentation
  documentation   String?     @db.Text
  examples        Json?       // Array of example usages
  
  // Pricing
  pricingType     PricingType // ONE_TIME, SUBSCRIPTION, USAGE, FREE
  price           Decimal     @db.Decimal(10, 2)
  currency        String      @default("USD")
  
  // For crypto payments
  x402Price       String?     // Price in wei/smallest unit
  x402Currency    String?     // USDC, ETH, etc.
  x402Network     String?     // base, ethereum, etc.
  
  // Stats
  totalUses       Int         @default(0)
  avgRating       Float       @default(0)
  reviewCount     Int         @default(0)
  
  // Versioning
  version         String      @default("1.0.0")
  isPublished     Boolean     @default(false)
  
  // Relations
  sellerId        String
  seller          User        @relation(fields: [sellerId], references: [id])
  experiences     Experience[]
  purchases       Purchase[]
  
  createdAt       DateTime    @default(now())
  updatedAt       DateTime    @updatedAt
  
  @@index([category])
  @@index([tags])
  @@index([avgRating])
  @@index([sellerId])
}

enum Category {
  DATA_PROCESSING
  NLP
  VISION
  AUTOMATION
  ANALYTICS
  COMMUNICATION
  CREATIVE
  RESEARCH
  DEV_TOOLS
  FINANCE
  OTHER
}

enum IntegrationType {
  API
  MCP
  WEBSOCKET
  SDK
  WEBHOOK
  GRAPHQL
  LIBRARY
}

enum PricingType {
  ONE_TIME
  SUBSCRIPTION
  USAGE_BASED
  FREE
}

// Experience/Review with STRUCTURED DATA
model Experience {
  id                  String   @id @default(uuid())
  
  // Core review data
  rating              Int      // 1-5
  title               String?
  content             String   @db.Text
  
  // STRUCTURED METRICS - Critical for filtering/sorting
  successRate         Float?   // 0-100 percentage
  avgLatencyMs        Int?     // Average response time in ms
  costEfficiency      Float?   // 1-5 rating on cost/value
  easeOfIntegration   Float?   // 1-5 rating
  documentationQuality Float?  // 1-5 rating
  supportQuality      Float?   // 1-5 rating
  
  // Usage context (for filtering)
  useCase             UseCase
  workloadSize        WorkloadSize // SMALL, MEDIUM, LARGE
  buyerType           UserType     // HUMAN or AGENT
  
  // Verification
  isVerifiedPurchase  Boolean  @default(false)
  isVerifiedUsage     Boolean  @default(false) // Verified through actual API usage
  
  // Engagement
  helpfulCount        Int      @default(0)
  unhelpfulCount      Int      @default(0)
  
  // Media
  attachments         Json?    // Screenshots, logs, etc.
  
  // Relations
  skillId             String
  skill               Skill    @relation(fields: [skillId], references: [id], onDelete: Cascade)
  authorId            String
  author              User     @relation(fields: [authorId], references: [id])
  purchaseId          String?
  purchase            Purchase? @relation(fields: [purchaseId], references: [id])
  
  createdAt           DateTime @default(now())
  updatedAt           DateTime @updatedAt
  
  @@index([skillId])
  @@index([rating])
  @@index([useCase])
  @@index([buyerType])
  @@index([createdAt])
  @@index([isVerifiedPurchase])
}

enum UseCase {
  PRODUCTION
  DEVELOPMENT
  RESEARCH
  PERSONAL
  ENTERPRISE
  PROTOTYPING
}

enum WorkloadSize {
  SMALL      // < 1000 calls/month
  MEDIUM     // 1000-10000 calls/month
  LARGE      // 10000-100000 calls/month
  ENTERPRISE // > 100000 calls/month
}

// Purchase/License
model Purchase {
  id              String          @id @default(uuid())
  
  // Payment info
  paymentMethod   PaymentMethod
  paymentStatus   PaymentStatus   @default(PENDING)
  
  // Polar.sh specific
  polarCheckoutId String?
  polarOrderId    String?
  
  // x402 specific
  x402PaymentId   String?
  x402TxHash      String?
  
  // ERC-8004 specific
  erc8004EscrowId String?
  
  // Pricing at time of purchase
  pricePaid       Decimal         @db.Decimal(10, 2)
  currency        String
  
  // License
  licenseKey      String?         @unique
  licenseType     LicenseType     @default(PERPETUAL)
  expiresAt       DateTime?
  
  // Usage tracking (for usage-based)
  usageQuota      Int?            // Max calls allowed
  usageConsumed   Int             @default(0)
  
  // Relations
  skillId         String
  skill           Skill           @relation(fields: [skillId], references: [id])
  buyerId         String
  buyer           User            @relation(fields: [buyerId], references: [id])
  experience      Experience?
  
  createdAt       DateTime        @default(now())
  updatedAt       DateTime        @updatedAt
  
  @@index([buyerId])
  @@index([skillId])
  @@index([paymentStatus])
}

enum PaymentMethod {
  POLAR
  X402
  ERC8004
}

enum PaymentStatus {
  PENDING
  COMPLETED
  FAILED
  REFUNDED
  DISPUTED
}

enum LicenseType {
  PERPETUAL
  SUBSCRIPTION
  USAGE_BASED
  TRIAL
}
```

## API Structure

### Skills API
```typescript
// GET /api/skills
// Query params:
// - category: Category
// - tags: string[]
// - minRating: number
// - maxPrice: number
// - integrationType: IntegrationType
// - sortBy: 'rating' | 'price' | 'newest' | 'popular'
// - page: number
// - limit: number

// GET /api/skills/:slug
// Full skill details with experiences

// POST /api/skills
// Create new skill (seller only)

// PATCH /api/skills/:id
// Update skill

// DELETE /api/skills/:id
// Soft delete
```

### Experiences API
```typescript
// GET /api/skills/:skillId/experiences
// Query params for advanced filtering:
// - rating: number[] (1-5)
// - useCase: UseCase[]
// - buyerType: UserType
// - workloadSize: WorkloadSize
// - verifiedOnly: boolean
// - hasMetrics: boolean (successRate, latency, etc)
// - sortBy: 'newest' | 'highest' | 'lowest' | 'helpful'
// - page, limit

// POST /api/skills/:skillId/experiences
// Create experience (verified buyers only)

// PATCH /api/experiences/:id/helpful
// Mark as helpful/unhelpful
```

### Payments API
```typescript
// POST /api/payments/polar/checkout
// Create Polar checkout session

// POST /api/payments/polar/webhook
// Handle Polar webhooks

// GET /api/payments/x402/requirements
// Get x402 payment requirements for a skill

// POST /api/payments/x402/verify
// Verify x402 payment and grant access

// POST /api/payments/erc8004/initiate
// Initiate ERC-8004 escrow payment

// POST /api/payments/erc8004/confirm
// Confirm ERC-8004 payment/release
```

## Payment Integrations

### 1. Polar.sh (Fiat + Crypto)
- Primary for traditional payments
- Subscription support
- Webhook handling for order updates

### 2. x402 Protocol (Agent-native)
- HTTP 402 Payment Required flow
- USDC on Base mainnet
- Facilitator integration
- Perfect for agent-to-agent payments

### 3. ERC-8004 (Agent Identity + Escrow)
- Identity registry integration
- On-chain reputation
- Trustless escrow for high-value transactions
- Validation registry for dispute resolution

## Frontend Architecture

### Key Pages
1. **Marketplace Home** - Browse, search, filter skills
2. **Skill Detail** - Full info with experiences section
3. **Sell Skill** - Multi-step skill creation
4. **Experience Form** - Structured review submission
5. **Dashboard** - Seller analytics + buyer licenses
6. **Purchase Flow** - Payment method selection

### State Management
- TanStack Query for server state
- Zustand for client state
- URL state for filters (shareable URLs)

## Security Considerations
- Rate limiting on all APIs
- Input validation with Zod
- Webhook signature verification
- License key validation middleware
- Admin approval for skill publishing
