#!/usr/bin/env python3
"""
Classify 384 repos — final version.
Strategy: description + topics first, README as fallback.
"""
import json, os, re
from collections import Counter

REPOS_JSON = "all_384_repos.json"
README_DIR = "readmes_raw"
OUTPUT = "repos_clasificados_384.json"

with open(REPOS_JSON) as f:
    data = json.load(f)
repos = data["items"]

def readme_head(full_name, chars=1200):
    safe = full_name.replace("/", "_")
    path = os.path.join(README_DIR, f"{safe}.md")
    if os.path.exists(path):
        try:
            with open(path, "r", errors="ignore") as f:
                return f.read(chars)
        except: pass
    return ""

# --- Well-known coding agent identifiers ---
CODING_HARNESSES = {
    "crush", "goose", "codex", "opencode", "jcode", "zeroclaw", "goclaw",
    "kwaak", "refact", "golutra", "pi_agent", "catnip", "maki", "oli",
    "herm", "ralph",
    "rsclaw", "maxclaw", "microclaw", "bizclaw", "tyclaw", "wireclaw",
    "thclaws",  "klawsh",
}

def classify(repo):
    name = repo["full_name"]
    owner, rname = name.split("/")
    desc = repo.get("description") or ""
    topics = " ".join(repo.get("topics") or [])
    readme = readme_head(name)
    dt = f"{desc} {topics}".lower()
    dt_full = f"{desc} {topics} {readme}".lower()

    # ---- OVERRIDES ----
    overrides = {
        # CODING_AGENT overrides
        "aws/amazon-q-developer-cli": "CODING_AGENT",
        "wandb/catnip": "CODING_AGENT",
        "Dicklesworthstone/pi_agent_rust": "CODING_AGENT",
        "Dicklesworthstone/ntm": "CODING_AGENT",
        "bosun-ai/kwaak": "CODING_AGENT",
        "tontinton/maki": "CODING_AGENT",
        "amrit110/oli": "CODING_AGENT",
        "the-open-agent/openagent": "CODING_AGENT",
        # ORCHESTRATOR
        "chenhg5/cc-connect": "ORCHESTRATOR",
        "AgentsMesh/AgentsMesh": "ORCHESTRATOR",
        "nixopus/nixopus": "ORCHESTRATOR",
        "rivet-dev/rivet": "ORCHESTRATOR",
        "katanemo/plano": "ORCHESTRATOR",
        "helmix/helix": "ORCHESTRATOR",
        "kubeshark/kubeshark": "ORCHESTRATOR",
        "asheshgoplani/agent-deck": "ORCHESTRATOR",
        "mlhher/late-cli": "ORCHESTRATOR",
        "aannoo/hcom": "ORCHESTRATOR",
        "mathomhaus/guild": "ORCHESTRATOR",
        "hiroppy/tmux-agent-sidebar": "ORCHESTRATOR",
        "illegalstudio/lazyagent": "ORCHESTRATOR",
        "madebyaris/native-cli-ai": "ORCHESTRATOR",
        "this-rs/project-orchestrator": "ORCHESTRATOR",
        "junhoyeo/contrabass": "ORCHESTRATOR",
        "TechDufus/openkanban": "ORCHESTRATOR",
        "fy0/CodeKanban": "ORCHESTRATOR",
        # OTHER_AI_AGENT
        "1Panel-dev/1Panel": "OTHER_AI_AGENT",
        "mudler/LocalAGI": "OTHER_AI_AGENT",
        "graykode/abtop": "OTHER_AI_AGENT",
        "vercel-labs/opensrc": "OTHER_AI_AGENT",
        "memovai/mimiclaw": "OTHER_AI_AGENT",
        "53AI/53AIHub": "OTHER_AI_AGENT",
        "entireio/cli": "OTHER_AI_AGENT",
        "reyamira/models": "OTHER_AI_AGENT",
        "jfernandez/mdserve": "OTHER_AI_AGENT",
        "agent-sh/agnix": "OTHER_AI_AGENT",
        "regent-vcs/re_gent": "OTHER_AI_AGENT",
        "RealZST/HarnessKit": "OTHER_AI_AGENT",
        "AkaraChen/aghub": "OTHER_AI_AGENT",
        "bitloops/bitloops": "OTHER_AI_AGENT",
        "Dicklesworthstone/meta_skill": "OTHER_AI_AGENT",
        "Dicklesworthstone/coding_agent_account_manager": "OTHER_AI_AGENT",
        "QingJ01/Clyde": "OTHER_AI_AGENT",
        "cortexkit/aft": "OTHER_AI_AGENT",
        "erans/lunaroute": "OTHER_AI_AGENT",
        "ZhangHanDong/mempal": "OTHER_AI_AGENT",
        "kenn-io/kata": "OTHER_AI_AGENT",
        # AGENT_SANDBOX
        "NVIDIA/OpenShell": "AGENT_SANDBOX",
        "strongdm/leash": "AGENT_SANDBOX",
        "akitaonrails/ai-jail": "AGENT_SANDBOX",
        "superradcompany/microsandbox": "AGENT_SANDBOX",
        "robcholz/vibebox": "AGENT_SANDBOX",
        "GreyhavenHQ/greywall": "AGENT_SANDBOX",
        "dtormoen/tsk-tsk": "AGENT_SANDBOX",
        "vrn21/bouvet": "AGENT_SANDBOX",
        "DecapodLabs/decapod": "AGENT_SANDBOX",
        # MCP_TOOL
        "vkhanhqui/figma-mcp-go": "MCP_TOOL",
        "matlab/matlab-mcp-core-server": "MCP_TOOL",
        "googleapis/mcp-toolbox": "MCP_TOOL",
        "Tencent/WeKnora": "MCP_TOOL",
        "bartolli/codanna": "MCP_TOOL",
        "sammcj/mcp-devtools": "MCP_TOOL",
        "aovestdipaperino/tokensave": "MCP_TOOL",
        "mrjoshuak/godoc-mcp": "MCP_TOOL",
        # DATABASE
        "pingcap/tidb": "DATABASE",
        "risingwavelabs/risingwave": "DATABASE",
        "MaterializeInc/materialize": "DATABASE",
        "activeloopai/deeplake": "DATABASE",
        "spiceai/spiceai": "DATABASE",
        "rilldata/rill": "DATABASE",
        # MEMORY_RAG
        "Gentleman-Programming/engram": "MEMORY_RAG",
        "yvgude/lean-ctx": "MEMORY_RAG",
        # SECURITY
        "kaplanelad/shellfirm": "SECURITY",
        "eqtylab/cupcake": "SECURITY",
        "ironsh/iron-sensor": "SECURITY",
        "safedep/gryph": "SECURITY",
        # DEVKIT_SDK
        "0xPlaygrounds/rig": "DEVKIT_SDK",
        "severity1/claude-agent-sdk-go": "DEVKIT_SDK",
        # CLI_TOOL
        "googleworkspace/cli": "CLI_TOOL",
        "larksuite/cli": "CLI_TOOL",
        "infracost/infracost": "CLI_TOOL",
        "nekocode/agent-worktree": "CLI_TOOL",
        # BROWSER_AUTOMATION
        "remorses/usecomputer": "BROWSER_AUTOMATION",
        # UNRELATED
        "qax-os/excelize": "UNRELATED",
        "metalbear-co/mirrord": "UNRELATED",
    }
    if name in overrides:
        return overrides[name]

    # ---- CODING_AGENT: actual agents that write code ----
    # 1a) By harness name
    if rname.lower() in CODING_HARNESSES:
        return "CODING_AGENT"
    # 1b) Direct description match
    if re.search(r"(^|\s)(coding|code)\s*(agent|assistant|harness|cli)", dt):
        return "CODING_AGENT"
    if re.search(r"agentic\s+coding|self.evolving.*coding.*agent|efficient\s+ai\s+coding\s+agent", dt):
        return "CODING_AGENT"
    if re.search(r"terminal.native.*coding.*agent|high.performance.*coding.*agent.*cli", dt):
        return "CODING_AGENT"
    if re.search(r"an?\s+(open.source\s+)?(extensible\s+)?ai\s+agent.*(beyond\s+)?code", dt_full):
        return "CODING_AGENT"
    if "multi-agent terminal collaboration" in dt:
        return "CODING_AGENT"
    # 1c) README confirms coding agent
    if re.search(r"(coding|code)\s+agent|agentic\s+coding", readme[:500].lower()):
        return "CODING_AGENT"

    # ---- BROWSER_AUTOMATION ----
    if re.search(r"browser\s+automation.*(ai|agent|cli)", dt):
        return "BROWSER_AUTOMATION"
    if re.search(r"headless\s+browser.*(ai|agent)", dt):
        return "BROWSER_AUTOMATION"

    # ---- DATABASE ----
    if re.search(r"(sql|distributed|vector|graph|multi.model)\s+database|data\s+warehouse|data\s+integration\s+platform|business\s+intelligence", dt):
        return "DATABASE"

    # ---- MCP_TOOL ----
    if re.search(r"mcp\s+(server|tool|protocol|client|gateway|proxy|agent)", dt):
        return "MCP_TOOL"
    if re.search(r"model\s+context\s+protocol", dt):
        return "MCP_TOOL"

    # ---- AGENT_SANDBOX ----
    if re.search(r"sandbox.*(ai\s+)?agent|agent.*sandbox", dt):
        return "AGENT_SANDBOX"
    if re.search(r"(microvm|micro[\s-]*sandbox|cube\s*sandbox|agent\s+runtime)", dt):
        return "AGENT_SANDBOX"
    if re.search(r"(safe|private|isolated|secure)\s+runtime.*(agent|ai)", dt):
        return "AGENT_SANDBOX"
    if re.search(r"operating\s+system\s+for\s+(agents|ai)", dt):
        return "AGENT_SANDBOX"
    if "platform" in dt and "agent" in dt and "sandbox" in readme[:500].lower():
        return "AGENT_SANDBOX"

    # ---- SECURITY (only from description + topics, not README) ----
    if re.search(r"penetration\s+testing|pentest|exploit.*(ai|agent)|vulnerab.*(scan|detect)", dt):
        return "SECURITY"
    if re.search(r"secret.*(vault|protect|scan).*(dev|agent|ai)", dt):
        return "SECURITY"
    if re.search(r"(agent|ai)\s*firewall|agent.*control\s+plane", dt):
        return "SECURITY"
    if re.search(r"terminal\s+security.*(agent|dev)", dt):
        return "SECURITY"
    if re.search(r"ai.*agent.*(guardrail|safety)", dt):
        return "SECURITY"

    # ---- MEMORY_RAG ----
    if re.search(r"(memory|rag|retrieval|knowledge)\s+(layer|system|store|engine|graph|base).*(agent|ai)", dt):
        return "MEMORY_RAG"
    if re.search(r"persistent\s+memory.*(agent|ai)", dt):
        return "MEMORY_RAG"

    # ---- DEVKIT_SDK ----
    if re.search(r"(agent\s+(development\s+)?kit|\badk\b|sdk.*(building|agent|ai))", dt):
        return "DEVKIT_SDK"
    if re.search(r"(framework|toolkit).*(building|agent|ai|llm)", dt):
        return "DEVKIT_SDK"

    # ---- CLI_TOOL ----
    if re.search(r"all.in.one\s+llm\s+cli|official.*cli|workspace.*cli", dt):
        return "CLI_TOOL"

    # ---- ORCHESTRATOR ----
    if re.search(r"orchestrat.*(agent|workflow|task|engine|platform)", dt):
        return "ORCHESTRATOR"
    if re.search(r"multi.agent.*(orchestrat|platform|coordinate|collaborat|swarm)", dt):
        return "ORCHESTRATOR"
    if re.search(r"manage\s+multiple.*(agent|terminal)", dt):
        return "ORCHESTRATOR"
    if re.search(r"agent.*(workflow|loop|coordinate|swarm)", dt):
        return "ORCHESTRATOR"
    if "(agent|ai).*(platform|orchestrat).*(workforce|team)" in dt:
        return "ORCHESTRATOR"

    # ---- OTHER_AI_AGENT ----
    if re.search(r"\bai\s+agent\b|autonomous\s+agent|multi.agent|agentic\b", dt):
        return "OTHER_AI_AGENT"
    if re.search(r"(agent|ai)\s+(workload|platform|runtime|service|app|system)", dt):
        return "OTHER_AI_AGENT"

    # ---- Fallback ----
    nl = name.lower()
    if any(w in nl for w in ["agent", "ai", "llm", "gpt", "claw"]):
        return "OTHER_AI_AGENT"
    return "UNRELATED"

