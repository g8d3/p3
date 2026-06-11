# ROADMAP — Ideas para orquestar-agentes

> Ideas discutidas pero no implementadas aún. Cuando una se implemente, se mueve a SKILL.md y se tacha acá.

## Arquitectura / Infraestructura

- [ ] **Use Crush SQLite database instead of terminal scraping**: Each Crush instance stores structured data in `.crush/crush.db` (messages with roles, sessions, timestamps, content as JSON). Reading this directly would eliminate the fragility of parsing terminal output like `:::` or `│`. Requires finding each agent's database (they may share depending on working directory).
- [ ] **XDG directory layout**: `~/.config/orquestar-agentes/` (config), `~/.local/share/orquestar-agentes/` (data), `~/.local/state/orquestar-agentes/` (runtime), `./.orquestar-agentes/` (project-local)
- [ ] **Config merging**: base (skill) → global (XDG) → local (project) — each overrides the previous
- [ ] **Config editor in web UI**: ⚙️ tab to view/edit config.json, save to project-local or global
- [ ] **Stats persistence**: crash counters, agent uptime, message counts per agent
- [ ] **Use XDG paths everywhere**: logs, PIDs, history, stats

## Daemons

- [ ] **Supervisor Level 2**: detect crash loops (≥5 in 5min), escalate by writing structured task to a1/tasks/ with agent output + diagnostic commands
- [ ] **Ciclador as agent group**: allow multiple ciclador instances for different project directories
- [ ] **Task-runner queue**: retry logic, timeout per task, parallel execution

## Web Dashboard

- [ ] **Config tab**: agent roles, descriptions, daemon intervals — all editable from browser
- [ ] **Agent groups**: define groups (desarrollo, contenido, etc.) with their own agents
- [ ] **Stats view**: crash history, uptime, message count per agent
- [ ] **Live log streaming**: SSE instead of polling for logs
- [ ] **Video player improvements**: proper HLS or MSE streaming, playlist support

## Video System

- [ ] **Base videos**: extract from social media APIs, pre-rendered templates
- [ ] **Template evolution**: metrics-driven template improvement (retention, engagement)
- [ ] **Streaming protocol**: replace segment-based approach with MSE or WebRTC
- [ ] **Audio library**: download/use real music instead of ffmpeg-generated tones

## AI / Autonomy

- [ ] **Explorador agent**: proactively opens web dashboard, tests features, reports UX issues
- [ ] **Self-configuration**: agents adjust their own daemon parameters based on stats
- [ ] **Cross-project ciclador**: scan multiple projects (p1, p2, p3) for issues

## Testing

- [ ] **Pipeline stress test**: continuously inject errors and verify maker→checker cycle completes
- [ ] **Chaos monkey**: randomly kill agents and verify supervisor revives them within 4s
