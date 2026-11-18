"""极简 Chrome DevTools WebSocket 客户端（只用标准库，不需要 node）。"""
import socket, base64, os, json, struct
from urllib.parse import urlparse


class WS:
    def __init__(self, url, timeout=30):
        u = urlparse(url)
        host = u.hostname or "127.0.0.1"
        port = u.port or 80
        path = u.path + (("?" + u.query) if u.query else "")
        self.sock = socket.create_connection((host, port), timeout=timeout)
        self.sock.settimeout(timeout)
        key = base64.b64encode(os.urandom(16)).decode()
        req = (f"GET {path} HTTP/1.1\r\nHost: {host}:{port}\r\nUpgrade: websocket\r\n"
               f"Connection: Upgrade\r\nSec-WebSocket-Key: {key}\r\nSec-WebSocket-Version: 13\r\n\r\n")
        self.sock.sendall(req.encode())
        buf = b""
        while b"\r\n\r\n" not in buf:
            chunk = self.sock.recv(4096)
            if not chunk:
                raise ConnectionError("handshake failed")
            buf += chunk
        self.buf = buf.split(b"\r\n\r\n", 1)[1]
        self.next_id = 0

    def _read(self, n):
        while len(self.buf) < n:
            chunk = self.sock.recv(65536)
            if not chunk:
                raise ConnectionError("socket closed")
            self.buf += chunk
        out, self.buf = self.buf[:n], self.buf[n:]
        return out

    def send(self, obj):
        data = json.dumps(obj).encode()
        header = b"\x81"
        n = len(data)
        mask = os.urandom(4)
        if n < 126:
            header += bytes([0x80 | n])
        elif n < 65536:
            header += bytes([0x80 | 126]) + struct.pack(">H", n)
        else:
            header += bytes([0x80 | 127]) + struct.pack(">Q", n)
        masked = bytes(b ^ mask[i % 4] for i, b in enumerate(data))
        self.sock.sendall(header + mask + masked)

    def recv(self):
        payload = b""
        while True:
            b1, b2 = self._read(2)
            opcode = b1 & 0x0F
            fin = b1 & 0x80
            length = b2 & 0x7F
            if length == 126:
                length = struct.unpack(">H", self._read(2))[0]
            elif length == 127:
                length = struct.unpack(">Q", self._read(8))[0]
            data = self._read(length)
            if opcode == 8:
                raise ConnectionError("closed by peer")
            if opcode == 9:
                continue
            payload += data
            if fin:
                return payload.decode("utf-8", "replace")

    def call(self, method, params=None, timeout_ms=60000):
        self.next_id += 1
        mid = self.next_id
        self.send({"id": mid, "method": method, "params": params or {}})
        while True:
            msg = json.loads(self.recv())
            if msg.get("id") == mid:
                if "error" in msg:
                    raise RuntimeError(str(msg["error"]))
                return msg.get("result", {})

    def close(self):
        try:
            self.sock.close()
        except Exception:
            pass
