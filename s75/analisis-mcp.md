# Análisis de decisiones: input-s74

## 1. MCP Config

| Decisión | Fuente | Detalle |
|---|---|---|
| **Archivo de configuración** | orch1.txt, orch2.txt | OpenCode usa `opencode.json` (o `opencode.jsonc`). Múltiples archivos se *fusionan* (merge), no se reemplazan. |
| **Ubicación del config** | orch1.txt | El archivo puede estar en varios directorios con orden de precedencia definido. |
| **Estructura MCP** | orch1.txt | Los MCP servers se configuran dentro de `opencode.json` con soporte para servers **locales** y **remotos**. |
| **MetaGPT env vars (referencia cruzada)** | mcp.txt | MetaGPT lee variables de entorno para LLM: `OPENAI_API_KEY`, `METAGPT_LLM_API_KEY`, `os.getenv`. Esto sirve como patrón de cómo *otros* sistemas (no OpenCode) configuran LLMs vía env vars. |
| **Fuente documentada** | orch1.txt | Docs oficiales: `https://opencode.ai/docs/mcp-servers/` y `https://open-code.ai/en/docs/config` |

> **Conclusión MCP:** La configuración de MCP en OpenCode se hace en `opencode.json[c]` con merge de múltiples archivos. Soporta servers locales y remotos. MetaGPT sirve como referencia de patrón alternativo (env vars).

---

## 2. Orquestación multi-agente

| Decisión | Fuente | Detalle |
|---|---|---|
| **Arquitectura de búsqueda** | orch1.txt | El agente usó búsqueda web secuencial + `web_fetch` para resolver preguntas de configuración. Rompió la pregunta en sub-búsquedas enfocadas. |
| **Razonamiento explícito en AST** | orch1.txt, orch2.txt | El agente documenta su razonamiento paso a paso en bloques `[razonamiento]` (e.g., "Locating OpenCode Config", "Analyzing Server Structure"). |
| **Múltiples herramientas en paralelo** | orch1.txt | Usó `web_search` + `web_fetch` de forma secuencial pero enfocada: primero busca, luego hace fetch de los resultados más relevantes. |
| **Refinamiento de búsqueda** | orch2.txt | Al no encontrar "launch config", el agente ajustó el query y volvió a buscar, mostrando capacidad de re-planificación. |
| **Investigación vs implementación** | (implícito) | Los inputs son sesiones de *investigación* (tipo `explorer`/`librarian`), no de implementación. El patrón es: investigar primero, implementar después. |

> **Conclusión orquestación:** El patrón es: pregunta inicial → razonamiento explícito → búsqueda web → fetch de resultados → síntesis. El agente ajusta estrategia si los resultados no son los esperados. Usa AST blocks para trazabilidad.

---

## 3. Visión

| Decisión | Fuente | Detalle |
|---|---|---|
| **No hay decisiones explícitas de visión** | mcp.txt, orch1.txt, orch2.txt | Ninguno de los tres inputs contiene referencias a configuración de visión, modelos multimodales, screenshots, ni procesamiento de imágenes. |
| **Área no cubierta** | — | El tema "visión" no fue abordado en ninguna de las sesiones analizadas. |

> **Conclusión visión:** Sin datos. Las sesiones se enfocaron exclusivamente en configuración de texto/LLM y MCP. Visión es un tema pendiente de investigar por separado.

---

## Resumen ejecutivo

| Tema | Estado |
|---|---|
| **MCP Config** | ✅ Documentado: `opencode.json[c]`, merge jerárquico, servers locales+remotos |
| **Multi-agente** | ✅ Patrón claro: pregunta → razonamiento → búsqueda → fetch → síntesis con re-planificación |
| **Visión** | ❌ No cubierto. Sesiones existentes no lo exploran. |

**Recomendación:** Para avanzar en visión, se necesita una sesión de investigación específica (e.g., `@librarian` buscando "opencode vision config", "multimodal models opencode", "screenshot MCP server").
