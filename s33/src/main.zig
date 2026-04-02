const std = @import("std");
const Io = std.Io;
const wordlist = @import("wordlist.zig").words;

const Aes256Gcm = std.crypto.aead.aes_gcm.Aes256Gcm;
const Keccak256 = std.crypto.hash.sha3.Keccak256;
const HmacSha512 = std.crypto.auth.hmac.sha2.HmacSha512;
const HmacSha256 = std.crypto.auth.hmac.sha2.HmacSha256;
const Secp256k1 = std.crypto.ecc.Secp256k1;

// ── BIP-39 Mnemonic ──────────────────────────────────────────────────────────

/// Generate a random 12-word BIP-39 mnemonic (128-bit entropy).
fn generateMnemonic(io: Io) [12][]const u8 {
    var entropy: [16]u8 = undefined;
    io.random(&entropy);
    return entropyToMnemonic(&entropy);
}

/// Convert 16 bytes of entropy to 12 mnemonic words (BIP-39).
fn entropyToMnemonic(entropy: *const [16]u8) [12][]const u8 {
    var sha_hash: [32]u8 = undefined;
    std.crypto.hash.sha2.Sha256.hash(entropy, &sha_hash, .{});

    var words: [12][]const u8 = undefined;
    for (0..12) |i| {
        var index: u16 = 0;
        const bit_offset = i * 11;
        for (0..11) |b| {
            const global_bit = bit_offset + b;
            const bit_val: u1 = blk: {
                if (global_bit < 128) {
                    const byte_idx = global_bit / 8;
                    const bit_idx: u3 = @intCast(7 - (global_bit % 8));
                    break :blk @truncate(entropy[byte_idx] >> bit_idx);
                } else {
                    const cs_bit = global_bit - 128;
                    const byte_idx = cs_bit / 8;
                    const bit_idx: u3 = @intCast(7 - (cs_bit % 8));
                    break :blk @truncate(sha_hash[byte_idx] >> bit_idx);
                }
            };
            index = (index << 1) | @as(u16, bit_val);
        }
        words[i] = wordlist[index];
    }
    return words;
}

/// Convert mnemonic words to a single space-joined string.
fn mnemonicToString(allocator: std.mem.Allocator, words: []const []const u8) ![]u8 {
    var total_len: usize = 0;
    for (words, 0..) |word, i| {
        if (i > 0) total_len += 1;
        total_len += word.len;
    }
    const result = try allocator.alloc(u8, total_len);
    var pos: usize = 0;
    for (words, 0..) |word, i| {
        if (i > 0) {
            result[pos] = ' ';
            pos += 1;
        }
        @memcpy(result[pos .. pos + word.len], word);
        pos += word.len;
    }
    return result;
}

// ── BIP-39 Seed Derivation ───────────────────────────────────────────────────

/// Derive a 64-byte seed from mnemonic words using PBKDF2-HMAC-SHA512 (2048 iterations).
fn mnemonicToSeed(words: []const []const u8, passphrase: []const u8) ![64]u8 {
    // Build mnemonic string
    var mnemonic_buf: [1024]u8 = undefined;
    var mnemonic_len: usize = 0;
    for (words, 0..) |word, i| {
        if (i > 0) {
            mnemonic_buf[mnemonic_len] = ' ';
            mnemonic_len += 1;
        }
        @memcpy(mnemonic_buf[mnemonic_len .. mnemonic_len + word.len], word);
        mnemonic_len += word.len;
    }
    const mnemonic = mnemonic_buf[0..mnemonic_len];

    // Salt = "mnemonic" + passphrase
    var salt_buf: [256]u8 = undefined;
    const prefix = "mnemonic";
    @memcpy(salt_buf[0..prefix.len], prefix);
    @memcpy(salt_buf[prefix.len .. prefix.len + passphrase.len], passphrase);
    const salt = salt_buf[0 .. prefix.len + passphrase.len];

    var seed: [64]u8 = undefined;
    try std.crypto.pwhash.pbkdf2(&seed, mnemonic, salt, 2048, HmacSha512);
    return seed;
}

