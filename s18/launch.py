#!/usr/bin/env python3

import subprocess
import os
from pathlib import Path

ROOT_DIR = Path(__file__).parent

def find_terminal():
    for term in ["gnome-terminal", "konsole", "xfce4-terminal", "alacritty", "kitty", "xterm", "wezterm", "foot"]:
        if os.system(f"which {term} >/dev/null 2>&1") == 0:
            return term
    return None

terminal = find_terminal()
if terminal:
    print(f"Starting in {terminal}...")
    if terminal in ["gnome-terminal", "konsole", "xfce4-terminal"]:
        subprocess.Popen([terminal, "--", "bash", "-c", f"cd {ROOT_DIR} && python3 bootstrap.py; exec bash"])
        subprocess.Popen([terminal, "--", "bash", "-c", f"cd {ROOT_DIR} && python3 tui.py; exec bash"])
    elif terminal in ["alacritty", "kitty", "wezterm", "foot"]:
        subprocess.Popen([terminal, "-e", "bash", "-c", f"cd {ROOT_DIR} && python3 bootstrap.py; exec bash"])
        subprocess.Popen([terminal, "-e", "bash", "-c", f"cd {ROOT_DIR} && python3 tui.py; exec bash"])
    else:
        subprocess.Popen([terminal, "-e", f"python3 {ROOT_DIR}/bootstrap.py"])
        subprocess.Popen([terminal, "-e", f"python3 {ROOT_DIR}/tui.py"])
else:
    print("No terminal found. Run manually:")
    print(f"  python3 {ROOT_DIR}/bootstrap.py")
    print(f"  python3 {ROOT_DIR}/tui.py")
