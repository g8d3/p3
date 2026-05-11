# Informe de Pruebas — CSV Tabulator

## Resumen

| Versión | Estado | Último build |
|---------|--------|-------------|
| Web Server | ✅ Corriendo | `http://100.102.52.59:8080/` |
| Android APK | ✅ Compila | `http://100.102.52.59:8080/csv-tabulator.apk` |
| Desktop | ✅ Compila | `./gradlew :composeApp:run` |
| Tests unitarios | ✅ 34/34 | `./gradlew :composeApp:test` |

---

## 1. Funcionalidades que funcionan correctamente

### Operaciones de archivo
- ✅ **New**: Crea archivo vacío (3×3)
- ✅ **Open**: Carga CSV desde cualquier ruta
- ✅ **Save**: Guarda en el archivo actual o en `data/`
- ✅ **List files**: Muestra CSVs disponibles en `data/`
- ✅ **CSV parsing**: Maneja comillas, commas internos, UTF-8

### Edición de celdas
- ✅ **Cell edit**: Actualiza valor individual
- ✅ **Add row**: Agrega fila vacía
- ✅ **Delete row**: Elimina fila por índice
- ✅ **Add column**: Agrega columna con nombre
- ✅ **Delete column**: Elimina columna por índice

### Built-in actions
- ✅ **To Uppercase**: En celdas, filas, columnas
- ✅ **To Lowercase**: En celdas, filas, columnas
- ✅ **Trim**: Elimina espacios alrededor

### Custom actions (no-shell)
- ✅ **Find & Replace**: Reemplazo de texto
- ✅ **Transform**: `reverse`, `length`, `substr(0,3)`, `padLeft`, `padRight`, `replace()`, `repeat()`
- ✅ **Prefix**: Agrega texto al inicio
- ✅ **Suffix**: Agrega texto al final

### Modos de selección
- ✅ **CELLS**: Múltiples celdas independientes
- ✅ **ROWS**: Filas completas
- ✅ **COLUMNS**: Columnas completas
- ✅ **NONE**: No hace nada (seguro)

---

## 2. Bugs identificados y corregidos

### BUG #1 (CORREGIDO): Shell injection en `{cell}` — CRÍTICO

**Severidad**: 🔴 ALTA — vulnerabilidad de seguridad

**Síntoma**: Cuando usabas un comando shell con `{cell}`, el valor de la celda se insertaba sin escapar. `$USER`, comillas, apóstrofes rompían el comando.

**Prueba**: `test6-escaping-bug.sh`

| Caso | Antes | Después |
|------|-------|---------|
| Texto normal `Ana García` | ✅ Funcionaba | ✅ Sigue funcionando |
| Apóstrofe `O'Brien` | ❌ `Syntax error: Unterminated quoted string` | ✅ `O'Brien` |
| `$USER` | ❌ Se expandía a `vuos` | ✅ Se mantiene como `$USER` |
| `$(rm -rf /)` | ❌ Se ejecutaba | ✅ Seguro |

**Causa raíz**: En `ShellCommandAction.kt` y `ShellExecutor.kt`, el reemplazo `{cell}` se hacía sin escapado. Cualquier caracter especial del shell rompía el comando.

**Fix**: Se agregó escapado por single-quote wrapping: el valor se envuelve en `'...'` y los apóstrofes internos se escapan como `'\''`.

**Archivos modificados**:
- `composeApp/src/main/kotlin/csvui/actions/ShellCommandAction.kt`
- `androidApp/src/main/kotlin/csvui/android/termux/ShellExecutor.kt`

---

## 3. Bugs identificados (pendientes)

### BUG #2: Status message incorrecto con selección NONE

**Severidad**: 🟡 BAJA

**Síntoma**: Cuando ejecutas una acción sin tener nada seleccionado, el status message dice "Action applied" aunque no pasó nada. El mensaje anterior persiste.

**Dónde**: `server/src/main/kotlin/webserver/AppState.kt` — `handleExecuteAction()` no actualiza el mensaje cuando `selection.type == NONE`.

### BUG #3: CSV parsing de valores con double quotes al inicio

**Severidad**: 🟡 BAJA

**Síntoma**: Un valor como `"Juan Pérez"` no se parsea correctamente si el CSV usa quoting estándar. El parser interpreta `""` al inicio como quote escapado.

**Dónde**: `composeApp/src/main/kotlin/csvui/csv/CsvHandler.kt`

### BUG #4: `tr` no maneja acentos

**Severidad**: 🟢 INFORMATIVO

**Síntoma**: `echo {cell} | tr '[:lower:]' '[:upper:]'` no convierte caracteres acentuados (GARCÍA → GARCíA). Esto es una limitación de `tr`, no del software. Solución: usar `echo {cell} | python3 -c "import sys; print(sys.stdin.read().upper())"`.

