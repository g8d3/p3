#!/usr/bin/env python3
"""WS test server — auto IPs, bind 0.0.0.0, works from phone."""
import asyncio, json, datetime, os, subprocess
from websockets.server import serve
from websockets.exceptions import ConnectionClosed

PORT = int(os.environ.get("PORT", 8080))

HTML = """<!DOCTYPE html>
<html><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>WS Test</title>
<style>
body{font-family:sans-serif;max-width:600px;margin:20px auto;padding:0 10px;text-align:center}
#status{padding:10px;font-weight:bold;border-radius:5px}
.ok{background:#d4edda;color:#155724}
.ko{background:#f8d7da;color:#721c24}
.wait{background:#fff3cd;color:#856404}
#log{background:#222;color:#0f0;padding:15px;height:250px;overflow-y:scroll;font-family:monospace;border-radius:5px;margin-top:15px;text-align:left}
.srv{color:#0ff}
.cli{color:#ff0}
button{padding:10px 15px;font-size:16px;cursor:pointer;margin:5px}
</style></head><body>
<h2>WebSocket Test</h2>
<p id="status" class="wait">Connecting...</p>
<p id="info"></p>
<button id="btnSend">Send message to server</button>
<button id="btnClose">Disconnect</button>
<div id="log"></div>
<script>
(function(){
var s=document.getElementById('status'),l=document.getElementById('log'),info=document.getElementById('info'),btn=document.getElementById('btnSend'),btnC=document.getElementById('btnClose');
function log(o,t,c){l.innerHTML+='<div class="'+c+'">['+new Date().toLocaleTimeString()+'] <b>'+o+':</b> '+t+'</div>';l.scrollTop=l.scrollHeight}
function connect(){
s.className='wait';s.textContent='Connecting...';
if(window.ws)try{window.ws.close()}catch(e){}
var ws=new WebSocket('ws://'+location.host+'/ws');
window.ws=ws;
ws.onopen=function(){s.className='ok';s.textContent='Connected';btn.disabled=false};
ws.onmessage=function(e){
var d=JSON.parse(e.data);
log(d.origen||'Server',d.texto||e.data,'srv');
};
ws.onclose=function(e){s.className='ko';s.textContent='Closed (code='+e.code+')';btn.disabled=true};
ws.onerror=function(){s.className='ko';s.textContent='Error'};
}
connect();
btn.onclick=function(){if(window.ws){window.ws.send('Hello from browser!');log('Client','Hello from browser!','cli')}};
btnC.onclick=function(){if(window.ws){window.ws.close()}};
})();
</script></body></html>"""

def get_ips():
    ips = {}
    try:
        out = subprocess.check_output(["ip", "-4", "-o", "addr", "show"], text=True)
        for line in out.splitlines():
            parts = line.split()
            if len(parts) >= 4:
                iface, addr = parts[1], parts[3].split("/")[0]
                ips.setdefault(iface, []).append(addr)
    except:
        pass
    return ips

async def handler(websocket):
    print(f"[WS] connected: {websocket.remote_address}")

    async def keepalive():
        try:
            while True:
                await asyncio.sleep(5)
                payload = json.dumps({"origen": "Server", "texto": f"keepalive {datetime.datetime.now().strftime('%H:%M:%S')}"})
                await websocket.send(payload)
        except ConnectionClosed:
            pass

    async def listener():
        try:
            async for message in websocket:
                print(f"[WS] msg from {websocket.remote_address}: {message}")
                reply = json.dumps({"origen": "Server", "texto": f"received: '{message}'"})
                await websocket.send(reply)
        except ConnectionClosed:
            pass

    await asyncio.gather(keepalive(), listener())
    print(f"[WS] disconnected: {websocket.remote_address}")

async def process_request(path, headers):
    if path == "/":
        body = HTML.encode()
        headers = [("Content-Type", "text/html; charset=utf-8"), ("Content-Length", str(len(body)))]
        return (200, headers, body)
    return None

async def main():
    async with serve(handler, "0.0.0.0", PORT, process_request=process_request):
        print(f"\n{'='*55}")
        print(f"  WS Test Server — http://0.0.0.0:{PORT}/")
        print(f"{'='*55}")
        ips = get_ips()
        for iface, addrs in ips.items():
            for ip in addrs:
                label = "Tailscale" if ip.startswith("100.") else "LAN" if not ip.startswith("127.") else "Local"
                print(f"  {label:10s} http://{ip}:{PORT}/")
        print(f"{'='*55}\n")
        await asyncio.get_running_loop().create_future()

if __name__ == "__main__":
    asyncio.run(main())
