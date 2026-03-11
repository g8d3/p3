# Project Metrics & Logs

## Session: No-Mnemonic Wallet Implementation

### Real Data (Not Human Metaphors)

**Active Time:** ~3 hours total
**Failed API Calls:** 12+
- AIMLAPI key invalid (500 errors) - 5 attempts
- SSML tags spoken literally - 3 attempts  
- Text too long (>2000 chars) - 4 attempts

**Successful API Calls:** 8 (Inworld Direct TTS)

### Cost Tracking

| Item | Cost |
|------|------|
| Inworld TTS | ~$0.02 (2,000 chars processed) |
| Compute | Minimal (local) |

### Key Frictions Encountered

1. **AIMLAPI Key Invalid** - The provided key didn't work on their API. Had to find Inworld Direct API.
2. **SSML Not Supported** - Inworld only supports `<break>` tags, not full SSML. Bracket tags `[happy]` are experimental and get spoken literally.
3. **Text Length Limit** - 2000 char max per request. Had to chunk content.
4. **No YouTube Auth** - Browser session has no Google account. OAuth setup required for autonomous uploads.

### What Worked

- Inworld Direct API with Basic auth
- Plain text only (no markup)
- Chunking + speed adjustment to match video

### What Needs Improvement

- Audio ends abruptly (no fade)
- Generic slide text
- No real wallet addresses shown
- No transaction hashes
- Script sounds like a human, not an AI

### Version History

| Version | Date | Description |
|---------|------|-------------|
| v1 | 2026-03-10 | Generic tutorial style - archived |
| v2 | TBD | Autonomous AI voice - in progress |

---

*This log is part of the autonomous builder archive.*