#!/usr/bin/env python3
"""
Agent Monitor TUI
=================
Interactive mind map / outline for monitoring AI agents.
Lee CSVs escritos por el orquestrador y los muestra como
un árbol jerárquico navegable (general → detalle).

Uso:
    python monitor.py

Los CSVs deben estar en ./data/
"""

from __future__ import annotations

import csv
from datetime import datetime
from pathlib import Path
from rich.text import Text

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.widgets import Footer, Header, RichLog, Static, Tree
import argparse

# ── Config ────────────────────────────────────────────────────────

MOBILE = False

DATA_DIR = Path(__file__).parent / "data"

# ── Iconos por estado ─────────────────────────────────────────────

STATUS_ICONS = {
    "active":       "🟢",
    "in_progress":  "🟡",
    "running":      "🟡",
    "completed":    "✅",
    "success":      "✅",
    "error":        "🔴",
    "failure":      "🔴",
    "failed":       "🔴",
    "pending":      "⏳",
    "idle":         "⚪",
    "warning":      "⚠️",
    "cancelled":    "✖️",
    "stopped":      "⏹",
    "unknown":      "❓",
}

LOG_ICONS = {
    "USER":        "👤",
    "ASSISTANT":   "🤖",
    "REASONING":   "🧠",
    "TOOL":        "🔧",
    "TOOL_RESULT": "✅",
    "INFO":        "ℹ️",
    "WARN":        "⚠️",
    "WARNING":     "⚠️",
    "ERROR":       "🔴",
    "DEBUG":       "🔵",
    "CRITICAL":    "💀",
}

def status_icon(status: str) -> str:
    return STATUS_ICONS.get(status.lower().strip(), "❓")

def log_icon(level: str) -> str:
    return LOG_ICONS.get(level.upper().strip(), "📝")

# ── Carga de datos ────────────────────────────────────────────────

def load_csv(filename: str) -> list[dict]:
    path = DATA_DIR / filename
    if not path.exists():
        return []
    with open(path, newline="") as f:
        reader = csv.DictReader(f)
        return list(reader)

def load_all() -> dict:
    return {
        "agents": load_csv("agents.csv"),
        "logs":   load_csv("logs.csv"),
    }

def log_color(level: str) -> str:
    return ("red" if level == "ERROR"
            else "yellow" if level in ("WARN", "WARNING")
            else "bright_blue" if level == "USER"
            else "bright_cyan" if level == "ASSISTANT"
            else "dim" if level == "REASONING"
            else "magenta" if level in ("TOOL", "TOOL_RESULT")
            else "")

# ── Estilos CSS ──────────────────────────────────────────────────

CSS_DEFAULT = """
Screen {
    layout: horizontal;
}

#tree-panel {
    width: 2fr;
    height: 100%;
    border: solid $primary 60%;
    overflow: auto;
}

#detail-panel {
    width: 3fr;
    height: 100%;
    border: solid $secondary 60%;
    padding: 0 1;
}

#detail-title {
    height: 3;
    text-style: bold;
    background: $surface;
    padding: 0 1;
    border-bottom: solid $border;
}

#detail-content {
    height: 1fr;
}

#detail-logs {
    height: 2fr;
    border-top: solid $border;
}

Tree {
    height: 1fr;
}
"""

CSS_MOBILE = """
Screen { layout: vertical; }
#tree-panel { width: 100%; height: 3fr; border: none; }
#detail-panel { width: 100%; height: 2fr; border-top: solid $primary 60%; }
#detail-title { height: 3; }
#detail-content { height: 1fr; }
#detail-logs { height: 2fr; }
"""

# ── Aplicación ────────────────────────────────────────────────────

