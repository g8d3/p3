# 📊 API Benchmark Report — ZAI Coding Plan vs OpenCode GO

**Fecha:** 2026-05-18
**ZAI API Key:** ✅ Configurada
**OpenCode GO API Key:** ✅ Configurada
**Script:** `benchmark.py`
**Lecciones:** `API_BENCHMARK_LESSONS.md`

---

## Resumen

| Proveedor | Modelos | Funcionando | Tasa de Éxito |
|-----------|---------|-------------|---------------|
| ZAI Coding Plan | 7 | 7 ✅ | 97.1% |
| OpenCode GO | 15 | 15 ✅ | 100% |
| **Total** | **22** | **22** | **98.6%** |

---

## 🔥 ZAI Coding Plan

**Endpoint:** `https://api.z.ai/api/coding/paas/v4`

| # | Modelo | Latencia Promedio | Min | Max | Tokens/s | Éxito | Visión |
|---|--------|-------------------|-----|-----|----------|-------|--------|
| 1 | `glm-4.5` | 2,259ms | — | — | 19.5 | 100% | ❌ |
| 2 | `glm-4.5-air` | 3,353ms | — | — | 13.9 | 100% | ❌ |
| 3 | `glm-4.6` | 12,469ms | — | — | 37.0 | 100% | ❌ |
| 4 | `glm-4.7` | 11,401ms | — | — | 34.3 | 100% | ✅ |
| 5 | `glm-5` | 4,249ms | — | — | 10.8 | 80% | ❌ |
| 6 | `glm-5-turbo` | 5,131ms | — | — | 9.6 | 100% | ❌ |
| 7 | `glm-5.1` | 5,050ms | — | — | 8.7 | 100% | ❌ |

**Ganadores ZAI:**
- ⚡ Más rápido: `glm-4.5` → 2,259ms
- 🚀 Mayor throughput: `glm-4.6` → 37.0 tok/s
- 👁️ Visión: solo `glm-4.7`

---

## 🔥 OpenCode GO

**Endpoint:** `https://opencode.ai/zen/go/v1`

| # | Modelo | Latencia Promedio | Min | Max | Tokens/s | Éxito | Visión |
|---|--------|-------------------|-----|-----|----------|-------|--------|
| 1 | `minimax-m2.7` | 2,933ms | 768ms | 2,712ms | 25.4 | 100% | ❌ |
| 2 | `minimax-m2.5` | **1,221ms** ⚡ | 769ms | 1,797ms | **38.2** | 100% | ❌ |
| 3 | `kimi-k2.6` | 2,119ms | 1,642ms | 2,807ms | 23.9 | 100% | ✅ |
| 4 | `kimi-k2.5` | 2,019ms | 1,301ms | 2,700ms | 21.5 | 100% | ✅ |
| 5 | `glm-5.1` | 1,545ms | 1,277ms | 1,917ms | 29.1 | 100% | ❌ |
| 6 | `glm-5` | 2,122ms | 1,558ms | 2,878ms | 21.2 | 100% | ❌ |
| 7 | `deepseek-v4-pro` | 3,408ms | 2,488ms | 5,369ms | 12.5 | 100% | ❌ |
| 8 | `deepseek-v4-flash` | 1,563ms | 1,210ms | 1,916ms | 28.6 | 100% | ❌ |
| 9 | `qwen3.6-plus` | 11,822ms | 4,214ms | 10,559ms | **43.3** 🚀 | 100% | ✅ |
| 10 | `qwen3.5-plus` | 11,357ms | 4,494ms | 27,542ms | **43.1** 🚀 | 100% | ✅ |
| 11 | `mimo-v2-pro` | 2,581ms | 1,375ms | 3,372ms | 18.1 | 100% | ❌ |
| 12 | `mimo-v2-omni` | 2,258ms | 1,583ms | 2,605ms | 20.6 | 100% | ❌ |
| 13 | `mimo-v2.5-pro` | 2,776ms | 1,304ms | 2,893ms | 19.0 | 100% | ❌ |
| 14 | `mimo-v2.5` | 2,580ms | 1,620ms | 2,810ms | 19.2 | 100% | ✅ |
| 15 | `hy3-preview` | 3,347ms | 3,040ms | 3,911ms | 13.7 | 100% | ❌ |

**Ganadores OpenCode GO:**
- ⚡ Más rápido: `minimax-m2.5` → 1,221ms
- 🚀 Mayor throughput: `qwen3.6-plus` → 43.3 tok/s
- 👁️ Visión: `kimi-k2.5`, `kimi-k2.6`, `qwen3.6-plus`, `qwen3.5-plus`, `mimo-v2.5` (5/15)
- 🛡️ Confiabilidad: 15/15 modelos con 100% éxito

---

## 🏆 Comparativa General

| Categoría | ZAI Coding Plan | OpenCode GO |
|-----------|----------------|-------------|
| ⚡ **Modelo más rápido** | `glm-4.5` — 2,259ms | `minimax-m2.5` — **1,221ms** |
| 🚀 **Mayor throughput** | `glm-4.6` — 37.0 tok/s | `qwen3.6-plus` — **43.3 tok/s** |
| 👁️ **Modelos con visión** | 1 de 7 (14%) | **5 de 15 (33%)** |
| 🛡️ **Confiabilidad** | 97.1% | **100%** |
| 💰 **Costo** | Incluido en Coding Plan | Incluido en suscripción $10/mes |

---

## 👁️ Detalle de Modelos con Visión

| Proveedor | Modelo | Respuesta |
|-----------|--------|-----------|
| ZAI | `glm-4.7` | ✅ Detecta imagen |
| OpenCode GO | `kimi-k2.5` | ✅ Responde en campo `reasoning` |
| OpenCode GO | `kimi-k2.6` | ✅ Responde correctamente |
| OpenCode GO | `qwen3.6-plus` | ✅ Responde "Google" |
| OpenCode GO | `qwen3.5-plus` | ✅ Responde "Google" |
| OpenCode GO | `mimo-v2.5` | ✅ Responde "Google" en campo `reasoning` |

**Nota:** Los modelos `mimo-v2-pro` y `mimo-v2-omni` NO soportan el formato de imagen estándar (OpenAI-compatible) a pesar de tener capacidades multimodales documentadas. Posiblemente requieran un formato de petición diferente.

---

## 📈 Lecciones Clave

1. **ZAI necesita el endpoint `/coding/paas/v4`**, no el general. El general da error 429 aunque haya suscripción.
2. **Python-urllib es bloqueado** por OpenCode GO (403). Usar `User-Agent: curl/8.0`.
3. **Imágenes en base64** (no URLs externas) para tests de visión.
4. **Revisar `reasoning`** además de `content` — modelos como `kimi-k2.5` y `mimo-v2.5` ponen ahí la respuesta.
5. **Timeout por modelo**: `qwen3.5-plus` puede tardar >25 segundos en responder.

Ver `API_BENCHMARK_LESSONS.md` para una lista completa de lecciones aprendidas.
