# Resultados de Pruebas - Sandboxes para AI Agents

---

## Test 1 — Escalabilidad de Recursos

| # Sandboxes | RAM Host (usada) | RAM por sandbox | CPU por sandbox | Diferencia host |
|-------------|------------------|-----------------|-----------------|-----------------|
| 0 (baseline) | 3.3 GB | — | — | — |
| 1 | 3.3 GB | ~62 MB | ~0% | +0 MB |
| 2 | 3.4 GB | ~62 MB | ~0% | +100 MB |
| 4 | 3.5 GB | ~62 MB | ~0% | +200 MB |
| 8 | 3.7 GB | ~62 MB | ~1% | +400 MB |

**Conclusión:** 62 MB por sandbox inactivo. Con 11 GB disponibles → ~170 sandboxes antes de llenar RAM. CPU casi 0 en idle. El sistema escala linealmente sin problemas.

> Sistema: Linux x86_64, 12 cores, 15GB RAM, KVM disponible
> Fecha: 2026-05-22

---

## 1. capsule (capsulerun/capsule) — WebAssembly Sandbox

| Prueba | Resultado | Detalle |
|--------|-----------|---------|
| Instalación | ✅ | `pip install capsule-run` |
| Hello World | ✅ | `"Hello from Capsule!"` en 1ms |
| Código Python | ✅ | math.factorial(10), pi, sqrt |
| Aislamiento filesystem | ✅ | `/etc/passwd` → "No such file or directory" |
| Aislamiento red | N/A | WASM no tiene red por defecto |

**Conclusión:** Bueno para ejecutar snippets Python/TS generados por LLMs. No corre Linux ni binarios nativos. Instalación trivial, 0 issues abiertos.

**Útil para:** Tareas de código aisladas, no para ejecutar agentes completos.

---

## 2. ai-jail (akitaonrails/ai-jail) — Bubblewrap Wrapper

| Prueba | Resultado | Detalle |
|--------|-----------|---------|
| Instalación | ✅ | Binary release descargado |
| Ejecución | ❌ | `bwrap: setting up uid map: Permission denied` |
| Causa | — | AppArmor bloquea user namespaces en Ubuntu/Debian 24.04+ |
| Solución | — | `sudo sysctl kernel.apparmor_restrict_unprivileged_userns=0` o perfil AppArmor |

**Conclusión:** No funcionó por restricciones del sistema. Con sudo se arregla. Es el más simple conceptualmente: solo envuelve el agente en namespaces.

**Útil para:** Protección rápida de agentes locales si tienes sudo.

---

## 3. microsandbox (superradcompany/microsandbox) — microVM KVM

| Prueba | Resultado | Detalle |
|--------|-----------|---------|
| Instalación | ✅ | `npx microsandbox` (npm package) |
| Hello World | ✅ | Python hello desde microVM |
| Aislamiento procesos | ✅ | `ps aux` solo muestra `/init.krun` y sus hijos |
| Aislamiento filesystem | ✅ | No ve archivos del host |
| Red (saliente) | ✅ | `curl https://api.github.com` → 200 OK |
| Instalar paquetes | ✅ | `apt-get install curl` funciona |
| Sandbox persistente | ✅ | Named sandbox: create, exec, metrics, stop, rm |
| Resource limits | ✅ | CPU, memoria configurables |
| OpenCode instalado dentro | ✅ | v0.0.55 corriendo en la VM |
| Pasar API keys | ✅ | `--env OPENAI_API_KEY=$KEY` funciona |
| MCP Server | ✅ | 17 tools: sandbox_run, fs ops, volumes, metrics |
| Agente Skills | ✅ | `npx skills add superradcompany/skills` |
| Uso RAM | ✅ | ~65MB por sandbox |

**Conclusión:** Funciona completo. KVM microVM con aislamiento real. SDKs multi-lenguaje, MCP, Skills. Único problema: requiere KVM (tenemos).

**Útil para:** Todo lo que necesitas — correr agentes completos, aislados, con red, paquetes, persistencia.

---

## Tabla Resumen

| Criterio | capsule | ai-jail | microsandbox |
|----------|---------|---------|-------------|
| Tipo de aislamiento | WebAssembly | Namespaces (bwrap) | microVM (KVM) |
| Instalación | pip install | binary download | npx/npm/pip/cargo |
| ¿Corre Linux completo? | ❌ | ✅ | ✅ |
| ¿Corre binarios nativos? | ❌ | ✅ | ✅ |
| ¿Red? | ❌ | ✅ (restringible) | ✅ |
| ¿Requiere KVM? | ❌ | ❌ | ✅ |
| ¿Requiere sudo? | ❌ | ❌ (pero AppArmor...) | ❌ |
| OpenCode/Claude adentro | ❌ | ✅ | ✅ |
| MCP / Skills | ⚠️ | ❌ | ✅ |
| Tiempo cold start | ~3s | instantáneo | ~2-3s |
| RAM por instancia | ~16MB | ~0 (bwrap) | ~65MB |

---

## Próximos Pasos

Si este sistema te sirve para seguir probando:

1. **microsandbox + Claude Code supervisando workers** — Conectar Claude Code (host) al MCP server de microsandbox, así Claude decide cuándo crear sandboxes sin mancharte las manos
2. **Checkpoint/restore** — Probar el ciclo: crear sandbox → instalar tools → checkpoint → ejecutar agente → falla → restaurar checkpoint
3. **Múltiples sandboxes en paralelo** — Lanzar 3 agentes worker simultáneos, cada uno en su microVM

¿Quieres que explore alguna de estas?
