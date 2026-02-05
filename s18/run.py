#!/usr/bin/env python3

import subprocess
import sys
import os
from pathlib import Path

ROOT_DIR = Path(__file__).parent
BOOTSTRAP = ROOT_DIR / "bootstrap.py"
TUI = ROOT_DIR / "tui.py"

def find_terminal():
    terminals = [
        "gnome-terminal",
        "konsole",
        "xfce4-terminal",
        "mate-terminal",
        "lxterminal",
        "xterm",
        "alacritty",
        "kitty",
        "wezterm",
        "foot"
    ]
    
    for term in terminals:
        if os.system(f"which {term} >/dev/null 2>&1") == 0:
            return term
    return None

def run_both():
    terminal = find_terminal()
    if not terminal:
        print("No compatible terminal found.")
        print("\nRun manually in two terminals:")
        print(f"  Terminal 1: {BOOTSTRAP}")
        print(f"  Terminal 2: {TUI}")
        return False
    
    term_commands = {
        "gnome-terminal": ["gnome-terminal", "--", "bash", "-c"],
        "konsole": ["konsole", "-e", "bash", "-c"],
        "xfce4-terminal": ["xfce4-terminal", "-e", "bash", "-c"],
        "mate-terminal": ["mate-terminal", "-x", "bash", "-c"],
        "lxterminal": ["lxterminal", "-e", "bash", "-c"],
        "xterm": ["xterm", "-e", "bash", "-c"],
        "alacritty": ["alacritty", "-e", "bash", "-c"],
        "kitty": ["kitty", "bash", "-c"],
        "wezterm": ["wezterm", "cli", "exec", "--", "bash", "-c"],
        "foot": ["foot", "bash", "-c"]
    }
    
    cmd = term_commands.get(terminal)
    if not cmd:
        print(f"Unknown terminal: {terminal}")
        return False
    
    print(f"Starting in {terminal}...")
    
    # Start bootstrap
    subprocess.Popen(cmd + [f"cd {ROOT_DIR} && python3 {BOOTSTRAP}; exec bash"])
    
    # Start tui
    subprocess.Popen(cmd + [f"cd {ROOT_DIR} && python3 {TUI}; exec bash"])
    
    return True

def main():
    if len(sys.argv) > 1:
        if sys.argv[1] == "bootstrap":
            os.system(f"python3 {BOOTSTRAP}")
        elif sys.argv[1] == "tui":
            os.system(f"python3 {TUI}")
        else:
            print("Usage: python3 run.py [bootstrap|tui]")
        return
    
    print("Autonomous Agent System Launcher")
    print("=" * 40)
    print()
    print("1. Run both (bootstrap + tui)")
    print("2. Run bootstrap only")
    print("3. Run tui only")
    print()
    
    try:
        choice = input("Select [1-3]: ").strip()
    except (EOFError, KeyboardInterrupt):
        print("\nGoodbye!")
        return
    
    if choice == "1":
        run_both()
    elif choice == "2":
        os.system(f"python3 {BOOTSTRAP}")
    elif choice == "3":
        os.system(f"python3 {TUI}")
    else:
        print("Invalid choice")

if __name__ == "__main__":
    main()
