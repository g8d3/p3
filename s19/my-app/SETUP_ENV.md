# 🔧 Environment Setup Guide for SkillsMarket

This guide helps you set up all required environment variables for local development.

## Quick Start (5 minutes)

```bash
# 1. Copy example file
cp .env.example .env.local

# 2. Generate secrets
openssl rand -base64 32          # For AUTH_SECRET
openssl rand -hex 16              # For LICENSE_SALT

# 3. Edit .env.local and paste generated values
nano .env.local  # or use VS Code

# 4. Start development
npx prisma dev      # In terminal 1: Starts database
npm run dev         # In terminal 2: Starts app
```

## Detailed Setup Guide

### 1. Database (DATABASE_URL)

#### Option A: Prisma Local (Recommended for Development) ✅
```bash
# Just run this command - it handles everything!
npx prisma dev
```
- ✅ No configuration needed
- ✅ Automatic database creation
- ✅ Perfect for development
- ❌ Not for production

#### Option B: Neon (Free Cloud) ☁️
```bash
# 1. Go to https://neon.tech
# 2. Sign up (GitHub/Google)
# 3. Create project → Name: "SkillsMarket"
# 4. Copy connection string:
#    postgresql://username:password@ep-xxx.aws.neon.tech/neondb?sslmode=require
# 5. Paste in .env.local:
DATABASE_URL="postgresql://username:password@ep-xxx.aws.neon.tech/neondb?sslmode=require"
```
- ✅ Free forever
- ✅ Serverless, auto-scaling
- ✅ Great for testing
- ✅ Production ready

### 2. Authentication (AUTH_SECRET)

```bash
# Generate secure random string
openssl rand -base64 32
# Output: abc123xyz789... (32+ chars)

# Or use online generator:
# https://generate-secret.vercel.app/32
```

Paste in `.env.local`:
```env
AUTH_SECRET="abc123xyz789..."
```

### 3. Polar.sh Payments

#### Get Access Token:
```bash
# 1. Visit: https://polar.sh/dashboard
# 2. Login or sign up
# 3. Go to: Settings (gear icon) → API Keys
# 4. Click: Create API Key
# 5. Select permissions:
#    ✓ products:read
#    ✓ products:write
#    ✓ checkouts:write
#    ✓ webhooks:read
#    ✓ webhooks:write
# 6. Copy the token (starts with "pol_")
```

#### Get Webhook Secret:
```bash
# 1. Visit: https://polar.sh/dashboard/your-org/settings/webhooks
# 2. Click: Create Webhook
# 3. Webhook URL: https://your-domain.com/api/payments/polar/webhook
#    For local: Use ngrok URL (see below)
# 4. Select events:
#    ✓ checkout.created
#    ✓ checkout.completed
#    ✓ order.created
#    ✓ order.paid
# 5. Click: Create
# 6. Copy Webhook Secret (starts with "whsec_")
```

Paste in `.env.local`:
```env
POLAR_ACCESS_TOKEN="pol_123456..."
POLAR_WEBHOOK_SECRET="whsec_789abc..."
POLAR_MODE="sandbox"
```

### 4. License System (LICENSE_SALT)

```bash
# Generate random hex string
openssl rand -hex 16
# Output: 1a2b3c4d5e6f7g8h (32 chars)

# Or use online:
# https://www.random.org/strings/
```

Paste in `.env.local`:
```env
LICENSE_SALT="1a2b3c4d5e6f7g8h..."
```

### 5. ERC-8004 Wallet (ERC8004_PRIVATE_KEY)

⚠️ **IMPORTANT**: Use dedicated test wallet for development!

#### Create New Wallet:
```bash
# Option 1: MetaMask (Easiest)
# 1. Install: https://metamask.io
# 2. Create wallet → Save seed phrase securely
# 3. Settings → Security → Reveal Private Key
# 4. Enter password → Copy private key
# Format: 0x1234567890abcdef... (64 hex chars)

# Option 2: Generate with CLI
npx viem-wallet-create
# Output: Address, Private Key, Mnemonic

# Option 3: Use existing wallet
# Export from MetaMask/Rainbow/Coinbase Wallet
```

