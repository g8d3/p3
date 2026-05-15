#!/usr/bin/env python3
"""
obs-panel.py — Panel de control visual para OBS Studio vía WebSocket

Uso:  python3 obs-panel.py
      python3 obs-panel.py --port 4455

Requiere: pip install textual simpleobsws
"""

import asyncio, json, os, subprocess, sys, time
from pathlib import Path
from typing import Optional

import simpleobsws
from textual import work, on
from textual.app import App, ComposeResult
from textual.containers import Horizontal, Vertical, VerticalScroll, Container, Grid
from textual.screen import ModalScreen
from textual.widgets import (
    Button, ListView, ListItem, Label, Input, Static, Header, Footer, TextArea, LoadingIndicator, Select, TabbedContent, TabPane
)
from textual.reactive import reactive
from textual.message import Message

# ═══════════════════════════════════════════════════════════════════
# CONFIG
# ═══════════════════════════════════════════════════════════════════

OBS_HOST = "127.0.0.1"
OBS_PORT = 4455
OBS_PASSWORD = "SFT16WlCaNoupRwt"
CONFIG_FILE = Path(__file__).parent / "obs-panel-buttons.json"
VIEWER_DISPLAY = ":99"  # display donde está OBS (para screenshots)

# ═══════════════════════════════════════════════════════════════════
# OBS CLIENT
# ═══════════════════════════════════════════════════════════════════

class OBSClient:
    def __init__(self):
        self.url = f"ws://{OBS_HOST}:{OBS_PORT}"
        self.ws = simpleobsws.WebSocketClient(url=self.url, password=OBS_PASSWORD)
        self.connected = False

    async def connect(self):
        try:
            await self.ws.connect()
            await self.ws.wait_until_identified()
            self.connected = True
            return True
        except Exception as e:
            self.connected = False
            return False

    async def disconnect(self):
        try: await self.ws.disconnect()
        except: pass
        self.connected = False

    async def call(self, req_type: str, data: dict = None) -> dict:
        req = simpleobsws.Request(req_type, data or {})
        resp = await self.ws.call(req)
        if not resp.ok():
            return {"error": str(resp.responseData)}
        return resp.responseData or {}

    async def get_scenes(self) -> tuple[list, str]:
        d = await self.call("GetSceneList")
        return d.get("scenes", []), d.get("currentProgramSceneName", "")

    async def get_sources(self, scene: str) -> list:
        d = await self.call("GetSceneItemList", {"sceneName": scene})
        return d.get("sceneItems", [])

    async def get_version(self) -> dict:
        return await self.call("GetVersion")


# ═══════════════════════════════════════════════════════════════════
# BUTTONS CONFIG
# ═══════════════════════════════════════════════════════════════════

DEFAULT_BUTTONS = {
    "quick_actions": [
        {"label": "📷 Screenshot", "action": "screenshot"},
        {"label": "⏺ Record", "action": "StartRecord"},
        {"label": "⏹ Stop Rec", "action": "StopRecord"},
        {"label": "▶ Stream", "action": "StartStream"},
        {"label": "⏹ Stop Str", "action": "StopStream"},
    ],
    "transforms": [
        {"label": "Centrar", "action": "center"},
        {"label": "Mitad Izq.", "action": "left_half"},
        {"label": "Mitad Der.", "action": "right_half"},
        {"label": "Mitad Sup.", "action": "top_half"},
        {"label": "Mitad Inf.", "action": "bottom_half"},
        {"label": "Fullscreen", "action": "fullscreen"},
        {"label": "Esq. Sup-Izq", "action": "corner_top_left"},
        {"label": "Esq. Sup-Der", "action": "corner_top_right"},
        {"label": "Esq. Inf-Izq", "action": "corner_bot_left"},
        {"label": "Esq. Inf-Der", "action": "corner_bot_right"},
    ],
    "custom": [],
}

def load_buttons() -> dict:
    if CONFIG_FILE.exists():
        try:
            data = json.loads(CONFIG_FILE.read_text())
            for k, v in DEFAULT_BUTTONS.items():
                data.setdefault(k, v)
            return data
        except: pass
    return dict(DEFAULT_BUTTONS)

def save_buttons(data: dict):
    CONFIG_FILE.write_text(json.dumps(data, indent=2))


# ═══════════════════════════════════════════════════════════════════
# MODAL: Add Source
# ═══════════════════════════════════════════════════════════════════

