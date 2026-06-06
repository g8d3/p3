#!/usr/bin/env python3
"""A2A Demo con tiempos sincronizados para narración TTS.
Cada paso: espera (pre-narración) → acción → espera (reacción)."""
import json, os, time, urllib.request, urllib.error

BASE = os.path.dirname(os.path.abspath(__file__))
ALPHA = "http://localhost:9001"
BETA = "http://localhost:9002"

def req(method, url, body=None):
    data = json.dumps(body).encode() if body else None
    r = urllib.request.Request(url, data=data, headers={"Content-Type":"application/json"} if body else {})
    try:
        resp = urllib.request.urlopen(r, timeout=10)
        return json.loads(resp.read()) if resp.status == 200 else {"error": resp.status}
    except Exception as e:
        return {"error": str(e)}

print("=" * 70)
print("  A2A PROTOCOL TEST — CON PAUSAS PARA NARRACIÓN")
print("  Monitor: http://localhost:9099")
print("  Alpha:   " + ALPHA)
print("  Beta:    " + BETA)
print("=" * 70)

# ── INTRO (5s) ──
time.sleep(5)

# ── PASO 1: DISCOVERY (pre 3s + acción 2s + post 3s = 8s) ──
time.sleep(3)
alpha_card = req("GET", f"{ALPHA}/.well-known/agent.json")
beta_card = req("GET", f"{BETA}/.well-known/agent.json")
aname = alpha_card.get("name","?")
bname = beta_card.get("name","?")
print(f"\n✅ Alpha: {aname}")
print(f"✅ Beta:  {bname}")
time.sleep(3)

# ── PASO 2: TASK (pre 3s + acción 3s + post 3s = 9s) ──
time.sleep(3)
task1 = req("POST", f"{ALPHA}/message:send", {
    "message": {"role":"user","parts":[{"text":"¿Qué clima hace?"}],"messageId":"m1"}
})
tid1 = task1.get("result",{}).get("id","")
print(f"\n📤 Tarea enviada: {tid1[:20]}...")
time.sleep(3)
poll1 = req("GET", f"{ALPHA}/tasks/{tid1}")
state1 = poll1.get("result",{}).get("status",{}).get("state","?")
print(f"✅ Estado: {state1}")
time.sleep(3)

# ── PASO 3: CANCEL (pre 3s + acción 2s + post 3s = 8s) ──
time.sleep(3)
task2 = req("POST", f"{ALPHA}/message:send", {
    "message": {"role":"user","parts":[{"text":"Escribe un reporte largo"}],"messageId":"m2"}
})
tid2 = task2.get("result",{}).get("id","")
print(f"\n📤 Tarea larga: {tid2[:20]}...")
time.sleep(2)
cancel = req("POST", f"{ALPHA}/tasks/{tid2}:cancel", {})
cs = cancel.get("result",{}).get("status",{}).get("state","?")
print(f"🛑 Cancelación: {cs}")
time.sleep(3)

# ── PASO 4: QUALITY (pre 4s + acción 4s + post 4s = 12s) ──
time.sleep(4)
r_good = req("POST", f"{BETA}/message:send", {
    "message": {"role":"user","parts":[{"text":"Revisa: def foo(): pass"}],"messageId":"m3"}
})
t_good = r_good.get("result",{}).get("id","")
time.sleep(2)
r_bad = req("POST", f"{BETA}/message:send", {
    "message": {"role":"user","parts":[{"text":"Este código tiene un bug"}],"messageId":"m4"}
})
t_bad = r_bad.get("result",{}).get("id","")
time.sleep(2)
p_good = req("GET", f"{BETA}/tasks/{t_good}")
p_bad = req("GET", f"{BETA}/tasks/{t_bad}")
s_good = p_good.get("result",{}).get("status",{}).get("state","?")
s_bad = p_bad.get("result",{}).get("status",{}).get("state","?")
print(f"\n📊 Bueno: {s_good}  |  Malo: {s_bad}")
if s_good == s_bad:
    print("❌❌❌ IGUALES — NO HAY CALIDAD EN A2A")
time.sleep(4)

# ── PASO 5: SOLUCIÓN (pre 3s + post 4s = 7s) ──
time.sleep(3)
print("\n💡 A2A-Q: extensión de calidad para A2A")
print("   Estados: pending-review, needs-revision, passed")
print("   Métricas: eficacia, eficiencia, hardware")
print("   RFC y código en GitHub")
time.sleep(4)

# ── CIERRE ──
print("\n" + "="*70)
print("  Próximo video: implementar A2A-Q en Python")
print("  github.com/g8d3/p3")
print("="*70)
print("\n=== FIN ===")
time.sleep(2)
