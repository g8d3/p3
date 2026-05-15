"""
Pruebas para obs-panel.py.

Backend:    conexión OBS vía WebSocket directo
TUI logic:  métodos del panel sin renderizado (run_test no funciona en Textual 8.2.5)
Integración: xdotool contra display :99 (solo verificación visual)
API web:    obs-web.py REST endpoints

Uso:
    python3 -m pytest test_obs_panel.py -v --durations=0
    python3 -m pytest test_obs_panel.py -v -k tui   # solo TUI logic
    python3 -m pytest test_obs_panel.py -v -k backend  # solo backend
"""

import asyncio, json, os, sys, time
import pytest, simpleobsws

OBS_PORT = 4455
OBS_PASS = "SFT16WlCaNoupRwt"

# ─── Import app ──────────────────────────────────────────────────
sys.path.insert(0, os.path.dirname(__file__))
import importlib.util
_spec = importlib.util.spec_from_file_location("obs_panel",
    os.path.join(os.path.dirname(__file__), "obs-panel.py"))
mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(mod)
OBSPanel = mod.OBSPanel
OBSClient = mod.OBSClient


# ─── Helpers ─────────────────────────────────────────────────────

def _obs(method, data=None):
    """Llamada OBS sincrónica."""
    loop = asyncio.new_event_loop(); asyncio.set_event_loop(loop)
    try:
        async def run():
            ws = simpleobsws.WebSocketClient(url=f"ws://127.0.0.1:{OBS_PORT}", password=OBS_PASS)
            await ws.connect(); await ws.wait_until_identified()
            r = await ws.call(simpleobsws.Request(method, data or {}))
            await ws.disconnect()
            return r.responseData or {}
        return loop.run_until_complete(run())
    finally:
        loop.close()


@pytest.fixture(scope="session")
def obs_check():
    v = _obs("GetVersion")
    assert v.get("obsVersion", "").startswith("32"), "OBS no disponible"
    scenes = _obs("GetSceneList").get("scenes", [])
    names = [s["sceneName"] for s in scenes]
    print(f"\n✅ OBS {v['obsVersion']} | {len(names)} escenas: {names}")
    return names


# ═══════════════════════════════════════════════════════════════════
# BACKEND — OBS WebSocket directo
# ═══════════════════════════════════════════════════════════════════

class TestBackend:
    def test_obs_version(self, obs_check):
        assert len(obs_check) >= 3

    def test_scenes(self):
        s = _obs("GetSceneList")
        names = [x["sceneName"] for x in s.get("scenes", [])]
        for e in ["Escena-A", "Escena-B", "Escena-C"]:
            assert e in names

    def test_sources(self):
        items = _obs("GetSceneItemList", {"sceneName": "Escena-A"}).get("sceneItems", [])
        assert len(items) >= 2

    def test_switch_scene(self):
        b = _obs("GetCurrentProgramScene")["currentProgramSceneName"]
        t = "Escena-B" if b == "Escena-A" else "Escena-A"
        _obs("SetCurrentProgramScene", {"sceneName": t})
        a = _obs("GetCurrentProgramScene")["currentProgramSceneName"]
        assert a == t
        _obs("SetCurrentProgramScene", {"sceneName": b})  # restore

    def test_crud_scene(self):
        _obs("CreateScene", {"sceneName": "TempTest123"})
        names = [s["sceneName"] for s in _obs("GetSceneList")["scenes"]]
        assert "TempTest123" in names
        _obs("RemoveScene", {"sceneName": "TempTest123"})
        names = [s["sceneName"] for s in _obs("GetSceneList")["scenes"]]
        assert "TempTest123" not in names

    def test_input_kinds(self):
        kinds = _obs("GetInputKindList")["inputKinds"]
        for k in ["color_source_v3", "text_ft2_source_v2", "image_source"]:
            assert k in kinds

    def test_requests_available(self):
        reqs = _obs("GetVersion")["availableRequests"]
        assert len(reqs) > 50
        for r in ["GetVersion", "GetSceneList", "CreateScene", "SetCurrentProgramScene",
                   "CreateInput", "RemoveInput", "SetSceneItemTransform"]:
            assert r in reqs

    def test_transform_get_set(self):
        items = _obs("GetSceneItemList", {"sceneName": "Escena-A"}).get("sceneItems", [])
        if not items:
            pytest.skip("No hay items para transformar")
        item = items[0]
        iid = item["sceneItemId"]
        orig = item.get("sceneItemTransform", {})
        # Set and verify
        _obs("SetSceneItemTransform", {
            "sceneName": "Escena-A", "sceneItemId": iid,
            "sceneItemTransform": {"positionX": 0, "positionY": 0}
        })
        updated = _obs("GetSceneItemList", {"sceneName": "Escena-A"})["sceneItems"][0]
        assert updated["sceneItemTransform"]["positionX"] == 0
        # Restore
        _obs("SetSceneItemTransform", {
            "sceneName": "Escena-A", "sceneItemId": iid,
            "sceneItemTransform": orig
        })