// ── BIP-32 HD Wallet Derivation ──────────────────────────────────────────────

const HARDENED: u32 = 0x80000000;

const ExtendedKey = struct {
    key: [32]u8,
    chain_code: [32]u8,
};

/// Derive master key from BIP-39 seed.
fn masterKeyFromSeed(seed: [64]u8) ExtendedKey {
    var mac: [64]u8 = undefined;
    HmacSha512.create(&mac, &seed, "Bitcoin seed");
    return .{
        .key = mac[0..32].*,
        .chain_code = mac[32..64].*,
    };
}

/// Derive a child key at the given index.
fn deriveChild(parent: ExtendedKey, index: u32) !ExtendedKey {
    var data: [37]u8 = undefined;
    if (index >= HARDENED) {
        data[0] = 0;
        @memcpy(data[1..33], &parent.key);
    } else {
        // Normal: compressed public key || index
        const privkey_scalar = Secp256k1.scalar.Scalar.fromBytes(parent.key, .big) catch return error.DerivationFailed;
        const pubkey_point = Secp256k1.basePoint.mul(privkey_scalar.toBytes(.big), .big) catch return error.DerivationFailed;
        const compressed = pubkey_point.toCompressedSec1();
        @memcpy(data[0..33], &compressed);
    }
    std.mem.writeInt(u32, data[33..37], index, .big);

    var mac: [64]u8 = undefined;
    HmacSha512.create(&mac, &data, &parent.chain_code);

    const il = mac[0..32].*;
    const ir = mac[32..64].*;

    const SecpScalar = Secp256k1.scalar.Scalar;
    const il_scalar = SecpScalar.fromBytes(il, .big) catch return error.DerivationFailed;
    const parent_scalar = SecpScalar.fromBytes(parent.key, .big) catch return error.DerivationFailed;
    const child_scalar = il_scalar.add(parent_scalar);

    if (child_scalar.isZero()) return error.DerivationFailed;

    return .{
        .key = child_scalar.toBytes(.big),
        .chain_code = ir,
    };
}

/// Derive Ethereum account at BIP-44 path m/44'/60'/0'/0/{index}.
fn deriveEthAccount(seed: [64]u8, account_index: u32) !ExtendedKey {
    var key = masterKeyFromSeed(seed);
    key = try deriveChild(key, 44 | HARDENED);
    key = try deriveChild(key, 60 | HARDENED);
    key = try deriveChild(key, 0 | HARDENED);
    key = try deriveChild(key, 0);
    key = try deriveChild(key, account_index);
    return key;
}

// ── Address Derivation ───────────────────────────────────────────────────────

/// Derive Ethereum address from private key bytes.
fn privateKeyToAddress(key: [32]u8) ![20]u8 {
    const privkey_scalar = Secp256k1.scalar.Scalar.fromBytes(key, .big) catch return error.KeyDerivationFailed;
    const pubkey_point = Secp256k1.basePoint.mul(privkey_scalar.toBytes(.big), .big) catch return error.KeyDerivationFailed;
    const pubkey_uncompressed = pubkey_point.toUncompressedSec1();

    // Address = last 20 bytes of keccak256(pubkey[1..])
    var hash: [32]u8 = undefined;
    Keccak256.hash(pubkey_uncompressed[1..], &hash, .{});

    var addr: [20]u8 = undefined;
    @memcpy(&addr, hash[12..32]);
    return addr;
}

/// Convert a 20-byte address to EIP-55 checksummed hex string.
fn addressToChecksum(addr: [20]u8) [42]u8 {
    // Lowercase hex of address
    const lower_hex = std.fmt.bytesToHex(&addr, .lower);

    // Keccak256 of lowercase hex
    var hash: [32]u8 = undefined;
    Keccak256.hash(&lower_hex, &hash, .{});

    var result: [42]u8 = undefined;
    result[0] = '0';
    result[1] = 'x';
    for (lower_hex, 0..) |c, i| {
        if (c >= '0' and c <= '9') {
            result[i + 2] = c;
        } else {
            // Each nibble of hash determines uppercase/lowercase
            const nibble_idx = i / 2;
            const nibble = if (i % 2 == 0) (hash[nibble_idx] >> 4) else (hash[nibble_idx] & 0x0f);
            if (nibble >= 8) {
                result[i + 2] = c - 32; // uppercase
            } else {
                result[i + 2] = c; // lowercase
            }
        }
    }
    return result;
}

