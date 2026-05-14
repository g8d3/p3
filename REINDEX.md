# Reindex — Hybrid Bash + AI

## Cómo funciona

Este directorio usa un reindex híbrido:

1. **Bash** (`reindex.sh`) escanea, encuentra directorios nuevos, ignora vacíos, recolecta metadata
2. **AI agent** (pi, opencode o hermes) genera descripciones de los proyectos nuevos
3. **Bash** aplica los cambios: renombra directorios, actualiza `FOLDER_INDEX.md`

## Uso

```bash
# Reindex normal (usa pi, el agente por defecto)
./reindex.sh

# Dry-run (solo muestra qué haría, no aplica cambios)
./reindex.sh --dry-run

# Usar un agente específico
REINDEX_AGENT=opencode ./reindex.sh
REINDEX_AGENT=hermes ./reindex.sh

# Sin output del AI a stderr
REINDEX_AGENT=pi ./reindex.sh 2>/dev/null
```

## Reglas

- **Directorios vacíos se ignoran** — no se crean entradas "scratchpad"
- Directorios con contenido se renombran a `sXX-nombre-descriptivo`
- Descripciones generadas por AI (máx 200 chars, inglés claro)
- El índice se mantiene ordenado numéricamente

## Agentes soportados

| Variable | Agente | Comando |
|---|---|---|
| `REINDEX_AGENT=pi` (default) | pi | `pi -p "@prompt"` |
| `REINDEX_AGENT=opencode` | OpenCode | `opencode run "@prompt"` |
| `REINDEX_AGENT=hermes` | Hermes Agent | `hermes run "@prompt"` |
