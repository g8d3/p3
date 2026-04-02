#!/usr/bin/env bash
set -euo pipefail

BIN="${1:-./zig-out/bin/evm-wallet}"
PASS=0
FAIL=0
TOTAL=0

green() { printf "\033[32m%s\033[0m\n" "$1"; }
red()   { printf "\033[31m%s\033[0m\n" "$1"; }

assert() {
    local desc="$1" expected="$2" actual="$3"
    TOTAL=$((TOTAL + 1))
    if [ "$expected" = "$actual" ]; then
        PASS=$((PASS + 1))
        printf "  %s %s\n" "$(green PASS)" "$desc"
    else
        FAIL=$((FAIL + 1))
        printf "  %s %s (expected=%s got=%s)\n" "$(red FAIL)" "$desc" "$expected" "$actual"
    fi
}

assert_contains() {
    local desc="$1" needle="$2" haystack="$3"
    TOTAL=$((TOTAL + 1))
    if echo "$haystack" | grep -qF -- "$needle"; then
        PASS=$((PASS + 1))
        printf "  %s %s\n" "$(green PASS)" "$desc"
    else
        FAIL=$((FAIL + 1))
        printf "  %s %s (missing: %s)\n" "$(red FAIL)" "$desc" "$needle"
    fi
}

assert_not_contains() {
    local desc="$1" needle="$2" haystack="$3"
    TOTAL=$((TOTAL + 1))
    if echo "$haystack" | grep -qF -- "$needle"; then
        FAIL=$((FAIL + 1))
        printf "  %s %s (should not contain: %s)\n" "$(red FAIL)" "$desc" "$needle"
    else
        PASS=$((PASS + 1))
        printf "  %s %s\n" "$(green PASS)" "$desc"
    fi
}

assert_matches() {
    local desc="$1" regex="$2" actual="$3"
    TOTAL=$((TOTAL + 1))
    if echo "$actual" | grep -qE "$regex"; then
        PASS=$((PASS + 1))
        printf "  %s %s\n" "$(green PASS)" "$desc"
    else
        FAIL=$((FAIL + 1))
        printf "  %s %s (regex=%s actual=%s)\n" "$(red FAIL)" "$desc" "$regex" "$actual"
    fi
}

echo "=== evm-wallet test suite ==="
echo ""

# ── 1. Basic output ──────────────────────────────────────────────────────────
echo "--- Basic output ---"
OUT=$($BIN)
assert_contains "prints header" "=== EVM Wallet ===" "$OUT"
assert_contains "prints address label" "Address:" "$OUT"
assert_contains "prints private key label" "Private Key:" "$OUT"
assert_contains "prints mnemonic label" "Mnemonic (12 words):" "$OUT"
assert_contains "prints warning" "WARNING:" "$OUT"
assert_contains "prints tip" "TIP:" "$OUT"

# ── 2. Address format ───────────────────────────────────────────────────────
echo "--- Address format ---"
ADDR=$(echo "$OUT" | grep "Address:" | awk '{print $2}')
assert_matches "address starts with 0x" "^0x" "$ADDR"
assert "address is 42 chars" "42" "${#ADDR}"
assert_matches "address is hex" "^0x[0-9a-fA-F]{40}$" "$ADDR"

# ── 3. Private key format ───────────────────────────────────────────────────
echo "--- Private key format ---"
PK=$(echo "$OUT" | grep "Private Key:" | awk '{print $3}')
assert_matches "pk starts with 0x" "^0x" "$PK"
assert "pk is 66 chars" "66" "${#PK}"
assert_matches "pk is hex" "^0x[0-9a-f]{64}$" "$PK"

# ── 4. Mnemonic format ──────────────────────────────────────────────────────
echo "--- Mnemonic format ---"
MNEM=$(echo "$OUT" | sed -n 's/^  //p')
WORDS=$(echo "$MNEM" | wc -w)
assert "mnemonic has 12 words" "12" "$WORDS"

# ── 5. JSON output ──────────────────────────────────────────────────────────
echo "--- JSON output ---"
JOUT=$($BIN --json)
assert_matches "json has address" '"address"' "$JOUT"
assert_matches "json has private_key" '"private_key"' "$JOUT"
assert_matches "json has mnemonic" '"mnemonic"' "$JOUT"
assert_matches "json encrypted=false" '"encrypted": false' "$JOUT"
assert_contains "json address starts 0x" '"0x' "$JOUT"

# validate json is parseable
JADDR=$(echo "$JOUT" | grep '"address"' | sed 's/.*: "\(.*\)".*/\1/')
assert_matches "json address valid" "^0x[0-9a-fA-F]{40}$" "$JADDR"

# ── 6. Help flag ────────────────────────────────────────────────────────────
echo "--- Help ---"
HELP=$($BIN --help 2>&1)
assert_contains "help shows usage" "USAGE:" "$HELP"
assert_contains "help shows --encrypt" "--encrypt" "$HELP"
assert_contains "help shows --json" "--json" "$HELP"
assert_contains "help shows --help" "--help" "$HELP"

HELP2=$($BIN -h 2>&1)
assert "-h same as --help" "$HELP" "$HELP2"

