# evm-wallet

A CLI tool for generating EVM (Ethereum) wallets, written in Zig.

## Features

- **BIP-39** mnemonic generation (12-word, 128-bit entropy)
- **BIP-32/44** HD wallet derivation (`m/44'/60'/0'/0/0`)
- **EIP-55** checksummed Ethereum addresses
- **AES-256-GCM** encryption with PBKDF2-SHA256 (600k iterations)
- JSON output mode
- Zero external dependencies (uses Zig stdlib crypto)

## Build

Requires Zig 0.16+.

```sh
zig build
```

The binary is output to `zig-out/bin/evm-wallet`.

## Usage

```
evm-wallet [OPTIONS]

OPTIONS:
  -e, --encrypt     Encrypt private key and mnemonic with a password
  -j, --json        Output as JSON
  -h, --help        Show help message
```

### Generate a wallet

```sh
evm-wallet
```

### Generate with encryption

```sh
evm-wallet --encrypt
```

### JSON output

```sh
evm-wallet --json
evm-wallet --encrypt --json
```

## Testing

```sh
zig build
./test.sh
```

## Security

- Private keys are generated using the OS CSPRNG
- Encryption uses AES-256-GCM with a random 96-bit nonce
- Key derivation uses PBKDF2-HMAC-SHA256 with 600,000 iterations (OWASP 2023 recommendation)
- Password input is read from `/dev/tty` with echo disabled when possible
