# Crush Memory — AI Provider Config
# Este archivo persiste entre sesiones. No repetir estas instrucciones.

## Proveedor por defecto
OPENCODE_GO_API_KEY está en el entorno. URL base: https://opencode.ai/zen/go/v1/

## Modelos principales
- Default: deepseek-v4-flash (1.5s, 28 tok/s) — rápido, sin visión
- Visión: mimo-v2.5 (2.6s, 19 tok/s) — visión ✅
- Rápido: minimax-m2.5 (1.2s, 38 tok/s) — el más rápido
- Throughput: qwen3.6-plus (11.8s, 43 tok/s) — más tokens/s pero latencia alta

## Benchmarks completos
En `s64-api-benchmarks/benchmarks/API_BENCHMARK_REPORT_FINAL.md` están los
tests de velocidad de TODOS los modelos disponibles, incluyendo ZAI Coding Plan
y OpenCode GO (22 modelos en total, 98.6% tasa de éxito).

## Cómo usar en prompts
Para pedir que el agente use un modelo específico:
"Usa deepseek-v4-flash para esto, y mimo-v2.5 si necesitas visión."
"El proxy LLM está en el puerto 9100, usa OpenCode GO como provider."
