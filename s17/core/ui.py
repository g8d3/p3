"""Terminal UI components using standard curses and rich."""

import curses
import sys
import os
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass
from datetime import datetime
from io import StringIO

try:
    from rich.text import Text
    from rich.console import Console
    from rich.panel import Panel
    from rich.table import Table
    from rich.box import Box, ROUNDED
    HAS_RICH = True
except ImportError:
    HAS_RICH = False


@dataclass
class UITheme:
    """Terminal UI theme."""
    
    bg_color: int = 0
    fg_color: int = 7
    header_fg: int = 3
    header_bg: int = 4
    highlight_fg: int = 7
    highlight_bg: int = 5
    success_fg: int = 2
    error_fg: int = 1
    warning_fg: int = 3
    info_fg: int = 6
    user_fg: int = 2
    assistant_fg: int = 3
    system_fg: int = 5
    border_fg: int = 8
    panel_bg: int = 0


class Colors:
    """Color pairs for curses."""
    
    BLACK = 0
    RED = 1
    GREEN = 2
    YELLOW = 3
    BLUE = 4
    MAGENTA = 5
    CYAN = 6
    WHITE = 7
    DEFAULT = 8
    
    @classmethod
    def init_pairs(cls, stdscr):
        """Initialize color pairs."""
        curses.start_color()
        curses.use_default_colors()
        for i in range(256):
            curses.init_pair(i, i, -1)
    
    @classmethod
    def pair(cls, fg: int, bg: int = 0) -> int:
        return curses.color_pair(fg) | curses.A_BOLD if fg < 8 else fg


class Panel:
    """Base panel class."""
    
    def __init__(self, stdscr, y: int, x: int, height: int, width: int, title: str = ""):
        self.stdscr = stdscr
        self.y = y
        self.x = x
        self.height = height
        self.width = width
        self.title = title
        self.content = []
        self.scroll_offset = 0
        self.ui = None
    
    def clear(self):
        """Clear the panel."""
        for y in range(self.height):
            try:
                self.stdscr.addstr(self.y + y, self.x, " " * self.width)
            except curses.error:
                pass
    
    def draw_border(self):
        """Draw panel border."""
        try:
            if self.title:
                title_str = f" {self.title} "
                self.stdscr.addstr(self.y, self.x, "┌", curses.color_pair(Colors.CYAN))
                self.stdscr.addstr(self.y, self.x + 1, title_str, curses.color_pair(Colors.CYAN))
                self.stdscr.addstr(self.y, self.x + len(title_str) + 1, "─" * (self.width - len(title_str) - 2), curses.color_pair(Colors.CYAN))
                self.stdscr.addstr(self.y, self.x + self.width - 1, "┐", curses.color_pair(Colors.CYAN))
                
                for y in range(self.y + 1, self.y + self.height - 1):
                    self.stdscr.addstr(y, self.x, "│", curses.color_pair(Colors.CYAN))
                    self.stdscr.addstr(y, self.x + self.width - 1, "│", curses.color_pair(Colors.CYAN))
                
                self.stdscr.addstr(self.y + self.height - 1, self.x, "└", curses.color_pair(Colors.CYAN))
                self.stdscr.addstr(self.y + self.height - 1, self.x + self.width - 1, "┘", curses.color_pair(Colors.CYAN))
                for x in range(self.x + 1, self.x + self.width - 1):
                    self.stdscr.addstr(self.y + self.height - 1, x, "─", curses.color_pair(Colors.CYAN))
            else:
                for y in range(self.y, self.y + self.height):
                    self.stdscr.addstr(y, self.x, "│", curses.color_pair(Colors.CYAN))
                    self.stdscr.addstr(y, self.x + self.width - 1, "│", curses.color_pair(Colors.CYAN))
                self.stdscr.addstr(self.y, self.x, "┌" + "─" * (self.width - 2) + "┐", curses.color_pair(Colors.CYAN))
                self.stdscr.addstr(self.y + self.height - 1, self.x, "└" + "─" * (self.width - 2) + "┘", curses.color_pair(Colors.CYAN))
        except curses.error:
            pass
    
    def add_text(self, y: int, x: int, text: str, color: int = Colors.WHITE):
        """Add text to panel."""
        try:
            self.stdscr.addstr(self.y + y, self.x + x, text[:self.width - x - 1], color)
        except curses.error:
            pass
    
    def render(self):
        """Render the panel."""
        self.clear()
        self.draw_border()
        for i, line in enumerate(self.content[self.scroll_offset:self.scroll_offset + self.height - 2]):
            self.add_text(i + 1, 1, line[:self.width - 2])
    
    def set_content(self, lines: List[str]):
        """Set panel content."""
        self.content = lines
        if len(self.content) > self.height - 2:
            self.scroll_offset = max(0, len(self.content) - (self.height - 2))


