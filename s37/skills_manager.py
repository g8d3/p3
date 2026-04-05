#!/usr/bin/env python3
"""Simple OpenCode skills manager - list and toggle skills."""

import os
import json
from pathlib import Path

SKILL_PATHS = [
    Path.home() / ".config/opencode/skills",
    Path.home() / ".claude/skills",
    Path.home() / ".agents/skills",
]

# Add project-local paths if in a git repo
def get_project_paths():
    cwd = Path.cwd()
    paths = []
    # Walk up to find git root
    for parent in [cwd] + list(cwd.parents):
        if (parent / ".git").exists():
            paths.extend([
                parent / ".opencode/skills",
                parent / ".claude/skills",
                parent / ".agents/skills",
            ])
            break
    return paths

def find_skills():
    """Find all skills and their status."""
    skills = []
    for base_path in SKILL_PATHS + get_project_paths():
        if not base_path.exists():
            continue
        for skill_dir in base_path.iterdir():
            if not skill_dir.is_dir() or skill_dir.name.startswith('.'):
                continue
            skill_file = skill_dir / "SKILL.md"
            disabled_file = skill_dir / "SKILL.md.disabled"
            if skill_file.exists() or disabled_file.exists():
                skills.append({
                    'name': skill_dir.name,
                    'path': skill_dir,
                    'enabled': skill_file.exists(),
                    'global': str(base_path).startswith(str(Path.home())),
                })
    return sorted(skills, key=lambda s: (s['global'], s['name']))

def toggle_skill(skill):
    """Toggle skill enabled/disabled."""
    skill_file = skill['path'] / "SKILL.md"
    disabled_file = skill['path'] / "SKILL.md.disabled"
    if skill['enabled']:
        skill_file.rename(disabled_file)
    else:
        disabled_file.rename(skill_file)
    skill['enabled'] = not skill['enabled']

def main():
    skills = find_skills()
    if not skills:
        print("No skills found.")
        return

    while True:
        print("\nSkills (x = enabled,   = disabled):")
        print("-" * 60)
        for i, skill in enumerate(skills, 1):
            status = "x" if skill['enabled'] else " "
            loc = "global" if skill['global'] else "local"
            print(f"{i:2}. [{status}] {skill['name']:30} ({loc})")
        print("-" * 60)
        print("Enter number to toggle, 'q' to quit: ", end="")
        
        choice = input().strip().lower()
        if choice == 'q':
            break
        if choice.isdigit():
            idx = int(choice) - 1
            if 0 <= idx < len(skills):
                toggle_skill(skills[idx])
                action = "Enabled" if skills[idx]['enabled'] else "Disabled"
                print(f"  → {action} {skills[idx]['name']}")
            else:
                print("  → Invalid number")
        elif choice:
            print("  → Enter a number or 'q'")

if __name__ == "__main__":
    main()