# ── 7. Unknown flag ─────────────────────────────────────────────────────────
echo "--- Error handling ---"
ERR=$($BIN --bogus 2>&1 || true)
assert_contains "unknown flag shows error" "Unknown option: --bogus" "$ERR"
assert_contains "unknown flag shows help" "USAGE:" "$ERR"

# ── 8. Encrypted wallet ─────────────────────────────────────────────────────
echo "--- Encrypted wallet ---"
EOUT=$(printf "mypass\nmypass\n" | $BIN --encrypt 2>/dev/null)
assert_contains "encrypted header" "=== EVM Wallet (Encrypted) ===" "$EOUT"
assert_contains "encrypted has address" "Address:" "$EOUT"
assert_contains "encrypted has algorithm" "AES-256-GCM" "$EOUT"
assert_contains "encrypted has kdf" "PBKDF2-SHA256" "$EOUT"
assert_contains "encrypted has salt" "Salt:" "$EOUT"
assert_contains "encrypted has nonce" "Nonce:" "$EOUT"
assert_contains "encrypted has ciphertext" "Ciphertext:" "$EOUT"
assert_contains "encrypted has warning" "WARNING: Store your password safely" "$EOUT"
assert_not_contains "no plaintext private key" "Private Key:  0x" "$EOUT"
assert_not_contains "no plaintext mnemonic" "Mnemonic (12 words):" "$EOUT"

# ── 9. Encrypted JSON ───────────────────────────────────────────────────────
echo "--- Encrypted JSON ---"
EJOUT=$(printf "secret\nsecret\n" | $BIN --encrypt --json 2>/dev/null)
assert_matches "enc json has encrypted=true" '"encrypted": true' "$EJOUT"
assert_matches "enc json has algorithm" '"AES-256-GCM"' "$EJOUT"
assert_matches "enc json has kdf" '"PBKDF2-SHA256"' "$EJOUT"
assert_matches "enc json has kdf_iterations" '"kdf_iterations": 600000' "$EJOUT"
assert_matches "enc json has private_key block" '"private_key": {' "$EJOUT"
assert_matches "enc json has mnemonic block" '"mnemonic": {' "$EJOUT"

# ── 10. Password mismatch ───────────────────────────────────────────────────
echo "--- Password validation ---"
MERR=$(printf "pass1\npass2\n" | $BIN --encrypt 2>&1 || true)
assert_contains "mismatch shows error" "passwords do not match" "$MERR"

EERR=$(printf "\n\n" | $BIN --encrypt 2>&1 || true)
assert_contains "empty password shows error" "password cannot be empty" "$EERR"

# ── 11. Uniqueness ──────────────────────────────────────────────────────────
echo "--- Uniqueness ---"
A1=$($BIN --json | grep '"address"' | sed 's/.*: "\(.*\)".*/\1/')
A2=$($BIN --json | grep '"address"' | sed 's/.*: "\(.*\)".*/\1/')
assert_not_contains "two runs produce different addresses" "$A1" "$A2"

# ── 12. EIP-55 checksum ─────────────────────────────────────────────────────
echo "--- EIP-55 checksum ---"
for i in 1 2 3 4 5; do
    ADDR=$($BIN --json | grep '"address"' | sed 's/.*: "\(.*\)".*/\1/')
    HEX="${ADDR:2}"
    UPPER=$(echo "$HEX" | tr -cd 'A-Z' | wc -c)
    LOWER=$(echo "$HEX" | tr -cd 'a-z' | wc -c)
    # EIP-55: if address has letters, at least some must differ in case
    HAS_LETTERS=$((UPPER + LOWER))
    if [ "$HAS_LETTERS" -gt 0 ]; then
        TOTAL=$((TOTAL + 1))
        if [ "$UPPER" -gt 0 ] && [ "$LOWER" -gt 0 ]; then
            PASS=$((PASS + 1))
            printf "  %s checksum run %d (upper=%d lower=%d)\n" "$(green PASS)" "$i" "$UPPER" "$LOWER"
        else
            FAIL=$((FAIL + 1))
            printf "  %s checksum run %d (upper=%d lower=%d)\n" "$(red FAIL)" "$i" "$UPPER" "$LOWER"
        fi
    fi
done

# ── 13. Encryption randomness ───────────────────────────────────────────────
echo "--- Encryption randomness ---"
SALT1=$(printf "same\nsame\n" | $BIN --encrypt --json 2>/dev/null | grep '"salt"' | head -1 | sed 's/.*: "\(.*\)".*/\1/')
SALT2=$(printf "same\nsame\n" | $BIN --encrypt --json 2>/dev/null | grep '"salt"' | head -1 | sed 's/.*: "\(.*\)".*/\1/')
assert_not_contains "different salts per run" "$SALT1" "$SALT2"

# ── Summary ──────────────────────────────────────────────────────────────────
echo ""
echo "=============================="
if [ "$FAIL" -eq 0 ]; then
    echo "$(green "ALL $TOTAL TESTS PASSED")"
else
    echo "$(red "$FAIL/$TOTAL TESTS FAILED") ($PASS passed)"
fi
echo "=============================="

exit $FAIL
