#!/usr/bin/env python3.12
"""Minimal MJPEG streaming server — generates frames with changing colors & numbers."""

import http.server
import io
import socketserver
import threading
import time

from PIL import Image, ImageDraw, ImageFont

WIDTH, HEIGHT = 640, 480
FPS = 4
PORT = 8080

latest_frame = None
frame_lock = threading.Lock()
font = None


def get_font(draw: ImageDraw.ImageDraw) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    global font
    if font is not None:
        return font
    for size in (120, 100, 80, 60, 40):
        try:
            font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", size)
            return font
        except (OSError, IOError):
            pass
    font = ImageFont.load_default()
    return font


def generate_frames():
    global latest_frame
    n = 0
    interval = 1.0 / FPS
    while True:
        r = (n * 7) % 256
        g = (n * 13 + 85) % 256
        b = (n * 19 + 170) % 256
        img = Image.new("RGB", (WIDTH, HEIGHT), (r, g, b))
        draw = ImageDraw.Draw(img)
        text = str(n)
        f = get_font(draw)
        bbox = draw.textbbox((0, 0), text, font=f)
        tw = bbox[2] - bbox[0]
        th = bbox[3] - bbox[1]
        x = (WIDTH - tw) // 2
        y = (HEIGHT - th) // 2
        draw.text((x, y), text, fill=(255 - r, 255 - g, 255 - b), font=f)

        buf = io.BytesIO()
        img.save(buf, "JPEG", quality=70)
        with frame_lock:
            latest_frame = buf.getvalue()
        n += 1
        time.sleep(interval)


HTML = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Live Stream</title>
<style>
  *{margin:0;padding:0;box-sizing:border-box}
  body{background:#000;display:flex;align-items:center;justify-content:center;min-height:100dvh}
  img{max-width:100vw;max-height:100dvh;display:block}
</style>
</head>
<body><img src="/video" alt="live stream"></body>
</html>"""


class Handler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/":
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Cache-Control", "no-cache")
            self.end_headers()
            self.wfile.write(HTML.encode())
        elif self.path == "/video":
            self.send_response(200)
            self.send_header("Content-Type", "multipart/x-mixed-replace; boundary=frame")
            self.send_header("Cache-Control", "no-cache")
            self.send_header("Connection", "close")
            self.end_headers()
            try:
                while True:
                    with frame_lock:
                        frame = latest_frame
                    if frame is None:
                        time.sleep(0.05)
                        continue
                    self.wfile.write(b"--frame\r\n")
                    self.wfile.write(b"Content-Type: image/jpeg\r\n")
                    self.wfile.write(
                        b"Content-Length: " + str(len(frame)).encode() + b"\r\n\r\n"
                    )
                    self.wfile.write(frame)
                    self.wfile.write(b"\r\n")
                    time.sleep(1.0 / FPS)
            except (BrokenPipeError, ConnectionResetError):
                pass
        else:
            self.send_response(404)
            self.end_headers()

    def log_message(self, format, *args):
        pass  # silent


class ThreadedServer(socketserver.ThreadingMixIn, http.server.HTTPServer):
    daemon_threads = True
    allow_reuse_address = True


if __name__ == "__main__":
    print(f"MJPEG stream at http://localhost:{PORT}/")
    threading.Thread(target=generate_frames, daemon=True).start()
    ThreadedServer(("0.0.0.0", PORT), Handler).serve_forever()
