#!/usr/bin/env python3
"""
Simple Video Streaming Server for LAN - No dependencies
Uses only Python standard library
"""

import os
import sys
import http.server
import socketserver
from pathlib import Path
import json

# Configuration
VIDEO_DIR = os.path.expanduser("~/Videos/ai-content/assets")
PORT = 8000

os.makedirs(VIDEO_DIR, exist_ok=True)

class StreamingHandler(http.server.SimpleHTTPRequestHandler):
    """Custom handler with video streaming support"""
    
    def do_GET(self):
        if self.path == '/' or self.path == '/index.html':
            self.send_html()
        elif self.path == '/api/videos':
            self.send_json()
        elif self.path.startswith('/video/'):
            self.stream_video()
        else:
            self.send_error(404)
    
    def send_html(self):
        """Send HTML video list"""
        videos = []
        for f in os.listdir(VIDEO_DIR):
            if f.endswith(('.mp4', '.mkv', '.avi', '.webm')):
                path = os.path.join(VIDEO_DIR, f)
                size = os.path.getsize(path)
                videos.append({'name': f, 'size': f"{size / 1024 / 1024:.1f} MB", 'url': f'/video/{f}'})
        
        html = '''<!DOCTYPE html>
<html>
<head>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>AI Content Videos</title>
    <style>
        body { font-family: -apple-system, sans-serif; padding: 20px; background: #1a1a2e; color: #fff; margin: 0; }
        h1 { color: #4cc9f0; }
        .video-list { list-style: none; padding: 0; }
        .video-item { background: #16213e; margin: 10px 0; padding: 15px; border-radius: 8px; }
        .video-item a { color: #4cc9f0; text-decoration: none; font-size: 18px; display: block; }
        .video-item span { color: #888; font-size: 14px; }
        .empty { color: #666; }
    </style>
</head>
<body>
    <h1>🎬 AI Content Videos</h1>
    <ul class="video-list】
'''
        
        for v in videos:
            html += f'<li class="video-item"><a href="{v["url"]}">{v["name"]}</a><span>{v["size"]}</span></li>\n'
        
        if not videos:
            html += '<li class="empty">No videos found</li>\n'
        
        html += '''</ul></body></html>'''
        
        self.send_response(200)
        self.send_header('Content-type', 'text/html')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        self.wfile.write(html.encode())
    
    def send_json(self):
        """Send JSON list of videos"""
        videos = []
        for f in os.listdir(VIDEO_DIR):
            if f.endswith(('.mp4', '.mkv', '.avi', '.webm')):
                path = os.path.join(VIDEO_DIR, f)
                size = os.path.getsize(path)
                videos.append({'name': f, 'size': size, 'url': f'/video/{f}'})
        
        self.send_response(200)
        self.send_header('Content-type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        self.wfile.write(json.dumps(videos).encode())
    
    def stream_video(self):
        """Stream video with range requests"""
        filename = self.path.replace('/video/', '')
        filepath = os.path.join(VIDEO_DIR, filename)
        
        if not os.path.exists(filepath):
            self.send_error(404, 'File not found')
            return
        
        file_size = os.path.getsize(filepath)
        range_header = self.headers.get('Range')
        
        if range_header:
            # Parse range
            try:
                range_spec = range_header.replace('bytes=', '')
                parts = range_spec.split('-')
                byte_start = int(parts[0]) if parts[0] else 0
                byte_end = int(parts[1]) if parts[1] else file_size - 1
            except:
                byte_start = 0
                byte_end = file_size - 1
            
            byte_end = min(byte_end, file_size - 1)
            content_length = byte_end - byte_start + 1
            
            # Read range
            with open(filepath, 'rb') as f:
                f.seek(byte_start)
                data = f.read(content_length)
            
            self.send_response(206)
            self.send_header('Content-type', 'video/mp4')
            self.send_header('Content-Range', f'bytes {byte_start}-{byte_end}/{file_size}')
            self.send_header('Accept-Ranges', 'bytes')
            self.send_header('Content-Length', str(content_length))
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(data)
        else:
            # Send entire file
            self.send_response(200)
            self.send_header('Content-type', 'video/mp4')
            self.send_header('Content-Length', str(file_size))
            self.send_header('Accept-Ranges', 'bytes')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            
            with open(filepath, 'rb') as f:
                self.wfile.write(f.read())

class ReuseAddrTCPServer(socketserver.TCPServer):
    allow_reuse_address = True

def get_local_ip():
    """Get local IP"""
    import socket
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except:
        return "127.0.0.1"

if __name__ == '__main__':
    ip = get_local_ip()
    print(f"""
==========================================
   🎬 Video Streaming Server
==========================================

   📱 Open on your phone:
   http://{ip}:{PORT}

   💻 Or on this computer:
   http://localhost:{PORT}

   📁 Videos: {VIDEO_DIR}
   
   Press Ctrl+C to stop
==========================================
""")
    
    os.chdir(VIDEO_DIR)
    with ReuseAddrTCPServer(('', PORT), StreamingHandler) as httpd:
        print(f'Server running at http://{ip}:{PORT}')
        httpd.serve_forever()
