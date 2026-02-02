"""CRUD panels for Terminal AI Chat App."""

from textual.app import App, ComposeResult
from textual.containers import Container, Horizontal, Vertical
from textual.widgets import Input, Static, ListView, ListItem, Label, Button, Log
from textual import events
from typing import Dict, List, Optional, Callable
from db import (
    ProviderDB, ModelDB, AgentDB, SessionDB, ToolDB, ScheduleDB,
    init_db, get_connection
)


class CRUDListPanel(Static):
    """Base class for CRUD list panels."""

    def __init__(self, id: str, title: str, db_class, **kwargs):
        super().__init__(**kwargs)
        self.panel_id = id
        self.title = title
        self.db_class = db_class
        self.items: List[Dict] = []
        self.selected_index = 0

    def compose(self) -> ComposeResult:
        yield Static(f"=== {self.title} ===", id=f"{self.panel_id}-title")
        yield ListView(id=f"{self.panel_id}-list")
        yield Horizontal(
            Button("C", id=f"{self.panel_id}-btn-create", variant="primary"),
            Button("R", id=f"{self.panel_id}-btn-read"),
            Button("U", id=f"{self.panel_id}-btn-update"),
            Button("D", id=f"{self.panel_id}-btn-delete"),
            id=f"{self.panel_id}-buttons"
        )
        yield Static("", id=f"{self.panel_id}-detail")
        yield Input(placeholder=f"Enter {self.title.lower()} name or data...", id=f"{self.panel_id}-input")

    def on_mount(self) -> None:
        self.refresh_items()

    def refresh_items(self):
        """Refresh items from database."""
        try:
            self.items = self.db_class.get_all()
            list_view = self.query_one(f"#{self.panel_id}-list", ListView)
            list_view.clear()
            for item in self.items:
                label = self.get_item_label(item)
                list_view.append(ListItem(Label(label), id=f"{self.panel_id}-item-{item['id']}"))
        except Exception as e:
            self.app.notify(f"Error loading {self.title}: {e}", severity="error")

    def get_item_label(self, item: Dict) -> str:
        """Get display label for item. Override in subclass."""
        return str(item)

    def get_selected_item(self) -> Optional[Dict]:
        """Get currently selected item."""
        list_view = self.query_one(f"#{self.panel_id}-list", ListView)
        if list_view.index is None:
            return None
        idx = list_view.index
        if 0 <= idx < len(self.items):
            return self.items[idx]
        return None

    def action_create(self):
        """Create new item."""
        input_widget = self.query_one(f"#{self.panel_id}-input", Input)
        name = input_widget.value.strip()
        if not name:
            self.app.notify(f"Enter a name for {self.title}", severity="warning")
            return
        try:
            self.db_class.create(name)
            input_widget.value = ""
            self.refresh_items()
            self.app.notify(f"{self.title[:-1]} created", severity="success")
        except Exception as e:
            self.app.notify(f"Error creating: {e}", severity="error")

    def action_read(self):
        """Read selected item details."""
        item = self.get_selected_item()
        if not item:
            self.app.notify(f"Select a {self.title[:-1].lower()}", severity="warning")
            return
        detail = self.query_one(f"#{self.panel_id}-detail", Static)
        detail_str = self.format_detail(item)
        detail.update(detail_str)

    def format_detail(self, item: Dict) -> str:
        """Format item details for display."""
        lines = [f"ID: {item['id']}"]
        for k, v in item.items():
            if k != 'id':
                lines.append(f"{k}: {v}")
        return "\n".join(lines)

    def action_update(self):
        """Update selected item."""
        item = self.get_selected_item()
        if not item:
            self.app.notify(f"Select a {self.title[:-1].lower()}", severity="warning")
            return
        input_widget = self.query_one(f"#{self.panel_id}-input", Input)
        new_name = input_widget.value.strip()
        if not new_name:
            self.app.notify("Enter new name", severity="warning")
            return
        try:
            self.db_class.update(item['id'], name=new_name)
            input_widget.value = ""
            self.refresh_items()
            self.app.notify(f"{self.title[:-1]} updated", severity="success")
        except Exception as e:
            self.app.notify(f"Error updating: {e}", severity="error")

    def action_delete(self):
        """Delete selected item."""
        item = self.get_selected_item()
        if not item:
            self.app.notify(f"Select a {self.title[:-1].lower()}", severity="warning")
            return
        try:
            self.db_class.delete(item['id'])
            self.refresh_items()
            self.app.notify(f"{self.title[:-1]} deleted", severity="success")
        except Exception as e:
            self.app.notify(f"Error deleting: {e}", severity="error")


