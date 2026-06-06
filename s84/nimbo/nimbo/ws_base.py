import asyncio


class WSConnection:
    """Abstract interface for a WebSocket connection.

    Both the native (built-in) and library-based backends implement this.
    """
    def __init__(self, reader, writer):
        self.reader = reader
        self.writer = writer
        self.closed = False

    async def send(self, data):
        raise NotImplementedError

    async def recv(self):
        raise NotImplementedError

    async def close(self):
        raise NotImplementedError


class WSManager:
    """Topic-based pub/sub manager for WebSocket connections.

    Works with any WSConnection that has send() and closed.
    """
    def __init__(self):
        self._topics = {}

    def add(self, ws, topic=""):
        if topic not in self._topics:
            self._topics[topic] = set()
        self._topics[topic].add(ws)

    def remove(self, ws, topic=""):
        self._topics.get(topic, set()).discard(ws)
        if topic and not self._topics.get(topic):
            self._topics.pop(topic, None)

    def remove_all(self, ws):
        for topic in list(self._topics.keys()):
            self._topics[topic].discard(ws)
            if not self._topics[topic]:
                self._topics.pop(topic, None)

    async def broadcast(self, data, topic=""):
        for ws in list(self._topics.get(topic, set())):
            if ws.closed:
                self._topics[topic].discard(ws)
                continue
            await ws.send(data)
