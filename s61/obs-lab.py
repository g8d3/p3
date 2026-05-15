#!/usr/bin/env python3
"""
obs-lab.py — Laboratorio OBS WebSocket: escenas, fuentes, layouts
===============================================================

Requisitos:
  - OBS Studio ejecutándose con WebSocket habilitado
  - pip install simpleobsws

Uso:
  1. Terminal 1:  source obs-lab.sh && demo         (inicia Xvfb + OBS + ventanas)
  2. Terminal 2:  python3 obs-lab.py                (controla OBS vía WebSocket)

O bien:
  1. Terminal 1:  obs-xvfb                          (Xvfb + OBS efímero)
  2. Terminal 2:  export DISPLAY=:99 && python3 obs-lab.py

Contraseña WebSocket (de tu config): SFT16WlCaNoupRwt
"""

import asyncio
import json
import sys
import textwrap
from typing import Any

import simpleobsws

# ─── Configuración ─────────────────────────────────────────────────────────
HOST = "127.0.0.1"
PORT = 4455
PASSWORD = "SFT16WlCaNoupRwt"

# Input kinds de OBS 32 para Linux (pueden variar entre versiones)
COLOR_KIND = "color_source_v3"
TEXT_KIND = "text_ft2_source_v2"

# ─── Cliente WebSocket ────────────────────────────────────────────────────


class OBSClient:
    """Wrapper alrededor de simpleobsws para calls más limpios."""

    def __init__(self, host=HOST, port=PORT, password=PASSWORD):
        url = f"ws://{host}:{port}"
        self.ws = simpleobsws.WebSocketClient(
            url=url,
            password=password,
        )

    async def __aenter__(self):
        await self.ws.connect()
        await self.ws.wait_until_identified()
        print(f"✅ Conectado a OBS WebSocket en {self.ws.url}")
        return self

    async def __aexit__(self, *args):
        await self.ws.disconnect()
        print("🔌 Desconectado de OBS WebSocket")

    async def call(self, request_type: str, data: dict | None = None) -> dict:
        """Ejecuta un request OBS WebSocket y devuelve responseData."""
        req = simpleobsws.Request(request_type, data)
        resp = await self.ws.call(req)
        if not resp.ok():
            raise RuntimeError(
                f"Request '{request_type}' falló: {resp.responseData}"
            )
        return resp.responseData or {}

    async def batch(self, requests: list[tuple[str, dict | None]]) -> list[dict]:
        """Ejecuta multiples requests en lote (más rápido)."""
        reqs = [simpleobsws.Request(rt, rd) for rt, rd in requests]
        results = await self.ws.call_batch(reqs, halt_on_failure=True)
        out = []
        for r in results:
            if not r.ok():
                raise RuntimeError(
                    f"Batch request falló: {r.responseData}"
                )
            out.append(r.responseData or {})
        return out


# ═══════════════════════════════════════════════════════════════════════════
#  LECCIONES PRÁCTICAS
# ═══════════════════════════════════════════════════════════════════════════


async def leccion_01_info(obs: OBSClient):
    """Lección 1: Obtener información de OBS."""
    print("\n" + "=" * 60)
    print("  📊 LECCIÓN 1: Información de OBS")
    print("=" * 60)

    # GetVersion — info de versión
    v = await obs.call("GetVersion")
    print(f"  Versión OBS:          {v.get('obsVersion')}")
    print(f"  Versión WebSocket:    {v.get('obsWebSocketVersion')}")
    print(f"  Versión RPC:          {v.get('rpcVersion')}")
    print(f"  Plataforma:           {v.get('platform')} {v.get('platformDescription')}")
    print(f"  CPU Cores:            {v.get('availableCores')}")

    # GetSceneList — escenas existentes
    scenes = await obs.call("GetSceneList")
    print(f"\n  Escena actual:        {scenes.get('currentProgramSceneName')}")
    print(f"  Escenas ({len(scenes.get('scenes', []))}):")
    for s in scenes.get("scenes", []):
        print(f"    - {s['sceneName']} (index: {s.get('sceneIndex', '?')})")

    # GetInputList — fuentes existentes
    inputs = await obs.call("GetInputList")
    print(f"\n  Fuentes ({len(inputs.get('inputs', []))}):")
    for inp in inputs.get("inputs", []):
        print(f"    - {inp['inputName']} (kind: {inp['inputKind']})")


