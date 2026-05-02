#!/usr/bin/env python3
"""
Download 10 sound effects from pixabay using CDP directly and measure time
"""
import requests
import time
import os
import subprocess
import websocket
import json

CDP_PORT = 9222
DOWNLOAD_DIR = '/home/vuos/Downloads'

class CDPClient:
    def __init__(self, ws_url):
        self.ws = websocket.create_connection(ws_url)
        self.msg_id = 0
    
    def send(self, method, params=None, timeout=10):
        self.msg_id += 1
        msg = {"id": self.msg_id, "method": method, "params": params or {}}
        self.ws.send(json.dumps(msg))
        
        self.ws.settimeout(timeout)
        while True:
            try:
                result = self.ws.recv()
                data = json.loads(result)
                if data.get('id') == self.msg_id:
                    if 'error' in data:
                        return None
                    return data.get('result', {})
            except Exception as e:
                return None
    
    def eval(self, js):
        result = self.send('Runtime.evaluate', {'expression': js, 'returnByValue': True})
        if result and 'result' in result:
            return result['result'].get('value')
        return None
    
    def close(self):
        self.ws.close()

def get_recent_files(seconds=60):
    """Get files modified in last N seconds"""
    now = time.time()
    recent = []
    for f in os.listdir(DOWNLOAD_DIR):
        if f.endswith('.mp3'):
            path = os.path.join(DOWNLOAD_DIR, f)
            mtime = os.path.getmtime(path)
            if now - mtime < seconds:
                recent.append((f, os.path.getsize(path), mtime))
    return sorted(recent, key=lambda x: x[2], reverse=True)

def main():
    print("=" * 60)
    print("Pixabay SFX Download Benchmark - 10 files")
    print("=" * 60)
    
    # Get initial recent files
    initial_files = set(f[0] for f in get_recent_files(300))
    print(f"Initial recent MP3 files: {len(initial_files)}")
    
    # Get page target
    resp = requests.get(f'http://localhost:{CDP_PORT}/json')
    targets = resp.json()
    
    # Find or open sound-effects page
    page = next((t for t in targets if 'pixabay.com/sound-effects' in t.get('url', '')), None)
    if not page:
        print("Opening pixabay sound-effects page...")
        subprocess.run(['agent-browser', '--cdp', str(CDP_PORT), 'open', 'https://pixabay.com/sound-effects/'], 
                      capture_output=True)
        time.sleep(3)
        resp = requests.get(f'http://localhost:{CDP_PORT}/json')
        targets = resp.json()
        page = next((t for t in targets if 'pixabay.com/sound-effects' in t.get('url', '')), None)
    
    if not page:
        page = next((t for t in targets if 'pixabay' in t.get('url', '').lower()), None)
    
    if not page:
        print("No page found!")
        return
    
    print(f"Connected to: {page['title']}")
    print(f"URL: {page['url']}")
    
    client = CDPClient(page['webSocketDebuggerUrl'])
    
    # Enable domains and set download behavior
    client.send('Page.enable')
    client.send('Runtime.enable')
    client.send('Page.setDownloadBehavior', {'behavior': 'allow', 'downloadPath': DOWNLOAD_DIR})
    
    # Navigate to sound-effects if not already there
    current_url = page.get('url', '')
    if 'sound-effects' not in current_url:
        print("Navigating to sound-effects...")
        client.send('Page.navigate', {'url': 'https://pixabay.com/sound-effects/'})
        time.sleep(3)
    
    # Get all download buttons
    download_buttons = client.eval('''(function() {
        const btns = document.querySelectorAll('[aria-label="Download"]');
        return btns.length;
    })()''')
    
    print(f"Found {download_buttons or 0} download buttons")
    
    if not download_buttons or download_buttons < 10:
        print("Warning: Less than 10 buttons found")
    
    # Download 10 files
    num_to_download = 10
    results = []
    total_start = time.time()
    
    for i in range(num_to_download):
        click_start = time.time()
        print(f"\n[{i+1}/{num_to_download}] Clicking download...", end=" ", flush=True)
        
        # Click download button by index
        clicked = client.eval(f'''(function() {{
            const btns = document.querySelectorAll('[aria-label="Download"]');
            if (btns.length > {i}) {{
                let el = btns[{i}];
                while (el && el.tagName !== 'BUTTON' && el.tagName !== 'A' && el.parentElement) {{
                    if (el.onclick || el.getAttribute('role') === 'button') break;
                    el = el.parentElement;
                }}
                el.click();
                return true;
            }}
            return false;
        }})()''')
        
        if not clicked:
            print(f"✗ Click failed")
            results.append({'index': i+1, 'success': False, 'error': 'click failed'})
            continue
        
        # Wait for download with polling
        downloaded_file = None
        for attempt in range(10):
            time.sleep(0.5)
            recent = get_recent_files(5)
            new_files = [f for f in recent if f[0] not in initial_files]
            if new_files:
                downloaded_file = new_files[-1]
                break
        
        click_time = time.time() - click_start
        
        if downloaded_file:
            fname, size, _ = downloaded_file
            print(f"✓ {fname} ({size:,} bytes) in {click_time:.2f}s")
            results.append({
                'index': i+1,
                'success': True,
                'file': fname,
                'size': size,
                'time': click_time
            })
            initial_files.add(fname)
        else:
            print(f"✗ Timeout ({click_time:.2f}s)")
            results.append({'index': i+1, 'success': False, 'error': 'timeout', 'time': click_time})
    
    total_time = time.time() - total_start
    
    # Summary
    print("\n" + "=" * 60)
    print("RESULTS")
    print("=" * 60)
    
    successful = [r for r in results if r['success']]
    failed = [r for r in results if not r['success']]
    
    print(f"Successful: {len(successful)}/{num_to_download}")
    print(f"Failed: {len(failed)}/{num_to_download}")
    print(f"Total time: {total_time:.2f} seconds")
    
    if successful:
        total_size = sum(r['size'] for r in successful)
        avg_time = total_time / len(successful)
        avg_size = total_size / len(successful)
        total_download_time = sum(r['time'] for r in successful)
        
        print(f"Total size: {total_size:,} bytes ({total_size/1024/1024:.2f} MB)")
        print(f"Average time per file: {avg_time:.2f} seconds")
        print(f"Total download time: {total_download_time:.2f} seconds")
        print(f"Average download time: {total_download_time/len(successful):.2f} seconds/file")
        print(f"Download speed: {total_size/total_download_time/1024:.1f} KB/s")
        
        # Per-file breakdown
        print("\nPer-file breakdown:")
        for r in successful:
            print(f"  #{r['index']}: {r['file'][:50]} - {r['size']/1024:.0f}KB in {r['time']:.2f}s")
    
    if failed:
        print("\nFailed downloads:")
        for r in failed:
            print(f"  - #{r['index']}: {r.get('error', 'unknown')} ({r.get('time', 0):.2f}s)")
    
    client.close()
    
    print("\n" + "=" * 60)

if __name__ == '__main__':
    main()
