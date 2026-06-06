"""WebSocket backend using the `websockets` library.

Starts websockets.serve() alongside the HTTP server on a separate port.
The HTTP server redirects WebSocket upgrade requests to the WS port,
or can be configured to handle both.
"""
import asyncio
import json
import os

import websockets
import websockets.server as ws_srv

from .ws_base import WSConnection


class WebsocketLibWSConnection(WSConnection):
    """Wraps a websockets library connection to match WSConnection interface."""
    def __init__(self, lib_ws):
        self._ws = lib_ws
        self.closed = False
        # reader/writer not used in this backend
        self.reader = None
        self.writer = None

    async def send(self, data):
        if self.closed:
            return
        try:
            if isinstance(data, str):
                await self._ws.send(data)
            else:
                await self._ws.send(data)
        except websockets.exceptions.ConnectionClosed:
            self.closed = True

    async def recv(self):
        if self.closed:
            return None
        try:
            msg = await asyncio.wait_for(self._ws.recv(), timeout=0.1)
            return msg
        except asyncio.TimeoutError:
            return None
        except websockets.exceptions.ConnectionClosed:
            self.closed = True
            return None

    async def close(self):
        self.closed = True
        try:
            await self._ws.close()
        except Exception:
            pass


class WebsocketsBackend:
    """Backend that uses the websockets library."""
    name = "websockets"

    def __init__(self, app):
        self.app = app
        self._server = None
        self._ws_port = None

    async def _keep_alive(self, ws, lib_ws):
        """Keep connection alive for idle WS (no registered handler)."""
        try:
            async for _ in lib_ws:
                pass
        except websockets.exceptions.ConnectionClosed:
            pass
        ws.closed = True

    async def handler(self, lib_ws):
        ws = WebsocketLibWSConnection(lib_ws)
        path = lib_ws.path
        if path == "/__nimbo/livereload":
            self.app._ws_manager.add(ws, "__nimbo_livereload")
            await ws.send(json.dumps({"type":"version","v":self.app._restart_count}))
            await self._keep_alive(ws, lib_ws)
            return
        for topic, handler in self.app._ws_handlers.items():
            self.app._ws_manager.add(ws, topic)
            await handler(ws)
            return
        self.app._ws_manager.add(ws)
        await self._keep_alive(ws, lib_ws)

    async def start(self, host, port):
        self._ws_port = port + 1
        self._server = await ws_srv.serve(
            self.handler, host, self._ws_port,
            ping_interval=60, ping_timeout=30
        )
        return self._ws_port

    @property
    def ws_port(self):
        return self._ws_port

    async def close(self):
        if self._server:
            self._server.close()
            await self._server.wait_closed()