async def leccion_02_escenas(obs: OBSClient):
    """Lección 2: Crear y gestionar escenas."""
    print("\n" + "=" * 60)
    print("  🎭 LECCIÓN 2: Crear escenas y navegar entre ellas")
    print("=" * 60)

    # 1. Crear 3 escenas
    for nombre in ["Escena-A", "Escena-B", "Escena-C"]:
        try:
            await obs.call("CreateScene", {"sceneName": nombre})
            print(f"  ✅ Escena creada: {nombre}")
        except RuntimeError as e:
            if "already exists" in str(e):
                print(f"  ⚠️  Escena ya existe: {nombre}")
            else:
                raise

    # 2. Cambiar a Escena-A
    await obs.call("SetCurrentProgramScene", {"sceneName": "Escena-A"})
    print("  🎯 Cambiado a Escena-A (programa)")

    # 3. Usar SetCurrentPreviewScene (solo funciona en Studio Mode)
    try:
        await obs.call("SetCurrentPreviewScene", {"sceneName": "Escena-B"})
        print("  🎯 Vista previa cambiada a Escena-B")
    except RuntimeError:
        print("  ⚠️  Studio Mode no activo — se necesita activar manualmente")

    # 4. Listar escenas actualizado
    scenes = await obs.call("GetSceneList")
    print(f"\n  Escenas después del cambio:")
    for s in scenes.get("scenes", []):
        prog = " ← PROGRAMA" if s["sceneName"] == scenes.get("currentProgramSceneName") else ""
        print(f"    - {s['sceneName']}{prog}")


async def leccion_03_fuentes(obs: OBSClient):
    """Lección 3: Agregar fuentes a las escenas."""
    print("\n" + "=" * 60)
    print("  📹 LECCIÓN 3: Agregar fuentes (inputs) a las escenas")
    print("=" * 60)

    # ─── Input kinds comunes en Linux ──────────────────────────────────
    # Lista completa: await obs.call("GetInputKindList")
    kinds = await obs.call("GetInputKindList")
    print(f"  Tipos de fuente disponibles ({len(kinds.get('inputKinds', []))}):")
    for k in kinds.get("inputKinds", [])[:15]:  # primeras 15
        print(f"    - {k}")

    # ─── Agregar fuentes a Escena-A ────────────────────────────────────
    scene_a = "Escena-A"

    # Fuente de texto (FreeType2 en Linux)
    try:
        await obs.call("CreateInput", {
            "sceneName": scene_a,
            "inputName": "Titulo",
            "inputKind": TEXT_KIND,
            "inputSettings": {
                "text": "Hola OBS desde WebSocket!",
                "font": {"face": "Monospace", "flags": 0, "size": 48},
                "color": 0xFFFFFF,
                "outline": True,
                "outline_color": 0x000000,
            },
            "sceneItemEnabled": True,
        })
        print(f"  ✅ Fuente de texto 'Titulo' agregada a {scene_a}")
    except RuntimeError as e:
        if "already exists" in str(e).lower():
            print(f"  ⚠️  Fuente 'Titulo' ya existe, actualizando...")
            await obs.call("SetInputSettings", {
                "inputName": "Titulo",
                "inputSettings": {"text": "Hola OBS desde WebSocket!"},
            })
        else:
            raise

    # Color source (fondo de color)
    try:
        await obs.call("CreateInput", {
            "sceneName": scene_a,
            "inputName": "Fondo",
            "inputKind": COLOR_KIND,
            "inputSettings": {
                "color": 0x1a1a2e,
                "width": 1920,
                "height": 1080,
            },
            "sceneItemEnabled": True,
        })
        print(f"  ✅ Fondo de color agregado a {scene_a}")
    except RuntimeError:
        print(f"  ⚠️  'Fondo' ya existe")

    # Image source (si hay una imagen de prueba)
    try:
        await obs.call("CreateInput", {
            "sceneName": scene_a,
            "inputName": "Logo",
            "inputKind": "image_source",
            "inputSettings": {
                "file": "",
            },
            "sceneItemEnabled": False,
        })
        print(f"  ✅ Fuente de imagen 'Logo' agregada a {scene_a}")
    except RuntimeError:
        print(f"  ⚠️  'Logo' ya existe")

    # ─── Captura de ventana (Window Capture) ────────────────────────
    # En OBS para Linux, el capture de ventanas es "xcomposite_input"
    # REQUIERE: un Window Manager (openbox) corriendo en el Xvfb.
    #   source obs-lab.sh && openbox-start
    # Primero listamos las ventanas disponibles con xdotool
    print("\n  🔍 Ventanas detectadas en el sistema (requiere DISPLAY=:99):")
    import subprocess
    try:
        result = subprocess.run(
            ["xdotool", "search", "."],
            capture_output=True, text=True, timeout=3
        )
        for wid in result.stdout.strip().split():
            name = subprocess.run(
                ["xdotool", "getwindowname", wid],
                capture_output=True, text=True, timeout=2
            ).stdout.strip()
            geo = subprocess.run(
                ["xdotool", "getwindowgeometry", wid],
                capture_output=True, text=True, timeout=2
            ).stdout.strip().split("\n")
            pos = geo[0] if len(geo) > 0 else ""
            sz = geo[1] if len(geo) > 1 else ""
            print(f"    [{wid}] {name}  {pos} {sz}")
    except Exception as e:
        print(f"    (no se pudo listar ventanas: {e})")

    # Agregar captura de ventana para xterm
    try:
        await obs.call("CreateInput", {
            "sceneName": scene_a,
            "inputName": "Captura-Ventana",
            "inputKind": "xcomposite_input",
            "inputSettings": {},
            "sceneItemEnabled": True,
        })
        print(f"  ✅ Captura de ventana agregada a {scene_a}")
        print("  ⚠️  NOTA: configura la ventana a capturar desde OBS UI o SetInputSettings")
    except RuntimeError as e:
        print(f"  ⚠️  No se pudo agregar captura de ventana: {e}")


