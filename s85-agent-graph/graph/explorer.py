"""
explorer — Scans p3 projects and populates the graph.
"""
import json
import os
from pathlib import Path
from .core import Graph


P3_ROOT = Path("/home/vuos/code/p3")


def scan_project_dirs(graph: Graph) -> dict[str, dict]:
    """Scan p3/ directories and register each as a Project node.
    Returns dict of dir_name -> node info.
    """
    results = {}
    for entry in sorted(P3_ROOT.iterdir()):
        if not entry.is_dir() or entry.name.startswith(".") or entry.name == "data":
            continue
        if entry.name.startswith("s") and entry.name[1:].split("-")[0].isdigit():
            name = entry.name
            desc = _describe_project(entry)
            node_id = graph.add_node(
                type="project",
                name=name,
                node_id=name,  # use name as stable ID so edges can reference it
                properties={
                    "path": str(entry),
                    "description": desc,
                    "scanned_at": graph._ts(),
                    "files_count": len(list(entry.rglob("*"))) if entry.exists() else 0,
                },
                agent_id="explorer"
            )
            results[name] = {"id": name, "path": str(entry), "description": desc}
        else:
            name = entry.name
            node_id = graph.add_node(
                type="project",
                name=name,
                properties={
                    "path": str(entry),
                    "description": "Non-standard directory",
                    "scanned_at": graph._ts(),
                },
                agent_id="explorer"
            )
            results[name] = {"id": node_id, "path": str(entry), "description": "Non-standard dir"}
    return results


def _describe_project(path: Path) -> str:
    """Try to extract a project description from README, MANIFIESTO, or known patterns."""
    for readme in ["README.md", "MANIFIESTO.md", "README"]:
        rp = path / readme
        if rp.exists():
            try:
                lines = rp.read_text().split("\n")
                for line in lines[:20]:
                    line = line.strip()
                    if line and not line.startswith("#"):
                        return line[:200]
            except Exception:
                pass
    # Fallback: look for known patterns
    name = path.name
    known = {
        "s84": "Nimbo framework + trading + A2A protocols",
        "s77-aan": "Agent Architecture Network — version registry + agent orchestration",
        "s73-framework": "Multi-agent framework — inbox/outbox IPC + WebSocket dashboard",
        "s82": "MITM proxy + crush agent system",
        "s50-multi-agent-orchestrator": "Multi-agent orchestrator experiments",
        "s63-agent-hub": "Agent Hub — WebSocket native + IPC",
        "s58-content-pipeline": "Content pipeline automation",
    }
    for key, desc in known.items():
        if name.startswith(key) or name == key:
            return desc
    return "Unknown project"


def scan_readmes(graph: Graph, projects: dict[str, dict]):
    """Scan README/manifesto files from known projects and register learnings."""
    for proj_name, info in projects.items():
        path = Path(info["path"])
        for doc_name in ["README.md", "MANIFIESTO.md", "doc/aprendizajes.md",
                         "doc/pendientes.md", "CHANGELOG.md", "SCHEMA.md",
                         "doc/manifiesto-v2.md"]:
            doc_path = path / doc_name
            if doc_path.exists():
                try:
                    text = doc_path.read_text()
                    aid = f"{proj_name}/{doc_name}"
                    graph.add_node(
                        type="artifact",
                        name=aid,
                        node_id=aid,
                        properties={
                            "path": str(doc_path),
                            "size": len(text),
                            "preview": text[:500],
                        },
                        agent_id="explorer"
                    )
                    pid = info.get("id", proj_name)
                    graph.add_edge(
                        source_id=pid,
                        type="contains",
                        target_id=aid,
                        properties={"doc_type": doc_name},
                        agent_id="explorer"
                    )
                except Exception:
                    pass
