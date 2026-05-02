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
| 7 | Disk critically full (89-90%, sustained 48+ hours) | 2026-04-29 | 2026-05-01 | 🔴 open | Free up disk space; monitor with `df -h` |
| 8 | Fixer applying redundant TTS JSON escaping fixes across runs | 2026-04-29 | 2026-04-30 | ⚠️ open | Investigate whether `tts-safe.sh` is being bypassed for some content |

## Pending Investigations

| # | Suspicion | Evidence | Needs |
|---|-----------|----------|-------|
| 5 | Invalid audio files from failed TTS calls | browser-discovery.mp3 was 101 bytes (JSON error) — now cleaned up. All 6 current audio files are valid. | ✅ Resolved — stale file removed; verify on next content generation |
| 6 | Inworld TTS only has 1 voice ("Timothy") available | Other voice IDs return 404. Current plan supports limited voices. | Check if plan upgrade unlocks more voices, or use emotion tags creatively to vary delivery |
| 7 | Disk usage at 90% may cause TTS or content generation failures | Events log shows sustained 89-90% disk usage since Apr 29 22:01, worsening to 90%. Monitoring frequency increased to 30s intervals on May 1. | Identify largest directories (`du -sh /*`), clean up old audio/temp files, or expand storage |

## Recurring Pattern Log

| Pattern | Frequency | Impact | Notes |
|---------|-----------|--------|-------|
| TTS long-text chunking | Medium (long posts) | Audio may skip chunks | `tts-inworld.sh` handles chunking with emotion cycling |
| TTS JSON escaping fix re-applied | Each fixer run (at least 3 runs, 5 fixes) | Redundant cycles; indicates root cause not eliminated | Check if new content bypasses `tts-safe.sh` or if fix is applied per-file without persistence |

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