class ChatPanel(Panel):
    """Chat message display panel."""
    
    def __init__(self, stdscr, y: int, x: int, height: int, width: int):
        super().__init__(stdscr, y, x, height, width, " Chat ")
        self.messages = []
    
    def add_message(self, role: str, content: str, metadata: Optional[Dict] = None):
        """Add a message to the chat."""
        timestamp = datetime.now().strftime("%H:%M:%S")
        
        if role == "user":
            role_color = curses.color_pair(Colors.GREEN)
            role_label = "You"
        elif role == "assistant":
            role_color = curses.color_pair(Colors.YELLOW)
            role_label = "AI"
        else:
            role_color = curses.color_pair(Colors.MAGENTA)
            role_label = role.title()
        
        lines = content.split("\n")
        
        header = f"[{timestamp}] {role_label}:"
        self.messages.append((header, role_color, True))
        
        for line in lines:
            self.messages.append((f"  {line}", role_color, False))
        
        if metadata:
            meta_lines = self.format_metadata(metadata)
            for line in meta_lines:
                self.messages.append((f"    {line}", curses.color_pair(Colors.CYAN), False))
        
        self.messages.append(("", Colors.WHITE, False))
        
        self.update_content()
    
    def format_metadata(self, metadata: Dict) -> List[str]:
        """Format metadata for display."""
        lines = []
        if "tokens_in" in metadata and "tokens_out" in metadata:
            lines.append(f"Tokens: {metadata['tokens_in']} in, {metadata['tokens_out']} out")
        if "latency_ms" in metadata:
            lines.append(f"Latency: {metadata['latency_ms']:.0f}ms")
        if "ttft_ms" in metadata:
            lines.append(f"TTFT: {metadata['ttft_ms']:.0f}ms")
        if "cost" in metadata:
            lines.append(f"Cost: ${metadata['cost']:.4f}")
        if "tokens_per_second" in metadata:
            lines.append(f"Speed: {metadata['tokens_per_second']:.1f} tok/s")
        return lines
    
    def update_content(self):
        """Update panel content from messages."""
        self.content = []
        for msg, color, is_header in self.messages:
            if is_header:
                self.content.append(msg)
            else:
                self.content.append(msg)
        self.set_content(self.content)
    
    def clear_chat(self):
        """Clear all messages."""
        self.messages = []
        self.content = []
        self.scroll_offset = 0


class TransparencyPanel(Panel):
    """Transparency info panel."""
    
    def __init__(self, stdscr, y: int, x: int, height: int, width: int):
        super().__init__(stdscr, y, x, height, width, " Transparency ")
        self.api_logs = []
        self.stats = {}
    
    def add_api_log(self, log: Dict):
        """Add API log entry."""
        timestamp = datetime.now().strftime("%H:%M:%S")
        
        status = log.get("status_code", "N/A")
        if status and status < 300:
            status_color = curses.color_pair(Colors.GREEN)
        elif status and status < 500:
            status_color = curses.color_pair(Colors.YELLOW)
        else:
            status_color = curses.color_pair(Colors.RED)
        
        latency = log.get("latency_ms", 0)
        tokens_in = log.get("tokens_in", 0)
        tokens_out = log.get("tokens_out", 0)
        
        entry = f"[{timestamp}] {log.get('provider_name', '?')}/{log.get('model_name', '?')} - {status} - {latency:.0f}ms - {tokens_in}/{tokens_out}t"
        
        self.api_logs.insert(0, (entry, status_color))
        
        if len(self.api_logs) > 50:
            self.api_logs = self.api_logs[:50]
        
        self.update_content()
    
    def update_stats(self, stats: Dict):
        """Update statistics."""
        self.stats = stats
        self.update_content()
    
    def update_content(self):
        """Update panel content."""
        self.content = []
        
        self.content.append("=== Statistics ===")
        if self.stats:
            for key, value in self.stats.items():
                if isinstance(value, float):
                    self.content.append(f"  {key}: {value:.2f}")
                else:
                    self.content.append(f"  {key}: {value}")
        else:
            self.content.append("  No data yet")
        
        self.content.append("")
        self.content.append("=== Recent API Calls ===")
        
        for log, color in self.api_logs[:20]:
            self.content.append(log)
        
        self.set_content(self.content)


