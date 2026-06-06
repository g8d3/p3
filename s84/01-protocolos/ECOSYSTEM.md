# Ecología de Artefactos — Diseño del Sistema

> Sistema multi-agente autónomo donde explorers atacan artefactos,
> ramas los reparan, y el artifact evoluciona para sobrevivir.

---

## 1. Visión General

Múltiples **semillas** (artifacts iniciales) son atacadas por **explorers**
que buscan fallas. Cada falla encontrada genera una **rama** (Director+Maker)
que la repara. Las reparaciones exitosas se **fusionan** en el artifact.

```
Semilla 1 ──► Artifact A1 ──► Explorers ──► Ramas ──► Artifact A2 ──► ...
Semilla 2 ──► Artifact B1 ──► Explorers ──► Ramas ──► Artifact B2 ──► ...
Semilla 3 ──► Artifact C1 ──► Explorers ──► Ramas ──► Artifact C2 ──► ...

Además: cross-pollination entre semillas
(una técnica descubierta en semilla 1 se aplica a semilla 2)
```

---

## 2. Componentes

### 2.1 Semilla

Un artifact inicial producido por un Iniciador (Director+Maker que se
ejecuta una sola vez). Cada semilla es un script Python diferente:

| Semilla | Propósito | Código inicial |
|---------|-----------|----------------|
| `promedios` | Calcula promedios | `promedios.py` |
| `contador` | Cuenta palabras | `contador.py` |
| `validador` | Valida emails | `validador.py` |
| `transformador` | Transforma CSV | `transformador.py` |

### 2.2 Artifact

El artifact es la unidad central. Es un archivo `.py` ejecutable que
evoluciona. Cada artifact tiene:

```json
{
  "id": "promedios-v7",
  "semilla": "promedios",
  "archivo": "artifacts/promedios-v7.py",
  "padres": ["promedios-v6a", "promedios-v6b"],
  "generacion": 7,
  "ficha_tecnica": {
    "lo_que_sabe_hacer": ["calcular_promedio", "manejar_lista_vacia",
                          "manejar_negativos", "thread_safe"],
    "lo_que_NO_sabe_hacer": ["manejar_strings", "archivos_grandes"],
    "cosas_que_fallaron": [],
    "ultimas_mejoras": ["thread_safe", "input_negativo"],
    "explorers_que_no_rompieron": ["explorer-velocidad", "explorer-formato"]
  },
  "metricas": {
    "lines": 45,
    "tests": 4,
    "tests_passing": 4,
    "exec_time_ms": 2.3,
    "ramas_exitosas": 2,
    "explorers_derrotados": 5
  }
}
```

### 2.3 Explorer

Un agente autónomo que recibe un artifact y lo prueba desde un ángulo
específico. Cada Explorer tiene:

```json
{
  "id": "explorer-null-input-03",
  "angulo": "inputs_extremos",
  "tecnicas": ["null", "empty_string", "negative", "very_large"],
  "artifactivo_actual": "promedios-v7",
  "historial": [
    {"artifact": "promedios-v5", "falla": false},
    {"artifact": "promedios-v6", "falla": "input_negativo_rompe"},
    {"artifact": "promedios-v6b", "falla": false}
  ],
  "efectividad": 0.33
}
```

**Cómo funciona un Explorer:**

```
1. Recibe artifact v7 y su ficha técnica
2. Dice: "la ficha dice que sabe manejar vacío y negativos.
   Voy a probar con input que sea una lista de strings."
3. Ejecuta: artifact.py con ["a", "b", "c"]
4. ┌─ Si explota → reporta falla → nace una rama
   └─ Si no explota → reporta éxito → sube su efectividad
5. Aprende: "strings no rompe, pero ¿y mezcla de tipos?"
   → La próxima vez intenta [1, "a", None]
```

Explorers NO arreglan. Solo encuentran. Si además arreglaran, no
habría presión selectiva real (sería como un examen donde el profesor
te da las respuestas).

### 2.4 Rama (Director + Maker)

Cuando un Explorer encuentra una falla, nace una rama:

```
Explorer reporta falla → Jardinero spawns:
  ┌─ Director-rama (port 92XX)
  │   Lee la falla, diseña el fix
  │   Delega a Maker
  └─ Maker-rama (port 92XX)
      Implementa el fix
      → Checker verifica
      → Si pasa → rama exitosa → espera fusión
      → Si no pasa → corrige (hasta 3 intentos)
      → Si no corrige → rama muere
```

La rama opera sobre una COPIA del artifact. No modifica el original
hasta que Checker confirma que el fix funciona y el Fusionador lo
incorpora.

### 2.5 Checker (compartido)

Un solo agente que juzga a todas las ramas con la misma vara.

```
Checker NO opina. Checker HACE:

1. ¿El archivo existe?               → os.path.exists()
2. ¿Tiene sintaxis válida?           → compile()
3. ¿Ejecuta sin error?               → subprocess.run(timeout=5)
4. ¿Produce la salida esperada?      → assert run(input) == esperado
5. ¿Tiene tests?                     → glob(test_*.py)
6. ¿Los tests pasan?                 → pytest
7. ¿La falla del Explorer ya no ocurre? → probar el caso exacto que falló

Reporta: {"paso": [1,2,3,4], "fallo": null, "artifacts": "promedios-v7a"}
```

