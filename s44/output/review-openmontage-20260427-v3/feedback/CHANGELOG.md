# v003 — Volume Fix + Visual Upgrades

## What changed
- **Volume:** narration boosted 3x, dropout_transition=0 removed fade-dips
- **SFX:** normalize=0 prevents volume drop when SFX play (was dividing by input count)
- **SFX density:** 17 cues (was 8 in v002) — typing sounds, risers, applause
- **Gaps:** 0.15s between paragraphs (was 0.3s) — tighter pacing
- **Overlays:** 4 meme gags (sad sandwich, mind blown, 69¢, terminal intro)
- **Callouts:** 3 info cards (12 pipelines, 52 tools, 69¢)
- **Timing:** exact per-paragraph (measured via ffprobe, not estimated)

## Known issues
- Ken Burns zoom: broken in ffmpeg 6.1 (zoompan filter bug in Ubuntu package)
- No B-roll footage: recording is still a single GitHub page looped
- No word-level animated captions: needs TTS engine with per-word timestamps
- Music: chord-progression synth, not yet synthwave/cyberpunk genre