// ── Encryption ───────────────────────────────────────────────────────────────

const EncryptedData = struct {
    ciphertext: []u8,
    salt: [32]u8,
    nonce: [12]u8,
};

/// Encrypt data with AES-256-GCM using a password-derived key (PBKDF2-SHA256, 600k iterations).
fn encryptWithPassword(io: Io, allocator: std.mem.Allocator, plaintext: []const u8, password: []const u8) !EncryptedData {
    var salt: [32]u8 = undefined;
    io.random(&salt);

    var nonce: [Aes256Gcm.nonce_length]u8 = undefined;
    io.random(&nonce);

    // Derive key: PBKDF2-HMAC-SHA256, 600,000 iterations (OWASP 2023 recommendation)
    var key: [Aes256Gcm.key_length]u8 = undefined;
    try std.crypto.pwhash.pbkdf2(&key, password, &salt, 600_000, HmacSha256);

    // Encrypt
    const ciphertext = try allocator.alloc(u8, plaintext.len + Aes256Gcm.tag_length);
    var tag: [Aes256Gcm.tag_length]u8 = undefined;
    Aes256Gcm.encrypt(ciphertext[0..plaintext.len], &tag, plaintext, "", nonce, key);
    @memcpy(ciphertext[plaintext.len..], &tag);

    return .{
        .ciphertext = ciphertext,
        .salt = salt,
        .nonce = nonce,
    };
}

// ── Password Input ───────────────────────────────────────────────────────────

fn readPassword(allocator: std.mem.Allocator, io: Io, stderr: *Io.Writer, prompt: []const u8) ![]u8 {
    try stderr.print("{s}", .{prompt});
    try stderr.flush();

    // If stdin is not a TTY (piped input), read directly from stdin
    if (std.c.isatty(std.posix.STDIN_FILENO) == 0) {
        var buf: [1024]u8 = undefined;
        var len: usize = 0;
        while (len < buf.len) {
            var byte: [1]u8 = undefined;
            const n = std.posix.read(std.posix.STDIN_FILENO, &byte) catch break;
            if (n == 0) break;
            if (byte[0] == '\n') break;
            if (byte[0] != '\r') {
                buf[len] = byte[0];
                len += 1;
            }
        }
        return allocator.dupe(u8, buf[0..len]);
    }

    // Interactive: open /dev/tty to hide echo
    const tty = std.Io.Dir.openFileAbsolute(io, "/dev/tty", .{ .mode = .read_only }) catch {
        var buf: [1024]u8 = undefined;
        var len: usize = 0;
        while (len < buf.len) {
            var byte: [1]u8 = undefined;
            const n = std.posix.read(std.posix.STDIN_FILENO, &byte) catch break;
            if (n == 0) break;
            if (byte[0] == '\n') break;
            if (byte[0] != '\r') {
                buf[len] = byte[0];
                len += 1;
            }
        }
        return allocator.dupe(u8, buf[0..len]);
    };
    defer tty.close(io);

    // Disable echo
    const termios = std.posix.tcgetattr(tty.handle) catch {
        var buf: [1024]u8 = undefined;
        const n = std.posix.read(tty.handle, &buf) catch 0;
        if (n == 0) return allocator.alloc(u8, 0);
        var end = n;
        while (end > 0 and (buf[end - 1] == '\n' or buf[end - 1] == '\r')) end -= 1;
        return allocator.dupe(u8, buf[0..end]);
    };
    const saved = termios;
    var no_echo = termios;
    no_echo.lflag.ECHO = false;
    no_echo.lflag.ECHONL = false;
    std.posix.tcsetattr(tty.handle, .NOW, no_echo) catch {
        var buf: [1024]u8 = undefined;
        const n = std.posix.read(tty.handle, &buf) catch 0;
        if (n == 0) return allocator.alloc(u8, 0);
        var end = n;
        while (end > 0 and (buf[end - 1] == '\n' or buf[end - 1] == '\r')) end -= 1;
        return allocator.dupe(u8, buf[0..end]);
    };

    var buf: [1024]u8 = undefined;
    const n = std.posix.read(tty.handle, &buf) catch 0;

    std.posix.tcsetattr(tty.handle, .NOW, saved) catch {};
    try stderr.print("\n", .{});

    if (n == 0) return allocator.alloc(u8, 0);
    var end = n;
    while (end > 0 and (buf[end - 1] == '\n' or buf[end - 1] == '\r')) end -= 1;
    return allocator.dupe(u8, buf[0..end]);
}

