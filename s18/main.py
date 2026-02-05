#!/usr/bin/env python3

"""
Autonomous Agent System - Main Entry Point

This is the single entry point that launches the TUI interface.
The TUI automatically starts the agent as a background subprocess.

Usage:
    python3 main.py
    ./main.py
"""

from textual.app import App, ComposeResult
from textual.containers import Container
from textual.widgets import Static

import ui

class MainApp(App):
    """Main application wrapper for the autonomous agent system."""
    
    CSS = """
    Screen {
        align: center middle;
    }
    Container {
        width: 60;
    }
    Static {
        text-align: center;
        margin: 1 0;
    }
    """

    def compose(self) -> ComposeResult:
        yield Container(
            Static("🤖 Autonomous Agent System", classes="title"),
            Static(""),
            Static("Starting UI with integrated agent..."),
            Static(""),
            Static("Press Ctrl+C to exit"),
        )

    def on_mount(self) -> None:
        """Launch the actual UI after showing startup screen."""
        import asyncio
        
        async def launch_ui():
            await asyncio.sleep(1)
            self.exit()
            ui.AgentUI().run()
        
        asyncio.create_task(launch_ui())

if __name__ == "__main__":
    # Direct launch for now - simpler approach
    ui.AgentUI().run()
