#!/usr/bin/env python3
"""
Privy No-Mnemonic Wallet Implementation
========================================
Seed phrases are a relic of the past - but the 'fix' almost broke my application.

This script demonstrates how to implement no-mnemonic wallets using Privy.
The key insight: Privy handles key sharding via TEE + Shamir Secret Sharing,
so users get self-custody without managing seed phrases.
"""

import os
import sys
from datetime import datetime

# Load environment variables
from dotenv import load_dotenv
load_dotenv()

from privy_eth_account import create_eth_account, PrivyHTTPClient
from eth_account.messages import encode_defunct, encode_typed_data


def main():
    print("=" * 60)
    print("🔐 PRIVY NO-MNEMONIC WALLET IMPLEMENTATION")
    print("=" * 60)
    print()
    
    # Configuration
    app_id = os.getenv("PRIVY_APP_ID")
    app_secret = os.getenv("PRIVY_APP_SECRET")
    authorization_key = os.getenv("PRIVY_AUTHORIZATION_KEY")
    
    # For demo: use test wallet if no credentials
    test_wallet_id = os.getenv("TEST_WALLET_ID", "wal_demo_123")
    test_wallet_address = os.getenv("TEST_WALLET_ADDRESS", "0x742d35Cc6634C0532925a3b844Bc9e7595f0bEb0")
    
    if not all([app_id, app_secret, authorization_key]):
        print("⚠️  No Privy credentials found - running in DEMO mode")
        print("   Set PRIVY_APP_ID, PRIVY_APP_SECRET, PRIVY_AUTHORIZATION_KEY to test real wallet")
        print()
        
        # Demonstrate the API structure without real credentials
        demo_flow()
        return
    
    print("✅ Credentials loaded - attempting wallet connection...")
    print()
    
    try:
        # Initialize Privy HTTP Client
        client = PrivyHTTPClient(
            app_id=app_id,
            app_secret=app_secret,
            authorization_key=authorization_key
        )
        
        # Create account instance for existing wallet
        account = create_eth_account(client, test_wallet_address, test_wallet_id)
        
        print(f"�wallet Address: {account.address}")
        print()
        
        # Demo: Sign a message
        message = "Hello from Privy no-mnemonic wallet!"
        signed = account.sign_message(encode_defunct(text=message))
        print(f"✍️  Signed message: {signed.message}")
        print(f"   Signature: {signed.signature.hex()[:40]}...")
        print()
        
        # Demo: Sign typed data (EIP-712)
        typed_data = {
            "domain": {
                "name": "My App",
                "version": "1",
                "chainId": 8453,  # Base
                "verifyingContract": "0xCc9c3D98163F4F6Af884e259132e15D6d27A5c57",
            },
            "message": {
                "from": account.address,
                "contents": "Hello, EIP-712!",
            },
            "primaryType": "Mail",
            "types": {
                "Mail": [
                    {"name": "from", "type": "Person"},
                    {"name": "contents", "type": "string"},
                ],
                "Person": [
                    {"name": "name", "type": "string"},
                ],
            },
        }
        
        signed_typed = account.sign_typed_data(typed_data)
        print(f"✍️  Signed typed data (EIP-712)")
        print(f"   Signature: {signed_typed.signature.hex()[:40]}...")
        print()
        
        print("🎉 PRIVY WALLET SUCCESS!")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        print()
        demo_flow()


def demo_flow():
    """Demonstrate the flow without real credentials"""
    print("📋 DEMO FLOW (No real credentials)")
    print("-" * 40)
    print()
    
    # Show what the integration looks like
    print("1️⃣  Initialize Privy Client:")
    print("   client = PrivyHTTPClient(")
    print("       app_id=APP_ID,")
    print("       app_secret=APP_SECRET,")
    print("       authorization_key=AUTH_KEY")
    print("   )")
    print()
    
    print("2️⃣  Create wallet account:")
    print("   account = create_eth_account(")
    print("       client,")
    print("       wallet_address,")
    print("       wallet_id")
    print("   )")
    print()
    
    print("3️⃣  Sign transactions (NO SEED PHRASE NEEDED!):")
    print("   signed = account.sign_message(encode_defunct(text='Hello'))")
    print()
    
    print("=" * 60)
    print("🔑 KEY INSIGHT: Privy uses 2-of-2 key sharding")
    print("   - Enclave share: secured by TEE")
    print("   - Auth share: encrypted, stored by Privy")
    print("   - User authenticates → both shares combine → sign")
    print("   - NO SEED PHRASE ever exists in full form!")
    print("=" * 60)


if __name__ == "__main__":
    main()
