#!/usr/bin/env python3
"""
API Benchmark - ZAI Coding Plan & OpenCode GO
Tests: availability, latency, throughput, cost, vision, reliability
"""

import os, time, json, sys, ssl, statistics, base64
from datetime import datetime
from urllib.request import Request, urlopen
from urllib.error import URLError, HTTPError

# ── Config ──
ZAI_API_KEY = os.environ.get('ZAI_API_KEY', '')
OPENCODE_GO_API_KEY = os.environ.get('OPENCODE_GO_API_KEY', '')

# NOTE: ZAI Coding Plan uses /api/coding/paas/v4, NOT the general /api/paas/v4
ZAI_BASE = "https://api.z.ai/api/coding/paas/v4"
OPENCODE_GO = "https://opencode.ai/zen/go/v1"

ZAI_MODELS = [
    "glm-4.5", "glm-4.5-air", "glm-4.6", "glm-4.7",
    "glm-5", "glm-5-turbo", "glm-5.1"
]

OPENCODE_GO_MODELS = [
    "minimax-m2.7", "minimax-m2.5", "kimi-k2.6", "kimi-k2.5",
    "glm-5.1", "glm-5", "deepseek-v4-pro", "deepseek-v4-flash",
    "qwen3.6-plus", "qwen3.5-plus", "mimo-v2-pro", "mimo-v2-omni",
    "mimo-v2.5-pro", "mimo-v2.5", "hy3-preview"
]

SSL_CTX = ssl.create_default_context()
SSL_CTX.check_hostname = False
SSL_CTX.verify_mode = ssl.CERT_NONE

PROMPTS = [
    ("Short reply", [{"role": "user", "content": "Reply with exactly: Hello world"}], 10),
    ("Python code",  [{"role": "user", "content": "Write a short Python function to reverse a string"}], 100),
    ("Simple QA",    [{"role": "user", "content": "What is 2+2? Reply with just the number"}], 10),
    ("Definition",   [{"role": "user", "content": "Explain what an API is in one sentence"}], 50),
    ("Haiku",        [{"role": "user", "content": "Write a haiku about coding"}], 80),
]

# Fetch a real image for vision tests
try:
    with urlopen('https://www.google.com/images/branding/googlelogo/2x/googlelogo_color_92x30dp.png',
                  timeout=10, context=SSL_CTX) as resp:
        VISION_IMG_B64 = base64.b64encode(resp.read()).decode()
except:
    # Fallback tiny red PNG
    VISION_IMG_B64 = 'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=='


def make_request(url, api_key, data, timeout=60):
    """Make HTTP request with consistent headers and SSL."""
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}",
        "User-Agent": "curl/8.0",
    }
    if "z.ai" in url:
        headers["Accept-Language"] = "en-US,en"
    
    req = Request(url, data=json.dumps(data).encode(), headers=headers, method="POST")
    start = time.time()
    try:
        with urlopen(req, timeout=timeout, context=SSL_CTX) as resp:
            elapsed = (time.time() - start) * 1000
            body = json.loads(resp.read())
            return {"success": True, "latency_ms": round(elapsed, 2), "body": body}
    except HTTPError as e:
        elapsed = (time.time() - start) * 1000
        err_body = e.read().decode(errors='replace')[:300]
        return {"success": False, "latency_ms": round(elapsed, 2),
                "error": f"HTTP {e.code}: {err_body}", "http_code": e.code}
    except URLError as e:
        elapsed = (time.time() - start) * 1000
        return {"success": False, "latency_ms": round(elapsed, 2),
                "error": f"Network: {e.reason}"}
    except Exception as e:
        elapsed = (time.time() - start) * 1000
        return {"success": False, "latency_ms": round(elapsed, 2), "error": str(e)}


