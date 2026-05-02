"""Textual Chat App - Simple terminal chat with CRUD support."""

from textual.app import App, ComposeResult
from textual.containers import Container, Horizontal, Vertical
from textual.widgets import Input, Static

from datetime import datetime
from typing import Dict, List


HELP_TEXT = """
╔════════════════════════════════════════════════════════╗
║  JUST PRESS SINGLE KEYS - NO CONTROL KEY NEEDED       ║
╠════════════════════════════════════════════════════════╣
║                                                        ║
║  /  → Chat mode      (just press / key)               ║
║  p  → Providers      (just press p key)               ║
║  m  → Models         (just press m key)               ║
║  a  → Agents         (just press a key)               ║
║  s  → Sessions       (just press s key)               ║
║  t  → Tools          (just press t key)               ║
║  h  → Schedules      (just press h key)               ║
║  c  → Clear chat     (just press c key)               ║
║  ?  → Toggle help    (just press ? key)               ║
║  q  → Quit app       (just press q key)               ║
║  Esc → Back to chat  (just press Escape key)          ║
║                                                        ║
╠════════════════════════════════════════════════════════╣
║  TO CHAT: Click bottom box → Type → Press ENTER       ║
╚════════════════════════════════════════════════════════╝
"""


class ChatPanel(Static):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.messages: List[Dict] = []
        self._text_content = ""

    def add_message(self, role: str, text: str, metadata: Dict = None):
        timestamp = datetime.now().strftime("%H:%M:%S")
        role_emoji = "bot" if role == "assistant" else "you"
        self._text_content += f"[{timestamp}] {role_emoji}: {text}\n"
        self.update(self._text_content)

    def clear(self):
        self.messages = []
        self._text_content = ""
        self.update("")


class ChatApp(App):
    CSS = """
    Screen { layout: vertical; }
    #main { layout: horizontal; height: 1fr; }
    #chat-area { width: 1fr; border: solid green; }
    #help-panel { width: 45; border: solid cyan; }
    #input-area { height: auto; border: solid blue; padding: 1; }
    #status-bar { height: auto; dock: bottom; background: $accent; color: $text; padding: 0 1; }
    """

    def __init__(self):
        super().__init__()
        self.mode = "chat"
        self._help_visible = True

    def compose(self) -> ComposeResult:
        with Horizontal(id="main"):
            with Vertical(id="chat-area"):
                yield ChatPanel(id="chat")
                yield Container(Input(placeholder="Click here, type, press ENTER", id="input"), id="input-area")
            with Vertical(id="help-panel"):
                yield Static(HELP_TEXT, id="help-content")
        yield Static("MODE: Chat | SINGLE KEYS: / p m a s t h c ? q | Esc=back", id="status-bar")

    def on_mount(self) -> None:
        self.update_status()

    def update_status(self):
        hints = {
            "chat": "MODE: Chat | SINGLE KEYS: /=chat p=providers m=models a=agents s=sessions t=tools h=schedules c=clear ?=help q=quit",
            "providers": "MODE: Providers (not implemented) | SINGLE KEYS: /=chat Esc=back q=quit",
            "models": "MODE: Models (not implemented) | SINGLE KEYS: /=chat Esc=back q=quit",
            "agents": "MODE: Agents (not implemented) | SINGLE KEYS: /=chat Esc=back q=quit",
            "sessions": "MODE: Sessions (not implemented) | SINGLE KEYS: /=chat Esc=back q=quit",
            "tools": "MODE: Tools (not implemented) | SINGLE KEYS: /=chat Esc=back q=quit",
            "schedules": "MODE: Schedules (not implemented) | SINGLE KEYS: /=chat Esc=back q=quit",
        }
        self.query_one("#status-bar", Static).update(hints.get(self.mode, ""))

    def toggle_help(self):
        self._help_visible = not self._help_visible
        help_panel = self.query_one("#help-panel")
        help_panel.display = self._help_visible

    def action_toggle_help(self):
        self.toggle_help()

    def action_chat_mode(self):
        self.mode = "chat"
        self.update_status()

    def action_clear_chat(self):
        self.query_one("#chat", ChatPanel).clear()

    def action_quit(self):
        self.exit()

    def action_nav(self, section: str):
        self.mode = section
        self.notify(f">>> {section.upper()} MODE <<<\n\nThis section is not yet implemented.\n\nPress / to return to chat or Esc to go back.", severity="warning", timeout=5)
        self.update_status()

    def on_key(self, event):
        """Handle keys globally before widgets get them."""
        key = event.key
        if key == "q":
            self.action_quit()
            event.stop()
        elif key == "?":
            self.action_toggle_help()
            event.stop()
        elif key == "/":
            self.action_chat_mode()
            event.stop()
        elif key == "p":
            self.action_nav("providers")
            event.stop()
        elif key == "m":
            self.action_nav("models")
            event.stop()
        elif key == "a":
            self.action_nav("agents")
            event.stop()
        elif key == "s":
            self.action_nav("sessions")
            event.stop()
        elif key == "t":
            self.action_nav("tools")
            event.stop()
        elif key == "h":
            self.action_nav("schedules")
            event.stop()
        elif key == "c":
            self.action_clear_chat()
            event.stop()
        elif key == "escape":
            self.action_chat_mode()
            event.stop()

    def on_input_submitted(self, event: Input.Submitted):
        if event.value.strip() and self.mode == "chat":
            chat = self.query_one("#chat", ChatPanel)
            chat.add_message("user", event.value)
            chat.add_message("assistant", f"Echo: {event.value}")
            event.input.value = ""


if __name__ == "__main__":
    app = ChatApp()
    app.run()
