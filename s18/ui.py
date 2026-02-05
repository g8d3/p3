# UI

import os
import json
import asyncio
import subprocess
from pathlib import Path
from datetime import datetime
from textual.app import App, ComposeResult
from textual.containers import Container, Horizontal
from textual.widgets import (
    Header, Footer, TabbedContent, Tab, TabPane,
    Log, Static, Tree, Input, Button, DataTable, RichLog, Label
)
from textual.reactive import reactive
from textual import events
from textual.keys import Keys

import config

bootstrap_process = None

class LogTab(Container):
    watch_task = None

    def compose(self) -> ComposeResult:
        yield Static("📜 Live Logs", classes="header")
        yield RichLog(id="log_widget", max_lines=config.MAX_LOG_LINES, auto_scroll=True)

    def on_mount(self) -> None:
        self.log_widget = self.query_one("#log_widget", RichLog)
        if config.LOG_FILE.exists():
            content = config.LOG_FILE.read_text()
            for line in content.split('\n')[-200:]:
                if line.strip():
                    self.log_widget.write(line)
        self.watch_task = asyncio.create_task(self.watch_log())

    def on_unmount(self) -> None:
        if self.watch_task and not self.watch_task.done():
            self.watch_task.cancel()

    async def watch_log(self):
        last_size = config.LOG_FILE.stat().st_size if config.LOG_FILE.exists() else 0
        while self.is_mounted:
            try:
                if config.LOG_FILE.exists():
                    current_size = config.LOG_FILE.stat().st_size
                    if current_size > last_size:
                        with open(config.LOG_FILE, 'r') as f:
                            f.seek(last_size)
                            new_content = f.read()
                            for line in new_content.split('\n'):
                                if line.strip():
                                    self.log_widget.write(line)
                        last_size = current_size
                await asyncio.sleep(0.5)
            except asyncio.CancelledError:
                break
            except Exception as e:
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
            if config.STATE_FILE.exists():
                self.state = json.loads(config.STATE_FILE.read_text())
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

class ScheduleTab(Container):
    state = reactive({})
    watch_task = None

    def compose(self) -> ComposeResult:
        yield Static("📅 Schedule & Intervals", classes="header")
        yield Static(id="current_interval", classes="info")
        yield Static("\n📋 Current Schedule:", classes="header")
        yield Static(id="intervals_list")
        yield Static("\n➕ Add New Interval:", classes="header")
        with Horizontal():
            yield Input(placeholder="Minutes (e.g., 5)", id="new_interval_input")
            yield Button("Add", id="add_interval_btn", variant="primary")
        yield Static("\n🗑 Management:", classes="header")
        with Horizontal():
            yield Button("Save Schedule", id="save_schedule_btn", variant="success")
            yield Button("Reset to Default", id="reset_schedule_btn", variant="warning")

    def on_mount(self) -> None:
        self.load_state()
        self.watch_task = asyncio.create_task(self.watch_state())

    def on_unmount(self) -> None:
        if self.watch_task and not self.watch_task.done():
            self.watch_task.cancel()

    def load_state(self):
        try:
            if config.STATE_FILE.exists():
                self.state = json.loads(config.STATE_FILE.read_text())
        except:
            pass
        self.update_display()

    async def watch_state(self):
        while self.is_mounted:
            self.load_state()
            self.update_display()
            await asyncio.sleep(2)

    def update_display(self):
        intervals = self.state.get("intervals", config.DEFAULT_INTERVALS)
        interval_idx = self.state.get("interval_idx", 0)
        current_interval = intervals[interval_idx] if interval_idx < len(intervals) else "N/A"
        
        current_widget = self.query_one("#current_interval", Static)
        current_widget.update(f"Current interval: {current_interval} minutes (cycle {interval_idx + 1} of {len(intervals)})")
        
        list_widget = self.query_one("#intervals_list", Static)
        list_text = ""
        for i, interval in enumerate(intervals):
            prefix = "[→] " if i == interval_idx else "[ ] "
            list_text += f"{prefix} {interval} minutes\n"
        list_widget.update(list_text)

    async def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "add_interval_btn":
            await self.add_interval()
        elif event.button.id == "save_schedule_btn":
            self.save_schedule()
        elif event.button.id == "reset_schedule_btn":
            self.reset_schedule()

    async def on_input_submitted(self, event: Input.Submitted) -> None:
        if event.input.id == "new_interval_input":
            await self.add_interval()

    async def add_interval(self):
        input_widget = self.query_one("#new_interval_input", Input)
        try:
            minutes = int(input_widget.value.strip())
            if minutes < 1:
                self.notify("Interval must be at least 1 minute", severity="warning")
                return
            
            intervals = self.state.get("intervals", config.DEFAULT_INTERVALS.copy())
            intervals.append(minutes)
            self.state["intervals"] = intervals
            self.save_state()
            self.notify(f"Added {minutes} minute interval", severity="success")
            input_widget.value = ""
        except ValueError:
            self.notify("Please enter a valid number", severity="error")

    def save_schedule(self):
        intervals = self.state.get("intervals", config.DEFAULT_INTERVALS)
        self.state["intervals"] = intervals
        self.save_state()
        self.notify(f"Saved {len(intervals)} intervals to schedule", severity="success")

    def reset_schedule(self):
        self.state["intervals"] = config.DEFAULT_INTERVALS.copy()
        self.save_state()
        self.notify("Reset to default intervals", severity="info")

    def save_state(self):
        try:
            config.STATE_FILE.write_text(json.dumps(self.state, indent=2))
        except Exception as e:
            self.notify(f"Failed to save state: {e}", severity="error")

    def notify(self, message: str, severity: str = "info"):
        self.app.notify(message, severity=severity)

