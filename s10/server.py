"""Simple WSGI web app for Smart Contract Security.

Provides three endpoints:
- /datasets (GET): returns placeholder dataset list.
- /audit (POST): accepts JSON with 'source' field and forwards to MythX API.
- /monitor (GET): placeholder for future real‑time monitoring.

Runs using Python's built‑in wsgiref.simple_server.
"""

import json
import os
from wsgiref.simple_server import make_server
from urllib.parse import parse_qs
import sys

# Helper to send JSON response
def json_response(start_response, status, data):
    response_body = json.dumps(data).encode('utf-8')
    headers = [('Content-Type', 'application/json'), ('Content-Length', str(len(response_body)))]
    start_response(status, headers)
    return [response_body]

def not_found(start_response):
    return json_response(start_response, '404 Not Found', {'error': 'Endpoint not found'})

def method_not_allowed(start_response, allowed):
    headers = [('Allow', allowed)]
    start_response('405 Method Not Allowed', headers)
    return [b'']

def handle_datasets(environ, start_response):
    if environ['REQUEST_METHOD'] != 'GET':
        return method_not_allowed(start_response, 'GET')
    sample = {
        'datasets': [
            {'name': 'Etherscan verified contracts', 'source': 'https://etherscan.io/contractsVerified'},
            {'name': 'OpenZeppelin contracts', 'source': 'https://github.com/OpenZeppelin/openzeppelin-contracts'}
        ]
    }
    return json_response(start_response, '200 OK', sample)

def handle_audit(environ, start_response):
    if environ['REQUEST_METHOD'] != 'POST':
        return method_not_allowed(start_response, 'POST')
    try:
        request_body_size = int(environ.get('CONTENT_LENGTH', 0))
    except (ValueError, TypeError):
        request_body_size = 0
    request_body = environ['wsgi.input'].read(request_body_size)
    try:
        data = json.loads(request_body.decode('utf-8')) if request_body else {}
    except json.JSONDecodeError:
        return json_response(start_response, '400 Bad Request', {'error': 'Invalid JSON'})
    source = data.get('source')
    if not source:
        return json_response(start_response, '400 Bad Request', {'error': 'Contract source code required'})
    api_key = os.getenv('MYTHX_API_KEY')
    if not api_key:
        return json_response(start_response, '500 Internal Server Error', {'error': 'MythX API key not configured'})
    # Perform a simple POST to MythX (placeholder). Use urllib.request from stdlib.
    import urllib.request
    try:
        req = urllib.request.Request(
            url='https://api.mythx.io/v1/analyses',
            data=json.dumps({'source': source}).encode('utf-8'),
            headers={
                'Content-Type': 'application/json',
                'Authorization': f'Bearer {api_key}'
            },
            method='POST'
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            resp_data = resp.read()
            resp_json = json.loads(resp_data.decode('utf-8'))
            return json_response(start_response, '200 OK', resp_json)
    except Exception as e:
        return json_response(start_response, '500 Internal Server Error', {'error': str(e)})

def handle_monitor(environ, start_response):
    if environ['REQUEST_METHOD'] != 'GET':
        return method_not_allowed(start_response, 'GET')
    return json_response(start_response, '200 OK', {'status': 'monitoring not implemented yet'})

# Dispatcher
def application(environ, start_response):
    path = environ.get('PATH_INFO', '')
    if path == '/datasets':
        return handle_datasets(environ, start_response)
    elif path == '/audit':
        return handle_audit(environ, start_response)
    elif path == '/monitor':
        return handle_monitor(environ, start_response)
    else:
        return not_found(start_response)

if __name__ == '__main__':
    port = int(os.getenv('PORT', '5000'))
    host = '0.0.0.0'
    print(f'Serving on http://{host}:{port}')
    httpd = make_server(host, port, application)
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print('Server stopped')
        sys.exit(0)
