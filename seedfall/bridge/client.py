"""Enough of a client to drive a bridge from a script or another process."""

from __future__ import annotations

import json
import socket


class Client:
    def __init__(self, host: str, port: int, token: str, timeout: float = 10):
        self.sock = socket.create_connection((host, port), timeout=timeout)
        self.stream = self.sock.makefile("rwb")
        self.token = token

    def send(self, verb: str, **args) -> dict:
        payload = {"verb": verb, "token": self.token}
        if args:
            payload["args"] = args
        self.stream.write((json.dumps(payload) + "\n").encode())
        self.stream.flush()
        line = self.stream.readline()
        if not line:
            return {"ok": False, "why": "The bridge closed."}
        try:
            return json.loads(line.decode())
        except json.JSONDecodeError as err:
            return {"ok": False, "why": f"unreadable reply: {err}"}

    def close(self) -> None:
        try:
            self.send("bye")
        except (OSError, ValueError):
            pass
        try:
            self.stream.close()
        except OSError:
            pass
        try:
            self.sock.close()
        except OSError:
            pass

    def __enter__(self):
        return self

    def __exit__(self, *_exc):
        self.close()
        return False
