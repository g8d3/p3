#!/usr/bin/env python3

import os
import json
import asyncio
from pathlib import Path
from datetime import datetime
from textual.app import App, ComposeResult
from textual.containers import Container
from textual.widgets import (
    Header, Footer, TabbedContent, Tab, TabPane,
    Log, Static, Tree, Input, Button, DataTable
)
from textual.reactive import reactive

ROOT_DIR = Path(__file__).parent
STATE_FILE = ROOT_DIR / "state.json"
LOG_FILE = ROOT_DIR / "logs" / "bootstrap.log"
COMMANDS_FILE = ROOT_DIR / ".commands.json"

class LogTab(Container):
    watch_task = None

    def compose(self) -> ComposeResult:
        yield Static("📜 Live Logs (auto-scrolling)", classes="header")
        yield Log(id="log_widget")

    def on_mount(self) -> None:
        self.log_widget = self.query_one("#log_widget", Log)
        if LOG_FILE.exists():
            for line in LOG_FILE.read_text().split('\n')[-100:]:
                if line.strip():
                    self.log_widget.write(line)
        self.watch_task = asyncio.create_task(self.watch_log())

    def on_unmount(self) -> None:
        if self.watch_task and not self.watch_task.done():
            self.watch_task.cancel()

    async def watch_log(self):
        last_size = LOG_FILE.stat().st_size if LOG_FILE.exists() else 0
        while self.is_mounted:
            try:
                if LOG_FILE.exists():
                    current_size = LOG_FILE.stat().st_size
                    if current_size > last_size:
                        with open(LOG_FILE, 'r') as f:
                            f.seek(last_size)
                            new_lines = f.read()
                            for line in new_lines.split('\n'):
                                if line.strip():
                                    self.log_widget.write(line)
                        last_size = current_size
                await asyncio.sleep(0.5)
            except asyncio.CancelledError:
                break
            except:
                await asyncio.sleep(1)

class StateTab(Container):
    watch_task = None
    state = reactive({})

    def compose(self) -> ComposeResult:
        yield Static("📊 System State", classes="header")
        yield DataTable(id="state_table")
        yield Static("\n📋 Pending Tasks", classes="header")
        yield Static(id="pending_tasks")
        yield Static("\n📜 Recent Actions", classes="header") 
        yield Static(id="recent_actions")

    def on_mount(self) -> None:
        self.load_state()
        self.watch_task = asyncio.create_task(self.watch_state())

    def on_unmount(self) -> None:
        if self.watch_task and not self.watch_task.done():
            self.watch_task.cancel()

    def load_state(self):
        try:
            if STATE_FILE.exists():
                self.state = json.loads(STATE_FILE.read_text())
        except:
            pass

    async def watch_state(self):
        while self.is_mounted:
            self.load_state()
            self.update_display()
            await asyncio.sleep(2)

    def update_display(self):
        table = self.query_one("#state_table", DataTable)
        table.clear()
        table.add_column("Key", width=20)
        table.add_column("Value", width=40)
        
        for key, value in self.state.items():
            if key not in ['task_history', 'last_actions', 'pending_tasks']:
                table.add_row(key, str(value)[:40])
        
        pending = self.query_one("#pending_tasks", Static)
        tasks = self.state.get('pending_tasks', [])
        if tasks:
            pending_text = "\n".join([f"• {t.get('description', 'N/A')[:60]}" for t in tasks])
            pending.update(pending_text)
        else:
            pending.update("No pending tasks ✅")
        
        recent = self.query_one("#recent_actions", Static)
        actions = self.state.get('last_actions', [])
        if actions:
            recent_text = "\n".join([f"• {a.get('description', 'N/A')[:60]}" for a in actions])
            recent.update(recent_text)
        else:
            recent.update("No recent actions")

class FilesTab(Container):
    def compose(self) -> ComposeResult:
        yield Static("📁 File Browser", classes="header")
        yield Tree("root", id="file_tree")

    def on_mount(self) -> None:
        tree = self.query_one("#file_tree", Tree)
        tree.root.expand()
        self.scan_directory(ROOT_DIR, tree.root, ROOT_DIR)

    def scan_directory(self, path: Path, node, root_dir: Path):
        for item in sorted(path.iterdir()):
            if item.name.startswith('.'):
                continue
            rel_path = item.relative_to(root_dir)
            label = f"{item.name}/" if item.is_dir() else item.name
            child = node.add(label, data=str(item))
            if item.is_dir() and not item.is_symlink():
                self.scan_directory(item, child, root_dir)

class ChatTab(Container):
    def compose(self) -> ComposeResult:
        yield Static("💬 Command Input", classes="header")
        yield Static("Send commands to trigger agent actions:", classes="info")
        yield Input(placeholder="Type a command or description...", id="command_input")
        yield Button("Send Command", id="send_btn", variant="primary")
        yield Static("\nRecent Commands:", classes="header")
        yield Log(id="command_log")

    async def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "send_btn":
            await self.send_command()

    async def on_input_submitted(self, event: Input.Submitted) -> None:
        await self.send_command()

    async def send_command(self):
        input_widget = self.query_one("#command_input", Input)
        command = input_widget.value.strip()
        if command:
            log = self.query_one("#command_log", Log)
            log.write(f"[{datetime.now().strftime('%H:%M:%S')}] {command}")
            
            # Write to commands file for bootstrap to process
            commands = []
            if COMMANDS_FILE.exists():
                commands = json.loads(COMMANDS_FILE.read_text())
            
            commands.append({
                "command": command,
                "timestamp": datetime.now().isoformat(),
                "processed": False
            })
            COMMANDS_FILE.write_text(json.dumps(commands, indent=2))
            
            input_widget.value = ""

class AgentTUI(App):
    CSS = """
    .header {
        text-style: bold;
        margin: 1 0;
        text-align: center;
    }
    .info {
        text-style: italic;
        margin: 0 0 1 0;
        color: gray;
    }
    Log {
        height: 1fr;
        border: solid $primary;
    }
    DataTable {
        height: 1fr;
    }
    Tree {
        height: 1fr;
    }
    #command_input {
        margin: 1 0;
    }
    #send_btn {
        margin: 1 0;
    }
    #command_log {
        height: 1fr;
    }
    """

    def compose(self) -> ComposeResult:
        yield Header()
        with TabbedContent(id="tabs"):
            with TabPane("Logs", id="logs"):
                yield LogTab()
            with TabPane("State", id="state"):
                yield StateTab()
            with TabPane("Files", id="files"):
                yield FilesTab()
            with TabPane("Command", id="chat"):
                yield ChatTab()
        yield Footer()

    def on_mount(self) -> None:
        self.title = "🤖 Autonomous Agent System"
        self.sub_title = "TUI Control Panel"

if __name__ == "__main__":
    app = AgentTUI()
    try:
        app.run()
    except KeyboardInterrupt:
        pass
