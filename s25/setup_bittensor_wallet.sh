#!/bin/bash
# Bittensor wallet setup script

set -e

WALLET_NAME="${1:-default}"
HOTKEY="${2:-default}"
WALLET_PATH="${3:-$HOME/.bittensor/wallets}"
N_WORDS="${4:-24}"

echo "Installing bittensor-cli..."
uv pip install bittensor-cli

echo "Creating wallet: $WALLET_NAME / $HOTKEY"
uv run btcli w create \
    --wallet-name "$WALLET_NAME" \
    --wallet-path "$WALLET_PATH" \
    --hotkey "$HOTKEY" \
    --n-words "$N_WORDS" \
    --no-use-password \
    --quiet

echo "Wallet created successfully!"
uv run btcli w list