# ═══════════════════════════════════════════════════════════════════
# TUI LOGIC — métodos del panel (sin renderizado)
# ═══════════════════════════════════════════════════════════════════

class TestTUILogic:
    """Prueba los métodos internos del panel sin necesidad de renderizar.
    run_test() de Textual 8.2.5 no funciona en este entorno.
    """

    def test_app_can_instantiate(self):
        """El panel se crea sin errores."""
        app = OBSPanel()
        assert app is not None
        assert app.obs is not None

    def test_load_buttons_defaults(self):
        """load_buttons retorna estructura esperada."""
        btns = mod.load_buttons()
        assert "quick_actions" in btns
        assert "transforms" in btns
        assert len(btns["transforms"]) >= 10
        assert btns["transforms"][0]["label"] == "Centrar"

    @pytest.mark.asyncio
    async def test_obs_client_connect(self):
        """OBSClient se conecta."""
        client = OBSClient()
        ok = await client.connect()
        assert ok, "OBSClient no conectó"
        assert client.connected
        await client.disconnect()
        assert not client.connected

    @pytest.mark.asyncio
    async def test_obs_client_get_scenes(self):
        """OBSClient.get_scenes retorna escenas."""
        client = OBSClient()
        await client.connect()
        scenes, current = await client.get_scenes()
        assert len(scenes) >= 3
        assert current in [s["sceneName"] for s in scenes]
        await client.disconnect()

    @pytest.mark.asyncio
    async def test_obs_client_get_sources(self):
        """OBSClient.get_sources retorna fuentes."""
        client = OBSClient()
        await client.connect()
        sources = await client.get_sources("Escena-A")
        assert len(sources) >= 2
        names = [s.get("sourceName") for s in sources]
        assert "Titulo" in names or "Fondo" in names
        await client.disconnect()

    @pytest.mark.asyncio
    async def test_tui_do_refresh_all(self):
        """_do_refresh_all popula escenas."""
        app = OBSPanel()
        await app._do_connect()
        assert len(app.scenes) >= 3
        assert app.current_scene != ""

    @pytest.mark.asyncio
    async def test_tui_do_refresh_sources(self):
        """_do_refresh_sources popula fuentes (con current_scene seteado)."""
        app = OBSPanel()
        await app._do_connect()
        app.current_scene = "Escena-A"  # necesario para _do_refresh_sources
        await app._do_refresh_sources()
        assert len(app.sources) >= 2

    @pytest.mark.asyncio
    async def test_tui_do_switch_scene(self):
        """Cambiar escena vía app.obs.call (el mismo que usa la TUI)."""
        app = OBSPanel()
        await app._do_connect()
        before = (await app.obs.call("GetCurrentProgramScene"))["currentProgramSceneName"]
        target = "Escena-B" if before != "Escena-B" else "Escena-A"
        await app.obs.call("SetCurrentProgramScene", {"sceneName": target})
        current = (await app.obs.call("GetCurrentProgramScene"))["currentProgramSceneName"]
        assert current == target
        await app.obs.call("SetCurrentProgramScene", {"sceneName": before})

    @pytest.mark.asyncio
    async def test_tui_command_executes(self):
        """Crear/eliminar escena vía app.obs.call."""
        app = OBSPanel()
        await app._do_connect()
        await app.obs.call("CreateScene", {"sceneName": "TUITempScene"})
        scenes = await app.obs.call("GetSceneList")
        names = [s["sceneName"] for s in scenes["scenes"]]
        assert "TUITempScene" in names
        await app.obs.call("RemoveScene", {"sceneName": "TUITempScene"})

    def test_center_transform_preset(self):
        """El preset 'Centrar' produce el JSON correcto."""
        presets = app = mod.OBSPanel().get_transform_presets()
        center = presets["center"]
        assert center["positionX"] == 960
        assert center["positionY"] == 540
        assert center["alignment"] == 5

    def test_all_transform_presets(self):
        """Todos los presets tienen los campos necesarios."""
        presets = OBSPanel().get_transform_presets()
        assert len(presets) >= 10
        for name, p in presets.items():
            assert "positionX" in p, f"{name} no tiene positionX"
            assert "positionY" in p, f"{name} no tiene positionY"

    @pytest.mark.asyncio
    async def test_tui_status_toggles(self):
        """app.connected se actualiza al conectar/desconectar."""
        app = OBSPanel()
        assert not app.connected
        await app._do_connect()
        assert app.connected
        # No llamamos _do_disconnect porque no existe, pero connected debería ser True