class InputModal(ModalScreen[str]):
    """Modal con un campo de texto y botón OK/Cancel."""
    def __init__(self, title: str, placeholder: str = ""):
        super().__init__()
        self.modal_title = title
        self.placeholder = placeholder

    def compose(self) -> ComposeResult:
        yield Grid(
            Label(self.modal_title, id="title"),
            Input(placeholder=self.placeholder, id="modal-input"),
            Horizontal(
                Button("Cancelar", variant="default", id="cancel"),
                Button("OK", variant="primary", id="ok"),
            ),
            id="dialog",
        )

    def on_button_pressed(self, event: Button.Pressed):
        if event.button.id == "ok":
            val = self.query_one("#modal-input", Input).value
            self.dismiss(val)
        elif event.button.id == "cancel":
            self.dismiss("")

    CSS = """
    #dialog { grid-size: 2; width: 50; padding: 1; }
    #title { column-span: 2; }
    """

# ═══════════════════════════════════════════════════════════════════
# MAIN APP
# ═══════════════════════════════════════════════════════════════════

class OBSPanel(App):
    CSS = """
    Screen { background: #1a1b26; }
    
    #tabs { height: 1fr; }
    TabPane { padding: 1; }
    
    #bottom-section { height: auto; max-height: 12; border: solid #3b4261; margin-top: 1; }
    #chat-section { height: auto; max-height: 10; border: solid #3b4261; }
    
    .panel-title { 
        background: #3b4261; color: #a9b1d6; 
        text-style: bold; padding: 0 1; height: 1; margin-bottom: 1;
    }
    
    ListView { height: 1fr; margin-bottom: 1; }
    
    #cmd-input { width: 1fr; }
    #chat-input { width: 1fr; }
    
    #status-bar { 
        height: 1; background: #1f2335; color: #565f89; 
        padding: 0 1; 
    }
    
    #response-display { 
        height: 3; background: #1f2335; color: #9ece6a;
        padding: 0 1; overflow-y: auto;
    }
    #chat-history { 
        height: 5; background: #1f2335; color: #c0caf5;
        padding: 0 1; overflow-y: auto;
    }
    
    Button { margin: 0 1; min-width: 10; }
    Button:hover { text-style: bold; }
    
    .btn-row { height: auto; margin-bottom: 1; }
    .transform-grid { height: auto; }
    """

    # Reactive state
    connected = reactive(False)
    current_scene = reactive("")
    current_source_id = reactive(0)
    current_source_name = reactive("")
    scenes = reactive([])
    sources = reactive([])

    def __init__(self):
        super().__init__()
        self.obs = OBSClient()
        self.buttons = load_buttons()
        self.chat_history = []

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        with Container():
            with TabbedContent(id="tabs"):
                with TabPane("📂 Escenas", id="tab-scenes"):
                    yield ListView(id="scene-list")
                    with Horizontal(classes="btn-row"):
                        yield Button("➕ Agregar", id="add-scene", variant="success")
                        yield Button("✕ Eliminar", id="del-scene", variant="error")
                with TabPane("📹 Fuentes", id="tab-sources"):
                    yield ListView(id="source-list")
                    with Horizontal(classes="btn-row"):
                        yield Button("➕ Agregar", id="add-source", variant="success")
                        yield Button("✕ Eliminar", id="del-source", variant="error")
                        yield Button("⬆ Subir", id="src-up")
                        yield Button("⬇ Bajar", id="src-down")
                with TabPane("🎯 Transformar", id="tab-transforms"):
                    yield Label("⚡ Acciones rápidas")
                    with Container(id="quick-btns", classes="btn-row"):
                        yield Button("📷 Captura", id="qact-screenshot")
                        yield Button("⏺ Grabar", id="qact-StartRecord")
                        yield Button("⏹ Parar", id="qact-StopRecord")
                    yield Label("📐 Presets")
                    with Container(id="transform-btns", classes="transform-grid"):
                        for label, action in [
                            ("🎯 Centrar", "center"),
                            ("◀ Mitad Izq", "left_half"),
                            ("Mitad Der ▶", "right_half"),
                            ("▲ Sup", "top_half"),
                            ("Inf ▼", "bottom_half"),
                            ("⛶ Full", "fullscreen"),
                            ("Sup-Izq", "corner_top_left"),
                            ("Sup-Der", "corner_top_right"),
                            ("Inf-Izq", "corner_bot_left"),
                        ]:
                            yield Button(label, id=f"tpreset-{action}")
                    yield Label("✏️ Manual")
                    with Horizontal():
                        with Vertical(): yield Label("X"); yield Input(id="tx-x", placeholder="X")
                        with Vertical(): yield Label("Y"); yield Input(id="tx-y", placeholder="Y")
                        with Vertical(): yield Label("W"); yield Input(id="tx-w", placeholder="W")
                        with Vertical(): yield Label("H"); yield Input(id="tx-h", placeholder="H")
                    yield Button("Aplicar", id="apply-transform", variant="primary")
            # ─── BOTTOM: Command ───
            with Vertical(id="bottom-section"):
                yield Label("📟 Comando", classes="panel-title")
                with Horizontal():
                    yield Input(id="cmd-input", placeholder="SetSceneItemTransform ...")
                    yield Button("▶", id="run-cmd", variant="primary")
                yield Static(id="response-display")
            # ─── CHAT ───
            with Vertical(id="chat-section"):
                yield Label("💬 Chat", classes="panel-title")
                yield VerticalScroll(id="chat-history")
                with Horizontal():
                    yield Input(id="chat-input", placeholder="Escribe...")
                    yield Button("▶", id="send-chat", variant="primary")
            yield Static(id="status-bar")
        yield Footer()

    def on_mount(self):
        self.set_interval(1, self._poll_connection)
        self.connect_obs()
        self.add_chat_message("🤖", "¡Hola! Panel de control OBS listo. Usa botones o escribe comandos.")

    # ─── LIFECYCLE ────────────────────────────────────────────────

    async def _poll_connection(self):
        was = self.connected
        self.connected = self.obs.connected
        if was != self.connected:
            if self.connected:
                self.refresh_all()
            self.update_status()

    def update_status(self):
        try:
            s = self.query_one("#status-bar", Static)
        except Exception:
            return  # app not mounted yet (e.g. during test)
        if self.connected:
            s.update(f"[green]● Conectado[/green] a ws://{OBS_HOST}:{OBS_PORT}  |  Escena: {self.current_scene}")
        else:
            s.update(f"[red]● Desconectado[/red] — intentando conectar a ws://{OBS_HOST}:{OBS_PORT}...")

    # ─── INTERNAL ASYNC METHODS (no @work, can be awaited) ────────

    async def _do_connect(self):
        ok = await self.obs.connect()
        self.connected = ok
        self.update_status()
        if ok:
            await self._do_refresh_all()
        return ok

    async def _do_refresh_all(self):
        if not self.obs.connected:
            await self._do_connect()
            if not self.obs.connected:
                return
        try:
            scenes, current = await self.obs.get_scenes()
            self.scenes = scenes
            self.current_scene = current or (scenes[0]["sceneName"] if scenes else "")
            self.update_scene_list()
            if self.current_scene:
                await self._do_refresh_sources()
            self.update_status()
        except Exception as e:
            self.connected = False

    async def _do_refresh_sources(self):
        if not self.current_scene:
            return
        try:
            self.sources = await self.obs.get_sources(self.current_scene)
            self.update_source_list()
        except Exception:
            pass

    # ─── WORKER WRAPPERS (return Worker, cannot be awaited) ────────

    @work(exclusive=True, group="obs")
    async def connect_obs(self):
        return await self._do_connect()

    @work(exclusive=True, group="obs")
    async def refresh_all(self):
        await self._do_refresh_all()

    @work(exclusive=True, group="obs")
    async def refresh_sources(self):
        await self._do_refresh_sources()

    # ─── UI UPDATES ───────────────────────────────────────────────

    def update_scene_list(self):
        try:
            lv = self.query_one("#scene-list", ListView)
            lv.clear()
            for s in self.scenes:
                name = s["sceneName"]
                selected = " ◀" if name == self.current_scene else ""
                lv.append(ListItem(Label(f"{name}{selected}")))
        except Exception as e:
            pass  # list not ready yet

    def update_source_list(self):
        try:
            lv = self.query_one("#source-list", ListView)
            lv.clear()
            for src in self.sources:
                name = src.get("sourceName", "?")
                vis = "👁" if src.get("sceneItemEnabled", True) else "👁‍🗨"
                lv.append(ListItem(Label(f"{vis} {name}")))
        except Exception as e:
            pass

    def update_transform_panel(self):
        """Fill transform inputs from current source's transform data."""
        for src in self.sources:
            if src.get("sceneItemId") == self.current_source_id:
                t = src.get("sceneItemTransform", {})
                try:
                    self.query_one("#tx-x", Input).value = str(round(t.get("positionX", 0), 1))
                    self.query_one("#tx-y", Input).value = str(round(t.get("positionY", 0), 1))
                    self.query_one("#tx-w", Input).value = str(round(t.get("width", 0), 1))
                    self.query_one("#tx-h", Input).value = str(round(t.get("height", 0), 1))
                except: pass
                break

    # ─── SCENE ACTIONS ────────────────────────────────────────────

    @on(ListView.Selected, "#scene-list")
    def on_scene_selected(self, event: ListView.Selected):
        if event.item is None or not event.item.children:
            return  # evento de selección vacía (ej. al hacer clear)
        label = event.item.children[0].renderable  # type: ignore
        name = str(label).replace(" ◀", "").strip()
        if not name:
            return
        # No modificar la UI aquí — delegar al worker
        self.switch_to_scene(name)

    @work(exclusive=True, group="obs")
    async def switch_to_scene(self, name: str):
        try:
            await self.obs.call("SetCurrentProgramScene", {"sceneName": name})
            self.current_scene = name
            self.update_scene_list()  # worker corre en el event loop, ya no hay conflicto
            await self._do_refresh_sources()
        except Exception as e:
            import sys
            print(f"[ERROR] switch_to_scene('{name}'): {e}", file=sys.stderr)
            self.set_response(f"❌ Error: {e}")

    @on(Button.Pressed, "#add-scene")
    def add_scene(self):
        def cb(name: str):
            if name:
                self._do_add_scene(name)
        self.push_screen(InputModal("Nombre de la nueva escena", "Escena-D"), cb)

    @work(exclusive=True, group="obs")
    async def _do_add_scene(self, name: str):
        try:
            await self.obs.call("CreateScene", {"sceneName": name})
            self._do_refresh_all()
        except Exception as e:
            self.set_response(f"❌ Error: {e}")

    @on(Button.Pressed, "#del-scene")
    @work(exclusive=True, group="obs")
    async def del_scene(self):
        if self.current_scene:
            await self.obs.call("RemoveScene", {"sceneName": self.current_scene})
            self.refresh_all()

    # ─── SOURCE ACTIONS ───────────────────────────────────────────

    @on(ListView.Selected, "#source-list")
    def on_source_selected(self, event: ListView.Selected):
        label = event.item.children[0].renderable  # type: ignore
        name = label.replace("👁 ", "").replace("👁‍🗨 ", "")
        for src in self.sources:
            if src.get("sourceName") == name:
                self.current_source_id = src.get("sceneItemId", 0)
                self.current_source_name = name
                self.update_transform_panel()
                break

    @on(Button.Pressed, "#add-source")
    def add_source_modal(self):
        def cb(name: str):
            if name:
                self._do_add_source(name)
        self.push_screen(InputModal("Nombre de la nueva fuente", "Mi fuente"), cb)

    @work(exclusive=True, group="obs")
    async def _do_add_source(self, name: str):
        if not self.current_scene:
            return
        try:
            await self.obs.call("CreateInput", {
                "sceneName": self.current_scene,
                "inputName": name,
                "inputKind": "color_source_v3",
                "inputSettings": {"color": 0x1a1a2e, "width": 400, "height": 300},
                "sceneItemEnabled": True,
            })
            await self._do_refresh_sources()
            self.set_response(f"✅ Fuente '{name}' agregada")
        except Exception as e:
            self.set_response(f"❌ Error: {e}")

    @on(Button.Pressed, "#del-source")
    @work(exclusive=True, group="obs")
    async def del_source(self):
        if self.current_source_name and self.current_scene:
            await self.obs.call("RemoveInput", {"inputName": self.current_source_name})
            self.current_source_name = ""
            self.current_source_id = 0
            await self._do_refresh_sources()

    @on(Button.Pressed, "#src-up")
    @work(exclusive=True, group="obs")
    async def src_up(self):
        # Get current item's index and decrement it
        for i, src in enumerate(self.sources):
            if src.get("sceneItemId") == self.current_source_id:
                if i > 0:
                    await self.obs.call("SetSceneItemIndex", {
                        "sceneName": self.current_scene,
                        "sceneItemId": self.current_source_id,
                        "sceneItemIndex": i - 1,
                    })
                    await self._do_refresh_sources()
                break

    @on(Button.Pressed, "#src-up")
    @work(exclusive=True, group="obs")
    async def src_up(self):
        for i, src in enumerate(self.sources):
            if src.get("sceneItemId") == self.current_source_id:
                if i > 0:
                    await self.obs.call("SetSceneItemIndex", {
                        "sceneName": self.current_scene,
                        "sceneItemId": self.current_source_id,
                        "sceneItemIndex": i - 1,
                    })
                    await self._do_refresh_sources()
                break

    @on(Button.Pressed, "#src-down")
    @work(exclusive=True, group="obs")
    async def src_down(self):
        for i, src in enumerate(self.sources):
            if src.get("sceneItemId") == self.current_source_id:
                if i < len(self.sources) - 1:
                    await self.obs.call("SetSceneItemIndex", {
                        "sceneName": self.current_scene,
                        "sceneItemId": self.current_source_id,
                        "sceneItemIndex": i + 1,
                    })
                    await self._do_refresh_sources()
                break

    # ─── TRANSFORM ACTIONS ────────────────────────────────────────

    @work(exclusive=True, group="obs")
    async def apply_transform(self, transform: dict):
        if not self.current_source_id or not self.current_scene:
            return
        full = {"sceneName": self.current_scene, "sceneItemId": self.current_source_id, "sceneItemTransform": transform}
        await self.obs.call("SetSceneItemTransform", full)
        await self._do_refresh_sources()
        self.set_response(f"✅ Transform aplicado: {json.dumps(transform)}")

    def get_transform_presets(self) -> dict:
        """Return preset transforms by name."""
        return {
            "center": {"positionX": 960, "positionY": 540, "alignment": 5},
            "left_half": {"positionX": 320, "positionY": 540, "alignment": 5, "width": 640, "height": 1080},
            "right_half": {"positionX": 1600, "positionY": 540, "alignment": 5, "width": 640, "height": 1080},
            "top_half": {"positionX": 960, "positionY": 270, "alignment": 5, "width": 1280, "height": 540},
            "bottom_half": {"positionX": 960, "positionY": 810, "alignment": 5, "width": 1280, "height": 540},
            "fullscreen": {"positionX": 0, "positionY": 0, "width": 1920, "height": 1080},
            "corner_top_left": {"positionX": 0, "positionY": 0, "width": 640, "height": 360},
            "corner_top_right": {"positionX": 1280, "positionY": 0, "width": 640, "height": 360},
            "corner_bot_left": {"positionX": 0, "positionY": 720, "width": 640, "height": 360},
            "corner_bot_right": {"positionX": 1280, "positionY": 720, "width": 640, "height": 360},
        }

    @on(Button.Pressed, "#apply-transform")
    def apply_manual_transform(self):
        try:
            x = float(self.query_one("#tx-x", Input).value or 0)
            y = float(self.query_one("#tx-y", Input).value or 0)
            w = float(self.query_one("#tx-w", Input).value or 0)
            h = float(self.query_one("#tx-h", Input).value or 0)
            self.apply_transform({"positionX": x, "positionY": y, "width": w, "height": h})
        except ValueError:
            self.set_response("❌ Valores inválidos en X/Y/W/H")

    # ─── QUICK BUTTONS (handled via button IDs) ───────────────────

    def on_button_pressed(self, event: Button.Pressed):
        bid = event.button.id or ""
        if bid.startswith("qact-"):
            action = bid.replace("qact-", "")
            self.handle_quick_action(action)
        elif bid.startswith("tpreset-"):
            action = bid.replace("tpreset-", "")
            preset = self.get_transform_presets().get(action)
            if preset:
                self.apply_transform(preset)
        elif bid.startswith("cbtn-"):
            action = bid.replace("cbtn-", "")
            self.handle_custom_action(action)

    def handle_quick_action(self, action: str):
        if action == "screenshot":
            self.do_screenshot()
        elif action in ("StartRecord", "StopRecord", "StartStream", "StopStream"):
            self.run_raw_command(action)

    @work(exclusive=True, group="obs")
    async def do_screenshot(self):
        import subprocess
        shot = f"/tmp/obs-panel-shot-{int(time.time())}.png"
        r = subprocess.run(["import", "-display", VIEWER_DISPLAY, "-window", "root", shot],
                         capture_output=True, text=True, timeout=10)
        if r.returncode == 0:
            self.set_response(f"📷 Screenshot: {shot}")
        else:
            self.set_response(f"❌ Screenshot falló: {r.stderr}")

    def handle_custom_action(self, action: str):
        # Custom actions are raw OBS commands or special
        for btn in self.buttons.get("custom", []):
            if btn.get("action") == action:
                cmd = btn.get("command", "")
                if cmd:
                    self.run_raw_command(cmd)
                break

    # ─── RAW COMMAND ──────────────────────────────────────────────

    @on(Button.Pressed, "#run-cmd")
    def run_cmd_click(self):
        inp = self.query_one("#cmd-input", Input)
        if inp.value.strip():
            self.run_raw_command(inp.value.strip())

    @work(exclusive=True, group="obs")
    async def run_raw_command(self, text: str):
        """Parse and execute 'CommandName {"key":"val"}' or just 'CommandName'."""
        self.set_response(f"▶ Ejecutando: {text}")
        parts = text.strip().split(" ", 1)
        cmd = parts[0]
        data = {}
        if len(parts) > 1:
            try: data = json.loads(parts[1])
            except: data = {"raw": parts[1]}
        try:
            result = await self.obs.call(cmd, data)
            if "error" in result:
                self.set_response(f"❌ Error: {result['error']}")
            else:
                js = json.dumps(result, indent=2)[:500]
                self.set_response(f"✅ {js}")
        except Exception as e:
            self.set_response(f"❌ Excepción: {e}")

    def set_response(self, text: str):
        self.query_one("#response-display", Static).update(text)

    # ─── CHAT ─────────────────────────────────────────────────────

    @on(Button.Pressed, "#send-chat")
    def on_chat_send(self):
        inp = self.query_one("#chat-input", Input)
        if inp.value.strip():
            self.add_chat_message("🧑", inp.value.strip())
            self.process_chat(inp.value.strip())
            inp.value = ""

    async def process_chat(self, text: str):
        """Process chat: try to interpret as OBS command, or call opencode."""
        # Try to execute directly as OBS command
        parts = text.strip().split(" ", 1)
        cmd = parts[0]
        # Check if first word looks like an OBS command (starts uppercase)
        if cmd[0].isupper() and any(c.islower() for c in cmd[1:]):
            self.add_chat_message("🤖", f"Interpretando como comando OBS: {text}")
            self.query_one("#cmd-input", Input).value = text
            self.run_raw_command(text)
            return

        # Otherwise, ask opencode AI
        self.add_chat_message("🤖", "Consultando IA...")
        await self.call_opencode(text)

    @work(exclusive=True, group="obs")
    async def call_opencode(self, text: str):
        system = (
            "Eres un asistente experto en OBS Studio y su API WebSocket. "
            "El usuario te hará peticiones sobre controlar OBS. "
            "RESPONDE SOLO CON EL COMANDO WebSocket exacto que ejecutarías, "
            "en formato: CommandName {\\\"param\\\": \\\"value\\\"}. "
            "Si necesitas más información, explica qué necesitas. "
            "Si el usuario pide configurar botones, responde con el JSON "
            "para agregar a obs-panel-buttons.json."
        )
        prompt = f"{system}\n\nUsuario: {text}\n\nComando:"

        try:
            r = subprocess.run(
                ["opencode", "run", prompt, "--model", "opencode-go/mimo-v2.5"],
                capture_output=True, text=True, timeout=30,
                env={**os.environ, "HOME": os.environ["HOME"]},
            )
            out = r.stdout.strip() or r.stderr.strip() or "(sin respuesta)"
            self.add_chat_message("🤖", out[:500])
            # Try to extract OBS command and auto-fill it
            for line in out.split("\n"):
                line = line.strip()
                if line and line[0].isupper() and "{" in line:
                    self.query_one("#cmd-input", Input).value = line
                    break
        except subprocess.TimeoutExpired:
            self.add_chat_message("🤖", "⏱️ La IA tardó demasiado. Intenta de nuevo.")
        except FileNotFoundError:
            self.add_chat_message("🤖", "❌ opencode no está instalado. Usa comandos OBS directos.")

    def add_chat_message(self, who: str, text: str):
        hist = self.query_one("#chat-history")
        hist.mount(Static(f"{who}: {text}"))
        hist.scroll_end()

# ═══════════════════════════════════════════════════════════════════
# ENTRY
# ═══════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="OBS Control Panel")
    parser.add_argument("--port", type=int, default=4455, help="WebSocket port")
    args = parser.parse_args()
    OBS_PORT = args.port
    app = OBSPanel()
    app.run()
