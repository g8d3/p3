---
name: orquestar-agentes
description: "Orquesta agentes Crush en tmux con bus de mensajes bidireccional vía inotify, supervisor, y ciclo autónomo de trabajo. Sin long polling."
---

# Orquestar Agentes

Abre N ventanas tmux con agentes Crush, bus de mensajes, supervisor de salud, y ciclo autónomo de trabajo.

## Arquitectura

```
┌──────────────────────────────────────────────────┐
│                   orquestar                        │
│  (scripts que abren, cierran, monitorean)          │
└──────┬──────────┬────────────┬───────────────────┘
       │          │            │
   ┌───▼──┐  ┌────▼────┐  ┌───▼────────┐
   │ busd │  │supervisor│  │  ciclador  │
   │ inot │  │ cada 30s │  │ cada 15min │
   └──┬───┘  └─────────┘  └───┬────────┘
      │                        │
   ┌──▼────────────────────────▼──┐
   │   /tmp/agent-bus/            │
   │   a1/in/ (maker)             │
   │   a2/in/ (checker)           │
   │   a3/in/ (free)              │
   │   ciclador/                  │
   └──────────────────────────────┘
```

## Vocabulario estandarizado

| Término | Significado |
|---------|-------------|
| **abrir N agentes** | Crear N ventanas tmux con `crush --yolo` |
| **reiniciar agente** | Cerrar Crush (Ctrl+C + Ctrl+D) y volver a abrirlo |
| **nueva sesión** | Ctrl+N dentro de Crush |
| **roles** | a1=maker, a2=checker, a3=video-maker |

## Regla crítica para el AI: delegar, no hacer

**⚠️ LEE ESTO ANTES DE CUALQUIER ACCIÓN. SI SALTAS ESTA SECCIÓN, VAS A HACER EL TRABAJO DE LOS AGENTES.**

### Pre-action checklist (obligatorio antes de tocar cualquier archivo)

Antes de editar, crear, o modificar algo, pregúntate:

1. **¿Esto es trabajo de un agente?** (código web → a1, video → a3, etc.)
   - Si sí → **no lo hagas tú**. Escríbele al agente correspondiente.
2. **¿Es un cambio en el sistema mismo?** (skills, daemons, config, arquitectura)
   - Si sí → pregúntale al usuario antes, no decidas solo.
3. **¿Estoy a punto de correr bash, editar un archivo, o crear un script?**
   - Si sí → **DETENTE**. Pregunta: ¿puede hacerlo un agente?
4. **¿Estoy debuggeando algo que un agente creó?**
   - Si sí → pregúntale al agente qué pasó, no revises el código tú mismo.

### Si tienes la menor duda: NO LO HAGAS. PREGUNTA AL USUARIO.

### Flujo correcto

```
usuario: "el video tiene pitido, haz loop infinito"
  → NO edito nada
  → escribo a a3 (video-maker): "genera video con música, loop infinito"
  → a3 ejecuta
  → si el agente no puede, entonces sí intervengo
```

### Flujo incorrecto (lo que he hecho repetidamente)

```
usuario: "el video tiene pitido"
  → edito video-maker script ✗
  → edito index.html (loop) ✗
  → ejecuto ffmpeg directo ✗
  → el sistema de agentes queda bypassed ✗
```

### Cuándo delegar

| Situación | A quién |
|-----------|---------|
| Bug en código web | a1/tasks/ (task-runner) o a1/in/ (AI) |
| Mejora en video/audio | a3/in/ |
| Error de sintaxis detectado | el ciclador ya lo hace solo |
| Nueva funcionalidad | a1/tasks/ con comandos explícitos |
| Sistema mismo (skills, daemons, config) | preguntar al usuario |
| Agente no responde | preguntar al usuario o escribir tarea estructurada a a1/tasks/ |

## Daemons

| Daemon | Qué hace | Ciclo |
|--------|----------|-------|
| **busd** | Entrega mensajes entre agentes vía inotify | Continuo (eventos) |
| **supervisor** | Monitorea salud de agentes y busd, los revive si fallan | Cada 30s |
| **ciclador** | Escanea el proyecto, asigna issues a maker, espera veredicto de checker | Cada 15min |

## Scripts (en `scripts/`)

| Comando | Descripción |
|---------|-------------|
| `scripts/orquestar N` | Abre N agentes + bus + supervisor + skills |
| `scripts/orquestar N --new-session` | Ídem con `--session s76-aN` |
| `scripts/reiniciar N` | Mata Crush y lo reabre en cada agente |
| `scripts/nueva-sesion N` | Envía Ctrl+N a cada agente |
| `scripts/detener N` | Mata daemons, cierra ventanas, limpia bus |

## Skills instaladas

Al ejecutar `orquestar`, se instalan en `~/.agents/skills/`:

| Skill | Propósito |
|-------|-----------|
| **maker** | Implementa features, corrige bugs, mejora configurabilidad |
| **checker** | Prueba, revisa código, valida cambios, detecta errores |

## Ciclo autónomo (ciclador)

Para activar el ciclo de trabajo 24/7, descomentar en `orquestar`:

```bash
# scripts/orquestar 3 (con ciclador activado en el script)
```

O iniciar manualmente:

```bash
nohup scripts/ciclador /ruta/al/proyecto 15 > /dev/null 2>&1 &
```

El ciclo:
1. **Scan**: busca dependencias desactualizadas, TODOs, archivos sin test
2. **Assign**: escribe tarea en inbox de maker (a1)
3. **Maker**: implementa, notifica a checker via `say checker "revisa: X"`
4. **Checker**: valida, responde a maker y escribe veredicto en inbox del ciclador
5. **Loop**: si checker aprueba → siguiente ciclo; si rechaza → maker corrige