class InputPanel(Panel):
    """User input panel."""
    
    def __init__(self, stdscr, y: int, x: int, height: int, width: int):
        super().__init__(stdscr, y, x, height, width, " Input ")
        self.input_text = ""
        self.cursor_pos = 0
        self.history = []
        self.history_index = -1
    
    def get_input(self, prompt: str = "> ") -> str:
        """Get user input."""
        self.stdscr.nodelay(True)
        self.clear()
        self.draw_border()
        
        self.input_text = ""
        self.cursor_pos = 0
        self.history_index = -1
        
        try:
            self.stdscr.addstr(self.y + 1, self.x + 1, prompt, curses.color_pair(Colors.CYAN))
            self.stdscr.addstr(self.y + 1, self.x + 1 + len(prompt), self.input_text)
            self.stdscr.move(self.y + 1, self.x + 1 + len(prompt) + self.cursor_pos)
            self.stdscr.refresh()
            
            while True:
                key = self.stdscr.getch()
                
                if key == curses.ERR:
                    if hasattr(self, 'ui') and self.ui and self.ui.key_queue:
                        key = self.ui.key_queue.pop(0)
                    else:
                        self.stdscr.refresh()
                        continue
                
                if key == curses.KEY_ENTER or key in (10, 13):
                    text = self.input_text
                    if text.strip():
                        self.history.append(text)
                        self.clear()
                        self.stdscr.nodelay(False)
                        return text
                    continue
                
                elif key in (curses.KEY_BACKSPACE, 127, 8):
                    if self.cursor_pos > 0:
                        self.input_text = self.input_text[:self.cursor_pos - 1] + self.input_text[self.cursor_pos:]
                        self.cursor_pos -= 1
                
                elif key == curses.KEY_DC:
                    if self.cursor_pos < len(self.input_text):
                        self.input_text = self.input_text[:self.cursor_pos] + self.input_text[self.cursor_pos + 1:]
                
                elif key == curses.KEY_LEFT:
                    if self.cursor_pos > 0:
                        self.cursor_pos -= 1
                
                elif key == curses.KEY_RIGHT:
                    if self.cursor_pos < len(self.input_text):
                        self.cursor_pos += 1
                
                elif key == curses.KEY_UP:
                    if self.history and self.history_index < len(self.history) - 1:
                        self.history_index += 1
                        self.input_text = self.history[-(self.history_index + 1)]
                        self.cursor_pos = len(self.input_text)
                
                elif key == curses.KEY_DOWN:
                    if self.history_index > 0:
                        self.history_index -= 1
                        self.input_text = self.history[-(self.history_index + 1)]
                        self.cursor_pos = len(self.input_text)
                    elif self.history_index == 0:
                        self.history_index = -1
                        self.input_text = ""
                        self.cursor_pos = 0
                
                elif 32 <= key <= 126:
                    char = chr(key)
                    self.input_text = self.input_text[:self.cursor_pos] + char + self.input_text[self.cursor_pos:]
                    self.cursor_pos += 1
                
                elif key == 27:
                    self.clear()
                    self.stdscr.nodelay(False)
                    return ""
                
                self.clear()
                self.draw_border()
                display_text = self.input_text[:self.width - len(prompt) - 3]
                display_pos = min(self.cursor_pos, len(display_text))
                
                self.stdscr.addstr(self.y + 1, self.x + 1, prompt, curses.color_pair(Colors.CYAN))
                self.stdscr.addstr(self.y + 1, self.x + 1 + len(prompt), display_text)
                
                if self.cursor_pos < len(self.input_text):
                    self.stdscr.move(self.y + 1, self.x + 1 + len(prompt) + display_pos)
                else:
                    self.stdscr.move(self.y + 1, self.x + 1 + len(prompt) + len(display_text))
                
                self.stdscr.refresh()
                
        except Exception:
            self.stdscr.nodelay(False)
            return ""
        finally:
            self.stdscr.nodelay(False)
    
    def clear_input(self):
        """Clear input field."""
        self.input_text = ""
        self.cursor_pos = 0


