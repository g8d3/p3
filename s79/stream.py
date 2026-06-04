#!/usr/bin/env python3
"""Minimal video stream — SSE + Canvas, zero deps, mobile-ready."""

import http.server, json, math, time
from socketserver import ThreadingMixIn

W, H = 320, 240

class Server(ThreadingMixIn, http.server.HTTPServer):
    allow_reuse_address = True
    daemon_threads = True

class Handler(http.server.BaseHTTPRequestHandler):
    def log_message(self, *a): pass

    def do_GET(self):
        if self.path == '/':
            self.send_response(200)
            self.send_header('Content-Type', 'text/html; charset=utf-8')
            self.end_headers()
            self.wfile.write(HTML.encode())
        elif self.path == '/stream':
            self.send_response(200)
            self.send_header('Content-Type', 'text/event-stream')
            self.send_header('Cache-Control', 'no-cache')
            self.end_headers()
            n = 0
            try:
                while True:
                    t = n * 0.1
                    data = json.dumps({
                        "bg": [sinc(128, 127, t, 1.0),
                               sinc(128, 127, t, 1.3, 2),
                               sinc(128, 127, t, 1.7, 4)],
                        "cx": sinc(160, 120, t, 0.8),
                        "cy": sinc(120, 80, t, 1.1),
                        "cr": sinc(127, 127, t, 1.5),
                        "cg": sinc(127, 127, t, 1.9, 1),
                        "cb": sinc(127, 127, t, 2.3, 2),
                        "n": n
                    })
                    self.wfile.write(f'data: {data}\n\n'.encode())
                    self.wfile.flush()
                    n += 1
                    time.sleep(1)
            except (BrokenPipeError, ConnectionResetError, OSError):
                pass
        else:
            self.send_response(404)
            self.end_headers()

def sinc(mid, amp, t, freq, phase=0):
    return round(mid + amp * math.sin(t * freq + phase))

HTML = '''<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1.0,user-scalable=no">
<title>stream</title>
<style>
*{margin:0;padding:0;box-sizing:border-box}
body{background:#111;display:flex;justify-content:center;align-items:center;min-height:100vh;min-height:100dvh}
canvas{display:block;max-width:100vw;max-height:100vh;width:min(100vw,calc(100vh*4/3));aspect-ratio:4/3}
</style>
</head>
<body>
<canvas id=c></canvas>
<script>
const c=document.getElementById('c'),ctx=c.getContext('2d');
c.width=320;c.height=240;
let cur=null,prev=null,t0=0;
const es=new EventSource('/stream');
es.onmessage=e=>{prev=cur;cur=JSON.parse(e.data);t0=performance.now()};
function lerp(a,b,t){return a+(b-a)*t}
function draw(){
  if(!cur){requestAnimationFrame(draw);return}
  const p=prev?Math.min((performance.now()-t0)/1000,1):1;
  const bg=prev?[lerp(prev.bg[0],cur.bg[0],p),lerp(prev.bg[1],cur.bg[1],p),lerp(prev.bg[2],cur.bg[2],p)]:cur.bg;
  ctx.fillStyle='rgb('+bg.map(Math.round).join(',')+')';
  ctx.fillRect(0,0,c.width,c.height);
  [cx,cy,cr,cg,cb]=['cx','cy','cr','cg','cb'].map(k=>prev?lerp(prev[k],cur[k],p):cur[k]);
  ctx.fillStyle='rgb('+[cr,cg,cb].map(Math.round).join(',')+')';
  ctx.beginPath();ctx.arc(cx,cy,28,0,Math.PI*2);ctx.fill();
  const n=prev?lerp(prev.n,cur.n,p):cur.n;
  ctx.fillStyle='#fff';ctx.font='bold 48px monospace';ctx.textAlign='center';
  ctx.fillText(Math.round(n).toString(),160,55);
  requestAnimationFrame(draw)
}
draw()
</script>
</body>
</html>'''

if __name__ == '__main__':
    s = Server(('0.0.0.0', 8080), Handler)
    print('http://0.0.0.0:8080')
    s.serve_forever()
