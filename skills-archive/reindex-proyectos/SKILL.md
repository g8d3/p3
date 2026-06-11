---
name: reindex-proyectos
description: Reindexa proyectos nuevos en p3/ — escanea, genera descripciones con AI, renombra directorios y actualiza FOLDER_INDEX.md.
---

# Reindex de Proyectos (p3)

Escanea `~/code/p3/` en busca de directorios `s*` no indexados, recolecta metadata (file tree, README, dependencias), invoca un AI agent para generar descripciones, renombra directorios a `s{NN}-{nombre}` y actualiza `FOLDER_INDEX.md`.

## Uso

```bash
cd ~/code/p3

# Default (usa opencode)
./reindex.sh

# Dry-run (solo muestra qué haría)
./reindex.sh --dry-run

# Con agente específico
REINDEX_AGENT=opencode ./reindex.sh
REINDEX_AGENT=crush   ./reindex.sh
REINDEX_AGENT=hermes  ./reindex.sh
```

## Agentes soportados

| Variable | Default | Agente |
|---|---|---|
| `REINDEX_AGENT=opencode` | ✅ sí | OpenCode |
| `REINDEX_AGENT=crush` | ❌ | Crush |
| `REINDEX_AGENT=hermes` | ❌ | Hermes |
| `REINDEX_AGENT=pi` | ❌ | pi |

## Qué hace

1. Escanea `s*` en busca de directorios no listados en `FOLDER_INDEX.md`
2. Ignora directorios vacíos
3. Recolecta: file tree (top 20 archivos), README header, package.json/pyproject.toml, extensiones dominantes
4. Construye prompt y llama al AI agent
5. Parsea la respuesta (formato: `sXX-name | description`)
6. Renombra directorios si es necesario
7. Actualiza `FOLDER_INDEX.md` (agrega/actualiza entradas, reordena numéricamente)

## Notas

- El script está en `~/code/p3/reindex.sh`
- Ver `~/code/p3/REINDEX.md` para documentación completa
- No requiere permisos especiales ni instalación de dependencias (usa solo bash + find + sed)