async def leccion_04_layout(obs: OBSClient):
    """Lección 4: Layout — posicionar y transformar elementos en escena."""
    print("\n" + "=" * 60)
    print("  📐 LECCIÓN 4: Layout — posicionar, escalar, ordenar")
    print("=" * 60)

    scene = "Escena-A"

    # Obtener todos los scene items de la escena
    items = await obs.call("GetSceneItemList", {"sceneName": scene})
    print(f"  Items en {scene}:")
    for item in items.get("sceneItems", []):
        name = item.get("sourceName", "?")
        item_id = item.get("sceneItemId", "?")
        enabled = item.get("sceneItemEnabled", False)
        transform = item.get("sceneItemTransform", {})
        pos = f"x:{transform.get('positionX','?')} y:{transform.get('positionY','?')}"
        sz = f"w:{transform.get('width','?')} h:{transform.get('height','?')}"
        print(f"    [{item_id}] {name} — visible={enabled} — pos({pos}) size({sz})")

    if not items.get("sceneItems"):
        print("  ⚠️  No hay items. Crea fuentes primero con leccion_03_fuentes()")
        return

    # ─── Transformar cada item ─────────────────────────────────────────
    for item in items.get("sceneItems", []):
        item_id = item["sceneItemId"]
        name = item["sourceName"]

        if name == "Fondo":
            # Fondo: pantalla completa
            await obs.call("SetSceneItemTransform", {
                "sceneName": scene,
                "sceneItemId": item_id,
                "sceneItemTransform": {
                    "positionX": 0,
                    "positionY": 0,
                    "width": 1920,
                    "height": 1080,
                    "scaleX": 1,
                    "scaleY": 1,
                },
            })
            # Mandar al fondo
            await obs.call("SetSceneItemIndex", {
                "sceneName": scene,
                "sceneItemId": item_id,
                "sceneItemIndex": 0,
            })
            print(f"  📐 Fondo → pantalla completa, índice 0")

        elif name == "Titulo":
            # Título: centrado arriba
            await obs.call("SetSceneItemTransform", {
                "sceneName": scene,
                "sceneItemId": item_id,
                "sceneItemTransform": {
                    "positionX": 960,
                    "positionY": 50,
                    "alignment": 5,  # 5 = center
                    "scaleX": 1.5,
                    "scaleY": 1.5,
                },
            })
            print(f"  📐 Título → centrado arriba, escalado 1.5x")

        elif name == "Captura-Ventana":
            # Captura de ventana: cuadrante inferior derecho
            await obs.call("SetSceneItemTransform", {
                "sceneName": scene,
                "sceneItemId": item_id,
                "sceneItemTransform": {
                    "positionX": 960,
                    "positionY": 540,
                    "width": 960,
                    "height": 540,
                },
            })
            print(f"  📐 Captura-Ventana → cuadrante inferior derecho")

        elif name == "Logo":
            # Logo: esquina inferior izquierda
            await obs.call("SetSceneItemTransform", {
                "sceneName": scene,
                "sceneItemId": item_id,
                "sceneItemTransform": {
                    "positionX": 100,
                    "positionY": 900,
                    "width": 200,
                    "height": 200,
                },
            })
            await obs.call("SetSceneItemEnabled", {
                "sceneName": scene,
                "sceneItemId": item_id,
                "sceneItemEnabled": True,
            })
            print(f"  📐 Logo → esquina inferior izquierda")

    print("\n  ✅ Layout aplicado")