def api_chat(base_url, model, messages, max_tokens=50, timeout=60):
    """Chat completion call."""
    url = f"{base_url}/chat/completions"
    api_key = ZAI_API_KEY if "z.ai" in base_url else OPENCODE_GO_API_KEY
    data = {"model": model, "messages": messages, "max_tokens": max_tokens, "stream": False}
    r = make_request(url, api_key, data, timeout)
    if r["success"]:
        b = r["body"]
        usage = b.get("usage", {})
        pt = usage.get("prompt_tokens", 0)
        ct = usage.get("completion_tokens", 0)
        tt = usage.get("total_tokens", 0)
        cost = float(b.get("cost", 0) or 0)
        content = b.get("choices", [{}])[0].get("message", {}).get("content", "") or ""
        finish = b.get("choices", [{}])[0].get("finish_reason", "")
        tps = (ct / (r["latency_ms"] / 1000)) if r["latency_ms"] > 0 and ct > 0 else 0
        r.update({
            "prompt_tokens": pt, "completion_tokens": ct, "total_tokens": tt,
            "cost": cost, "content_len": len(content), "finish_reason": finish,
            "tokens_per_second": round(tps, 2), "model_used": b.get("model", model),
        })
    return r


def test_vision(base_url, model):
    """Check if model supports vision using a real base64 image."""
    url = f"{base_url}/chat/completions"
    api_key = ZAI_API_KEY if "z.ai" in base_url else OPENCODE_GO_API_KEY
    data = {
        "model": model,
        "messages": [{"role": "user", "content": [
            {"type": "text", "text": "Describe this image in one word."},
            {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{VISION_IMG_B64}"}}
        ]}],
        "max_tokens": 30
    }
    r = make_request(url, api_key, data, timeout=30)
    if not r["success"]:
        return False
    content = str(r["body"].get("choices", [{}])[0].get("message", {}).get("content", "") or "")
    # Also check reasoning field (some models like Kimi put vision output there)
    reasoning = str(r["body"].get("choices", [{}])[0].get("message", {}).get("reasoning", "") or "")
    combined = (content + " " + reasoning).lower()
    # If the model responds meaningfully to image content, it supports vision
    keywords = ["google", "logo", "image", "color", "blue", "red", "yellow", "green", "letter"]
    return any(k in combined for k in keywords)


def benchmark_model(provider, model, base_url):
    """Run all benchmarks on one model."""
    print(f"  📡 {provider}/{model}...", end=" ", flush=True)
    res = {
        "provider": provider, "model": model,
        "tests": [], "success_count": 0, "error_count": 0,
        "latencies": [], "tokens_per_sec": [], "costs": [], "total_tokens_list": [],
        "vision": None
    }

    for name, msgs, max_tok in PROMPTS:
        r = api_chat(base_url, model, msgs, max_tok)
        r["test_name"] = name
        res["tests"].append(r)
        if r["success"]:
            res["success_count"] += 1
            res["latencies"].append(r["latency_ms"])
            res["tokens_per_sec"].append(r.get("tokens_per_second", 0))
            res["costs"].append(r.get("cost", 0))
            res["total_tokens_list"].append(r.get("total_tokens", 0))
        else:
            res["error_count"] += 1

    # Vision test
    res["vision"] = test_vision(base_url, model)

    # Aggregates
    n = res["success_count"]
    res["avg_latency_ms"] = round(statistics.mean(res["latencies"]), 2) if res["latencies"] else 0
    res["min_latency_ms"] = min(res["latencies"]) if res["latencies"] else 0
    res["max_latency_ms"] = max(res["latencies"]) if res["latencies"] else 0
    res["avg_tokens_per_second"] = round(statistics.mean(res["tokens_per_sec"]), 2) if res["tokens_per_sec"] else 0
    res["max_tokens_per_second"] = max(res["tokens_per_sec"]) if res["tokens_per_sec"] else 0
    res["avg_cost"] = round(statistics.mean(res["costs"]), 6) if res["costs"] else 0
    res["total_cost"] = round(sum(res["costs"]), 6) if res["costs"] else 0
    res["avg_tokens_per_call"] = round(statistics.mean(res["total_tokens_list"]), 1) if res["total_tokens_list"] else 0
    res["total_tokens_used"] = sum(res["total_tokens_list"])
    total = res["success_count"] + res["error_count"]
    res["success_rate"] = round((res["success_count"] / total) * 100, 1) if total else 0

    status = "✅" if res["success_rate"] >= 80 else ("⚠️" if res["success_rate"] >= 50 else "❌")
    print(f"{status} {res['success_count']}/{total} | "
          f"lat={res['avg_latency_ms']}ms | tps={res['avg_tokens_per_second']} | "
          f"cost=${res['avg_cost']:.6f} | vis={'✅' if res['vision'] else '❌'}")
    return res


def generate_report(all_results):
    """Build markdown report."""
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    lines = []
    lines.append("# 📊 API Benchmark Report")
    lines.append(f"**Generated:** {now}")
    lines.append(f"**ZAI API Key:** {'✅ Set' if ZAI_API_KEY else '❌ Missing'}")
    lines.append(f"**OpenCode GO API Key:** {'✅ Set' if OPENCODE_GO_API_KEY else '❌ Missing'}")
    lines.append("")

    # Summary table
    lines.append("## 📋 Model Summary\n")
    lines.append("| # | Provider | Model | Status | Avg Latency | Min | Max | Tokens/s | Cost/call | Success | Vision |")
    lines.append("|---|----------|-------|--------|-------------|-----|-----|----------|-----------|---------|--------|")
    idx = 0
    for prov, models in all_results.items():
        for m in models:
            idx += 1
            icon = "✅" if m["success_rate"] >= 80 else ("⚠️" if m["success_rate"] >= 50 else "❌")
            vis = "✅" if m.get("vision") else "❌"
            lat_str = f"{m['avg_latency_ms']}ms" if m['avg_latency_ms'] > 0 else "N/A"
            tps_str = f"{m['avg_tokens_per_second']}" if m['avg_tokens_per_second'] > 0 else "N/A"
            lines.append(
                f"| {idx} | {prov} | `{m['model']}` | {icon} | "
                f"{lat_str} | {m['min_latency_ms']}ms | {m['max_latency_ms']}ms | "
                f"{tps_str} | ${m['avg_cost']:.6f} | "
                f"{m['success_rate']}% | {vis} |"
            )

    # Best performers
    lines.append("\n## 🏆 Best Performers\n")
    for prov, models in all_results.items():
        working = [m for m in models if m["success_count"] > 0]
        if not working:
            lines.append(f"### {prov}")
            lines.append("_No models responded successfully._\n")
            continue
        best_lat = min(working, key=lambda x: x["avg_latency_ms"])
        best_tps = max(working, key=lambda x: x["avg_tokens_per_second"])
        best_rel = max(working, key=lambda x: x["success_rate"])
        lines.append(f"### {prov} ({len(working)}/{len(models)} working)")
        lines.append(f"- ⚡ **Fastest:** `{best_lat['model']}` → {best_lat['avg_latency_ms']}ms avg")
        lines.append(f"- 🚀 **Best throughput:** `{best_tps['model']}` → {best_tps['avg_tokens_per_second']} tok/s")
        lines.append(f"- 🛡️ **Most reliable:** `{best_rel['model']}` → {best_rel['success_rate']}%")
        lines.append("")

    # Vision
    lines.append("## 👁️ Vision Support\n")
    lines.append("| Provider | Model | Vision |")
    lines.append("|----------|-------|--------|")
    for prov, models in all_results.items():
        for m in models:
            vis = "✅ Yes" if m.get("vision") else "❌ No"
            lines.append(f"| {prov} | `{m['model']}` | {vis} |")
    lines.append("")

    # Detailed per-model
    lines.append("## 📈 Detailed Per-Model Results\n")
    for prov, models in all_results.items():
        for m in models:
            lines.append(f"### {prov} / `{m['model']}`\n")
            lines.append(f"- **Availability:** {m['success_rate']}% ({m['success_count']}/{m['success_count']+m['error_count']})")
            lines.append(f"- **Latency:** avg={m['avg_latency_ms']}ms | min={m['min_latency_ms']}ms | max={m['max_latency_ms']}ms")
            lines.append(f"- **Throughput:** avg={m['avg_tokens_per_second']} tok/s | max={m['max_tokens_per_second']} tok/s")
            lines.append(f"- **Cost:** ${m['avg_cost']:.6f}/call | total=${m['total_cost']:.6f}")
            lines.append(f"- **Tokens:** {m['avg_tokens_per_call']}/call | {m['total_tokens_used']} total")
            lines.append(f"- **Vision:** {'✅ Supported' if m.get('vision') else '❌ Not supported'}")
            lines.append("| # | Test | Latency | Tokens/s | Tokens | Cost | Status | Details |")
            lines.append("|---|------|---------|----------|--------|------|--------|---------|")
            for i, t in enumerate(m["tests"], 1):
                ok = "✅" if t["success"] else "❌"
                err = t.get("error", "")[:60] if not t["success"] else ""
                lines.append(f"| {i} | {t.get('test_name','')} | {t['latency_ms']}ms | "
                            f"{t.get('tokens_per_second',0)} | {t.get('total_tokens',0)} | "
                            f"${t.get('cost',0):.6f} | {ok} | {err} |")
            lines.append("")

    # Provider comparison
    lines.append("## 🆚 Provider Comparison\n")
    for prov, models in all_results.items():
        working = [m for m in models if m["success_count"] > 0]
        if not working:
            lines.append(f"### {prov}")
            lines.append("_No models available._\n")
            continue
        avg_lat = statistics.mean([m["avg_latency_ms"] for m in working])
        avg_tps = statistics.mean([m["avg_tokens_per_second"] for m in working])
        avg_cost = statistics.mean([m["avg_cost"] for m in working])
        avg_rate = statistics.mean([m["success_rate"] for m in working])
        vis_ct = sum(1 for m in models if m.get("vision"))
        lines.append(f"### {prov} ({len(working)}/{len(models)} working)")
        lines.append(f"- **Avg Latency:** {round(avg_lat, 2)}ms")
        lines.append(f"- **Avg Throughput:** {round(avg_tps, 2)} tok/s")
        lines.append(f"- **Avg Cost per Call:** ${avg_cost:.6f}")
        lines.append(f"- **Avg Success Rate:** {round(avg_rate, 1)}%")
        lines.append(f"- **Models with Vision:** {vis_ct}/{len(models)}")
        lines.append("")

    return "\n".join(lines)


def main():
    print("=" * 65)
    print("  🚀 API BENCHMARK — ZAI Coding Plan vs OpenCode GO")
    print("=" * 65)

    if not ZAI_API_KEY:
        print("❌ ZAI_API_KEY not set"); sys.exit(1)
    if not OPENCODE_GO_API_KEY:
        print("❌ OPENCODE_GO_API_KEY not set"); sys.exit(1)

    print(f"\n📋 ZAI Coding Plan ({len(ZAI_MODELS)}): {', '.join(ZAI_MODELS)}")
    print(f"📋 OpenCode GO ({len(OPENCODE_GO_MODELS)}): {', '.join(OPENCODE_GO_MODELS)}")

    all_results = {}
    t0 = time.time()

    print(f"\n{'='*65}")
    print(f"  🔥 ZAI CODING PLAN ({len(ZAI_MODELS)} models)")
    print(f"{'='*65}")
    zai_results = [benchmark_model("ZAI", m, ZAI_BASE) for m in ZAI_MODELS]
    all_results["ZAI Coding Plan"] = zai_results

    print(f"\n{'='*65}")
    print(f"  🔥 OPENCODE GO ({len(OPENCODE_GO_MODELS)} models)")
    print(f"{'='*65}")
    oc_results = [benchmark_model("OpenCode GO", m, OPENCODE_GO) for m in OPENCODE_GO_MODELS]
    all_results["OpenCode GO"] = oc_results

    elapsed = time.time() - t0
    report = generate_report(all_results)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")

    with open(f"benchmark_report_{ts}.md", "w") as f:
        f.write(report)
    with open(f"benchmark_raw_{ts}.json", "w") as f:
        json.dump(all_results, f, indent=2)

    print(f"\n{'='*65}")
    print(f"  ✅ BENCHMARK COMPLETE — {elapsed:.0f}s")
    print(f"{'='*65}\n")
    print(report)


if __name__ == "__main__":
    main()