class MenuPanel(Panel):
    """Menu/selection panel."""
    
    def __init__(self, stdscr, y: int, x: int, height: int, width: int, title: str = " Menu "):
        super().__init__(stdscr, y, x, height, width, title)
        self.items = []
        self.selected_index = 0
        self.on_select = None
    
    def set_items(self, items: List[str], on_select: Optional[Callable[[int, str], None]] = None):
        """Set menu items."""
        self.items = items
        self.selected_index = 0
        self.on_select = on_select
        self.update_content()
    
    def update_content(self):
        """Update panel content."""
        self.content = []
        for i, item in enumerate(self.items):
            if i == self.selected_index:
                self.content.append(f" > {item} <")
            else:
                self.content.append(f"   {item}   ")
        self.set_content(self.content)
    
    def handle_input(self, key: int) -> Optional[int]:
        """Handle menu input. Returns selected index or None."""
        if key == curses.KEY_UP:
            self.selected_index = max(0, self.selected_index - 1)
            self.update_content()
            return None
        elif key == curses.KEY_DOWN:
            self.selected_index = min(len(self.items) - 1, self.selected_index + 1)
            self.update_content()
            return None
        elif key in (curses.KEY_ENTER, 10, 13):
            if self.on_select:
                self.on_select(self.selected_index, self.items[self.selected_index])
            return self.selected_index
        return None


class StatusBar:
    """Status bar at bottom of screen."""
    
    def __init__(self, stdscr, height: int, width: int):
        self.stdscr = stdscr
        self.height = height
        self.width = width
    
    def render(self, left: str = "", center: str = "", right: str = ""):
        """Render status bar."""
        try:
            self.stdscr.addstr(self.height - 1, 0, " " * self.width)
            
            if left:
                self.stdscr.addstr(self.height - 1, 1, left[:20], curses.color_pair(Colors.CYAN))
            
            if center:
                center_start = (self.width - len(center)) // 2
                self.stdscr.addstr(self.height - 1, center_start, center, curses.color_pair(Colors.YELLOW))
            
            if right:
                self.stdscr.addstr(self.height - 1, self.width - len(right) - 2, right, curses.color_pair(Colors.CYAN))
        except curses.error:
            pass