async def leccion_05_batch(obs: OBSClient):
    """Lección 5: Batch requests — operaciones atómicas."""
    print("\n" + "=" * 60)
    print("  ⚡ LECCIÓN 5: Batch requests (múltiples operaciones atómicas)")
    print("=" * 60)

    scene = "Escena-A"

    # Crear múltiples fuentes en batch
    requests = [
        ("CreateInput", {
            "sceneName": scene,
            "inputName": "Test-Batch-1",
            "inputKind": COLOR_KIND,
            "inputSettings": {"color": 0xFF5733, "width": 200, "height": 200},
            "sceneItemEnabled": True,
        }),
        ("CreateInput", {
            "sceneName": scene,
            "inputName": "Test-Batch-2",
            "inputKind": COLOR_KIND,
            "inputSettings": {"color": 0x33FF57, "width": 200, "height": 200},
            "sceneItemEnabled": True,
        }),
    ]

    try:
        results = await obs.batch(requests)
        print(f"  ✅ Batch completado: {len(results)} fuentes creadas")
    except RuntimeError as e:
        if "already exists" in str(e).lower():
            print("  ⚠️  Algunas fuentes batch ya existen (usar nombres diferentes)")
        else:
            raise

    # Ahora posicionar ambas fuentes nuevas
    items = await obs.call("GetSceneItemList", {"sceneName": scene})
    batch_transforms = []
    for item in items.get("sceneItems", []):
        name = item["sourceName"]
        item_id = item["sceneItemId"]
        if name == "Test-Batch-1":
            batch_transforms.append(
                ("SetSceneItemTransform", {
                    "sceneName": scene,
                    "sceneItemId": item_id,
                    "sceneItemTransform": {"positionX": 100, "positionY": 300, "width": 200, "height": 200},
                })
            )
        elif name == "Test-Batch-2":
            batch_transforms.append(
                ("SetSceneItemTransform", {
                    "sceneName": scene,
                    "sceneItemId": item_id,
                    "sceneItemTransform": {"positionX": 350, "positionY": 300, "width": 200, "height": 200},
                })
            )

    if batch_transforms:
        await obs.batch(batch_transforms)
        print("  ✅ Batch transforms aplicados")