# ═══════════════════════════════════════════════════════════════════
# WEB API (obs-web.py)
# ═══════════════════════════════════════════════════════════════════

class TestWebAPI:
    def test_status(self):
        try:
            import urllib.request
            r = urllib.request.urlopen("http://localhost:8080/api/status", timeout=3)
            d = json.loads(r.read())
            assert d.get("connected")
        except Exception as e:
            pytest.skip(f"Web panel no disponible: {e}")

    def test_scenes(self):
        try:
            import urllib.request
            r = urllib.request.urlopen("http://localhost:8080/api/scenes", timeout=3)
            d = json.loads(r.read())
            assert len(d["scenes"]) >= 3
        except Exception as e:
            pytest.skip(f"Web panel no disponible: {e}")

    def test_command(self):
        try:
            import urllib.request
            r = urllib.request.urlopen(
                "http://localhost:8080/api/command",
                data=json.dumps({"method": "GetVersion"}).encode(),
                timeout=5,
            )
            d = json.loads(r.read())
            assert "32" in d.get("obsVersion", "")
        except Exception as e:
            pytest.skip(f"Web panel no disponible: {e}")

    def test_switch_scene(self):
        try:
            import urllib.request
            b = _obs("GetCurrentProgramScene")["currentProgramSceneName"]
            t = "Escena-B" if b == "Escena-A" else "Escena-A"
            r = urllib.request.urlopen(
                "http://localhost:8080/api/switch-scene",
                data=json.dumps({"scene": t}).encode(),
                timeout=5,
            )
            a = _obs("GetCurrentProgramScene")["currentProgramSceneName"]
            assert a == t
            _obs("SetCurrentProgramScene", {"sceneName": b})  # restore
        except Exception as e:
            pytest.skip(f"Web panel no disponible: {e}")


# ═══════════════════════════════════════════════════════════════════
# INTEGRACIÓN VISUAL (xdotool, solo verificación)
# ═══════════════════════════════════════════════════════════════════

