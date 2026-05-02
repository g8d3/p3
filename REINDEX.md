# Reindex Instruction

Scan the `/home/vuos/code/p3` directory for any `s*` folders (e.g. `s50`, `s51`, …) that are **not listed** in `FOLDER_INDEX.md`.

For each new folder found:

1. **Explore its contents** — read key files like `package.json`, `README.md`, `main.py`, `requirements.txt`, config files, and any source code to understand what the project does.
2. **Write a one-line description** (max 200 chars) explaining what the project is/does.
3. **Update `FOLDER_INDEX.md`** — insert the new row(s) into the table in numerical order. Follow the existing format exactly:
   ```
   | `sXX-descriptive-name` | One-line description. |
   ```
4. **Name the folder descriptively** — if the folder is still just `sXX` (no dash suffix), rename it to `sXX-descriptive-name` using `mv`. Keep the `sXX-` number prefix.

## Rules

- Preserve alphabetical/numerical sort order in the table.
- The folder name format is always `s<number>-<kebab-case-description>`.
- If a folder is empty, name it `sXX-scratch` and describe it as "Empty placeholder directory."
- Write descriptions in plain English — no marketing fluff, just what it actually does.
- Do not modify existing rows — only add new ones or rename bare `sXX` folders.
