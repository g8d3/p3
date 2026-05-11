# CSV Tabulator — Guía Completa del Proyecto

## Tabla de Contenidos
1. [¿Qué es este proyecto?](#1-qué-es-este-proyecto)
2. [Estructura general](#2-estructura-general)
3. [Archivos de configuración (raíz)](#3-archivos-de-configuración-raíz)
4. [Módulo `composeApp` — App de Escritorio](#4-módulo-composeapp--app-de-escritorio)
5. [Módulo `server` — Servidor Web](#5-módulo-server--servidor-web)
6. [Módulo `androidApp` — App Android](#6-módulo-androidapp--app-android)
7. [Las 3 capas del código compartido](#7-las-3-capas-del-código-compartido)
8. [Cómo compilar y ejecutar cada versión](#8-cómo-compilar-y-ejecutar-cada-versión)
9. [Glosario para principiantes](#9-glosario-para-principiantes)

---

## 1. ¿Qué es este proyecto?

Es una **aplicación Kotlin Multiplatform** que funciona en **3 formas distintas**:

| Versión | ¿Qué es? | ¿Cómo la usas? |
|---------|----------|----------------|
| **Desktop** (`composeApp`) | App de ventana en tu PC | Doble clic al JAR |
| **Web** (`server`) | Servidor al que te conectas por navegador | `http://ip:8080` |
| **Android** (`androidApp`) | APK que instalas en tu teléfono | Side-load el APK |

Las **3 versiones comparten el mismo motor** (modelo de datos, lector CSV, sistema de acciones). Cambia solo la interfaz de usuario.

### Flujo de datos

```
Archivo CSV 
    │
    ▼
CsvHandler (lee/escribe el archivo CSV)
    │
    ▼
CsvData (los datos en memoria: headers + rows)
    │
    ▼
Action framework (BuiltinActions, ShellCommandAction, etc.)
    │
    ▼
UI (Desktop / Web / Android — muestran la tabla y dejan al usuario editarla)
```

---

## 2. Estructura general

```
s56/                              ← CARPETA RAIZ DEL PROYECTO
│
├── build.gradle.kts              ← Build raíz (solo declara plugins)
├── settings.gradle.kts           ← Lista los módulos del proyecto
├── gradle.properties             ← Propiedades globales de Gradle
├── local.properties              ← Ruta del Android SDK (solo para Android)
│
├── gradlew                       ← Script para ejecutar Gradle (Linux/Mac)
├── gradlew.bat                   ← Script para ejecutar Gradle (Windows)
├── gradle/                       ← Configuración de Gradle
│   ├── libs.versions.toml        ← ⭐ CATÁLOGO DE VERSIONES (todas las dependencias)
│   └── wrapper/                  ← El "instalador" de Gradle
│       ├── gradle-wrapper.jar
│       └── gradle-wrapper.properties
│
├── data/                         ← 📁 Aquí guarda los CSV el servidor web
│   └── sample.csv
│
├── composeApp/                   ← 📦 Módulo 1: App Desktop (Compose)
├── server/                       ← 📦 Módulo 2: Servidor Web (Ktor)
└── androidApp/                   ← 📦 Módulo 3: App Android
```

**Heurística #1**: Cada `build.gradle.kts` le dice a Gradle cómo compilar ese módulo.
**Heurística #2**: El código compartido está DENTRO de `composeApp/src/main/kotlin/csvui/` y los otros módulos lo "importan" configurando las rutas en su propio `build.gradle.kts`.

---

## 3. Archivos de configuración (raíz)

### `settings.gradle.kts` — Los módulos del proyecto

```kotlin
rootProject.name = "csv-tabulator"
include(":composeApp")   // Módulo de escritorio
include(":server")        // Módulo web
include(":androidApp")    // Módulo Android
```

Cada `include()` es una carpeta con su propio `build.gradle.kts`.

### `gradle/libs.versions.toml` — ⭐ El catálogo de versiones

**Este es el archivo más importante para entender las dependencias.** Es como una "tabla de verdad" donde están todas las versiones de librerías que usa el proyecto:

```toml
[versions]
kotlin = "2.0.21"                    # Versión del lenguaje Kotlin
compose = "1.7.1"                    # Compose Multiplatform (interfaz gráfica)
ktor = "3.0.2"                       # Ktor (servidor web)
agp = "8.5.2"                        # Android Gradle Plugin

[libraries]
ktor-server-core = { module = "io.ktor:ktor-server-core", version.ref = "ktor" }
compose-bom = { module = "androidx.compose:compose-bom", version.ref = "compose-bom" }

[plugins]
kotlin-jvm = { id = "org.jetbrains.kotlin.jvm", version.ref = "kotlin" }
android-application = { id = "com.android.application", version.ref = "agp" }
```

**Heurística #3**: Cada módulo usa `alias(libs.plugins.X)` y `implementation(libs.Y.Z)` en lugar de escribir versiones a mano. Esto evita conflictos de versiones.

### `gradle.properties` — Variables globales

```properties
org.gradle.jvmargs=-Xmx2g          # Memoria máxima para Gradle (2GB)
kotlin.code.style=official         # Estilo de código Kotlin oficial
android.useAndroidX=true           # Usar AndroidX (necesario para Compose)
```

### `local.properties` — Ruta del Android SDK (solo tu máquina)

```properties
sdk.dir=/home/vuos/android-sdk
```

Este archivo **no se sube a git** porque cada máquina tiene su propia ruta del SDK.

---

## 4. Módulo `composeApp` — App de Escritorio

```
composeApp/
├── build.gradle.kts
└── src/
    ├── main/kotlin/csvui/         ← ⭐ CÓDIGO COMPARTIDO (los otros módulos lo reusan)
    │   ├── Main.kt                ← Punto de entrada de la app Desktop
    │   ├── model/                 ← Modelos de datos
    │   │   ├── CsvData.kt         ← Datos CSV (headers, rows) + Selection + CellPosition
    │   │   └── Action.kt          ← DataAction interface + ActionDefinition + ActionType enum
    │   ├── csv/                    ← Lector/Escritor CSV
    │   │   └── CsvHandler.kt      ← Parsea CSV (maneja comillas, commas) y escribe CSV
    │   ├── actions/               ← Sistema de acciones
    │   │   ├── ActionExecutor.kt   ← Ejecuta acciones sobre un rango de celdas
    │   │   ├── ActionLibrary.kt    ← Guarda/carga acciones personalizadas (JSON en ~/.csv-tabulator/)
    │   │   ├── BuiltinActions.kt   ← Acciones preinstaladas (Uppercase, Lowercase, Trim, FindReplace, Transform, Prefix, Suffix)
    │   │   └── ShellCommandAction.kt ← Acción base: ejecuta comandos shell en las celdas
    │   └── ui/                    ← Interfaz de usuario Desktop (SOLO para composeApp)
    │       ├── App.kt
    │       ├── MainScreen.kt
    │       ├── DataTable.kt
    │       ├── ActionPanel.kt
    │       ├── ActionEditor.kt
    │       └── FileDialogs.kt
    └── test/kotlin/csvui/         ← Pruebas unitarias (34 tests)
        ├── CsvHandlerTest.kt      ← 7 tests: parseo, escritura, roundtrip
        ├── CsvDataTest.kt         ← 10 tests: operaciones CRUD en el modelo
        └── ActionsTest.kt         ← 16 tests: todas las acciones, selecciones
```

### ¿Qué hace cada archivo del core compartido?

| Archivo | Qué hace | ¿Por qué es importante? |
|---------|----------|------------------------|
| `CsvData.kt` | Define `CsvData(headers, rows)`, `CellPosition(row,col)`, `Selection(type, indices)` | Es la representación en memoria del archivo CSV |
| `Action.kt` | Define `DataAction` (interfaz), `ActionDefinition` (serializable), `ActionType` (enum) | Es el contrato que toda acción debe cumplir |
| `CsvHandler.kt` | `parse(content)` convierte texto a `CsvData`, `write(data)` convierte `CsvData` a texto CSV | Maneja comillas, commas dentro de valores |
| `ActionExecutor.kt` | Toma un `CsvData` + `Selection` + `DataAction` y devuelve el nuevo `CsvData` modificado | El cerebro que aplica las acciones |
| `BuiltinActions.kt` | `ToUpperCase`, `ToLowerCase`, `Trim`, `FindReplace`, `Transform`, `Prefix`, `Suffix` | Acciones que no necesitan shell |
| `ShellCommandAction.kt` | Toma un template como `echo {cell} \| wc -w` y ejecuta el comando por cada celda | La acción base que pidió el usuario |
| `ActionLibrary.kt` | Guarda acciones personalizadas en `~/.csv-tabulator/action-library.json` | Persistencia entre sesiones |

### `composeApp/build.gradle.kts` — Dependencias de Desktop

```kotlin
plugins {
    alias(libs.plugins.kotlin.jvm)         // Kotlin para JVM
    alias(libs.plugins.compose)             // Compose Multiplatform
    alias(libs.plugins.compose.compiler)    // Compilador de Compose
}

dependencies {
    implementation(compose.desktop.currentOs)  // Compose para el SO actual
    implementation(compose.material3)          // Componentes Material3
}
```

**Heurística #4**: `compose.desktop.currentOs` es un "accessor" especial del plugin Compose. Automáticamente usa las librerías nativas del sistema operativo donde corres.

---

## 5. Módulo `server` — Servidor Web

```
server/
├── build.gradle.kts
└── src/main/
    ├── kotlin/webserver/
    │   ├── Main.kt            ← Punto de entrada + rutas HTTP
    │   └── AppState.kt        ← Estado del servidor + lógica de cada API
    └── resources/web/         ← Archivos servidos como página web
        ├── index.html         ← ⭐ App web completa (HTML + CSS + JavaScript)
        └── csv-tabulator.apk  ← APK descargable
```

### Cómo funciona

Cuando ejecutas el servidor:
1. Ktor inicia un servidor HTTP en el puerto 8080
2. Escucha peticiones en `http://localhost:8080/`
3. Sirve `index.html` cuando entras a la raíz
4. Las rutas `/api/*` son la API REST que usa el JavaScript

**Flujo de una acción en el web:**

```
Usuario: hace clic en "To Uppercase"
    │
    ▼
JavaScript: fetch POST /api/action/execute  { action: {...}, selection: {...} }
    │
    ▼
AppState.handleExecuteAction():
    1. Recibe JSON
    2. Crea el objeto Action desde la definición
    3. Ejecuta ActionExecutor.execute(csvData, selection, action)
    4. Guarda el nuevo csvData
    5. Responde con el JSON completo de los datos
    │
    ▼
JavaScript: recibe la respuesta y renderiza la tabla actualizada
```

### `server/build.gradle.kts`

```kotlin
plugins {
    alias(libs.plugins.kotlin.jvm)
    alias(libs.plugins.kotlin.serialization)  // Para JSON
    application                                // Para generar script ejecutable
}

dependencies {
    implementation(libs.ktor.server.core)              // Núcleo de Ktor
    implementation(libs.ktor.server.netty)             // Servidor Netty (HTTP)
    implementation(libs.ktor.server.content.negotiation)
    implementation(libs.ktor.serialization.kotlinx.json)
    implementation(libs.ktor.server.status.pages)
    implementation(libs.kotlinx.serialization.json)
}

kotlin {
    sourceSets.main.kotlin.srcDir(
        "../composeApp/src/main/kotlin/csvui/model"    // ← Reusa el modelo
        "../composeApp/src/main/kotlin/csvui/csv"      // ← Reusa el CSV handler
        "../composeApp/src/main/kotlin/csvui/actions"  // ← Reusa las acciones
    )
}
```

**Heurística #5**: El servidor NO copia el código del modelo/CSV/acciones. En su lugar, le dice a Gradle "compila también esos archivos de la carpeta de composeApp". Así evitamos duplicar código.

**Heurística #6**: Las rutas de la API son `POST /api/algo` porque modifican el estado del servidor. `GET /api/algo` solo para lecturas.

---

## 6. Módulo `androidApp` — App Android

```
androidApp/
├── build.gradle.kts
└── src/main/
    ├── AndroidManifest.xml                    ← Permisos + declaración de la app
    ├── kotlin/csvui/android/
    │   ├── MainActivity.kt                    ← Punto de entrada Android
    │   ├── termux/
    │   │   ├── ShellExecutor.kt               ← Ejecuta comandos en el teléfono
    │   │   └── CrashReporter.kt               ← Captura errores para reportarlos
    │   └── ui/
    │       ├── MainScreen.kt                  ← Toda la UI (table, acciones, diálogos)
    │       └── AppViewModel.kt                ← Estado + lógica de la app
    └── res/values/
        ├── strings.xml
        └── themes.xml
```

### Cómo funciona Android

- **`MainActivity.kt`**: Es lo que Android ejecuta al abrir la app. Crea la ventana con Compose.
- **`AppViewModel.kt`**: Similar a `AppState.kt` del servidor. Tiene el estado (`csvData`, `selection`, etc.) y los métodos para modificarlo.
- **`ShellExecutor.kt`**: Detects if Termux is installed. If yes → use its bash. If no → fall back to Android's limited `sh`.
- **`CrashReporter.kt`**: Escribe errores a `csv-tabulator-crash.log` en el almacenamiento interno de la app. Tiene un botón "Report" que comparte el log.

### `androidApp/build.gradle.kts`

```kotlin
plugins {
    alias(libs.plugins.kotlin.android)         // Kotlin para Android (NO kotlin.jvm)
    alias(libs.plugins.compose.compiler)        // Compilador de Compose
    alias(libs.plugins.android.application)     // Plugin de Android
}

android {
    namespace = "csvui.android"    // Identificador único de la app
    compileSdk = 34                // Android 14
    minSdk = 26                    // Android 8.0 (mínimo soportado)
    targetSdk = 34                 // Target Android 14
}

dependencies {
    implementation(platform(libs.compose.bom))      // Bill of Materials (versiones consistentes)
    implementation(libs.compose.material3)           // Componentes Material3
    implementation(libs.activity.compose)            // Activity + Compose
}
```

**Heurística #7**: `minSdk = 26` significa que la app funciona en Android 8.0+ (98% de dispositivos). Si pones 21 funcionaría en el 99% pero no podrías usar APIs modernas.

### `AndroidManifest.xml` — La carta de presentación de la app

```xml
<manifest>
    <uses-permission android:name="android.permission.READ_EXTERNAL_STORAGE" />
    
    <application android:label="CSV Tabulator" android:theme="@style/Theme.CsvTabulator">
        <activity android:name=".MainActivity" android:exported="true">
            <intent-filter>
                <action android:name="android.intent.action.MAIN" />
                <category android:name="android.intent.category.LAUNCHER" />
            </intent-filter>
        </activity>
    </application>
</manifest>
```

- `android:exported="true"` — Esta actividad puede ser lanzada desde el exterior (el launcher de apps)
- `MAIN + LAUNCHER` — Es la pantalla principal que aparece cuando tocas el ícono de la app

---

## 7. Las 3 capas del código compartido

Las 3 versiones (Desktop, Web, Android) comparten EXACTAMENTE el mismo código en estas 3 carpetas:

```
composeApp/src/main/kotlin/csvui/
├── model/       ← Estructuras de datos (CsvData, Selection, Action)
├── csv/         ← Lector/escritor CSV
└── actions/     ← Sistema de acciones (BuiltinActions, ShellCommandAction, ActionLibrary)
```

### ¿Por qué esto es poderoso?

- **Un solo bug fix**: Arreglas el CSV parser UNA VEZ y las 3 versiones quedan arregladas
- **Una sola feature nueva**: Agregas un nuevo tipo de acción en `BuiltinActions.kt` y aparece en Desktop, Web y Android
- **Tests**: Los tests en `composeApp/src/test/` prueban el código compartido, así que sabes que funciona en todas partes

### Diagrama de dependencias

```
                    ┌─────────────────────┐
                    │   model/CsvData.kt   │
                    │   model/Action.kt    │  ← NO dependen de nada
                    └─────────┬───────────┘
                              │
                    ┌─────────▼───────────┐
                    │   csv/CsvHandler.kt  │  ← Depende de model/
                    └─────────┬───────────┘
                              │
                    ┌─────────▼───────────┐
                    │  actions/*.kt        │  ← Depende de model/ + csv/
                    └─────────┬───────────┘
                              │
         ┌────────────────────┼────────────────────┐
         ▼                    ▼                    ▼
┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐
│   Desktop UI    │  │  Web UI/Ktor    │  │  Android UI     │
│  (composeApp/)  │  │   (server/)     │  │ (androidApp/)   │
└─────────────────┘  └─────────────────┘  └─────────────────┘
```

---

## 8. Cómo compilar y ejecutar cada versión

### Requisitos

| Herramienta | Para qué sirve | Dónde está |
|-------------|---------------|------------|
| **Java 21 JDK** | Compilar Kotlin/JVM | Instalado via SDKMAN |
| **Android SDK** | Compilar APK | `/home/vuos/android-sdk` |
| **Gradle** | Build system | Wrapper incluido (`./gradlew`) |

### Desktop

```bash
cd /home/vuos/code/p3/s56
./gradlew :composeApp:run

# O construir JAR ejecutable:
./gradlew :composeApp:packageUberJarForCurrentOS
java -jar composeApp/build/compose/jars/CsvTabulator-linux-x64-1.0.0.jar
```

### Server Web

```bash
cd /home/vuos/code/p3/s56

# Desarrollo (con Gradle):
./gradlew :server:run

# Producción (más rápido):
./gradlew :server:installDist
server/build/install/server/bin/server
# → Abre http://localhost:8080
```

### Android APK

```bash
cd /home/vuos/code/p3/s56
./gradlew :androidApp:assembleDebug
# APK generado en: androidApp/build/outputs/apk/debug/androidApp-debug.apk
```

### Tests

```bash
# Todos los tests del core compartido:
./gradlew :composeApp:test
# 34 tests, deben pasar todos
```

---

## 9. Glosario para principiantes

| Término | Significado |
|---------|-------------|
| **Kotlin Multiplatform (KMP)** | Kotlin que puede compilar a JVM (Desktop), JavaScript (Web) y Android/iPhone |
| **Gradle** | El "constructor" que compila el código, baja dependencias de internet, y genera los archivos .jar o .apk |
| **Gradle Wrapper** (`gradlew`) | Un script que descarga automáticamente la versión correcta de Gradle. Así todos usan la misma versión |
| **Módulo** | Una carpeta con su propio `build.gradle.kts`. Cada módulo produce algo diferente (app desktop, servidor, APK) |
| **Dependencia** | Una librería externa que el proyecto necesita (Ktor, Compose, etc.). Se declaran en `build.gradle.kts` |
| **Version Catalog** | Archivo `libs.versions.toml` que centraliza TODAS las versiones de las dependencias |
| **Compose** | Framework de interfaz gráfica (como React pero para Kotlin). Declaras la UI con funciones `@Composable` |
| **Ktor** | Framework para hacer servidores web en Kotlin |
| **JVM** | Java Virtual Machine — el "motor" que ejecuta el código compilado |
| **APK** | Android Package — el formato de instalación de apps Android |
| **SDK** | Software Development Kit — herramientas necesarias para compilar para una plataforma (Android SDK, JDK) |
| **Manifest** (`AndroidManifest.xml`) | Archivo XML que le dice a Android qué permisos necesita tu app, qué actividades tiene, etc. |
| **Jetpack Compose** | La versión para Android de Compose (vs Compose Multiplatform que es para Desktop + Android + Web) |

### Heurísticas rápidas

1. **Si ves `build.gradle.kts`** → ahí se declaran las dependencias de ese módulo
2. **Si ves `src/main/kotlin/`** → ahí está el código fuente principal
3. **Si ves `src/test/kotlin/`** → ahí están los tests
4. **Si ves `libs.versions.toml`** → ahí están TODAS las versiones de librerías del proyecto
5. **Los 3 módulos comparten `model/`, `csv/`, `actions/`** → lo que cambia es SOLO la UI
6. **El servidor guarda CSVs en `data/`** → relativo a donde ejecutas el servidor
7. **Android guarda CSVs en `filesDir/csv-data/`** → almacenamiento interno de la app
8. **Los comandos shell en Android** → si tienes Termux usa bash completo, si no usa sh limitado

---

## Resumen visual

```
TU CÓDIGO (lo que escribiste) → Kotlin .kt files
              │
              ▼
GRADLE (build system) → Lee build.gradle.kts, baja dependencias, compila
              │
              ▼
ARCHIVO GENERADO según el módulo:
  composeApp/ → .jar (ejecutable Desktop)
  server/     → servidor HTTP (corre con java)
  androidApp/ → .apk (instalable Android)
              │
              ▼
EL USUARIO corre/instala el archivo generado
```

### Preguntas frecuentes

**Q: ¿Por qué hay 3 módulos en lugar de 1?**
R: Porque cada uno produce un tipo diferente de aplicación. Pero comparten el 80% del código (modelo + CSV + acciones).

**Q: ¿Qué es un `build.gradle.kts`?**
R: Es un archivo de configuración escrito en Kotlin que le dice a Gradle cómo compilar ese módulo: qué plugins usar, qué dependencias bajar, cómo se llama la app, etc.

**Q: ¿Dónde están los datos cuando uso el servidor web?**
R: En la carpeta `data/` al lado del servidor. Si corres desde `s56/`, los CSV están en `s56/data/`.

**Q: ¿Dónde están los datos cuando uso el APK Android?**
R: En el almacenamiento interno de la app: normalmente `/data/data/csvui.android/files/csv-data/`. No es accesible desde el explorador de archivos sin root, pero la app te muestra la lista y puedes compartirlos desde el botón de archivos.

**Q: ¿Cómo reporto un error?**
R: En la app Android, toca el ícono del insecto (🐛) en la barra superior. Abre un email/whatsapp con el log de errores. Envíalo y puedo leerlo para corregir el problema.