class UITerminal:
    """Main terminal UI controller."""
    
    def __init__(self):
        self.stdscr = None
        self.theme = UITheme()
        self.chat_panel = None
        self.transparency_panel = None
        self.input_panel = None
        self.menu_panel = None
        self.status_bar = None
        self.panels = []
        self.key_queue = []
        self.ready = False
    
    def init_screen(self):
        """Initialize curses screen with proper terminal setup."""
        self.stdscr = curses.initscr()
        curses.noecho()
        curses.cbreak()
        self.stdscr.keypad(True)
        Colors.init_pairs(self.stdscr)
        curses.curs_set(1)
        
        # Send terminal setup sequences for better compatibility
        self.stdscr.addstr("\033[?1049h")  # Enable alternate screen
        self.stdscr.addstr("\033[?1h")     # Enable application cursor
        self.stdscr.addstr("\033[?25l")    # Hide cursor initially
        self.stdscr.refresh()
    
    def setup_panels(self, height: int, width: int):
        """Setup UI panels based on screen size."""
        chat_width = max(40, int(width * 0.6))
        trans_width = width - chat_width - 2
        
        self.chat_panel = ChatPanel(self.stdscr, 1, 0, height - 5, chat_width)
        self.chat_panel.ui = self
        self.transparency_panel = TransparencyPanel(self.stdscr, 1, chat_width + 1, height - 5, trans_width)
        self.transparency_panel.ui = self
        self.input_panel = InputPanel(self.stdscr, height - 4, 0, 3, width)
        self.input_panel.ui = self
        self.status_bar = StatusBar(self.stdscr, height, width)
        
        self.panels = [self.chat_panel, self.transparency_panel, self.input_panel]
    
    def cleanup(self):
        """Cleanup curses - properly restore terminal state."""
        try:
            if self.stdscr:
                # Hide cursor before exiting
                curses.curs_set(0)
                # Save cursor position and move to known location
                self.stdscr.addstr(curses.LINES - 1, 0, "\n")
                # Send proper exit sequences for problematic terminals
                self.stdscr.addstr("\033[?1049l")  # Disable alternate screen
                self.stdscr.addstr("\033[?1l")     # Disable application cursor
                self.stdscr.addstr("\033[?25h")    # Show cursor (normal state)
                self.stdscr.refresh()
                curses.nocbreak()
                self.stdscr.keypad(False)
                curses.echo()
                curses.endwin()
        except curses.error:
            pass
    
    def render(self):
        """Render all panels."""
        for panel in self.panels:
            panel.render()
        self.stdscr.refresh()
    
    def clear(self):
        """Clear screen."""
        self.stdscr.clear()
    
    def show_menu(self, title: str, items: List[str], on_select: Optional[Callable] = None) -> int:
        """Show a modal menu."""
        height = min(len(items) + 4, 20)
        width = max(30, max(len(item) for item in items) + 10)
        menu_panel = MenuPanel(
            self.stdscr,
            (curses.LINES - height) // 2,
            (curses.COLS - width) // 2,
            height,
            width,
            title
        )
        menu_panel.set_items(items, on_select)
        menu_panel.render()
        self.stdscr.refresh()
        
        while True:
            key = self.stdscr.getch()
            result = menu_panel.handle_input(key)
            if result is not None:
                menu_panel.clear()
                return result
            menu_panel.render()
            self.stdscr.refresh()
    
    def show_form(self, title: str, fields: List[str], defaults: List[str] = None) -> List[str]:
        """Show a form for input."""
        if defaults is None:
            defaults = ["" for _ in fields]
        
        form_height = len(fields) * 2 + 4
        form_width = max(50, max(len(f) for f in fields) + 30)
        
        y = (curses.LINES - form_height) // 2
        x = (curses.COLS - form_width) // 2
        
        results = defaults[:]
        current_field = 0
        
        self.stdscr.clear()
        
        try:
            self.stdscr.addstr(y, x + (form_width - len(title)) // 2, title, curses.color_pair(Colors.CYAN))
            
            for i, field in enumerate(fields):
                self.stdscr.addstr(y + 2 + i * 2, x + 2, field + ":")
                self.stdscr.addstr(y + 2 + i * 2, x + len(field) + 4, results[i][:form_width - len(field) - 10])
            
            self.stdscr.addstr(y + form_height - 2, x + 2, "[Enter] Submit  [Esc] Cancel")
            
            while current_field < len(fields):
                self.stdscr.move(y + 2 + current_field * 2, x + len(fields[current_field]) + 4 + len(results[current_field]))
                self.stdscr.refresh()
                
                self.stdscr.addstr(y + 2 + current_field * 2, x + len(fields[current_field]) + 4, " " * (form_width - len(fields[current_field]) - 10))
                self.stdscr.addstr(y + 2 + current_field * 2, x + len(fields[current_field]) + 4, results[current_field])
                self.stdscr.move(y + 2 + current_field * 2, x + len(fields[current_field]) + 4 + len(results[current_field]))
                self.stdscr.refresh()
                
                key = self.stdscr.getch()
                
                if key in (curses.KEY_ENTER, 10, 13):
                    current_field += 1
                elif key == 27:
                    return []
                elif key == curses.KEY_BACKSPACE or key in (127, 8):
                    if results[current_field]:
                        results[current_field] = results[current_field][:-1]
                elif 32 <= key <= 126:
                    if len(results[current_field]) < form_width - len(fields[current_field]) - 10:
                        results[current_field] += chr(key)
        except curses.error:
            pass
        
        return results
    
    def show_message(self, message: str, title: str = " Message "):
        """Show a message box."""
        lines = message.split("\n")
        height = len(lines) + 4
        width = max(40, max(len(line) for line in lines) + 4)
        
        y = (curses.LINES - height) // 2
        x = (curses.COLS - width) // 2
        
        try:
            self.stdscr.addstr(y, x, "┌" + "─" * (width - 2) + "┐", curses.color_pair(Colors.CYAN))
            self.stdscr.addstr(y, x + (width - len(title)) // 2, title, curses.color_pair(Colors.CYAN) | curses.A_REVERSE)
            self.stdscr.addstr(y + 1, x, "│", curses.color_pair(Colors.CYAN))
            self.stdscr.addstr(y + 1, x + width - 1, "│", curses.color_pair(Colors.CYAN))
            self.stdscr.addstr(y + 2, x, "│", curses.color_pair(Colors.CYAN))
            self.stdscr.addstr(y + 2, x + width - 1, "│", curses.color_pair(Colors.CYAN))
            self.stdscr.addstr(y + 3, x, "└" + "─" * (width - 2) + "┘", curses.color_pair(Colors.CYAN))
            
            for i, line in enumerate(lines):
                display_line = line[:width - 4]
                self.stdscr.addstr(y + 1 + i, x + 2, display_line)
            
            self.stdscr.addstr(y + height - 1, x + (width - 15) // 2, "[ Press any key ]")
            self.stdscr.refresh()
            self.stdscr.getch()
        except curses.error:
            pass

    def inject_key(self, key: str) -> bool:
        """Inject a keystroke into the TUI. Returns True if accepted."""
        if not self.stdscr:
            return False

        key_map = {
            'enter': curses.KEY_ENTER,
            'esc': 27,
            'escape': 27,
            'up': curses.KEY_UP,
            'down': curses.KEY_DOWN,
            'left': curses.KEY_LEFT,
            'right': curses.KEY_RIGHT,
            'home': curses.KEY_HOME,
            'end': curses.KEY_END,
            'delete': curses.KEY_DC,
            'backspace': curses.KEY_BACKSPACE,
            'tab': 9,
            'f1': curses.KEY_F1,
            'f2': curses.KEY_F2,
            'f3': curses.KEY_F3,
            'f4': curses.KEY_F4,
            'f5': curses.KEY_F5,
            'f6': curses.KEY_F6,
            'f7': curses.KEY_F7,
            'f8': curses.KEY_F8,
            'f9': curses.KEY_F9,
            'f10': curses.KEY_F10,
            'f11': curses.KEY_F11,
            'f12': curses.KEY_F12,
        }

        if key in key_map:
            key_code = key_map[key]
        elif len(key) == 1:
            key_code = ord(key)
        else:
            key_code = ord(key[0])

        self.key_queue.append(key_code)
        return True

    def get_screen_text(self) -> str:
        """Get current screen contents as text."""
        if not self.stdscr:
            return ""

        try:
            height, width = self.stdscr.getmaxyx()
            lines = []
            for y in range(height):
                row = []
                for x in range(width - 1):
                    try:
                        char = self.stdscr.instr(y, x, 1).decode('utf-8', errors='replace')
                        row.append(char)
                    except:
                        row.append(' ')
                lines.append(''.join(row))
            return '\n'.join(lines)
        except curses.error:
            return ""

    def get_state(self) -> Dict[str, Any]:
        """Get current TUI state."""
        return {
            'has_screen': self.stdscr is not None,
            'ready': self.ready,
            'panels': len(self.panels),
            'chat_panel_active': self.chat_panel is not None,
            'transparency_panel_active': self.transparency_panel is not None,
            'input_panel_active': self.input_panel is not None,
            'status_bar_active': self.status_bar is not None,
            'queued_keys': len(self.key_queue),
        }
