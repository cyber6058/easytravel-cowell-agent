from __future__ import annotations

import base64
import json
import os
import socket
import struct
import urllib.error
import urllib.request
from dataclasses import dataclass

from ...errors import SourceUnavailableError


CDP_HTTP = "http://127.0.0.1:9333"


@dataclass(frozen=True, slots=True)
class ImportedSession:
    cookies: dict[str, str]


def import_cdp_session(
    *,
    cdp_http: str = CDP_HTTP,
    domain_match: str = "voyage.com.tw",
) -> ImportedSession:
    socket_connection = None
    try:
        socket_connection = _connect(_ws_url(cdp_http))
        _send(socket_connection, {"id": 1, "method": "Storage.getCookies", "params": {}})
        for _ in range(50):
            message = json.loads(_recv(socket_connection))
            if message.get("id") == 1:
                cookies = {
                    cookie["name"]: cookie["value"]
                    for cookie in message["result"]["cookies"]
                    if domain_match in cookie.get("domain", "")
                }
                return ImportedSession(cookies=cookies)
    except (OSError, urllib.error.URLError, ValueError, KeyError, json.JSONDecodeError) as error:
        raise SourceUnavailableError(
            "SOURCE_UNAVAILABLE",
            "Controlled Cowell Chrome is unavailable; start it and log in, then retry",
        ) from error
    finally:
        if socket_connection is not None:
            socket_connection.close()
    return ImportedSession(cookies={})


def _ws_url(cdp_http: str) -> str:
    with urllib.request.urlopen(cdp_http.rstrip("/") + "/json/version", timeout=5) as response:
        return json.load(response)["webSocketDebuggerUrl"]


def _connect(url: str) -> socket.socket:
    if not url.startswith("ws://"):
        raise ValueError("CDP websocket URL must start with ws://")
    hostport, path = url[5:].split("/", 1)
    host, port = hostport.split(":")
    connection = socket.create_connection((host, int(port)), timeout=10)
    key = base64.b64encode(os.urandom(16)).decode()
    request = (
        f"GET /{path} HTTP/1.1\r\n"
        f"Host: {host}:{port}\r\n"
        "Upgrade: websocket\r\nConnection: Upgrade\r\n"
        f"Sec-WebSocket-Key: {key}\r\nSec-WebSocket-Version: 13\r\n\r\n"
    )
    connection.sendall(request.encode())
    response = b""
    while b"\r\n\r\n" not in response:
        response += connection.recv(1)
    if b"101" not in response:
        raise ConnectionError(f"CDP websocket upgrade failed: {response[:80]!r}")
    return connection


def _send(connection: socket.socket, obj: object) -> None:
    payload = json.dumps(obj).encode()
    header = bytearray([0x81])
    length = len(payload)
    mask = os.urandom(4)
    if length < 126:
        header.append(0x80 | length)
    elif length < 65536:
        header += bytes([0x80 | 126]) + struct.pack(">H", length)
    else:
        header += bytes([0x80 | 127]) + struct.pack(">Q", length)
    header += mask
    masked = bytes(byte ^ mask[index % 4] for index, byte in enumerate(payload))
    connection.sendall(bytes(header) + masked)


def _recv(connection: socket.socket) -> bytes:
    def read_exactly(length: int) -> bytes:
        buffer = b""
        while len(buffer) < length:
            buffer += connection.recv(length - len(buffer))
        return buffer

    header = read_exactly(2)
    length = header[1] & 0x7F
    if length == 126:
        length = struct.unpack(">H", read_exactly(2))[0]
    elif length == 127:
        length = struct.unpack(">Q", read_exactly(8))[0]
    return read_exactly(length)
