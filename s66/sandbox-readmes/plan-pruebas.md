# Plan de Pruebas: Sandbox Multi-Agente

## Agentes a probar

| Agente | API Key | Cómo pasar al sandbox | Modelo default |
|--------|---------|-----------------------|----------------|
| **OpenCode** | `OPENAI_API_KEY` | `--env OPENAI_API_KEY=$KEY` | — |
| **Claude Code** | `ANTHROPIC_AUTH_TOKEN` + `ANTHROPIC_BASE_URL` | `--env ANTHROPIC_AUTH_TOKEN=$TOKEN --env ANTHROPIC_BASE_URL=$URL` | — |
| **Pi** | key propia en `auth.json` | `--env OPENCODE_GO_API_KEY=$KEY` (o pasar el auth.json) | deepseek-v4-flash |
| **Goose** | `ZAI_API_KEY` | `--env ZAI_API_KEY=$KEY` | glm-5 |

## Objetivo
Medir si microsandbox permite ejecutar múltiples agentes AI en paralelo sin degradación, y si el patrón supervisor-worker (checkpoint/restore) mejora la tasa de finalización de tareas.

---

## Test 1 — Escalabilidad: recursos vs número de agentes

Medir cuántos sandboxes podemos tener simultáneamente antes de saturar el sistema.

| # Sandboxes | RAM host (total) | RAM por sandbox | CPU host | Cold start (total) |
|-------------|------------------|-----------------|----------|-------------------|
| 1 | ? | ? | ? | ? |
| 2 | ? | ? | ? | ? |
| 4 | ? | ? | ? | ? |
| 8 | ? | ? | ? | ? |

**Procedimiento:**
1. Crear N sandboxes Ubuntu (512MB RAM, 1 CPU cada uno)
2. Esperar que todos estén `running`
3. Ejecutar `msb metrics` en cada uno + `free -h` en el host
4. Destruir todo

**Criterio de éxito:** Poder tener 4+ sandboxes sin swap ni throttling.

---

## Test 2 — Tarea simple en 1 agente (baseline)

Crear 1 sandbox con OpenCode instalado, pasarle una tarea, medir:

| Métrica | Valor |
|---------|-------|
| Cold start → agente listo | ? |
| Tiempo de tarea | ? |
| RAM usada (pico) | ? |
| CPU usada (promedio) | ? |
| ¿Completó? | ? |
| ¿Errores? | ? |

**Tarea:** `"Create a python script that generates a random password of 16 characters with letters, numbers and symbols. Save it to /tmp/password.py and run it."`

---

## Test 3 — Escalamiento: misma tarea en N agentes

Repetir Test 2 con 2, 4 agentes simultáneos.

| # Agentes | Tiempo total | Completados | Fallos | RAM total |
|-----------|-------------|-------------|--------|-----------|
| 1 | ? | ? | ? | ? |
| 2 | ? | ? | ? | ? |
| 4 | ? | ? | ? | ? |

---

## Test 4 — Checkpoint/Restore (simulación supervisor)

1. Crear sandbox, instalar tools, tomar checkpoint (`checkpoint-1`)
2. Ejecutar tarea multi-paso
3. Si el agente se traba (>60s sin output): matar, restaurar checkpoint-1, reintentar
4. Medir cuántos reintentos necesita vs sin checkpoint

**Tarea multi-paso:**
```
Paso 1: Install python3, pip, flask
Paso 2: Create a Flask app with 3 routes
Paso 3: Run the app and verify it responds
Paso 4: Add a SQLite database
Paso 5: Test the full stack
```

**Hipótesis:** Con checkpoint, cada reintento parte del paso donde falló, ahorrando tiempo.

---

## Test 5 — Aislamiento entre agentes

Verificar que el agente A no puede ver/afectar al agente B:

1. Crear sandbox A y B
2. Escribir archivo secreto en A (`/secret.txt`)
3. Intentar leer `/secret.txt` desde B
4. Ejecutar `stress --cpu 4` en A, medir si B se afecta

---

## Test 6 — Sesión nueva (fresh start)

Verificar que una sesión nueva siempre parte de un estado limpio:

1. Usar agente, crear archivos, instalar paquetes
2. Destruir sandbox
3. Crear sandbox nuevo con misma imagen
4. Verificar que los archivos/paquetes anteriores NO existen

**Criterio:** Fresh start = sin residuos.

---

## Logística

**API key disponible:** OpenAI (164 chars)
**Agente a usar:** OpenCode (usa OpenAI)
**Comando base:**
```bash
npx microsandbox exec <nombre> \
  --env "OPENAI_API_KEY=$OPENAI_API_KEY" \
  -- opencode -p "<tarea>" -q
```

**Medición:**
```bash
# Recursos por sandbox
npx microsandbox metrics <nombre>

# Recursos del host
free -m
top -bn1 | head -5
```
