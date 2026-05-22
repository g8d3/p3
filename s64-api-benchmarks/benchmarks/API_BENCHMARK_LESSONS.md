# Lecciones Aprendidas — API Benchmark ZAI Coding Plan & OpenCode GO

## 🔧 Problemas Técnicos y Soluciones

### 1. Endpoint Correcto de ZAI
- **Problema:** Usaba `https://api.z.ai/api/paas/v4` (endpoint general)
- **Error:** `HTTP 429 — Insufficient balance or no resource package`
- **Causa:** El endpoint general requiere créditos separados. El Coding Plan tiene su propio endpoint.
- **Solución:** Usar `https://api.z.ai/api/coding/paas/v4`
- **Referencia:** Documentación ZAI: "When using the GLM Coding Plan, you need to configure the dedicated Coding endpoint"

### 2. User-Agent Bloqueado por OpenCode GO
- **Problema:** Python devolvía `HTTP 403 — error code: 1010`
- **Causa:** `urllib` envía por defecto `User-Agent: Python-urllib/3.x`, que OpenCode GO bloquea
- **Solución:** Forzar `User-Agent: curl/8.0` en los headers
- **Detalle:** `curl` funciona porque envía `User-Agent: curl/8.0` por defecto

### 3. Certificados SSL en Entorno Corporativo
- **Problema:** Errores de certificado SSL en algunas redes
- **Solución:** Usar `ssl._create_unverified_context()` o crear contexto con `verify_mode = ssl.CERT_NONE`
- **Nota:** Solo para entornos controlados; en producción usar certificados válidos

### 4. Timeouts en Modelos Lentos
- **Problema:** Modelos como `qwen3.5-plus` tardan >25 segundos en responder
- **Solución:** Aumentar timeout a 60-120 segundos para estos modelos
- **Recomendación:** Poner modelos rápidos primero en el orden de benchmark para obtener datos útiles incluso si hay timeout

### 5. Formato de Imagen para Visión
- **Problema:** El test de visión fallaba con URLs externas (Wikipedia, etc.)
- **Causa:** Las URLs externas pueden no ser accesibles desde los servidores de la API (bloqueo CDN, geo-restricción, etc.)
- **Solución:** Enviar la imagen en base64 embebido: `"data:image/png;base64,..."`
- **Formato correcto (OpenAI-compatible):**
  ```json
  {
    "type": "image_url",
    "image_url": {"url": "data:image/png;base64,iVBORw0..."}
  }
  ```

### 6. Modelos que Responden en `reasoning` en vez de `content`
- **Problema:** Modelos como `kimi-k2.5` ponen la respuesta de visión en el campo `reasoning` o `reasoning_content`, no en `content`
- **Solución:** Revisar ambos campos: `message.content` y `message.reasoning` (o `reasoning_content`)
- **Código:**
  ```python
  content = msg.get('content') or ''
  reasoning = msg.get('reasoning') or msg.get('reasoning_content') or ''
  combined = content + ' ' + reasoning
  ```

### 7. Consistencia de Nombres de Modelo
- **OpenCode GO lista:** `mimo-v2-pro`, `mimo-v2-omni`, `mimo-v2.5-pro`, `mimo-v2.5`
- **Documentación menciona:** MiMo V2 Pro, MiMo V2 Omni, MiMo-V2.5, MiMo-V2.5-Pro
- **Lección:** El `id` del modelo en la API puede diferir del nombre comercial. Usar siempre `GET /v1/models` para obtener los IDs exactos.

### 8. Headers Adicionales para ZAI
- **Problema:** ZAI requiere header adicional `Accept-Language`
- **Solución:** Incluir `Accept-Language: en-US,en` en todas las peticiones a la API de ZAI

### 9. Límites de Tokens en Tests de Visión
- **Problema:** Algunos modelos usan tokens de razonamiento. Con `max_tokens` bajo (<30), el contenido de salida puede quedar vacío
- **Solución:** Usar `max_tokens >= 50-60` para tests de visión que incluyan razonamiento

## 📊 Datos de las APIs

### ZAI (Z.AI) Coding Plan
| Propiedad | Valor |
|-----------|-------|
| Base URL (Coding) | `https://api.z.ai/api/coding/paas/v4` |
| Base URL (General) | `https://api.z.ai/api/paas/v4` |
| Auth | `Authorization: Bearer <ZAI_API_KEY>` |
| Modelos endpoint | `GET /models` |
| Chat endpoint | `POST /chat/completions` |
| Headers extra | `Accept-Language: en-US,en` |
| Documentación | https://docs.z.ai/ |

### OpenCode GO
| Propiedad | Valor |
|-----------|-------|
| Base URL | `https://opencode.ai/zen/go/v1` |
| Auth | `Authorization: Bearer <OPENCODE_GO_API_KEY>` |
| Modelos endpoint | `GET /v1/models` |
| Chat endpoint | `POST /v1/chat/completions` |
| Modelo especial | `minimax-m2.7` usa endpoint Anthropic: `POST /v1/messages` |
| Documentación | https://dev.opencode.ai/docs/go/ |

## 🧪 Mejores Prácticas para Benchmarking de APIs

1. **Probar endpoints individualmente con curl** antes de escribir el script
2. **No asumir que Python-urllib funciona** — forzar User-Agent tipo navegador/curl
3. **Timeout por modelo, no global** — algunos modelos son 10x más lentos que otros
4. **Procesar paralelamente** (concurrent.futures) para benchmarks grandes
5. **Ordenar modelos por velocidad** (rápidos primero) para tener datos útiles si hay timeout
6. **No confiar en URLs externas para visión** — usar base64
7. **Revisar campos alternativos** en la respuesta (reasoning, reasoning_content, etc.)
8. **Verificar la documentación de cada provider** — cada uno puede requerir headers diferentes
9. **Validar que las variables de entorno se propagan** al proceso hijo
