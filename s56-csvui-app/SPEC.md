# CSV Tabulator — Especificación

## 1. Propósito

Un solo comando de terminal que inicia un servidor web para editar archivos CSV
visualmente desde el navegador (móvil o desktop). Sin base de datos, sin instalación
compleja, sin depender de Java.

```bash
csv-tabulator /ruta/a/mis/csvs
# → Abre http://localhost:8080 con los CSVs de ese directorio
```

## 2. Arquitectura

```
Una sola máquina:
  Terminal: csv-tabulator ./datos/
       ↓
  Servidor Go (binario único ~5MB) en :8080
       ↓
  Navegador (móvil/desktop) → Tabulator JS
       ↓
  Lee/escribe CSVs en ./datos/
```

- **Backend**: Go, sin dependencias externas (stdlib: net/http, encoding/csv, encoding/json)
- **Frontend**: Tabulator JS 6.x (CDN) + vanilla JS
- **Sin base de datos**: los datos son archivos .csv
- **Sin compilación**: el frontend se sirve como HTML estático embebido en el binario Go
- **Sin Java, sin Node, sin npm**

## 3. Comando de terminal

```bash
csv-tabulator [directorio]
```

- `directorio` opcional, por defecto el directorio actual
- Inicia servidor web en `http://localhost:8080`
- El directorio especificado es la raíz de datos (se listan sus .csv)
- Los archivos se leen y escriben directamente en ese directorio

## 4. Interfaz de usuario

### 4.1 Cabecera (file-bar)

```
┌──────────────────────────────────────────────────────────┐
│ 📁 /ruta/completa/al/directorio/                          │  ← ruta fija
│ [📂 seleccionar archivo ▼]  (auto-load al seleccionar)   │
└──────────────────────────────────────────────────────────┘
```

- **Ruta fija**: muestra el directorio de datos desde que se carga la página.
  No cambia al seleccionar un archivo.
- **Dropdown único**: lista los archivos .csv del directorio.
  Al seleccionar uno, se carga automáticamente.
  El dropdown siempre muestra el nombre del archivo actual.
- **No hay input de texto para la ruta del archivo.**
- **No hay botón Load, Open, Browse, Save.**

### 4.2 Toolbar

```
[New] [+Row] [-Row] [+Col] [-Col]  [☰ sidebar]
```

- `New`: crea archivo nuevo vacío (3×3) en el directorio
- `+Row` / `-Row`: agrega/elimina filas de la selección actual
- `+Col` / `-Col`: agrega/elimina columnas
- `☰`: abre/cierra la sidebar de acciones

### 4.3 Tabla (Tabulator JS)

- **Selección**: tap en celda → la selecciona (toggle). Tap en otra celda → la agrega.
  Tap en celda seleccionada → la deselecciona.
- **Selección por arrastre**: mantener presionado y arrastrar → selecciona rango.
- **Edición inline**: doble tap en celda → aparece input → Enter confirma, Escape cancela.
- **Ordenamiento**: tap en header de columna.
- **Filtros**: inputs debajo de cada header.
- **Paginación**: 25/50/100/500/1000 filas por página.
- **Columnas movibles**: no (interfiere con selección por arrastre).

### 4.4 Sidebar de acciones (☰)

```
SELECTION
  3 cells selected
  [📋 Row] [📊 Column] [✕ Clear]

BUILT-IN
  [To Uppercase]
  [To Lowercase]
  [Trim Whitespace]

CUSTOM ACTIONS
  [+ New]
  [Reverse Text]   ▶ ✎ ✕
  [Get Length]     ▶ ✎ ✕
  [...]
```

- **Selection**: muestra cuántas celdas hay seleccionadas.
  Botones: Row (toda la fila), Column (toda la columna), Clear.
- **Built-in**: acciones predefinidas sin configuración.
- **Custom Actions**: acciones creadas por el usuario.
  ▶ ejecuta, ✎ edita, ✕ elimina.
- **+ New**: abre editor para crear nueva acción personalizada.

### 4.5 Tipos de acción

| Tipo | Descripción | Configuración |
|------|-------------|---------------|
| `TO_UPPER` | Mayúsculas | ninguna |
| `TO_LOWER` | Minúsculas | ninguna |
| `TRIM` | Recortar espacios | ninguna |
| `FIND_REPLACE` | Buscar y reemplazar | findText, replaceText |
| `TRANSFORM` | reverse, length, substr, padLeft, etc. | transformExpression |
| `PREFIX` | Agregar prefijo | findText (el prefijo) |
| `SUFFIX` | Agregar sufijo | findText (el sufijo) |
| `SHELL_COMMAND` | Ejecutar comando shell por celda | commandTemplate, includeHeader |

### 4.6 Editor de acciones (modal)

```
┌─────────────────────────────────────┐
│  Create / Edit Custom Action        │
│                                     │
│  Name: [________________]           │
│  Description: [________________]    │
│  Type: [Shell Command ▼]            │
│                                     │
│  [Command Template]                 │
│  echo {cell} | wc -w                │
│                                     │
│  [✔] Include header row             │
│                                     │
│           [Cancel] [Create]         │
└─────────────────────────────────────┘
```

## 5. API REST

Todas las rutas bajo `/api/`. El frontend se sirve en `/`.

| Método | Ruta | Cuerpo | Respuesta |
|--------|------|--------|-----------|
| GET | `/api/data` | — | `{headers, rows, selection, status}` |
| GET | `/api/info` | — | `{status, fileName, filePath, rowCount, colCount}` |
| POST | `/api/cell` | `{row, col, value}` | `{headers, rows, ...}` |
| POST | `/api/row` | `{action: "add"\|"delete", index}` | `{...}` |
| POST | `/api/column` | `{action: "add"\|"delete"\|"rename", index?, header?}` | `{...}` |
| POST | `/api/file` | `{action: "new"\|"open", path}` | `{...}` |
| POST | `/api/save` | `{path?}` | `{...}` |
| POST | `/api/action/execute` | `{action: ActionDefinition, selection: Selection}` | `{...}` |
| GET | `/api/files` | — | `["file1.csv", ...]` |
| GET | `/api/actions` | — | `[ActionDefinition, ...]` |
| POST | `/api/actions` | `ActionDefinition` | `[ActionDefinition, ...]` |
| PUT | `/api/actions/{id}` | `ActionDefinition` | `[ActionDefinition, ...]` |
| DELETE | `/api/actions/{id}` | — | `[ActionDefinition, ...]` |

### Formatos

**Selection:**
```json
{"type": "CELLS", "indices": [], "cells": [{"row": 0, "col": 0}, {"row": 0, "col": 1}]}
```

**ActionDefinition:**
```json
{
  "id": "abc123",
  "name": "Count Words",
  "description": "Cuenta palabras con wc",
  "type": "SHELL_COMMAND",
  "commandTemplate": "echo {cell} | wc -w",
  "findText": "",
  "replaceText": "",
  "transformExpression": "",
  "includeHeader": false
}
```

## 6. Persistencia

- **CSVs**: en el directorio que el usuario especifica al iniciar el servidor
- **Acciones personalizadas**: en `~/.csv-tabulator/action-library.json`
- **No hay sesiones, no hay base de datos**

## 7. Entrega

- Un solo binario: `csv-tabulator` (~5MB, Go, sin dependencias)
- El frontend HTML/CSS/JS está embebido en el binario
- No requiere Java, Node, npm, ni ninguna instalación