---

## 4. Mejora propuesta: Destino de transformación

Tu idea es excelente: poder elegir **dónde** va el resultado de una acción, no solo transformar en el mismo lugar.

### Diseño propuesto

Actualmente una acción tiene:
- **Source**: las celdas seleccionadas
- **Transform**: la operación (uppercase, shell command, etc.)
- **Destination**: implícitamente las mismas celdas (in-place)

Con la mejora:
- **Source**: las celdas seleccionadas
- **Transform**: la operación
- **Destination**: ⭐ **dónde se escribe el resultado** (nuevo parámetro)

### Tipos de destino

| Destino | Descripción | Ejemplo de uso |
|---------|-------------|----------------|
| `SAME` | En el mismo lugar (comportamiento actual) | UpperCase en el mismo sitio |
| `NEW_COLUMN` | Crear nueva columna a la derecha con los resultados | Extraer iniciales a nueva columna |
| `COLUMN[n]` | Columna específica (reemplaza contenido) | Poner resultados en columna "Resultado" |
| `NEW_ROW` | Nueva fila al final con los resultados | Acumular transformaciones |

### Cambios necesarios

**API** — nuevo campo `destination` en las requests:
```json
{
  "action": {"name": "Upper", "type": "TO_UPPER"},
  "selection": {"type": "COLUMNS", "indices": [0]},
  "destination": {
    "type": "NEW_COLUMN",
    "header": "Nombre Mayusc."
  }
}
```

**UI** — en el ActionEditor, un selector de destino:
```
┌─────────────────────────────┐
│ Destino: [Same place ▼]     │
│   ○ Same place              │
│   ● New column → header: [ ]│
│   ○ Column #: [0]           │
└─────────────────────────────┘
```

---

## 5. Mejoras adicionales sugeridas

### 5.1 Feedback visual de progreso

Cuando ejecutas una acción en muchas celdas, no hay indicador de progreso. Sugiero:
- Barra de progreso durante la ejecución
- Contador: "Procesando celda 5/100..."

### 5.2 Historial de acciones (Undo)

Poder deshacer la última acción sería muy valioso. Implementación simple:
- Mantener un stack de `CsvData` anteriores (máximo 10-20)
- Botón "Undo" en la toolbar

### 5.3 Vista previa de la acción

Antes de ejecutar, mostrar cómo quedarían los datos:
```
UpperCase en [Nombre] → ¿Vista previa?
  Ana García → ANA GARCÍA
  Carlos López → CARLOS LÓPEZ
```

### 5.4 Atajos de teclado (web/desktop)

- `Ctrl+Z`: Undo
- `Ctrl+S`: Save
- `Ctrl+Shift+U`: UpperCase
- `Enter`: Editar celda / Confirmar edición
- `Tab`: Siguiente celda
- `Delete`: Limpiar celda

### 5.5 Selección por drag (web/desktop)

Poder hacer clic y arrastrar para seleccionar un rango de celdas, como en Excel.

### 5.6 Exportar resultados

Además de guardar el CSV completo, poder exportar SOLO los resultados de una acción a un archivo separado.

### 5.7 Comandos que operan sobre toda la fila

Poder pasar toda la fila como argumento en lugar de celda por celda:
- `{row}` → reemplaza con todos los valores de la fila separados por tabs
- `{row.csv}` → reemplaza con la fila en formato CSV

---

## 6. Resultados de pruebas automatizadas

```
TEST 1: File operations          ✅ 4/4
TEST 2: Cell editing + CRUD      ✅ 6/6
TEST 3: Built-in actions         ✅ 4/4 
TEST 4: Custom actions           ✅ 6/6
TEST 5: Shell commands           ✅ 5/5 (1 borderline: locale en tr)
TEST 6: Shell escaping           ✅ 3/4 (1 es bug de parseo CSV, no shell)

Tests unitarios (JVM)            ✅ 34/34
```

---

## 7. Cómo reproducir las pruebas tú mismo

```bash
cd /home/vuos/code/p3/s56

# Pruebas unitarias (core compartido)
./gradlew :composeApp:test

# Pruebas de integración contra el servidor
bash tests/test5-shell-commands.sh    # Comandos shell
bash tests/test6-escaping-bug.sh      # Escapado (después del fix)

# Ver datos de prueba
cat data/pruebas.csv
```

---

## 8. Estado actual del servidor

- **URL**: `http://100.102.52.59:8080/`
- **CSVs disponibles**: `data/pruebas.csv`, `data/sample.csv`, `data/escaping-test.csv`
- **APK**: `http://100.102.52.59:8080/csv-tabulator.apk` (15MB, con fix de escapado)
- **Tests**: `tests/` — scripts de prueba
- **Directorio de datos**: `data/`