# Run
results = []
for repo in repos:
    cat = classify(repo)
    results.append({
        "name": repo["full_name"],
        "stars": repo["stargazers_count"],
        "language": repo.get("language") or "Unknown",
        "description": (repo.get("description") or "")[:150],
        "category": cat,
        "url": repo["html_url"],
    })

stats = Counter(r["category"] for r in results)
print(f"Total: {len(results)} repos\n")
print(f"{'Categoría':<25} {'Count':>6}")
print("-" * 33)
for cat, count in stats.most_common():
    pct = count / len(results) * 100
    print(f"{cat:<25} {count:>5}  ({pct:.0f}%)")

grouped = {}
for r in results:
    grouped.setdefault(r["category"], []).append(r)
for cat in grouped:
    grouped[cat].sort(key=lambda x: x["stars"], reverse=True)

output = {
    "stats": dict(stats.most_common()),
    "total_repos": len(results),
    "search_query": "ai+agent language:Rust,go,C++,zig,c stars:>100 pushed:>2026-01-01",
    "categories": {cat: grouped[cat] for cat in grouped},
}
with open(OUTPUT, "w") as f:
    json.dump(output, f, indent=2, ensure_ascii=False)

# Markdown report
with open("CLASIFICACION_384.md", "w") as f:
    f.write("# Clasificación de 384 Repositorios AI Agent\n\n")
    f.write("**Búsqueda:** `ai agent` en Rust, Go, C++, Zig, C | Stars > 100 | Push > 2026-01-01\n\n")
    f.write(f"**Total:** {len(results)} repos | **{stats['CODING_AGENT']} coding agents** (como Crush)\n\n")
    f.write("## Resumen\n\n")
    f.write("| Categoría | Count | % |\n")
    f.write("|----------|------|---|\n")
    for cat, count in stats.most_common():
        f.write(f"| **{cat}** | **{count}** | {count/len(results)*100:.0f}% |\n")
    f.write("\n---\n\n")
    for cat in ["CODING_AGENT", "OTHER_AI_AGENT", "ORCHESTRATOR", "MCP_TOOL", "AGENT_SANDBOX", "SECURITY", "DEVKIT_SDK", "MEMORY_RAG", "BROWSER_AUTOMATION", "CLI_TOOL", "DATABASE", "UNRELATED"]:
        items = grouped.get(cat, [])
        if not items: continue
        f.write(f"## {cat} ({len(items)} repos)\n\n")
        f.write("| Stars | Repo | Language | Description |\n")
        f.write("|------|------|----------|-------------|\n")
        for r in items[:50]:
            safe_desc = r["description"][:80].replace("|", "\\|") if r["description"] else ""
            f.write(f"| {r['stars']}★ | [{r['name']}]({r['url']}) | {r['language']} | {safe_desc} |\n")
        if len(items) > 50:
            f.write(f"| ... | ({len(items)-50} more) | | |\n")
        f.write("\n---\n\n")

print(f"\nSaved: {OUTPUT}, CLASIFICACION_384.md")
