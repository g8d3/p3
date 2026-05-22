#!/usr/bin/env python3
"""
Comprehensive classification of GitHub AI repos from CSV.
Reads gh_search_results.csv, classifies each repo, updates the CSV,
and generates repos_clasificados.json with detailed analysis.
"""

import csv
import json
import re
import os

CSV_PATH = "/home/vuos/code/p3/s54-gh-repo-readmes/gh_search_results.csv"
OUTPUT_JSON = "/home/vuos/code/p3/s65/repos_clasificados.json"

def load_csv(path):
    rows = []
    with open(path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            rows.append(row)
    return rows

def save_csv(path, rows):
    if not rows:
        return
    fieldnames = rows[0].keys()
    with open(path, 'w', encoding='utf-8', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def classify_repo(row):
    """
    Classify a repo based on name, description, topics, and readme.
    Strategy: hard-coded name overrides first (most precise), then regex.
    """
    name = (row.get('name', '') or '').lower()
    description = (row.get('description', '') or '').lower()
    topics = (row.get('topics', '') or '').lower()
    readme = (row.get('readme', '') or '').lower()
    
    text = f"{name} {description} {topics} {readme}"
    
    # =========================================================
    # PHASE 1: HARD-CODED NAME-BASED OVERRIDES (most precise)
    # =========================================================
    
    # -- DATABASE --
    if re.search(r'(pingcap/tidb|databend|risingwave|materializeinc/materialize|spiceai/spiceai|matrixorigin/(matrixone|memoria)|rilldata/rill|zunor/paro)', name):
        return 'DATABASE'
    if name.startswith('pingcap/'):
        return 'DATABASE'
    
    # -- OTHER (not relevant) --
    if re.search(r'(1panel-dev/1panel|qax-os/excelize|kubeshark/kubeshark|chenhg5/cc-connect|ghuntley/how-to-build-a-coding-agent|googleworkspace/cli|larksuite/cli|rivet-dev/rivet|yaoapp/yao|53ai/53aihub|second-state/echokit_server|rivet-dev/rivet)', name):
        return 'OTHER'
    if 'onflow/flow' in name:
        return 'OTHER'
    if 'zeroclaw-labs/zeroclaw' in name:
        return 'OTHER'
    if 'nixopus/nixopus' in name:
        return 'OTHER'
    if 'diggerhq/opencomputer' in name:
        return 'AGENT_SANDBOX'
    if 'materializeinc/materialize' in name:
        return 'DATABASE'
    
    # -- BROWSER_AUTOMATION --
    if re.search(r'(vercel-labs/agent-browser|h4ckf0r0day/obscura|vibiumdev/vibium|mediar-ai/terminator|gsd-build/gsd-browser|embedding-shapes/one-agent-one-browser|actionbook/actionbook|browserwing/browserwing|kernel/kernel-images)', name):
        return 'BROWSER_AUTOMATION'
    if 'lahfir/agent-desktop' in name:
        return 'BROWSER_AUTOMATION'
    
    # -- MCP_TOOL --
    if re.search(r'(googleapis/mcp-toolbox|vkhanhqui/figma-mcp-go|matlab/matlab-mcp-core-server|samvallad33/vestige|gojue/moling|smart-mcp-proxy/mcpproxy-go|ckanthony/openapi-mcp|paiml/paiml-mcp-agent-toolkit|sammcj/mcp-devtools|soth-ai/mcp-reticle|devwhodevs/engraph|saidutt46/domain-check|agent-sh/agnix|permit0-ai/permit0|agentregistry-dev/agentregistry|pgedge/pgedge-postgres-mcp|alash3al/stash|compresr-ai/context-gateway)', name):
        return 'MCP_TOOL'
    if 'step-security/dev-machine-guard' in name:
        return 'MCP_TOOL'
    if 'realzst/harnesskit' in name:
        return 'MCP_TOOL'
    if 'marmotdata/marmot' in name:
        return 'MCP_TOOL'
    if 'agentgateway/agentgateway' in name:
        return 'MCP_TOOL'
    
    # -- AGENT_SANDBOX --
    if re.search(r'(superradcompany/microsandbox|nvidia/openshell|tencentcloud/cubesandbox|cubesandbox|rivet-dev/agent-os|kubernetes-sigs/agent-sandbox|agent-sandbox/agent-sandbox|superhq-ai/shuru|zerobootdev/zeroboot|capsulerun/capsule|greyhavenhq/greywall|jingkaihe/matchlock|dtormoen/tsk-tsk|ashishb/amazing-sandbox|akihirosuda/alcless|dredozubov/hazmat|akitaonrails/ai-jail|parcadei/ouros|xiaods/k8e|mattolson/agent-sandbox|th0rgal/sandboxed\.sh|bytedance/varmor)', name):
        return 'AGENT_SANDBOX'
    if 'superhq-ai/superhq' in name:
        return 'AGENT_SANDBOX'
    
    # -- SECURITY --
    if re.search(r'(vxcontrol/pentagi|armur-ai/pentest-swarm-ai|xalgord/xalgorix|wardgate/wardgate|sleuthco/clawshield-public|glitchedgitz/grroxy|innerwarden/innerwarden|clawvisor/clawvisor|cisco-ai-defense/defenseclaw|bakelens/crust|m4xxxxx/aixvuln|the-17/agentsecrets|strongdm/leash|sheeki03/tirith|safedep/pmg|safedep/gryph|canyonroad/agentsh|eqtylab/cupcake|rhino-acoustic/neuronfs|kontext-security/kontext-cli|mathematic-inc/earl|infisical/agent-vault|kaplanelad/shellfirm)', name):
        return 'SECURITY'
    if 'lucky' in name and 'pipelock' in name:
        return 'SECURITY'
    if 'cordum-io/cordum' in name:
        return 'SECURITY'
    if 'stephengangue/warden' in name:
        return 'SECURITY'
    if 'clawshell/clawshell' in name:
        return 'SECURITY'
    
    # -- CODING_AGENT (explicit examples from task + clear coding agent harnesses) --
    coding_agent_names = [
        'aaif-goose/goose', 'charmbracelet/crush', '1jehuang/jcode',
        'smallcloudai/refact', 'smtg-ai/claude-squad',
        'mikeyobrien/ralph-orchestrator',
        # Other clear coding agents
        'dicklesworthstone/pi_agent_rust',
        'aws/amazon-q-developer-cli',
        'wandb/catnip',
        'tontinton/maki',
        'bosun-ai/kwaak',
        'codeany-ai/codeany',
        'aduermael/herm',
        'thclaws/thclaws',
        'amrit110/oli',
        'zhanghandong/agent-spec',
        'r1n7aro/locus',
        'liuxiaopai-ai/ralph-desktop',
        'yologdev/yoyo-evolve',
    ]
    for cn in coding_agent_names:
        if cn in name:
            return 'CODING_AGENT'
    
    # -- DEVKIT_SDK --
    if re.search(r'(google/adk-go|0xplaygrounds/rig|trpc-group/trpc-agent-go|ingenimax/agent-sdk-go|zavora-ai/adk-rust|jetify-com/ai|opper-ai/opperator|looplj/axonhub|nlpodyssey/openai-agents-go|agenticgokit/agenticgokit|stellarlinkco/agentsdk-go|modu-ai/moai-adk|go-kratos/blades|charmbracelet/fantasy|ldclabs/anda|m-mizutani/gollem|deepnoodle-ai/dive|brekkylab/ailoy|wiseaidotdev/autogpt|clearloop/walrus|crabtalk/crabtalk)', name):
        return 'DEVKIT_SDK'
    if 'tuyoogame/tyclaw' in name:
        return 'DEVKIT_SDK'
    if 'yomorun/yomo' in name:
        return 'DEVKIT_SDK'
    if 'liquid os-ai/autoagents' in name or 'autoauth' in name:
        return 'DEVKIT_SDK'
    if 'infinitibit/graphbit' in name:
        return 'DEVKIT_SDK'
    if 'eastreams/loong' in name:
        return 'DEVKIT_SDK'
    
    # -- MEMORY_RAG --
    if re.search(r'(memvid/memvid|canner/wrenai|tencent/weknora|screenpipe/screenpipe|dmtrkovalenko/fff|gentleman-programming/engram|memohai/memoh|limecloud/lime|iwe-org/iwe|rtk-ai/icm|sopaco/deepwiki-rs|mnemon-dev/mnemon|ourmem/omem|lightningrag/lightningrag|mathomhaus/guild|zhimaai/chatclaw|kweaver-ai/kweaver-core|angelnicolasc/graymatter|varun29ankus/shodh-memory|yantrikos/yantrikdb-server|zhanhandong/mempal|matrixorigin/memoria|dicklesworthstone/meta_skill)', name):
        return 'MEMORY_RAG'
    if 'lighthart-labs/dreamserver' in name:
        return 'MEMORY_RAG'
    if 'describo' in name:
        return 'MEMORY_RAG'
    
    # -- ORCHESTRATOR (by name) --
    if re.search(r'(hatchet-dev/hatchet|katanemo/plano|coze-dev/coze-loop|the-open-agent/openagent|docker/docker-agent|kocoro-lab/shannon|thousandbirdsinc/chidori|adolfousier/opencrabs|klawsh/klaw\.sh|nwiizo/ccswarm|junhoyeo/contrabass|this-rs/project-orchestrator|kevinelliott/agentpipe|nextlevelbuilder/goclaw|golutra/golutra|kelos-dev/kelos|kdlbs/kandev|madebyaris/native-cli-ai|goldziher/ai-rulez|agentfield/agentfield|agentsmesh/agentsmesh|agent-fm/agentfm-core|mlhher/late-cli|sympozium-ai/sympozium|versuscontrol/versus-incident|graniet/llm|pacficstudio/openase|decapodlabs/decapod|rapidaai/voice-ai|harvard-cns/orla|huanchong-99/solodawn)', name):
        return 'ORCHESTRATOR'
    if 'openclaw-rocks/openclaw-operator' in name:
        return 'ORCHESTRATOR'
    if 'mudrii/openclaw-dashboard' in name:
        return 'CLI_TOOL'
    
    # -- CLI_TOOL (by name) --
    if re.search(r'(sigoden/aichat|entireio/cli|max-sixty/worktrunk|graykode/abtop|asheshgoplani/agent-deck|mvanhorn/cli-printing-press|samber/cc-skills-golang|qufei1993/skills-hub|ogulcancelik/herdr|neiii/bridle|reyamira/models|nowledge-co/con-terminal|hookdeck/hookdeck-cli|geekjourneyx/jina-cli|erickochen/purple|fy0/codekanban|robcholz/vibebox|illegalstudio/lazyagent|dynatrace-oss/dtctl|yuanchuan/aivo|subinium/agf|madeye/mcp-cli|dicklesworthstone/coding_agent_account_manager|erans/lunaroute|wesm/kata|severity1/claude-agent-sdk-go|m7medvision/lazycommit|bgdnvk/clanker|xingkongliang/skills-manager|specstoryai/getspecstory|akarachen/aghub|jrswab/axe|suitedaces/computer-agent|dingtalk-real-ai/dingtalk-workspace-cli|wecomteam/wecom-cli|quailyquaily/aqua|tang-vu/contribai|hiroppy/tmux-agent-sidebar|eljulians/skillfile|arkylab/aspm|chenhg5/agencycli|babelcloud/gbox|enriquefft/openclaw-kapso-whatsapp|regent-vcs/re_gent|aannoo/hcom|nekocode/agent-worktree|ind-igo/cx|dicklesworthstone/ntm|jfernandez/mdserve|vercel-labs/opensrc|voltr0py/mog)', name):
        return 'CLI_TOOL'
    if 'qingj01/clyde' in name:
        return 'OTHER'
    if 'voocel/ainovel-cli' in name:
        return 'OTHER'
    if 'lighthart-labs/dreamserver' in name:
        return 'MEMORY_RAG'
    if 'run-bigpig/jcp' in name:
        return 'OTHER'
    
    # =========================================================
    # PHASE 2: REGEX-BASED CLASSIFICATION (broader patterns)
    # =========================================================
    
    # Database
    if re.search(r'(distributed\s+)?sql\s+database', text):
        return 'DATABASE'
    if re.search(r'data\s+(warehouse|agent\s+ready)', text):
        return 'DATABASE'
    
    # Browser automation
    if re.search(r'browser\s+automation\s+(cli\s+)?for\s+ai', text):
        return 'BROWSER_AUTOMATION'
    if re.search(r'headless\s+browser\s+for', text):
        return 'BROWSER_AUTOMATION'
    
    # MCP
    if re.search(r'\bmcp\s+server\b', text) and 'sandbox' not in text:
        if not re.search(r'(platform|orchestrat|workflow)', text):
            return 'MCP_TOOL'
    if re.search(r'\bmcp\s+toolbox\b', text):
        return 'MCP_TOOL'
    
    # Sandbox
    if re.search(r'(sandbox|microvm|isolated\s+runtime).*(ai\s+)?agent', text) and not re.search(r'(framework|sdk|kit|manager)', text):
        return 'AGENT_SANDBOX'
    
    # Security
    if re.search(r'(pentest|penetration\s+testing)', text):
        return 'SECURITY'
    
    # Coding agent (broader)
    if re.search(r'(coding|code)\s+(agent|harness)', description):
        return 'CODING_AGENT'
    if re.search(r'agentic\s+coding', description):
        return 'CODING_AGENT'
    if re.search(r'(ai\s+)?coding\s+(agent|assistant).*(cli|terminal)', text):
        return 'CODING_AGENT'
    if re.search(r'(edit|write|modify)\s+(files?|code)\s+(using|with|by)\s+(ai|llm)', text):
        return 'CODING_AGENT'
    
    # DevKit/SDK
    if re.search(r'(agent\s+development\s+kit|adk\b)', text):
        return 'DEVKIT_SDK'
    if re.search(r'(sdk|framework|toolkit)\s+for\s+building.*(agent|ai)', text) and 'sandbox' not in text:
        return 'DEVKIT_SDK'
    
    # Memory/RAG
    if re.search(r'memory\s+layer\s+for\s+ai', text):
        return 'MEMORY_RAG'
    if re.search(r'(persistent|long.term|cognitive)\s+memory.*(agent|ai)', text):
        return 'MEMORY_RAG'
    if re.search(r'knowledge\s+(platform|base|graph).*(ai|agent)', text):
        return 'MEMORY_RAG'
    if re.search(r'rag\b', text) and 'database' not in text:
        return 'MEMORY_RAG'
    
    # Orchestrator
    if re.search(r'orchestrat.*(engine|platform|framework|background|task|agent)', text):
        return 'ORCHESTRATOR'
    if re.search(r'durable\s+workflow', text):
        return 'ORCHESTRATOR'
    if re.search(r'multi.agent\s+(orchestrat|coordinat)', text):
        return 'ORCHESTRATOR'
    if re.search(r'coordina(te|tion).*(multi|agent)', text):
        return 'ORCHESTRATOR'
    
    # CLI tool
    if re.search(r'(all.in.one\s+llm\s+cli|llm\s+cli\s+tool|cli\s+tool\s+for)', text):
        return 'CLI_TOOL'
    if re.search(r'cli.*(built\s+for|designed\s+for)\s+(humans\s+and\s+)?(ai\s+)?agents', text):
        return 'CLI_TOOL'
    
    # Default
    return 'OTHER'


def parse_stars(stars_str):
    """Parse star count like '44.9k' or '1,234' to int."""
    s = stars_str.strip().lower().replace(',', '')
    if s.endswith('k'):
        try:
            return int(float(s[:-1]) * 1000)
        except ValueError:
            return 0
    try:
        return int(s)
    except ValueError:
        return 0


def get_classification_reason(category):
    reasons = {
        'CODING_AGENT': 'AI coding agent harness - CLI/TUI tool that uses LLMs for software engineering tasks',
        'AGENT_SANDBOX': 'Sandbox/isolated runtime for executing AI agents securely',
        'ORCHESTRATOR': 'Multi-agent orchestration/workflow coordination platform',
        'BROWSER_AUTOMATION': 'Browser control automation for AI agents',
        'MEMORY_RAG': 'Memory, knowledge base, or RAG system for AI agents',
        'MCP_TOOL': 'MCP protocol server or toolbox for AI agent tool integration',
        'DEVKIT_SDK': 'Agent development kit or framework for building AI agents',
        'CLI_TOOL': 'CLI tool for AI agent management, monitoring, or support',
        'DATABASE': 'Database or data warehouse for AI agent workloads',
        'SECURITY': 'Security, governance, or pentesting tool for AI agents',
        'OTHER': 'Not directly relevant to AI agent infrastructure',
    }
    return reasons.get(category, 'Other')


def main():
    rows = load_csv(CSV_PATH)
    print(f"Loaded {len(rows)} repos from CSV")
    
    classified = {cat: [] for cat in [
        'CODING_AGENT', 'AGENT_SANDBOX', 'ORCHESTRATOR', 'BROWSER_AUTOMATION',
        'MEMORY_RAG', 'MCP_TOOL', 'DEVKIT_SDK', 'CLI_TOOL', 'DATABASE',
        'SECURITY', 'OTHER'
    ]}
    
    for row in rows:
        category = classify_repo(row)
        row['clasificacion_ia'] = category
        
        name = row.get('name', '')
        stars = row.get('stars', '0')
        lang = row.get('language', '')
        desc = row.get('description', '')
        
        classified[category].append({
            'name': name,
            'stars': stars,
            'language': lang,
            'description': desc,
            'classification_reason': get_classification_reason(category),
        })
    
    # Save updated CSV
    save_csv(CSV_PATH, rows)
    print(f"Saved updated CSV to {CSV_PATH}")
    
    # Build report
    report = {
        'total_repos': len(rows),
        'classification_stats': {},
        'categories': {},
    }
    
    for cat, repos in classified.items():
        report['classification_stats'][cat] = len(repos)
        report['categories'][cat] = {
            'count': len(repos),
            'repos': sorted(repos, key=lambda r: parse_stars(r['stars']), reverse=True),
        }
    
    # Add summary for key categories
    report['summary'] = {
        'CODING_AGENT': [r['name'] for r in sorted(classified['CODING_AGENT'], key=lambda r: parse_stars(r['stars']), reverse=True)],
        'AGENT_SANDBOX': [r['name'] for r in sorted(classified['AGENT_SANDBOX'], key=lambda r: parse_stars(r['stars']), reverse=True)],
        'ORCHESTRATOR': [r['name'] for r in sorted(classified['ORCHESTRATOR'], key=lambda r: parse_stars(r['stars']), reverse=True)],
    }
    
    with open(OUTPUT_JSON, 'w', encoding='utf-8') as f:
        json.dump(report, f, indent=2, ensure_ascii=False)
    print(f"Saved report to {OUTPUT_JSON}")
    
    # Print summary
    print("\n=== CLASSIFICATION STATS ===")
    for cat in ['CODING_AGENT', 'AGENT_SANDBOX', 'ORCHESTRATOR', 'BROWSER_AUTOMATION',
                'MEMORY_RAG', 'MCP_TOOL', 'DEVKIT_SDK', 'CLI_TOOL', 'DATABASE',
                'SECURITY', 'OTHER']:
        print(f"  {cat:25s}: {len(classified[cat])}")
    
    print("\n=== CODING_AGENT REPOS (more relevant) ===")
    for r in sorted(classified['CODING_AGENT'], key=lambda x: parse_stars(x['stars']), reverse=True):
        print(f"  {r['name']:55s} ⭐{r['stars']:>6s}  {r['language']:8s}  {r['description'][:80]}")
    
    print("\n=== AGENT_SANDBOX REPOS ===")
    for r in sorted(classified['AGENT_SANDBOX'], key=lambda x: parse_stars(x['stars']), reverse=True):
        print(f"  {r['name']:55s} ⭐{r['stars']:>6s}  {r['language']:8s}  {r['description'][:80]}")
    
    print("\n=== ORCHESTRATOR REPOS ===")
    for r in sorted(classified['ORCHESTRATOR'], key=lambda x: parse_stars(x['stars']), reverse=True):
        print(f"  {r['name']:55s} ⭐{r['stars']:>6s}  {r['language']:8s}  {r['description'][:80]}")


if __name__ == '__main__':
    main()