Si Checker falla en cualquier paso, la rama no pasa. No hay opción,
no hay "casi pasa". Hechos.

### 2.6 Fusionador

Cuando hay N ramas exitosas (configurable, default 2), el Fusionador
toma las versiones de todas y las combina:

```
Rama-A: promedios-v7a.py (maneja strings)
Rama-B: promedios-v7b.py (maneja concurrencia)

Fusionador:
1. Toma el código de cada rama
2. Los combina en promedios-v8.py
3. Ejecuta: ¿el código combinado sigue pasando todos los tests?
   └─ Si sí → promedios-v8 nace
   └─ Si no → Fusionador intenta 3 estrategias de merge
       └─ Si fallan → corta el artifact en dos:
          promedios-v8a (string-safe) y promedios-v8b (thread-safe)
          → dos artifacts hermanos que evolucionan separados
```

### 2.7 Jardinero

Loop que corre cada 30s y mantiene el ecosistema:

```python
while True:
    for cada artifact:
        n_explorers = count(explorers on this artifact)
        if n_explorers < artifact.complejidad * 2:
            spawn_explorer(artifact, angulo_nuevo())

        for cada rama:
            if rama.edad > 3 * TIMEOUT and not rama.exitosa:
                log(f"Rama {rama.id} murió: no produjo fix")
                kill(rama)

        for cada explorer:
            if explorer.fallas_consecutivas >= 6:
                log(f"Explorer {explorer.id} se retira: ya no encuentra nada")
                retire(explorer)
            elif explorer.edad > 30 and explorer.efectividad < 0.1:
                log(f"Explorer {explorer.id} inefectivo, descartado")
                kill(explorer)
                # spawn uno nuevo con ángulo mutado del mejor explorer
                spawn_explorer(artifact, mutar(mejor_explorer().angulo))

    sleep(30)
```

### 2.8 Cross-pollination

Cuando un artifact descubre cómo hacer algo, esa técnica se propaga:

```
promedios-v7 aprende "manejar_strings"
  → Jardinero nota que contador-v5 NO sabe manejar strings
  → Inyecta en contador-v5: "aprende de promedios-v7 a manejar strings"
  → Contador-v5 podría saltarse varias generaciones de evolución
```

Esto acelera la evolución: lo que un artifact descubre, todos lo heredan.

---

## 3. Stack Tecnológico

| Componente | Implementación | Por qué |
|-----------|----------------|---------|
| Agentes | `a2a_server.py` (modificado) | Protocolo A2A, puertos dinámicos |
| Comunicación | HTTP + JSON entre agentes | Ya funciona, visible en monitor |
| Memoria central | SQLite (`ecosystem.db`) | Portable, consultable, barato |
| Artifacts | Archivos `.py` en `artifacts/` | Ejecutables, contrastables |
| Explorers | Agentes A2A con rol `explorer` | Misma infraestructura que makers |
| Ramas | Duplas Director+Maker temporales | Nacen y mueren bajo demanda |
| Jardinero | Script Python + tmux | Loop de 30s, monitorea SQLite |
| Monitor | HTTP server en :9099 | Misma infra que ya tenemos |

---

## 4. Flujo Completo

```
t=0:   Iniciador produce promedios-v1.py
t=30:  Jardinero spawns 2 explorers en promedios-v1
t=60:  Explorer-A: "input vacío rompe!" → Ram-a nace (9004,9005)
t=90:  Explorer-B: "no maneja negativos!" → Ram-b nace (9006,9007)
t=120: Rama-A completa fix → Checker verifica ✅
t=150: Rama-B completa fix → Checker verifica ✅
t=151: Fusionador combina → promedios-v2.py
t=180: Jardinero spawns explorers más agresivos en v2
       ... ciclo continúa ...
```

---

## 5. Preguntas Abiertas

1. **Explorers con LLM** → ¿los explorers usan un LLM para generar
   casos de prueba, o siguen estrategias fijas? Propongo: fijas al
   inicio, con LLM opcional para exploración avanzada.

2. **Costo** → cada explorer usa una llamada al LLM para "pensar"
   el caso de prueba. Con 10 explorers y 10 ciclos, son 100 llamadas.
   ¿Costo aceptable para el experimento?

3. **Deadlock evolutivo** → ¿qué pasa si un artifact es tan bueno que
   ningún explorer encuentra fallas? El Jardinero debería generar
   explorers "mutantes" con ángulos más extremos. Si tras 3 rondas
   de mutaciones nadie encuentra nada, el artifact se declara
   "inmune" y se archiva.

4. **Métrica de éxito** → ¿cuándo paramos? No paramos. Cada artifact
   sigue evolucionando mientras haya explorers que encuentren fallas.
   El sistema solo se detiene si todos los artifacts son inmunes a
   todos los explorers (deadlock evolutivo).

---

*Este documento es el diseño inicial. Cada componente se refinará
al implementarlo.*