async def leccion_06_escena_compuesta(obs: OBSClient):
    """Lección 6: Escena compuesta — crear un layout tipo 'talking head' o dashboard."""
    print("\n" + "=" * 60)
    print("  🖥️  LECCIÓN 6: Escena compuesta — layout tipo dashboard")
    print("=" * 60)

    scene = "Escena-B"

    # Asegurar que la escena existe
    try:
        await obs.call("CreateScene", {"sceneName": scene})
    except RuntimeError:
        pass  # ya existe

    # Fondo degradado
    try:
        await obs.call("CreateInput", {
            "sceneName": scene,
            "inputName": "Dashboard-BG",
            "inputKind": COLOR_KIND,
            "inputSettings": {"color": 0x16213e, "width": 1920, "height": 1080},
            "sceneItemEnabled": True,
        })
    except RuntimeError:
        pass

    # Barra superior
    try:
        await obs.call("CreateInput", {
            "sceneName": scene,
            "inputName": "Header-Bar",
            "inputKind": COLOR_KIND,
            "inputSettings": {"color": 0x0f3460, "width": 1920, "height": 60},
            "sceneItemEnabled": True,
        })
    except RuntimeError:
        pass

    # Panel izquierdo (captura de ventana xterm)
    try:
        await obs.call("CreateInput", {
            "sceneName": scene,
            "inputName": "Panel-Terminal",
            "inputKind": "xcomposite_input",
            "inputSettings": {},
            "sceneItemEnabled": True,
        })
    except RuntimeError:
        pass

    # Panel derecho (otro color)
    try:
        await obs.call("CreateInput", {
            "sceneName": scene,
            "inputName": "Panel-Derecho",
            "inputKind": COLOR_KIND,
            "inputSettings": {"color": 0x533483, "width": 400, "height": 600},
            "sceneItemEnabled": True,
        })
    except RuntimeError:
        pass

    # Texto título
    try:
        await obs.call("CreateInput", {
            "sceneName": scene,
            "inputName": "Dashboard-Title",
            "inputKind": TEXT_KIND,
            "inputSettings": {
                "text": "Dashboard en Vivo",
                "font": {"face": "Monospace", "size": 32},
                "color": 0xFFFFFF,
            },
            "sceneItemEnabled": True,
        })
    except RuntimeError:
        pass

    # Obtener items y posicionar
    items = await obs.call("GetSceneItemList", {"sceneName": scene})
    transforms = []
    indices = []

    for item in items.get("sceneItems", []):
        item_id = item["sceneItemId"]
        name = item["sourceName"]

        if name == "Dashboard-BG":
            transforms.append(("SetSceneItemTransform", {
                "sceneName": scene, "sceneItemId": item_id,
                "sceneItemTransform": {"positionX": 0, "positionY": 0, "width": 1920, "height": 1080},
            }))
            indices.append(("SetSceneItemIndex", {
                "sceneName": scene, "sceneItemId": item_id, "sceneItemIndex": 0,
            }))

        elif name == "Header-Bar":
            transforms.append(("SetSceneItemTransform", {
                "sceneName": scene, "sceneItemId": item_id,
                "sceneItemTransform": {"positionX": 0, "positionY": 0, "width": 1920, "height": 60},
            }))
            indices.append(("SetSceneItemIndex", {
                "sceneName": scene, "sceneItemId": item_id, "sceneItemIndex": 1,
            }))

        elif name == "Dashboard-Title":
            transforms.append(("SetSceneItemTransform", {
                "sceneName": scene, "sceneItemId": item_id,
                "sceneItemTransform": {"positionX": 960, "positionY": 30, "alignment": 5},
            }))

        elif name == "Panel-Terminal":
            transforms.append(("SetSceneItemTransform", {
                "sceneName": scene, "sceneItemId": item_id,
                "sceneItemTransform": {"positionX": 50, "positionY": 100, "width": 1000, "height": 700},
            }))

        elif name == "Panel-Derecho":
            transforms.append(("SetSceneItemTransform", {
                "sceneName": scene, "sceneItemId": item_id,
                "sceneItemTransform": {"positionX": 1100, "positionY": 100, "width": 400, "height": 700},
            }))

    if transforms:
        await obs.batch(transforms)
    if indices:
        await obs.batch(indices)

    print("  ✅ Dashboard layout creado en 'Escena-B'")

    # Cambiar a esta escena
    await obs.call("SetCurrentProgramScene", {"sceneName": scene})
    print("  🎯 Cambiado a Escena-B")