#### Get Testnet ETH (for testing):
```bash
# Visit: https://sepoliafaucet.com
# Enter your wallet address
# Click: Request testnet ETH
```

Paste in `.env.local`:
```env
ERC8004_PRIVATE_KEY="0x1234567890abcdef..."
```

### 6. x402 Payments

```bash
# 1. Visit: https://x402.org
# 2. Sign up for facilitator account
# 3. Dashboard → API Keys
# 4. Generate new API key
# 5. Copy the key
```

Paste in `.env.local`:
```env
X402_FACILITATOR_API_KEY="x402_api_key_123..."
X402_FACILITATOR_URL="https://api.x402.org"
```

### 7. Base Network RPC

#### Public (Free, Dev):
```env
BASE_RPC_URL="https://mainnet.base.org"
BASE_SEPOLIA_RPC_URL="https://sepolia.base.org"
```

#### Infura (Higher Limits):
```bash
# 1. Go to: https://infura.io
# 2. Sign up → Create project
# 3. Create API Key → Select "Base"
# 4. RPC URL: https://base-mainnet.infura.io/v3/YOUR_KEY
```

#### Alchemy (Web3 Optimized):
```bash
# 1. Go to: https://www.alchemy.com
# 2. Sign up → Create app → Name: "SkillsMarket"
# 3. Network: Base → Mainnet
# 4. RPC URL: https://base-mainnet.g.alchemy.com/v2/YOUR_KEY
```

## Testing Webhooks Locally

Polar requires HTTPS webhook URL. Use ngrok:

```bash
# 1. Install ngrok
brew install ngrok  # Mac
choco install ngrok # Windows

# 2. Start ngrok
ngrok http 3000

# 3. Copy URL
# Output: https://abc123.ngrok.io

# 4. Update Polar webhook
# Go to Polar dashboard → Webhooks
# Set URL: https://abc123.ngrok.io/api/payments/polar/webhook

# 5. Test payment flow
# The webhook will be called when payment completes
```

## Verify Setup

```bash
# 1. Check .env.local exists
cat .env.local

# 2. Start database
npx prisma dev

# 3. Start app
npm run dev

# 4. Visit
open http://localhost:3000

# 5. Check for errors
# If no errors, setup is complete! 🎉
```

## Common Issues

### "Database connection failed"
- Solution: Run `npx prisma dev` first
- Solution: Check DATABASE_URL format

### "Polar webhook not working"
- Solution: Use ngrok for HTTPS URL
- Solution: Verify POLAR_WEBHOOK_SECRET matches

### "Invalid private key"
- Solution: Must start with "0x"
- Solution: Must be 64 hex characters

### "RPC connection error"
- Solution: Check BASE_RPC_URL is correct
- Solution: Try different RPC provider (Infura/Alchemy)

## Next Steps

Once environment is set up:

1. ✅ Run migrations: `npx prisma migrate dev`
2. ✅ Seed database (optional): `npx prisma db seed`
3. ✅ Start dev server: `npm run dev`
4. ✅ Build for production: `npm run build`
5. ✅ Deploy: `vercel deploy` (or Vercel dashboard)

## Production Deployment

For Vercel:
```bash
# 1. Push to GitHub
# 2. Import in Vercel
# 3. Add environment variables in Project Settings
# 4. Set POLAR_MODE=production
# 5. Use production RPC URLs
# 6. Deploy
```

For Other Platforms:
- Railway: Add variables in dashboard
- Docker: Pass in docker-compose.yml
- AWS/GCP: Use ECS/Fargate environment variables

## Help & Resources

- Prisma: https://pris.ly/d
- Better Auth: https://www.better-auth.com
- Polar: https://polar.sh/docs
- x402: https://x402.org
- ERC-8004: https://eips.ethereum.org/EIPS/eip-8004
- Base: https://docs.base.org

## Security Checklist

- [ ] Never commit .env files
- [ ] Use different secrets for dev/prod
- [ ] Rotate secrets regularly
- [ ] Use separate testnet/mainnet wallets
- [ ] Enable 2FA on all accounts
- [ ] Audit access logs

---

**Ready to build?** 🚀

```bash
npm run dev
```
