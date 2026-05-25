#!/usr/bin/env python3
"""Servidor APK + reportes + test panel + auto-refresh."""
import http.server
import json
import os
from datetime import datetime
from urllib.parse import urlparse, parse_qs

PORT = 9099
APK_DIR = "/home/vuos/code/p3/s71/VoiceButtonApp/app/build/outputs/apk/debug"
REPORTS_FILE = os.path.join(APK_DIR, "reports.json")
LOCK = __import__("threading").Lock()

CATEGORIES = ["crash", "feature", "evento", "estado", "resultado"]
CAT_LABELS = {"crash":"💥 Crash","feature":"💡 Mejora","evento":"📌 Evento","estado":"🔍 Estado","resultado":"✅ Resultado"}
CAT_COLORS = {"crash":"#ff4444","feature":"#44aa44","evento":"#4488ff","estado":"#ff8800","resultado":"#8844ff"}

def load_reports():
    if not os.path.exists(REPORTS_FILE): return []
    try:
        with open(REPORTS_FILE) as f: return json.load(f)
    except: return []

def save_report(report):
    with LOCK:
        reports = load_reports()
        report["id"] = len(reports) + 1
        report["received_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        reports.insert(0, report)
        with open(REPORTS_FILE, "w") as f:
            json.dump(reports, f, indent=2, ensure_ascii=False)
    return report["id"]

def _h(t):
    return str(t).replace("&","&amp;").replace("<","&lt;").replace(">","&gt;")

def table_rows(reports):
    """Devuelve solo las filas <tr> de la tabla para actualizaci├│n parcial."""
    rows = ""
    for r in reports:
        rid = r.get("id",""); rtype = r.get("type","unknown")
        color = CAT_COLORS.get(rtype,"#999"); label = CAT_LABELS.get(rtype,rtype.upper())
        recv = r.get("received_at",""); msg = _h(r.get("message",""))
        detail = _h(r.get("detail","")); extra = _h(r.get("extra",""))
        stack = r.get("stacktrace",""); device = _h(r.get("device",""))
        dh = f"<span class='info'>{detail}</span>"
        if extra: dh += f"<br><span class='info'>extra: {extra}</span>"
        if device: dh += f"<br><span class='info'>{device}</span>"
        if stack: dh += f"<pre>{_h(stack[:500])}</pre>"
        rows += f"<tr><td>{rid}</td><td><span class='tag' style='background:{color}'>{label}</span></td><td class='info'>{recv}</td><td>{msg}</td><td>{dh}</td></tr>"
    return rows

HTML_HEAD = """<!DOCTYPE html>
<html><head><meta charset='utf-8'><meta name='viewport' content='width=device-width,initial-scale=1'>
<title>VoiceButtons</title><style>
*{box-sizing:border-box}body{font-family:sans-serif;margin:20px;max-width:1200px}
h1{color:#333;margin:0 0 4px 0;font-size:22px}
.sub{color:#666;font-size:13px;margin-bottom:16px}
.tabs{margin-bottom:16px}
.tabs a{padding:8px 16px;margin-right:4px;border-radius:4px;text-decoration:none;font-size:14px}
.tabs a.active{background:#1976D2;color:#fff}
.tabs a.inactive{background:#eee;color:#333}
.filtros{background:#f5f5f5;padding:12px;border-radius:6px;margin-bottom:12px}
.filtros label{margin-right:12px;cursor:pointer;font-size:14px}
.filtros label input{vertical-align:middle;margin-right:3px}
.filtros .btnrapido{display:inline-block;padding:4px 12px;margin:4px 4px 0 0;border-radius:4px;border:none;cursor:pointer;font-size:12px;color:#fff}
.testpanel{background:#eef4ff;padding:12px;border-radius:6px;margin-bottom:12px;border:1px solid #ccd8ee}
.testpanel h3{margin:0 0 8px 0;font-size:15px;color:#336}
.testpanel input[type=text]{flex:1;padding:6px 8px;border:1px solid #ccc;border-radius:4px;font-size:14px}
.testpanel .row{display:flex;gap:6px;margin-bottom:8px;align-items:center;flex-wrap:wrap}
.testpanel .btn{padding:6px 14px;border:none;border-radius:4px;cursor:pointer;color:#fff;font-size:13px}
.testpanel .btn:hover{opacity:.85}
table{width:100%;border-collapse:collapse;font-size:13px}
td,th{padding:6px 8px;border:1px solid #ddd;text-align:left;vertical-align:top}
th{background:#f5f5f5;position:sticky;top:0;font-size:12px}
td .tag{display:inline-block;padding:2px 6px;border-radius:3px;font-size:11px;font-weight:bold;color:#fff}
pre{background:#f8f8f8;padding:6px;font-size:11px;max-height:120px;overflow:auto;white-space:pre-wrap;margin:2px 0}
.info{color:#666;font-size:12px}
#tabla{width:100%}
#count{color:#666;font-size:13px;margin:4px 0}
</style></head><body>
<h1>VoiceButtons</h1>
<p class='sub'>APK + telemetr&iacute;a &middot; <a href='/apks'>APKs</a> &middot; <a href='/reports'>Reportes</a></p>"""

HTML_FOOT = "</body></html>"

def build_apks_page():
    entries = []
    for f in os.listdir(APK_DIR):
        full = os.path.join(APK_DIR, f)
        if os.path.isfile(full) and not f.endswith(".sha1") and not f.endswith(".json"):
            entries.append((f, os.path.getmtime(full), os.path.getsize(full)))
    entries.sort(key=lambda x: x[1], reverse=True)
    html = HTML_HEAD + "<hr><ul>"
    for name, mtime, size in entries:
        sz = f"{size/1024:.0f} KB" if size < 1024**2 else f"{size/(1024**2):.1f} MB"
        dt = datetime.fromtimestamp(mtime).strftime("%Y-%m-%d %H:%M:%S")
        html += f"<li><a href='/{name}' download><b>{name}</b></a> <span class='info'>({sz}, {dt})</span></li>"
    html += "</ul>" + HTML_FOOT
    return html

def build_reports_page(selected_cats):
    reports = load_reports()
    if selected_cats:
        reports = [r for r in reports if r.get("type","") in selected_cats]

    qs = "&".join(f"cat={c}" for c in selected_cats) if selected_cats else ""
    qs_arg = f"?{qs}" if qs else ""

    html = HTML_HEAD

    # ── Test panel ──
    html += """<div class='testpanel'>
    <h3>🧪 Campo de prueba</h3>
    <div class='row'>
      <input type='text' id='testInput' placeholder='Escribe algo y presiona Enter...' autofocus style='flex:1;padding:6px 8px;border:1px solid #ccc;border-radius:4px;font-size:14px'>
    </div>
    <div class='row' style='font-size:12px;color:#666' id='testStatus'>Al presionar Enter se genera evento + estado + resultado.</div>
  </div>"""

    # ── Filtros ──
    html += "<div class='filtros'><form method='GET' action='/reports' id='filtroForm'>"
    for cat in CATEGORIES:
        checked = "checked" if cat in selected_cats else ""
        html += f"<label><input type='checkbox' name='cat' value='{cat}' {checked} onchange='this.form.submit()'>{CAT_LABELS[cat]}</label>"
    html += "<br>"
    html += "<button type='button' class='btnrapido' style='background:#4488ff' onclick=\"window.location='/reports?cat=evento&cat=estado&cat=resultado'\">📊 Evento+Estado+Resultado</button>"
    html += "<button type='button' class='btnrapido' style='background:#666' onclick=\"window.location='/reports'\">Mostrar todos</button>"
    html += "<button type='button' class='btnrapido' style='background:#cc3333;float:right' onclick=\"if(confirm('Borrar todos los reportes?'))fetch('/clear-reports',{method:'POST'}).then(()=>location.reload())\">🗑 Borrar todos</button>"
    html += "</form></div>"

    # ── Tabla auto-refrescable ──
    html += f"<p id='count'>{len(reports)} reportes</p>"
    html += "<table><thead><tr><th>#</th><th>Tipo</th><th>Fecha</th><th>Mensaje</th><th>Detalle</th></tr></thead>"
    html += f"<tbody id='tablaCuerpo'>{table_rows(reports)}</tbody></table>"
    if not reports:
        html += "<p>No hay reportes con ese filtro.</p>"

    # ── Auto-refresh JS ──
    html += f"""<script>
const cats = {json.dumps(selected_cats)};
const qs = cats.length ? '?cat='+cats.join('&cat=') : '';
async function refresh() {{
  try {{
    let r = await fetch('/api/reports'+qs);
    let data = await r.json();
    document.getElementById('count').textContent = data.count + ' reportes';
    document.getElementById('tablaCuerpo').innerHTML = data.rows;
  }} catch(e) {{}}
}}
setInterval(refresh, 2000);

document.getElementById('testInput').addEventListener('keydown', function(e) {{
  if(e.key === 'Enter') {{
    let txt = e.target.value.trim() || '(vacio)';
    document.getElementById('testStatus').textContent = '⏳ Enviando...';
    fetch('/test', {{
      method:'POST',
      headers:{{'Content-Type':'application/json'}},
      body:JSON.stringify({{type:'text', text:txt}})
    }}).then(r=>r.json()).then(res=>{{
      if(res.ok) {{
        document.getElementById('testStatus').textContent = '✅ ' + res.msg;
        e.target.value = '';
        refresh();
      }} else {{
        document.getElementById('testStatus').textContent = '❌ Error';
      }}
    }});
  }}
}});
refresh();
</script>"""

    html += HTML_FOOT
    return html


class Handler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=APK_DIR, **kwargs)

    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path
        if path in ("/","/apks"):
            self._html(build_apks_page())
        elif path == "/reports":
            params = parse_qs(parsed.query)
            self._html(build_reports_page(params.get("cat",[])))
        elif path == "/api/reports":
            params = parse_qs(parsed.query)
            selected = params.get("cat",[])
            reports = load_reports()
            if selected:
                reports = [r for r in reports if r.get("type","") in selected]
            self._json({"count": len(reports), "rows": table_rows(reports)})
        else:
            super().do_GET()

    def do_POST(self):
        parsed = urlparse(self.path)
        if parsed.path == "/report":
            try:
                body = self.rfile.read(int(self.headers.get("Content-Length",0)))
                data = json.loads(body)
                save_report(data)
                self._json({"ok": True})
            except Exception as e:
                self._json({"ok": False, "error": str(e)}, 400)
        elif parsed.path == "/test":
            try:
                body = self.rfile.read(int(self.headers.get("Content-Length",0)))
                data = json.loads(body)
                t = data.get("type","text")
                txt = data.get("text","")
                key = data.get("key","")

                if t == "text":
                    save_report({"type":"evento","message":f"Test: escribir \"{txt}\"","detail":"simulaci\u00f3n desde panel","device":"test"})
                    save_report({"type":"estado","message":"campo de texto","detail":txt[:20],"device":"test"})
                    save_report({"type":"resultado","message":"texto insertado","detail":f"\"{txt}\"","device":"test"})
                    self._json({"ok":True,"msg":f"Enviado: \"{txt}\""})
                elif t == "key":
                    save_report({"type":"evento","message":f"Test: presionar {key}","detail":"simulaci\u00f3n desde panel","device":"test"})
                    save_report({"type":"estado","message":"campo enfocado","detail":f"tecla={key}","device":"test"})
                    save_report({"type":"resultado","message":f"tecla {key} ejecutada","detail":"","device":"test"})
                    self._json({"ok":True,"msg":f"Tecla {key} enviada"})
                elif t == "voice":
                    save_report({"type":"evento","message":"Test: inicio de voz","detail":"simulaci\u00f3n desde panel","device":"test"})
                    save_report({"type":"estado","message":"campo enfocado","detail":"escuchando...","device":"test"})
                    save_report({"type":"resultado","message":"voz reconocida","detail":"\"esto es una prueba de voz\"","device":"test"})
                    self._json({"ok":True,"msg":"Voz simulada"})
                elif t == "crash":
                    save_report({"type":"crash","message":"java.lang.NullPointerException","detail":"FloatingButtonService.sendCrash()","stacktrace":"java.lang.NullPointerException\n\tat com.voicebutton.FloatingButtonService.sendCrash(FloatingButtonService.kt:1)\n\tat com.voicebutton.FloatingButtonService.executeAction(FloatingButtonService.kt:2)\n\tat android.view.View.onClick(View.java:3)","device":"test"})
                    self._json({"ok":True,"msg":"Crash simulado"})
                else:
                    self._json({"ok":False,"error":"tipo desconocido"},400)
            except Exception as e:
                self._json({"ok":False,"error":str(e)},400)
        elif parsed.path == "/clear-reports":
            with LOCK:
                with open(REPORTS_FILE, "w") as f:
                    json.dump([], f)
            self._json({"ok": True})
        else:
            self.send_error(404)

    def _html(self, html):
        encoded = html.encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type","text/html; charset=utf-8")
        self.send_header("Content-Length",str(len(encoded)))
        self.send_header("Cache-Control","no-cache")
        self.end_headers()
        self.wfile.write(encoded)

    def _json(self, obj, status=200):
        encoded = json.dumps(obj, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type","application/json; charset=utf-8")
        self.send_header("Content-Length",str(len(encoded)))
        self.end_headers()
        self.wfile.write(encoded)

    def log_message(self, fmt, *args):
        print(f"[{datetime.now().strftime('%H:%M:%S')}] {args[0]} {args[1]} {args[2]}")

if __name__ == "__main__":
    httpd = http.server.HTTPServer(("0.0.0.0", PORT), Handler)
    print(f"Servidor: http://0.0.0.0:{PORT}")
    print(f"  APKs:     http://0.0.0.0:{PORT}/apks")
    print(f"  Reportes: http://0.0.0.0:{PORT}/reports")
    httpd.serve_forever()
