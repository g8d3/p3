# No-Mnemonic Wallet Implementation

Comparison of Privy vs Capsule for embedded MPC wallets.

## Setup

```bash
pip install -r requirements.txt
```

## Environment Variables

Create `.env` file with:

```env
# Privy (get from https://privy.io)
PRIVY_APP_ID=your_privy_app_id
PRIVY_APP_SECRET=your_privy_app_secret
PRIVY_AUTHORIZATION_KEY=your_authorization_key

# Capsule (get from https://usecapsule.com)
CAPSULE_API_KEY=your_capsule_api_key

# For testing
TEST_PRIVATE_KEY=0x...
TEST_WALLET_ADDRESS=0x...
```

## Usage

```python
# Privy
python privy_wallet.py

# Capsule  
python capsule_wallet.py
```