class ProvidersPanel(CRUDListPanel):
    """Providers CRUD panel."""

    def __init__(self, **kwargs):
        super().__init__("providers", "Providers", ProviderDB, **kwargs)

    def get_item_label(self, item: Dict) -> str:
        return f"{item['name']} ({item['provider_type']})"


class ModelsPanel(CRUDListPanel):
    """Models CRUD panel."""

    def __init__(self, **kwargs):
        super().__init__("models", "Models", ModelDB, **kwargs)

    def get_item_label(self, item: Dict) -> str:
        return f"{item['name']} ({item['model_id']})"


class AgentsPanel(CRUDListPanel):
    """Agents CRUD panel."""

    def __init__(self, **kwargs):
        super().__init__("agents", "Agents", AgentDB, **kwargs)

    def get_item_label(self, item: Dict) -> str:
        return f"{item['name']}"


class SessionsPanel(CRUDListPanel):
    """Sessions CRUD panel."""

    def __init__(self, **kwargs):
        super().__init__("sessions", "Sessions", SessionDB, **kwargs)

    def get_item_label(self, item: Dict) -> str:
        name = item['name'] or f"Session {item['id']}"
        return f"{name}"


class ToolsPanel(CRUDListPanel):
    """Tools CRUD panel."""

    def __init__(self, **kwargs):
        super().__init__("tools", "Tools", ToolDB, **kwargs)

    def get_item_label(self, item: Dict) -> str:
        return f"{item['name']}"


class SchedulesPanel(CRUDListPanel):
    """Schedules CRUD panel."""

    def __init__(self, **kwargs):
        super().__init__("schedules", "Schedules", ScheduleDB, **kwargs)

    def get_item_label(self, item: Dict) -> str:
        status = "✓" if item['enabled'] else "✗"
        return f"{item['name']} ({item['cron_expression']}) {status}"


class ChatHistoryPanel(Static):
    """Chat history panel for viewing messages in a session."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.messages: List[Dict] = []

    def compose(self) -> ComposeResult:
        yield Static("=== Chat History ===", id="chat-history-title")
        yield ListView(id="chat-history-list")
        yield Static("Select a session to view messages", id="chat-history-empty")

    def show_session(self, session_id: int):
        """Show messages for a session."""
        from db import MessageDB
        self.messages = MessageDB.get_by_session(session_id)
        list_view = self.query_one("#chat-history-list", ListView)
        list_view.clear()
        for msg in self.messages:
            role = msg['role'][:4]
            content = msg['content'][:40] + "..." if len(msg['content']) > 40 else msg['content']
            list_view.append(ListItem(
                Label(f"[{role}] {content}"),
                id=f"msg-{msg['id']}"
            ))


class SettingsPanel(Static):
    """Settings panel."""

    def compose(self) -> ComposeResult:
        yield Static("=== Settings ===", id="settings-title")
        yield Static("API Key:", id="settings-api-key-label")
        yield Input(password=True, placeholder="Enter API key...", id="settings-api-key")
        yield Static("Default Provider:", id="settings-provider-label")
        yield Input(placeholder="Provider name...", id="settings-provider")
        yield Static("Theme:", id="settings-theme-label")
        yield Input(placeholder="light/dark/auto...", id="settings-theme")
        yield Button("Save Settings", id="settings-save", variant="primary")


if __name__ == "__main__":
    init_db()
    print("Database initialized")
