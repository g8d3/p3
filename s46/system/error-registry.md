# Error Registry

> Central log of all tool failures, fixes applied, and recurring errors.
> Updated automatically by the fixer agent and manual investigation.

---

## Current Known Issues

| # | Issue | First Seen | Last Seen | Status | Fix Applied |
|---|-------|------------|-----------|--------|-------------|
| 1 | TTS JSON escaping (special chars breaking JSON payload) | 2026-04-29 | 2026-04-29 | ✅ Fixed | `system/tts-safe.sh` created (Python-based API calls) |
| 2 | `opencode run` crashes with MemoryExhaustion | 2026-04-29 | 2026-04-29 | ✅ Fixed | `ulimit -v` removed from `parallel-launch.sh` |
| 3 | googlex.com DNS resolution failure | 2026-04-29 | 2026-04-29 | ✅ Fixed | URL corrected to x.com in task 02 |
| 4 | Gemini 3.1 preview models return 503 | 2026-04-29 | 2026-04-29 | ✅ Resolved | Fallback to gemini-3-flash-preview + gemini-2.5-flash |

## Pending Investigations

| # | Suspicion | Evidence | Needs |
|---|-----------|----------|-------|
| 5 | Invalid audio files from failed TTS calls | browser-discovery.mp3 is 101 bytes (JSON error). Old Kokoro TTS with shell variable expansion fails on special chars. | Retry with tts-inworld.sh or tts-safe.sh |
| 6 | Inworld TTS only has 1 voice ("Timothy") available | Other voice IDs return 404. Current plan supports limited voices. | Check if plan upgrade unlocks more voices, or use emotion tags creatively to vary delivery |

## Recurring Pattern Log

| Pattern | Frequency | Impact | Notes |
|---------|-----------|--------|-------|
| TTS long-text chunking | Medium (long posts) | Audio may skip chunks | `tts-inworld.sh` handles chunking with emotion cycling |

---

## How to Add an Error

```markdown
| N | Brief description | date | date | open | Workaround or fix pending |
```

## How to Check

```bash
# Scan recent logs for known error patterns
./system/fixer-agent.sh

# View all logged events
cat scheduler/logs/events.log | tail -20

# View fixer history
cat scheduler/logs/fixer.log
```
