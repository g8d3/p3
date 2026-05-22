# API Benchmark Script

Un script completo para evaluar y comparar modelos de IA de las APIs ZAI y OpenCode GO.

## Características

- 📋 **Listado de modelos disponibles** para ambas APIs
- ⚡ **Medición de latencia** en milisegundos
- 🚀 **Cálculo de throughput** (tokens por segundo)
- 💰 **Cálculo de costos** aproximados
- 🛡️ **Tasa de éxito** y disponibilidad
- 📊 **Estadísticas detalladas** (media, mediana, mínimo, máximo)
- 🆚 **Comparativa general** entre APIs
- 💾 **Exportación a JSON** con resultados detallados

## Requisitos

- Python 3.8 o superior
- Variables de entorno:
  - `ZAI_API_KEY`: Tu clave API de ZAI
  - `OPENCODE_GO_API_KEY`: Tu clave API de OpenCode GO

## Instalación y Uso

### Método 1: Automático (recomendado)

```bash
# Clonar o descargar los archivos
chmod +x run_benchmark.sh
./run_benchmark.sh
```

### Método 2: Manual

```bash
# Instalar dependencias
pip3 install -r requirements.txt

# Configurar variables de entorno
export ZAI_API_KEY='tu_clave_zai'
export OPENCODE_GO_API_KEY='tu_clave_opencode_go'

# Ejecutar el benchmark
python3 api_benchmark.py
```

## Métricas Measures

El script mide las siguientes métricas para cada modelo:

### Métricas de Rendimiento
- **Latencia (ms)**: Tiempo de respuesta en milisegundos
- **Tokens por segundo**: Throughput del modelo
- **Tiempo de respuesta total**: Tiempo completo desde la petición hasta la respuesta

### Métricas de Costo
- **Costo por test**: Costo estimado por cada petición
- **Costo total**: Costo acumulado de todas las pruebas
- **Costo por token**: Estimación basada en pricing estándar

### Métricas de Disponibilidad
- **Tasa de éxito**: Porcentaje de peticiones exitosas
- **Códigos de estado**: HTTP status codes de las respuestas
- **Errores**: Detalles de fallos en peticiones

### Capabilities Test
- **Completación de texto**: Básica capacidad de generación de texto
- **Visión**: Soporte para imágenes (multimodal)
- **Modo JSON**: Capacidad de generar respuestas estructuradas
- **Llamadas a funciones**: Soporte para function calling

## Estructura de Resultados

Los resultados se guardan en un archivo JSON con la siguiente estructura:

```json
{
  "timestamp": "2024-01-01T12:00:00",
  "zai": {
    "available_models": ["gpt-3.5-turbo", "gpt-4"],
    "model_results": [
      {
        "model": "gpt-3.5-turbo",
        "total_tests": 5,
        "successful_tests": 5,
        "success_rate": 100.0,
        "avg_latency_ms": 245.67,
        "median_latency_ms": 234.12,
        "min_latency_ms": 123.45,
        "max_latency_ms": 456.78,
        "avg_tokens_per_second": 45.67,
        "avg_cost_per_test": 0.000123,
        "total_cost": 0.000615
      }
    ]
  },
  "opencode_go": {
    // Similar structure
  }
}
```

## Tips de Interpretación

### ⚡ Bajo Latencia = Mejor Rendimiento
- **< 200ms**: Excelente para aplicaciones en tiempo real
- **200-500ms**: Bueno para aplicaciones generales
- **> 500ms**: Puede afectar la experiencia del usuario

### 🚀 Alto Throughput = Mayor Eficiencia
- **> 50 tokens/sec**: Excelente para procesamiento batch
- **30-50 tokens/sec**: Bueno para uso moderado
- **< 30 tokens/sec**: Puede ser cuello de botella

### 💰 Costo-Efectividad
- Comparar costo por token entre modelos
- Considerar la relación costo-rendimiento
- Monitorear costos en producción

### 🛡️ Disponibilidad y Fiabilidad
- **> 95%**: Excelente para producción
- **80-95%**: Aceptable para desarrollo
- **< 80%**: Considerar cambiar de proveedor

## Personalización

### Modificar Prompts de Prueba
Edita la lista `self.test_prompts` en `api_benchmark.py`:

```python
self.test_prompts = [
    "Hello, how are you today?",
    "What is the capital of France?",
    # ... tus prompts personalizados
]
```

### Cambiar Número de Tests
Modifica `num_tests` en `benchmark_model()`:

```python
benchmark = self.benchmark_model('zai', model, num_tests=10)
```

### Añadir Métricas Personalizadas
Extiende el método `make_api_call()` para medir métricas adicionales.

## Solución de Problemas

### Problema Común: Variables de Entorno
```bash
# Verificar variables de entorno
echo $ZAI_API_KEY
echo $OPENCODE_GO_API_KEY

# Si están vacías, establecerlas
export ZAI_API_KEY='tu_clave_aqui'
export OPENCODE_GO_API_KEY='tu_clave_aqui'
```

### Problema Común: Errores de Red
- Verificar conexión a internet
- Confirmar que las APIs están disponibles
- Revisar firewall/proxy

### Problema Común: Limites de API
- Algunas APIs tienen límites de velocidad (rate limiting)
- Considerar agregar pausas entre peticiones
- Usar caché para resultados repetidos

## Contribuciones

Si encuentras bugs o quieres sugerir mejoras:
1. Abre un issue en el repositorio
2. Envía un pull request con tus cambios
3. Incluye pruebas que validen tu solución

## License

MIT License - puedes usar y modificar este script libremente.