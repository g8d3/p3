# Text-to-Image Models — Best Value Comparison (2026)

**Principle:** Pareto efficiency — maximum quality per dollar.
We want the point where spending more gives negligible improvement.

---

## The Pareto Frontier

```
Quality
  10 │                          ★ Gemini Pro (~$0.10+/img)
     │                          
   9 │              ★ Luma Photon ($0.016) ★ FLUX 1.1 Pro ($0.04)
     │           ★ FLUX Dev ($0.025)    ★ GPT-image-2 (API)
   8 │        ★ DALL-E 3 Std ($0.04) ★ Recraft v3 ($0.04)
     │     ★ SD3.5 Medium ($0.035)
   7 │          ★ Midjourney Basic (~$0.05)  
     │       ★ Luma Flash ($0.004)
   6 │  ★ FLUX Schnell ($0.003)
     │
     └────────────────────────────────────── Cost
      $0       $0.02       $0.04       $0.06      $0.10+
```

**The sweet spot is $0.015–$0.04/image** — 90% of max quality for 10-20% of the cost.

---

## Quick Reference: All Options in One Table

| Model | Cost/Img | Quality | Resolution | Speed | API? | Best For |
|---|---|---|---|---|---|---|
| **FLUX Schnell** (Replicate) | $0.003 | 6/10 | 1024×1024 | ⚡ Very fast | ✅ | Prototyping, bulk concepts, thumbnails |
| **Luma Photon Flash 720p** | $0.002 | 6/10 | 720p | ⚡ Instant | ✅ | Ultra-budget bulk |
| **Luma Photon Flash 1080p** | $0.004 | 7/10 | 1080p | ⚡ Instant | ✅ | Budget general purpose |
| **Luma Photon 720p** | $0.008 | 8/10 | 720p | ⚡ Fast | ✅ | Quality on a budget |
| **★ Luma Photon 1080p** | **$0.016** | **9/10** | **1080p** | **⚡ Fast** | **✅** | **🥇 BEST VALUE** |
| **FLUX Dev** (Replicate) | $0.025 | 8/10 | 1024×1024 | 🟡 Medium | ✅ | Reliable quality |
| **SD 3.5 Medium** (Stability API) | $0.035 | 7/10 | 1024×1024 | ⚡ Fast | ✅ | Open-source cloud |
| **FLUX 1.1 Pro** (Replicate) | $0.040 | 9/10 | Up to 1440×1440 | ⚡ Fast | ✅ | Top-tier, proven |
| **DALL-E 3** Standard | $0.040 | 8/10 | 1024×1024 | 🟡 Medium | ✅ | Text rendering, reliable |
| **Recraft v3** | $0.040 | 8/10 | High res | ⚡ Fast | ✅ | Graphic design, SVG, branding |
| **Midjourney Basic** | ~$0.05 | 8/10 | High res | ⚡ Fast | ❌ No official API | Artistic/cinematic |
| **Ideogram v3** (Replicate) | $0.090 | 8/10 | High res | ⚡ Fast | ✅ | Best text-in-image |
| **DALL-E 3** HD | $0.160 | 9/10 | 1792×1024 | 🟡 Medium | ✅ | Max quality per-shot |

---

## Free / Local (Self-Hosted)

If you have a GPU, these cost $0/image after hardware:

| Model | Quality | VRAM | Resolution | Speed (4090) | License | Notes |
|---|---|---|---|---|---|---|
| **FLUX.1-dev** | 9/10 | 12-24 GB | 1024×1024 | 30-60s | Non-commercial weights | Highest quality local |
| **FLUX.1-schnell** | 6-7/10 | 8 GB+ | 1024×1024 | ⚡ Fast (4-8 steps) | Apache 2.0 | Fast local gen |
| **SD 3.5 Large** | 8/10 | 16 GB (8 quantized) | 1024×1024 | 🟡 Medium | Community license | Best open local |
| **SD 3.5 Medium** | 7-8/10 | 8 GB | 1024×1024 | ⚡ Fast | Community license | Good quality, lower HW |
| **SDXL** | 7/10 | 8 GB | 1024×1024 | 🟡 Medium | Open RAIL++-M | Mature ecosystem |
| **SD 1.5** | 5/10 | 4 GB | 512×512 | ⚡ Fast | Open RAIL-M | Runs anywhere |

---

## Recommended for Our Pipeline

### Primary (API-based, cost matters)
**🥇 Luma Photon 1080p @ $0.016/image**
- 9/10 quality (independent benchmarks beat FLUX 1.1 and Midjourney)
- 3x cheaper than FLUX 1.1 Pro
- Has API, character consistency, ComfyUI support
- For video content: ~6-10 images per video → $0.10-0.16/video cost

### Fallback (even cheaper)
**Luma Photon Flash 1080p @ $0.004/image**
- Used when quality isn't critical (e.g., concept illustration)
- 7/10 quality — perfectly adequate for background visuals

### For experimentation / local (if GPU available)
**FLUX.1-schnell** (Apache 2.0, 8GB VRAM)
- Fast, free, good enough for concept generation
- Can run on lower-end GPUs

---

## Integration with Pipeline

```
Script → Extract visual keywords → Luma API → Generate images
                                              ↓
        Stock footage (Pexels) ←───────┬────→ AI images
                                        ↓
                              Video assembler interleaves
                              both with screen recording
                                        ↓
                                    final video
```

Images would be used for:
- **Concept illustrations** — "what if this but better" visual comparisons
- **Meme-style reactions** — custom images for punchlines
- **Section dividers** — themed title cards between script sections
- **Thumbnail generation** — video thumbnail from the most visual moment

---

## Sample Cost Projection

| Usage | Images/Video | Cost/Image | Total Cost/Video |
|---|---|---|---|
| Thumbnail only | 1 | $0.016 | $0.016 |
 | Illustrations | 4 | $0.016 | $0.064 |
| Heavy visuals + thumbnail | 10 | $0.016 | $0.16 |
| Ultra-budget (Flash) | 10 | $0.004 | $0.04 |

Compare to: ElevenLabs TTS ($0.05/video), Kokoro TTS ($0.003/video),
Kling video gen ($5+/video). Image generation is negligible cost.

---

## Recommendation

**Use Luma Photon 1080p ($0.016/image).**
At ~$0.10/video for illustrations, it's the best Pareto point — 90% of the
quality of the most expensive models for a fraction of the cost.