class AgentMonitor(App):
    """Monitor interactivo de agentes con mapa mental navegable."""

    TITLE = "🤖 Agent Monitor"
    CSS = CSS_DEFAULT

    BINDINGS = [
        Binding("q",           "quit",       "Salir",    show=True),
        Binding("r",           "refresh",    "Refrescar", show=True),
        Binding("escape",      "focus_tree", "Árbol",    show=False),
        Binding("h",           "collapse",   "Colapsar", show=False),
    ]

    # ── Ciclo de vida ──────────────────────────────────────────

    def compose(self) -> ComposeResult:
        yield Header()
        with Horizontal():
            with Vertical(id="tree-panel"):
                yield Tree("🤖 System Overview", id="agent-tree")
            with Vertical(id="detail-panel"):
                yield Static(id="detail-title")
                yield RichLog(id="detail-content", highlight=True, markup=True)
                yield RichLog(id="detail-logs",   highlight=True, markup=True)
        yield Footer()

    def on_mount(self) -> None:
        self._last_hash = ""
        self._refresh()
        # Cada 3 segundos mira si los CSVs cambiaron
        self.set_interval(3, self._refresh)

    # ── Refresco ───────────────────────────────────────────────

    def _data_hash(self, data: dict) -> str:
        a = len(data["agents"])
        l = len(data["logs"])
        last = data["logs"][-1].get("log_id", "") if data["logs"] else ""
        return f"{a}-{l}-{last}"

    def _refresh(self) -> None:
        data = load_all()
        h = self._data_hash(data)
        if h == self._last_hash:
            return
        self._last_hash = h

        agents = data["agents"]
        total, active, err = len(agents), 0, 0
        for a in agents:
            s = a.get("status", "")
            if s in ("active", "in_progress", "running"):
                active += 1
            elif s in ("error", "failure", "failed"):
                err += 1
        self.sub_title = (
            f"{total} agentes  🟢{active}  🔴{err}  "
            f"─ {datetime.now():%H:%M:%S}"
        )

        self._build_tree(data)

    # ── Árbol (mapa mental) ────────────────────────────────────

    def _save_expanded(self, tree) -> set[str]:
        """Guarda qué nodos están expandidos antes del refresh."""
        expanded = set()
        def walk(nodes):
            for child in nodes:
                d = child.data or {}
                typ = d.get("type", "")
                if typ == "agent":
                    key = f"agent:{d.get('id','')}"
                elif typ == "log":
                    key = f"log:{d.get('id','')}"
                else:
                    key = ""
                if key and child.is_expanded:
                    expanded.add(key)
                if hasattr(child, 'children'):
                    walk(list(child.children))
        walk(list(tree.root.children))
        return expanded

    def _restore_expanded(self, tree, expanded: set[str]) -> None:
        """Expande los nodos que estaban expandidos antes del refresh."""
        def walk(nodes):
            for child in nodes:
                d = child.data or {}
                typ = d.get("type", "")
                if typ == "agent":
                    key = f"agent:{d.get('id','')}"
                elif typ == "log":
                    key = f"log:{d.get('id','')}"
                else:
                    key = ""
                if key and key in expanded:
                    child.expand()
                if hasattr(child, 'children'):
                    walk(list(child.children))
        walk(list(tree.root.children))

    def _build_tree(self, data: dict) -> None:
        tree = self.query_one("#agent-tree", Tree)
        expanded = self._save_expanded(tree)
        tree.clear()

        agents = data["agents"]
        logs = data["logs"]
        root = tree.root

        for agent in agents:
            aid = agent["agent_id"]
            name = agent.get("name", aid)
            st = agent.get("status", "unknown")
            role = agent.get("role", "")

            icon = status_icon(st)
            if st in ("error", "failure", "failed"):
                label_style = "bold red"
            elif st in ("in_progress", "running"):
                label_style = "bold yellow"
            elif st == "active":
                label_style = "bold green"
            else:
                label_style = ""

            agent_label = Text.assemble(
                (f"{icon} ", ""),
                (name, label_style),
                (f"  [{st}]", "dim white"),
                (f"  {role}", "cyan"),
            )

            agent_node = root.add(agent_label, data={"type": "agent", "id": aid})

            # Filter logs for this agent, show chronologically
            agent_logs = [l for l in logs if l.get("agent_id") == aid]
            for entry in agent_logs:
                lvl = entry.get("level", "INFO").upper()
                lic = log_icon(lvl)
                msg = entry.get("message", "")[:120]
                ms = log_color(lvl)
                agent_node.add_leaf(
                    Text.assemble((f"{lic} ", ""), (msg, ms)),
                    data={"type": "log", "id": entry.get("log_id", "")},
                )

        # Restore expansion
        if expanded:
            self._restore_expanded(tree, expanded)
        else:
            root.expand()
            # También expandir el primer nivel de agentes
            for child in list(root.children):
                child.expand()

        tree.focus()

    # ── Panel de detalle ────────────────────────────────────────

    def on_tree_node_selected(self, event: Tree.NodeSelected) -> None:
        node = event.node
        d = node.data or {}
        typ = d.get("type", "")
        title   = self.query_one("#detail-title", Static)
        content = self.query_one("#detail-content", RichLog)
        logs    = self.query_one("#detail-logs", RichLog)
        content.clear()
        logs.clear()

        try:
            if typ == "agent":
                self._show_agent(d["id"], title, content, logs)
            elif typ == "log":
                self._show_log(d["id"], title, content, logs)
            else:
                label = node.label
                title.update(label.plain if isinstance(label, Text) else str(label))
        except Exception as e:
            title.update(f"❌ Error: {e}")
            content.write(f"[red]Error al mostrar detalle:\n{e}[/]")

    def _show_agent(self, agent_id: str, title: Static, content: RichLog, logs: RichLog) -> None:
        data = load_all()
        agent = next((a for a in data["agents"] if a["agent_id"] == agent_id), None)
        if not agent:
            title.update(f"Agent {agent_id} not found")
            return

        name = agent.get("name", agent_id)
        st   = agent.get("status", "?")
        icon = status_icon(st)
        title.update(f"{icon}  {name}")

        content.write(Text.assemble(
            ("Status:  ", "bold"), (f"{icon}  {st}\n", ""),
            ("Role:    ", "bold"), (f"{agent.get('role', '—')}\n", ""),
            ("Model:   ", "bold"), (f"{agent.get('model', '—')}\n", ""),
            ("Created: ", "bold"), (f"{agent.get('created_at', '—')}\n", ""),
            ("Updated: ", "bold"), (f"{agent.get('updated_at', '—')}\n", ""),
        ))

        # Logs del agente (últimos, con foco en errores)
        agent_logs = [l for l in data["logs"] if l.get("agent_id") == agent_id]
        errors = [l for l in agent_logs if l.get("level", "").upper() in ("ERROR", "CRITICAL")]

        if errors:
            logs.write("[bold red]🔴  Errors[/]")
            for e in errors[-5:]:
                logs.write(f"  🔴  {e.get('message', '')}")
                logs.write(f"       [{e.get('timestamp', '')}]")
        else:
            logs.write("[green]✅  No errors[/]")

        logs.write("\n[bold]📝  Recent activity[/]")
        for e in agent_logs[-8:]:
            lvl = e.get("level", "INFO").upper()
            lic = log_icon(lvl)
            logs.write(f"  {lic}  {e.get('message', '')[:100]}")

    def _show_log(self, log_id: str, title: Static, content: RichLog, logs: RichLog) -> None:
        data = load_all()
        entry = next((l for l in data["logs"] if l["log_id"] == log_id), None)
        if not entry:
            title.update(f"Log {log_id} not found")
            return

        lvl = entry.get("level", "INFO").upper()
        lic = log_icon(lvl)
        title.update(f"{lic}  [{lvl}]  {entry.get('message', '')[:60]}")

        content.write(Text.assemble(
            ("Log ID:    ", "bold"), (f"{entry.get('log_id', '—')}\n", ""),
            ("Agent:     ", "bold"), (f"{entry.get('agent_id', '—')}\n", ""),
            ("Timestamp: ", "bold"), (f"{entry.get('timestamp', '—')}\n", ""),
            ("Level:     ", "bold"), (f"{lic}  {lvl}\n",
                "red" if lvl == "ERROR" else
                "yellow" if lvl in ("WARN", "WARNING") else
                "green" if lvl == "INFO" else
                "bright_blue" if lvl == "USER" else
                "bright_cyan" if lvl == "ASSISTANT" else
                "dim" if lvl == "REASONING" else
                "magenta" if lvl in ("TOOL", "TOOL_RESULT") else ""),
            ("Message:   ", "bold"), (f"{entry.get('message', '')}\n", ""),
        ))

    # ── Acciones ────────────────────────────────────────────────

    def action_refresh(self) -> None:
        self._refresh()
        self.notify("🔄 Refreshed")

    def action_focus_tree(self) -> None:
        self.query_one("#agent-tree", Tree).focus()

    def action_collapse(self) -> None:
        tree = self.query_one("#agent-tree", Tree)
        for child in list(tree.root.children):
            child.collapse()


# ── Entry point ───────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--mobile", action="store_true", help="Modo compacto para móvil")
    args = parser.parse_args()

    global MOBILE
    MOBILE = args.mobile

    if MOBILE:
        AgentMonitor.CSS = CSS_MOBILE
    else:
        AgentMonitor.CSS = CSS_DEFAULT

    app = AgentMonitor()
    app.run()


if __name__ == "__main__":
    main()
