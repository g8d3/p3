#!/usr/bin/env python3
"""
Download sound effect from pixabay using CDP directly
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
        """Evaluate JavaScript and return result"""
        result = self.send('Runtime.evaluate', {'expression': js, 'returnByValue': True})
        if result and 'result' in result:
            return result['result'].get('value')
        return None
    
    def close(self):
        self.ws.close()

def main():
    # Get page target
    print("Getting browser targets...")
    resp = requests.get(f'http://localhost:{CDP_PORT}/json')
    targets = resp.json()
    
    # Find the pixabay page
    page = next((t for t in targets if 'pixabay' in t.get('url', '').lower()), None)
    if not page:
        page = next((t for t in targets if t['type'] == 'page'), None)
    
    if not page:
        print("No page found!")
        return
    
    print(f"Connected to: {page['title']}")
    print(f"URL: {page['url']}")
    
    client = CDPClient(page['webSocketDebuggerUrl'])
    
    # Enable domains
    print("\nEnabling CDP domains...")
    client.send('Page.enable')
    client.send('Runtime.enable')
    client.send('DOM.enable')
    
    # Set download behavior
    print("Setting download behavior...")
    client.send('Page.setDownloadBehavior', {'behavior': 'allow', 'downloadPath': DOWNLOAD_DIR})
    
    # Find and click download button using JavaScript
    print("\nFinding download button...")
    
    # First, let's see what buttons are available
    buttons_info = client.eval('''
        Array.from(document.querySelectorAll('button')).slice(0, 20).map(b => ({
            text: b.innerText.trim().substring(0, 30),
            aria: b.getAttribute('aria-label') || '',
            class: b.className.substring(0, 50)
        }))
    ''')
    
    print("Available buttons:")
    for i, btn in enumerate(buttons_info or []):
        print(f"  {i}: {btn}")
    
    # Find download button
    download_result = client.eval('''
        (function() {
            const buttons = document.querySelectorAll('button');
            for (let btn of buttons) {
                const text = btn.innerText.toLowerCase();
                const aria = (btn.getAttribute('aria-label') || '').toLowerCase();
                if (text.includes('download') || aria.includes('download')) {
                    return {
                        found: true,
                        text: btn.innerText,
                        selector: btn.tagName + (btn.className ? '.' + btn.className.split(' ')[0] : '')
                    };
                }
            }
            return {found: false};
        })()
    ''')
    
    print(f"\nDownload button search result: {download_result}")
    
    if download_result and download_result.get('found'):
        # Click the download button
        print("Clicking download button...")
        clicked = client.eval('''
            (function() {
                const buttons = document.querySelectorAll('button');
                for (let btn of buttons) {
                    const text = btn.innerText.toLowerCase();
                    const aria = (btn.getAttribute('aria-label') || '').toLowerCase();
                    if (text.includes('download') || aria.includes('download')) {
                        btn.click();
                        return true;
                    }
                }
                return false;
            })()
        ''')
        print(f"Clicked: {clicked}")
        
        # Wait for download
        print("Waiting for download...")
        time.sleep(5)
        
        # Check for new files
        print("\nRecent files in Downloads:")
        result = subprocess.run(['ls', '-lt', DOWNLOAD_DIR], capture_output=True, text=True)
        print(result.stdout[:800])
        
        # Find and play recent audio
        files = sorted(os.listdir(DOWNLOAD_DIR), 
                      key=lambda f: os.path.getmtime(os.path.join(DOWNLOAD_DIR, f)),
                      reverse=True)
        
        found_audio = False
        for f in files[:5]:
            if f.endswith(('.mp3', '.wav', '.ogg')):
                filepath = os.path.join(DOWNLOAD_DIR, f)
                mtime = os.path.getmtime(filepath)
                age = time.time() - mtime
                print(f"\nFound audio: {f}")
                print(f"  Path: {filepath}")
                print(f"  Size: {os.path.getsize(filepath)} bytes")
                print(f"  Age: {age:.1f} seconds")
                
                if age < 120:  # Downloaded in last 2 minutes
                    print("\nPlaying...")
                    subprocess.run(['ffplay', '-nodisp', '-autoexit', filepath])
                    found_audio = True
                    break
        
        if not found_audio:
            print("\nNo recent audio files found")
    else:
        print("Download button not found, trying alternative approach...")
        
        # Try clicking first visible button with "Download" in any attribute
        client.eval('''
            (function() {
                const allElements = document.querySelectorAll('*');
                for (let el of allElements) {
                    if (el.tagName === 'BUTTON' || el.tagName === 'A') {
                        const html = el.outerHTML.toLowerCase();
                        if (html.includes('download')) {
                            el.click();
                            return 'Clicked: ' + el.tagName + ' - ' + (el.innerText || el.textContent).substring(0, 50);
                        }
                    }
                }
                return 'Nothing found';
            })()
        ''')
    
    client.close()

if __name__ == '__main__':
    main()
