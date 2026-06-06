import hashlib
import base64
import struct
import asyncio

from .ws_base import WSConnection

MAGIC = b"258EAFA5-E914-47DA-95CA-5AB5DC96C2A5"
OP_CONT = 0x0
OP_TEXT = 0x1
OP_BIN = 0x2
OP_CLOSE = 0x8
OP_PING = 0x9
OP_PONG = 0xA


def accept_key(key):
    sha1 = hashlib.sha1(key.encode() + MAGIC).digest()
    return base64.b64encode(sha1).decode()


def encode_frame(data, opcode=OP_TEXT):
    if isinstance(data, str):
        data = data.encode("utf-8")
    frame = bytearray()
    frame.append(0x80 | opcode)
    length = len(data)
    if length < 126:
        frame.append(length)
    elif length < 65536:
        frame.append(126)
        frame.extend(struct.pack(">H", length))
    else:
        frame.append(127)
        frame.extend(struct.pack(">Q", length))
    frame.extend(data)
    return bytes(frame)


def decode_frame(data):
    if len(data) < 2:
        return None, data
    b1, b2 = data[0], data[1]
    opcode = b1 & 0x0F
    masked = (b2 & 0x80) != 0
    length = b2 & 0x7F
    offset = 2
    if length == 126:
        if len(data) < 4: return None, data
        length = struct.unpack(">H", data[2:4])[0]
        offset = 4
    elif length == 127:
        if len(data) < 10: return None, data
        length = struct.unpack(">Q", data[2:10])[0]
        offset = 10
    if masked:
        if len(data) < offset + 4: return None, data
        mask = data[offset:offset + 4]
        offset += 4
    if len(data) < offset + length:
        return None, data
    payload = data[offset:offset + length]
    if masked:
        payload = bytes(b ^ mask[i % 4] for i, b in enumerate(payload))
    remaining = data[offset + length:]
    if opcode == OP_CLOSE:
        return ("__close__",), remaining
    if opcode == OP_PING:
        return ("__ping__", payload), remaining
    if opcode == OP_PONG:
        return ("__pong__",), remaining
    try:
        return (opcode, payload.decode("utf-8")), remaining
    except UnicodeDecodeError:
        return (opcode, payload), remaining


class NativeWSConnection(WSConnection):
    def __init__(self, reader, writer):
        super().__init__(reader, writer)
        self._buf = b""

    async def send(self, data):
        if self.closed:
            return
        frame = encode_frame(data)
        try:
            self.writer.write(frame)
            await self.writer.drain()
        except (ConnectionError, BrokenPipeError):
            self.closed = True

    async def recv(self):
        while True:
            if self._buf:
                result, self._buf = decode_frame(self._buf)
            else:
                try:
                    chunk = await asyncio.wait_for(self.reader.read(4096), timeout=0.1)
                except asyncio.TimeoutError:
                    return None
                except (ConnectionError, BrokenPipeError):
                    self.closed = True
                    return None
                if not chunk:
                    self.closed = True
                    return None
                result, self._buf = decode_frame(chunk)
            if result is None:
                continue
            if result[0] == "__close__":
                self.closed = True
                try:
                    self.writer.write(encode_frame("", OP_CLOSE))
                    await self.writer.drain()
                except Exception:
                    pass
                return None
            if result[0] == "__ping__":
                try:
                    self.writer.write(encode_frame(result[1], OP_PONG))
                    await self.writer.drain()
                except Exception:
                    pass
                continue
            if result[0] == "__pong__":
                continue
            return result[1]

    async def close(self):
        self.closed = True
        try:
            self.writer.write(encode_frame("", OP_CLOSE))
            await self.writer.drain()
            self.writer.close()
        except Exception:
            pass