class FilesTab(Container):
    def compose(self) -> ComposeResult:
        yield Static("📁 File Browser", classes="header")
        yield Tree("root", id="file_tree")

    def on_mount(self) -> None:
        tree = self.query_one("#file_tree", Tree)
        tree.root.expand()
        self.scan_directory(config.ROOT_DIR, tree.root, config.ROOT_DIR)

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
    watch_task = None
    last_ai_response = ""
    last_mtime = 0

    def compose(self) -> ComposeResult:
        yield Static("💬 Chat with Agent", classes="header")
        yield Input(placeholder="Type a command, question, or greeting...", id="command_input")
        yield Button("Send", id="send_btn", variant="primary")
        yield Static("\n🤖 AI Responses:", classes="info")
        yield Static(id="ai_response", classes="response")
        yield Static(id="ai_debug", classes="debug")
        yield Static("\n📝 Your Commands:", classes="header")
        yield Log(id="command_log")

    def on_mount(self) -> None:
        self.load_last_response()
        self.watch_task = asyncio.create_task(self.watch_responses())

    def on_unmount(self) -> None:
        if self.watch_task and not self.watch_task.done():
            self.watch_task.cancel()

    def load_last_response(self):
        debug_widget = self.query_one("#ai_debug", Static)
        debug_widget.update(f"Debug: Watching {config.AI_RESPONSES_FILE}")
        
        if config.AI_RESPONSES_FILE.exists():
            mtime = config.AI_RESPONSES_FILE.stat().st_mtime
            self.last_mtime = mtime
            content = config.AI_RESPONSES_FILE.read_text()
            if content.strip():
                response_widget = self.query_one("#ai_response", Static)
                response_widget.update(content.strip())
                debug_widget.update(f"Debug: Loaded response (mtime: {mtime})")
            else:
                debug_widget.update(f"Debug: File exists but empty")
        else:
            debug_widget.update("Debug: File does not exist")

    async def watch_responses(self):
        while self.is_mounted:
            try:
                if config.AI_RESPONSES_FILE.exists():
                    mtime = config.AI_RESPONSES_FILE.stat().st_mtime
                    content = config.AI_RESPONSES_FILE.read_text()
                    
                    if mtime > self.last_mtime or content.strip() != self.last_ai_response:
                        self.last_mtime = mtime
                        self.last_ai_response = content.strip()
                        
                        response_widget = self.query_one("#ai_response", Static)
                        response_widget.update(self.last_ai_response)
                        
                        debug_widget = self.query_one("#ai_debug", Static)
                        debug_widget.update(f"Debug: Updated at {datetime.fromtimestamp(mtime).strftime('%H:%M:%S')}")
                        
                        self.app.notify("New AI response received", severity="info")
                
                await asyncio.sleep(1)
            except asyncio.CancelledError:
                break
            except Exception as e:
                debug_widget = self.query_one("#ai_debug", Static)
                debug_widget.update(f"Debug: Error watching: {e}")
                await asyncio.sleep(2)

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
            log.write(f"\n[{datetime.now().strftime('%H:%M:%S')}] You: {command}")
            
            commands = []
            if config.COMMANDS_FILE.exists():
                commands = json.loads(config.COMMANDS_FILE.read_text())
            
            commands.append({
                "command": command,
                "timestamp": datetime.now().isoformat(),
                "processed": False
            })
            config.COMMANDS_FILE.write_text(json.dumps(commands, indent=2))
            
            input_widget.value = ""

class AgentUI(App):
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
        text-style: dim;
    }
    .debug {
        text-style: italic;
        margin: 0 0 1 0;
        color: cyan;
        text-style: dim;
        height: 1;
    }
    .response {
        margin: 1 0;
        padding: 1;
        border: solid gray;
        text-style: bold;
        height: 1fr;
        overflow: auto;
    }
    RichLog {
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
        margin: 0 1 1 0;
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
            with TabPane("Schedule", id="schedule"):
                yield ScheduleTab()
            with TabPane("Chat", id="chat"):
                yield ChatTab()
        yield Footer()

    def on_mount(self) -> None:
        self.title = "🤖 Autonomous Agent System"
        self.sub_title = "Ctrl+Q to Quit"
        self.start_bootstrap()

    def on_unmount(self) -> None:
        global bootstrap_process
        if bootstrap_process and bootstrap_process.poll() is None:
            self.log("Stopping bootstrap process...")
            bootstrap_process.terminate()
            try:
                bootstrap_process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                bootstrap_process.kill()

    def on_key(self, event: events.Key) -> None:
        if event.key == Keys.ControlQ:
            self.quit_all()
    
    def quit_all(self):
        global bootstrap_process
        import time
        
        if bootstrap_process and bootstrap_process.poll() is None:
            self.log(f"Quitting all processes (agent PID: {bootstrap_process.pid})")
            
            commands = []
            if config.COMMANDS_FILE.exists():
                commands = json.loads(config.COMMANDS_FILE.read_text())
            
            commands.append({
                "command": "quit",
                "timestamp": datetime.now().isoformat(),
                "processed": False
            })
            config.COMMANDS_FILE.write_text(json.dumps(commands, indent=2))
            
            time.sleep(0.5)
        
        self.exit()

    def start_bootstrap(self):
        global bootstrap_process
        agent_py = config.ROOT_DIR / "agent.py"
        if agent_py.exists():
            bootstrap_process = subprocess.Popen(
                ['python3', str(agent_py)],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                cwd=config.ROOT_DIR
            )
            self.log(f"Started agent.py (PID: {bootstrap_process.pid})")
        else:
            self.log("agent.py not found!")

if __name__ == "__main__":
    app = AgentUI()
    try:
        app.run()
    except KeyboardInterrupt:
        pass
