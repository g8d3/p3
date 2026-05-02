#!/usr/bin/env python3
"""Gemini API caller — handles JSON safely without bash variable mangling.

Usage: _gemini_call.py <model> <prompt_text> <output_file>
"""
import json, sys, os, urllib.request

model = sys.argv[1]
prompt = sys.argv[2]
outfile = sys.argv[3]

api_key = os.environ.get('GEMINI_API_KEY') or os.environ.get('GOOGLE_API_KEY', '')
if not api_key:
    with open(outfile, 'w') as f:
        json.dump({'error': 'no API key'}, f)
    sys.exit(1)

payload = json.dumps({
    'contents': [{'parts': [{'text': prompt}]}]
}).encode('utf-8')

url = f'https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}'
req = urllib.request.Request(url, data=payload, headers={'Content-Type': 'application/json'})

try:
    resp = urllib.request.urlopen(req)
    data = json.loads(resp.read())
    text = data['candidates'][0]['content']['parts'][0]['text'].strip()
    # Extract JSON from markdown code blocks if present
    if '```json' in text:
        text = text.split('```json')[1].split('```')[0].strip()
    elif '```' in text:
        text = text.split('```')[1].split('```')[0].strip()
    result = json.loads(text)
    with open(outfile, 'w') as f:
        json.dump(result, f, indent=2)
except Exception as e:
    with open(outfile, 'w') as f:
        json.dump({'error': str(e), 'raw': text[:500] if 'text' in dir() else 'parse failed'}, f)