async def leccion_07_limpieza(obs: OBSClient):
    """Lección 7: Limpiar — eliminar fuentes y escenas."""
    print("\n" + "=" * 60)
    print("  🧹 LECCIÓN 7: Limpieza (descomenta para ejecutar)")
    print("=" * 60)
    print("  ⚠️  EJECUCIÓN BLOQUEADA POR SEGURIDAD")
    print("  Descomenta el código abajo si quieres eliminar todo.")

    # ─── Descomenta para limpiar ──────────────────────────────────────
    # # Eliminar escenas de prueba
    # for s in ["Escena-A", "Escena-B", "Escena-C"]:
    #     try:
    #         await obs.call("RemoveScene", {"sceneName": s})
    #         print(f"  🗑️  Escena eliminada: {s}")
    #     except RuntimeError:
    #         pass
    # print("  ✅ Limpieza completada")
    pass


async def leccion_08_automatizacion(obs: OBSClient):
    """Lección 8: Script de automatización — ciclo de layout dinámico."""
    print("\n" + "=" * 60)
    print("  🤖 LECCIÓN 8: Automatización — ciclo de layouts")
    print("=" * 60)

    for escena in ["Escena-A", "Escena-B", "Escena-C"]:
        try:
            await obs.call("SetCurrentProgramScene", {"sceneName": escena})
            print(f"  🎯 Cambiado a {escena}")
            await asyncio.sleep(2)  # esperar 2 segundos
        except RuntimeError:
            print(f"  ⚠️  Escena '{escena}' no encontrada, saltando...")

    print("  ✅ Ciclo de escenas completado")
    # Volver a Escena-A
    try:
        await obs.call("SetCurrentProgramScene", {"sceneName": "Escena-A"})
    except RuntimeError:
        pass


# ═══════════════════════════════════════════════════════════════════════════
#  REFERENCIA RÁPIDA
# ═══════════════════════════════════════════════════════════════════════════

REFERENCIA = """
═══════════════════════════════════════════════════════════════
  📖 REFERENCIA RÁPIDA — OBS WebSocket v5 API
═══════════════════════════════════════════════════════════════

📂 ESCENAS:
  GetSceneList()                                           → lista de escenas
  GetCurrentProgramScene()                                 → escena activa
  CreateScene(sceneName)                                   → crear escena
  RemoveScene(sceneName)                                   → eliminar escena
  SetCurrentProgramScene(sceneName)                        → cambiar escena
  SetCurrentPreviewScene(sceneName)                        → cambiar previsualización

📹 FUENTES (INPUTS):
  GetInputList()                                           → lista de fuentes
  GetInputKindList()                                       → tipos de fuente
  CreateInput(sceneName, inputName, inputKind, inputSettings, sceneItemEnabled)
  RemoveInput(inputName)
  SetInputName(inputName, newInputName)
  GetInputSettings(inputName)
  SetInputSettings(inputName, inputSettings)
  GetSourceActive(sourceName)                              → si está en programa

📐 LAYOUT (SCENE ITEMS):
  GetSceneItemList(sceneName)                              → items en escena
  SetSceneItemTransform(sceneName, sceneItemId, sceneItemTransform)
  SetSceneItemEnabled(sceneName, sceneItemId, sceneItemEnabled)
  SetSceneItemIndex(sceneName, sceneItemId, sceneItemIndex)  → orden z

🎯 TRANSFORM (sceneItemTransform):
  positionX, positionY         → posición en px
  width, height                → tamaño en px
  scaleX, scaleY               → escala (1.0 = 100%)
  rotation                     → rotación en grados
  alignment                    → 5=centro, 1=sup-izq, 3=sup-der, etc.
  boundsType                   → "OBS_BOUNDS_NONE", "OBS_BOUNDS_SCALE_INNER", etc.

💡 INPUT KINDS COMUNES EN LINUX (OBS 32):
  text_ft2_source_v2           → texto FreeType2
  color_source_v3              → fondo de color solido
  image_source                 → imagen desde archivo
  xcomposite_input             → captura de ventana X11 (requiere WM)
  monitor_capture              → captura de pantalla completa
  browser_source               → fuente de navegador web
  slideshow                    → presentación de imágenes

  🔍 Para listar todos: python3 -c "
    import asyncio, simpleobsws
    async def f():
      ws = simpleobsws.WebSocketClient(url='ws://localhost:4455', password='SFT16WlCaNoupRwt')
      await ws.connect(); await ws.wait_until_identified()
      r = await ws.call(simpleobsws.Request('GetInputKindList'))
      for k in r.responseData['inputKinds']: print(k)
      await ws.disconnect()
    asyncio.run(f())
  "

⚡ BATCH:
  obs.ws.call_batch(Request[...], halt_on_failure=True)

📤 STREAMING / GRABACIÓN:
  StartStream() / StopStream()
  StartRecord() / StopRecord()
  ToggleRecord()
  GetStreamStatus()
  GetRecordStatus()

🔧 UTILIDADES:
  GetVersion()
  GetStats()
  BroadcastCustomEvent(eventData)
  TriggerHotkeyByName(hotkeyName)
  TriggerHotkeyByKeySequence(keyId)
"""


