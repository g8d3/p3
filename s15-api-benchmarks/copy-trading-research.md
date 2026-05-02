# Copy Trading Platforms on Perp DEXes - Research Findings

## Platform 1: Aster + Simpfor.fun

### Aster DEX
**Description**: Decentralized perpetual exchange formed through the merger of Astherus and APX Finance in late 2024.

**Key Features**:
- **Trading Modes**:
  - Perpetual Mode (Pro) - order book interface with advanced tools
  - 1001x - one-click MEV-resistant perpetual contracts
  - Spot mode - traditional trading
- **Yield Products**:
  - asBNB liquid staking derivative
  - USDF stablecoin (Aster Earn)
- **Trading Volume**: Cumulative trading volume surpassing $10 billion
- **Roadmap**: Zero-knowledge proofs, dedicated L1 blockchain, intent-based system for cross-chain execution

### Simpfor.fun
**Description**: Copy-trading platform that has integrated Aster.

**Key Features**:
- Multi-platform copy trading support
- Access to top traders on Aster exchange
- Proven trader performance data
- Benefits: High-leverage trading infrastructure, exposure to rapidly growing platform, enhanced trading options

**Links**:
- Simpfor.fun: https://simpfor.fun/
- Aster: (via merger of Astherus and APX Finance)

## Platform 2: Hyperliquid

**Description**: Perpetual DEX with custom L1 blockchain (HyperBFT), offering CEX-like execution with DEX self-custody. No VC backing, entirely bootstrapped.

### Copy Trading Feature: User Vaults
- **User Vaults**: On-chain copy trading where users deposit into a vault managed by a successful trader
- **Leader Compensation**: Vault leader earns 10% of profits
- **Copy Mechanism**: Depositors automatically mirror trades performed by the leader
- **Key Product**: Part of Hyperliquid's product suite for both traders and builders

**Key Features**:
- **High Performance**: HyperBFT consensus mechanism (0.2s median latency, 200,000 orders/second)
- **Dual-State Architecture**: HyperCore (trading engine) + HyperEVM (smart contract layer) sharing same memory state
- **No VC Funding**: Zero VC backing - bootstrapped by founders' HFT firm profits
- **Vertical Integration**: Owns full stack (L1 + Exchange) capturing value at validator layer
- **HIP-2 (Hyperliquidity)**: Automated market-making ensuring liquidity for new tokens

**Trading Products**:
- Perpetual Exchange: Up to 50x leverage on crypto assets, CLOB, cross and isolated margin
- Spot Exchange: Gas-free spot trading for native tokens (HIP-1) and USDC
- HLP Vault: Users deposit USDC to act as market maker, earning PnL from spread and fees
- User Vaults: On-chain copy trading (10% profit share to leader)
- LSTs: Stake HYPE to earn validator rewards via Kinetiq

**Risks**:
- Validator centralization (24 validators as of late 2025)
- Bridge risk (trusted multisig, not ZK-bridge)
- Automated market-making logic risks (e.g., $15.3M JELLY token incident)

**Links**: Hyperliquid docs mention User Vaults for copy trading

---

## Platform 3: dYdX Vaults

**Description**: Decentralized perp DEX on custom blockchain (dYdX Chain), offering vaults for automated market-making.

### Copy Trading Feature: Single-Name Vaults
- **Vault Architecture**: Permissionless smart contracts accepting USDC deposits
- **Pricing Mechanism**: Uses dYdX Chain's on-chain price index to compute fair value
- **Automated Quotes**: Generates multiple bids/offers around fair price automatically
- **Risk Management**: Self-balances based on inventory and capital, adjusts quotes to manage exposure
- **Cost Efficiency**: Average $500/month per market vs previous $2,500/month - extremely cheap
- **Protocol Native**: Enshrined in dYdX Chain, high uptime, minimal dependencies

**Key Features**:
- **Permissionless Deposits**: Anyone can deposit USDC to provide liquidity
- **Fair Value Pricing**: Uses validator's index price and internal inventory
- **Automated Market Making**: Places multiple bids/offers on both sides of mid-price
- **Round-the-Clock Liquidity**: 100% uptime assuming chain is running
- **Decentralized**: No dependence on external market-making providers
- **Experimental Phase**: Vaults currently in experimental/observation period (118 markets tested)

**Vault Performance Data** (from research report):
- Total cost of liquidity: $58,549.97/month (across 117 markets)
- Average cost per market: $500.43/month
- PnL outcomes ranged widely: from best to worst performers with significant variance
- Top two best outcomes generated large PnL, typical market shows slightly negative PnL

**Links**: dYdX Community Forum - Vaults Research Report

---

## Summary of Copy Trading Platforms on Perp DEXes

### Platforms with Copy Trading Features

| Platform | Copy Trading Feature | Key Details | Status |
|-----------|---------------------|--------|------|
| Simpfor.fun | Multi-platform copy trading | Integrates Aster, allows copying top traders | Requires login for access |
| Hyperliquid | User Vaults (On-chain copy trading) | Leader earns 10% of profits, depositors mirror trades automatically | Active, public data available |
| dYdX | Single-name Vaults (Automated market-making) | Permissionless USDC deposits, computes fair price via validator index | Not exactly copy trading but related liquidity mechanism |
| Aster | Direct integration with copy trading platforms | Trading modes: Perp Mode (Pro), 1001x (MEV-resistant), Spot | Available via Simpfor.fun |

### Platforms to Explore Further
- GMX (GLP vault model - mentioned as yield-bearing collateral provider)
- Lighter (mentioned in research as competitive but in "price war")
- Apex Omni (mentioned in search results as copy trading platform)
- Dexodus (mentioned as having copy trading feature)

### Research Methodology
- Searched Google for "copy trading perp DEX", "GMX copy trading", "dYdX copy trading"
- Visited Medium articles about perp DEX comparisons
- Explored dYdX Community Forum vaults research
- Analyzed platform documentation and features

**Last Updated**: 2026-01-29

---