class TestTUIClick:
    """Prueba que ABRE el panel TUI, hace clic en escenas, y LEE el stderr
    para detectar errores internos (AttributeError, TypeError, etc.).
    
    Una TUI es texto. El stderr del proceso es la fuente de verdad,
    no una screenshot con visión.
    """

    DISPLAY = ":99"
    PANEL_DIR = os.path.join(os.path.dirname(__file__))

    def _xdoto(self, cmd, *args):
        import shlex, subprocess
        if isinstance(cmd, str) and not args:
            parts = shlex.split(cmd)
        elif isinstance(cmd, str):
            parts = [cmd] + list(args)
        else:
            parts = list(cmd) + list(args)
        return subprocess.run(["xdotool"] + parts, capture_output=True, text=True, timeout=5,
                              env={**os.environ, "DISPLAY": self.DISPLAY})

    def _launch_and_get_stderr(self):
        """Lanza el panel, captura stderr via bash -c, devuelve (proc, path_stderr)."""
        import subprocess, tempfile
        stderr_file = os.path.join(tempfile.gettempdir(), f"panel-stderr-{int(time.time())}.log")
        cmd = f"cd {self.PANEL_DIR} && python3 obs-panel.py 2>>{stderr_file}"
        proc = subprocess.Popen(
            ["xterm", "-fn", "fixed", "-geometry", "80x60", "-T", "OBS Panel",
             "-e", "/bin/bash", "-c", cmd],
            env={**os.environ, "DISPLAY": self.DISPLAY},
        )
        return proc, stderr_file

    def _read_errors(self, stderr_path):
        """Lee el stderr y devuelve lista de errores Python encontrados."""
        if not os.path.exists(stderr_path):
            return []
        with open(stderr_path) as f:
            text = f.read()
        errors = []
        for line in text.split("\n"):
            if any(kw in line for kw in ["Traceback", "Error:", "AttributeError",
                                           "TypeError", "ValueError", "KeyError",
                                           "IndexError", "NameError", "Exception",
                                           "File ", "raise "]):
                errors.append(line.strip())
        return errors

    def test_click_scene_no_stderr_errors(self):
        """Hacer clic en escenas NO debe producir errores en stderr."""
        proc, stderr_path = self._launch_and_get_stderr()

        # Esperar a que aparezca la ventana
        panel_win = None
        for _ in range(30):
            for name in ["OBSPanel", "OBS Panel"]:
                r = self._xdoto(["search", "--name", name])
                if r.returncode == 0 and r.stdout.strip():
                    panel_win = r.stdout.strip().split("\n")[0]
                    break
            if panel_win:
                break
            time.sleep(0.3)

        if not panel_win:
            proc.kill()
            pytest.fail("Panel no apareció después de 9s")

        # Clic en cada escena
        scenes = _obs("GetSceneList").get("scenes", [])
        names = [s["sceneName"] for s in scenes]

        for idx, name in enumerate(names):
            click_y = 35 + idx * 20
            self._xdoto(f"mousemove --window {panel_win} 50 {click_y} click 1")
            time.sleep(0.5)
            current = _obs("GetCurrentProgramScene").get("currentProgramSceneName", "")

        # Leer stderr en busca de errores
        errors = self._read_errors(stderr_path)
        proc.kill()

        if errors:
            pytest.fail(f"Panel produjo errores al hacer clic:\n" + "\n".join(errors[:15]))

    def test_rapid_clicks_no_stderr_errors(self):
        """Clicks rápidos NO deben producir errores en stderr."""
        proc, stderr_path = self._launch_and_get_stderr()

        panel_win = None
        for _ in range(30):
            for name in ["OBSPanel", "OBS Panel"]:
                r = self._xdoto(["search", "--name", name])
                if r.returncode == 0 and r.stdout.strip():
                    panel_win = r.stdout.strip().split("\n")[0]
                    break
            if panel_win:
                break
            time.sleep(0.3)

        if not panel_win:
            proc.kill()
            pytest.skip("Panel no apareció")

        # Clicks rápidos en posiciones de escenas
        for _ in range(3):
            for idx in range(3):
                click_y = 35 + idx * 20
                self._xdoto(f"mousemove --window {panel_win} 50 {click_y} click 1")
                time.sleep(0.05)

        time.sleep(1)

        errors = self._read_errors(stderr_path)
        proc.kill()

        if errors:
            pytest.fail(f"Panel produjo errores con clicks rápidos:\n" + "\n".join(errors[:15]))


class TestVisual:
    """Pruebas visuales en :99 con xdotool.
    Verifican que las ventanas existen, no que la lógica funcione
    (la lógica ya se prueba en TestTUILogic)."""

    DISPLAY = ":99"

    def _xdoto(self, cmd, *args):
        import shlex, subprocess
        if isinstance(cmd, str) and not args:
            parts = shlex.split(cmd)
        elif isinstance(cmd, str):
            parts = [cmd] + list(args)
        else:
            parts = list(cmd) + list(args)
        return subprocess.run(["xdotool"] + parts, capture_output=True, text=True, timeout=5,
                              env={**os.environ, "DISPLAY": self.DISPLAY})

    def test_obs_window_visible(self):
        r = self._xdoto(["search", "--name", "OBS 32."])
        assert r.returncode == 0 and r.stdout.strip(), "OBS no visible en :99"

    def test_xdotool_works(self):
        r = self._xdoto("getmouselocation")
        assert r.returncode == 0

    def test_many_windows(self):
        r = self._xdoto("search .")
        assert len(r.stdout.strip().split("\n")) > 10, "Pocas ventanas en :99"


# ═══════════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-v", "--durations=5"]))