// ── Output Helpers ───────────────────────────────────────────────────────────

fn printHex(buf: []u8, data: []const u8) []u8 {
    const hex_charset = "0123456789abcdef";
    for (data, 0..) |byte, i| {
        buf[i * 2] = hex_charset[byte >> 4];
        buf[i * 2 + 1] = hex_charset[byte & 0x0f];
    }
    return buf[0 .. data.len * 2];
}

fn printEncryptedBlock(writer: *Io.Writer, data: EncryptedData) !void {
    var salt_hex: [64]u8 = undefined;
    var nonce_hex: [24]u8 = undefined;
    var ct_hex: [512]u8 = undefined;
    try writer.print("  Algorithm:  AES-256-GCM\n", .{});
    try writer.print("  KDF:        PBKDF2-SHA256 (600,000 iterations)\n", .{});
    try writer.print("  Salt:       {s}\n", .{printHex(&salt_hex, &data.salt)});
    try writer.print("  Nonce:      {s}\n", .{printHex(&nonce_hex, &data.nonce)});
    try writer.print("  Ciphertext: {s}\n", .{printHex(&ct_hex, data.ciphertext)});
}

// ── Main ─────────────────────────────────────────────────────────────────────

pub fn main(init: std.process.Init) !void {
    const arena = init.arena.allocator();
    const io = init.io;

    var stdout_buf: [4096]u8 = undefined;
    var stdout_writer: Io.File.Writer = .init(.stdout(), io, &stdout_buf);
    const stdout = &stdout_writer.interface;

    var stderr_buf: [1024]u8 = undefined;
    var stderr_writer: Io.File.Writer = .init(.stderr(), io, &stderr_buf);
    const stderr = &stderr_writer.interface;

    const args = try init.minimal.args.toSlice(arena);

    var encrypt = false;
    var output_json = false;

    var idx: usize = 1;
    while (idx < args.len) : (idx += 1) {
        const arg = args[idx];
        if (std.mem.eql(u8, arg, "--encrypt") or std.mem.eql(u8, arg, "-e")) {
            encrypt = true;
        } else if (std.mem.eql(u8, arg, "--json") or std.mem.eql(u8, arg, "-j")) {
            output_json = true;
        } else if (std.mem.eql(u8, arg, "--help") or std.mem.eql(u8, arg, "-h")) {
            try printHelp(stderr);
            try stderr.flush();
            return;
        } else {
            try stderr.print("Unknown option: {s}\n", .{arg});
            try printHelp(stderr);
            try stderr.flush();
            std.process.exit(1);
        }
    }

    // Generate 12-word mnemonic (BIP-39, 128-bit entropy)
    const words = generateMnemonic(io);

    // Derive seed and account
    const seed = try mnemonicToSeed(&words, "");
    const account = try deriveEthAccount(seed, 0);
    const address = try privateKeyToAddress(account.key);
    const checksum = addressToChecksum(address);

    // Format outputs
    const mnemonic_str = try mnemonicToString(arena, &words);
    var pk_hex_buf: [64]u8 = undefined;
    const pk_hex = printHex(&pk_hex_buf, &account.key);

    if (encrypt) {
        const password = try readPassword(arena, io, stderr, "Enter password to encrypt wallet: ");
        if (password.len == 0) {
            try stderr.print("Error: password cannot be empty\n", .{});
            try stderr.flush();
            std.process.exit(1);
        }
        const confirm = try readPassword(arena, io, stderr, "Confirm password: ");
        if (!std.mem.eql(u8, password, confirm)) {
            try stderr.print("Error: passwords do not match\n", .{});
            try stderr.flush();
            std.process.exit(1);
        }

        const enc_pk = try encryptWithPassword(io, arena, &account.key, password);
        const enc_mnemonic = try encryptWithPassword(io, arena, mnemonic_str, password);

        if (output_json) {
            var salt_hex: [2][64]u8 = undefined;
            var nonce_hex: [2][24]u8 = undefined;
            var ct_hex: [2][512]u8 = undefined;
            try stdout.print(
                \\{{
                \\  "address": "{s}",
                \\  "private_key": "0x{s}",
                \\  "mnemonic": "{s}",
                \\  "encrypted": true,
                \\  "encryption": {{
                \\    "algorithm": "AES-256-GCM",
                \\    "kdf": "PBKDF2-SHA256",
                \\    "kdf_iterations": 600000,
                \\    "private_key": {{
                \\      "salt": "{s}",
                \\      "nonce": "{s}",
                \\      "ciphertext": "{s}"
                \\    }},
                \\    "mnemonic": {{
                \\      "salt": "{s}",
                \\      "nonce": "{s}",
                \\      "ciphertext": "{s}"
                \\    }}
                \\  }}
                \\}}
                \\
            , .{
                &checksum,                                  pk_hex,                                       mnemonic_str,
                printHex(&salt_hex[0], &enc_pk.salt),       printHex(&nonce_hex[0], &enc_pk.nonce),       printHex(&ct_hex[0], enc_pk.ciphertext),
                printHex(&salt_hex[1], &enc_mnemonic.salt), printHex(&nonce_hex[1], &enc_mnemonic.nonce), printHex(&ct_hex[1], enc_mnemonic.ciphertext),
            });
        } else {
            try stdout.print("\n=== EVM Wallet (Encrypted) ===\n\n", .{});
            try stdout.print("Address:    {s}\n\n", .{&checksum});
            try stdout.print("Private Key (encrypted):\n", .{});
            try printEncryptedBlock(stdout, enc_pk);
            try stdout.print("\nMnemonic (encrypted):\n", .{});
            try printEncryptedBlock(stdout, enc_mnemonic);
            try stdout.print("\nWARNING: Store your password safely. Without it, the wallet cannot be recovered.\n", .{});
        }
    } else {
        if (output_json) {
            try stdout.print(
                \\{{
                \\  "address": "{s}",
                \\  "private_key": "0x{s}",
                \\  "mnemonic": "{s}",
                \\  "encrypted": false
                \\}}
                \\
            , .{ &checksum, pk_hex, mnemonic_str });
        } else {
            try stdout.print("\n=== EVM Wallet ===\n\n", .{});
            try stdout.print("Address:      {s}\n", .{&checksum});
            try stdout.print("Private Key:  0x{s}\n\n", .{pk_hex});
            try stdout.print("Mnemonic ({d} words):\n", .{words.len});
            try stdout.print("  {s}\n\n", .{mnemonic_str});
            try stdout.print("WARNING: Save these credentials securely. Anyone with access can control your funds.\n", .{});
            try stdout.print("TIP: Use --encrypt to protect the private key with a password.\n", .{});
        }
    }

    try stdout.flush();
}

fn printHelp(writer: *Io.Writer) !void {
    try writer.print(
        \\evm-wallet - Generate EVM wallets with optional encryption
        \\
        \\USAGE:
        \\  evm-wallet [OPTIONS]
        \\
        \\OPTIONS:
        \\  -e, --encrypt     Encrypt private key and mnemonic with a password
        \\  -j, --json        Output as JSON
        \\  -h, --help        Show this help message
        \\
        \\EXAMPLES:
        \\  evm-wallet                  Generate a wallet (12-word mnemonic)
        \\  evm-wallet --encrypt        Generate and encrypt with a password
        \\  evm-wallet --json           Output wallet as JSON
        \\  evm-wallet -e -j            Encrypted wallet as JSON
        \\
    , .{});
}