# ═══════════════════════════════════════════════════════════════════════════
#  MAIN
# ═══════════════════════════════════════════════════════════════════════════

async def main():
    print("╔═══════════════════════════════════════════════════════════════╗")
    print("║        🎬  OBS LAB — Laboratorio de WebSocket y Layouts       ║")
    print("╚═══════════════════════════════════════════════════════════════╝")
    print()
    print(f"  Conectando a ws://{HOST}:{PORT} ...")

    # ─── Parsear argumentos ────────────────────────────────────────────
    lecciones = {
        "1": leccion_01_info,
        "2": leccion_02_escenas,
        "3": leccion_03_fuentes,
        "4": leccion_04_layout,
        "5": leccion_05_batch,
        "6": leccion_06_escena_compuesta,
        "7": leccion_07_limpieza,
        "8": leccion_08_automatizacion,
    }

    args = sys.argv[1:]
    if not args:
        # Ejecutar todas
        ejecutar = list(lecciones.values())
    else:
        ejecutar = []
        for arg in args:
            if arg in lecciones:
                ejecutar.append(lecciones[arg])
            elif arg == "--ref":
                print(REFERENCIA)
                return
            else:
                print(f"  ⚠️  Lección '{arg}' no encontrada. Usa: 1-8 o --ref")
                print(f"  Disponibles: {', '.join(lecciones.keys())}")
                return

    # ─── Conectar y ejecutar ───────────────────────────────────────────
    try:
        async with OBSClient() as obs:
            for leccion in ejecutar:
                try:
                    await leccion(obs)
                except Exception as e:
                    print(f"  ❌ Error en {leccion.__name__}: {e}")
    except ConnectionRefusedError:
        print()
        print("  ❌ ERROR: No se pudo conectar a OBS WebSocket.")
        print()
        print("  Asegúrate de que OBS está corriendo con WebSocket habilitado:")
        print()
        print("    Opción 1: Usa obs-lab.sh para iniciar OBS en Xvfb:")
        print("      source obs-lab.sh && demo")
        print()
        print("    Opción 2: Inicia OBS manualmente:")
        print("      obs --websocket 4455 --password SFT16WlCaNoupRwt &")
        print()
        print("    Opción 3: Verifica la configuración:")
        print("      cat ~/.config/obs-studio/plugin_config/obs-websocket/config.json")
        print()
        sys.exit(1)

    print()
    print("╔═══════════════════════════════════════════════════════════════╗")
    print("║        ✅  LABORATORIO COMPLETADO                            ║")
    print("╚═══════════════════════════════════════════════════════════════╝")
    print()
    print("  Para ver la referencia completa:")
    print("    python3 obs-lab.py --ref")
    print()
    print("  Para ejecutar lecciones específicas:")
    print("    python3 obs-lab.py 1 3 4")
    print()


if __name__ == "__main__":
    asyncio.run(main())
