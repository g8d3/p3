# s34

Ethereum utilities using ethers.js.

## Scripts

### Check Balance
```bash
WALLET_ADDRESS=0x... node check-balance.js
```

### Create Wallet
```bash
node cw.js
```

## Environment Variables

| Variable | Description |
|----------|-------------|
| `WALLET_ADDRESS` | Wallet address for balance check |
| `WPWD` | Password for encrypted JSON wallet |
| `RAW` | Set to `false` to hide mnemonic/private key (default: true) |
| `JSON` | Set to `true` to output encrypted JSON wallet (requires `WPWD`) |

## Install

```bash
npm install
```