"""A loopback JSON-lines server over the protocol. Off unless you start it.

Deliberately small and deliberately local:

- it binds **127.0.0.1 only**, never a routable address;
- it requires a token, minted per session and printed once at start;
- it speaks one JSON object per line, and answers one per line — and a line
  is at most `checks.MAX_LINE` bytes, where it was as long as the sender
  liked and read whole into memory before anything looked at it;
- it holds the `Game` on its own thread and serialises every command, so two
  seats cannot interleave halfway through a jump.

That is enough to drive a chronicle from outside, to let an agent hold a
character, and to seat a second captain — without opening anything to a
network. There is no discovery, no broadcast and no unauthenticated verb.
"""

from __future__ import annotations

import json
import secrets
import socket
import threading

from .checks import MAX_LINE
from .protocol import describe, dispatch, snapshot


def _no_constant(name: str):
    """`json.loads` reads `NaN` and `Infinity` as numbers unless told not to,
    and a `NaN` that is let in is a `NaN` in the purse. Refused at parse."""
    raise ValueError(f"{name} is not a number JSON allows")

HOST = "127.0.0.1"
#: 0 asks the OS for a free port, which is what you want by default.
PORT = 0


class Bridge:
    """A running game with a socket in front of it."""

    def __init__(self, game, host: str = HOST, port: int = PORT,
                 token: str = ""):
        self.game = game
        self.token = token or secrets.token_hex(8)
        self.lock = threading.Lock()
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.sock.bind((host, port))
        self.sock.listen(4)
        self.host, self.port = self.sock.getsockname()
        self.running = False
        self._thread = None
        self.seats: dict = {}

    # ── lifecycle ──────────────────────────────────────────────────────────

    def start(self) -> "Bridge":
        self.running = True
        self._thread = threading.Thread(target=self._serve, daemon=True)
        self._thread.start()
        return self

    def stop(self) -> None:
        self.running = False
        try:
            self.sock.close()
        except OSError:
            pass

    def address(self) -> dict:
        return {"host": self.host, "port": self.port, "token": self.token}

    # ── serving ────────────────────────────────────────────────────────────

    def _serve(self) -> None:
        while self.running:
            try:
                conn, _who = self.sock.accept()
            except OSError:
                return
            threading.Thread(target=self._talk, args=(conn,),
                             daemon=True).start()

    def _talk(self, conn) -> None:
        # A caller that resets mid-conversation used to raise out of this
        # thread (on the buffered stream's flush at close) as an uncaught
        # exception. The far end going away ends the conversation, quietly.
        try:
            self._converse(conn)
        except OSError:
            pass

    def _converse(self, conn) -> None:
        with conn, conn.makefile("rwb") as stream:
            while self.running:
                try:
                    raw = stream.readline(MAX_LINE + 1)
                except (OSError, ValueError):
                    return
                # Asked again after the read, not only before it: a line that
                # was already blocked in `readline` when the bridge stopped
                # would otherwise be served — one command past the stop.
                if not raw or not self.running:
                    return
                if len(raw) > MAX_LINE and not raw.endswith(b"\n"):
                    # Read the rest of the line and throw it away, a bounded
                    # chunk at a time, so the next line is a command again.
                    # Hanging up instead would close a socket with unread
                    # bytes in it, which is a reset — and a reset can take
                    # the refusal down with it before the caller reads it.
                    if not self._skip_line(stream):
                        return
                    reply = {"ok": False,
                             "why": f"A line is at most {MAX_LINE:,} bytes."}
                else:
                    reply = self.handle_line(raw.decode("utf-8", "replace"))
                try:
                    body = json.dumps(reply)
                except (TypeError, ValueError) as err:
                    # Never let a reply kill the connection. The first version
                    # did exactly that: a survey result carried a Lifeform,
                    # json.dumps raised in this thread, and the caller was left
                    # reading an empty line with nothing to go on.
                    body = json.dumps({"ok": False,
                                       "why": f"reply not serialisable: {err}"})
                try:
                    stream.write((body + "\n").encode())
                    stream.flush()
                except (BrokenPipeError, OSError):
                    return
                if reply.get("closed"):
                    return

    @staticmethod
    def _skip_line(stream) -> bool:
        """Discard up to the end of the current line. False at end of file."""
        while True:
            try:
                chunk = stream.readline(MAX_LINE + 1)
            except (OSError, ValueError):
                return False
            if not chunk:
                return False
            if chunk.endswith(b"\n"):
                return True

    def handle_line(self, line: str) -> dict:
        """One line in, one reply out. Exposed so the suite can skip sockets."""
        if len(line.rstrip("\r\n")) > MAX_LINE:
            return {"ok": False, "why": f"A line is at most {MAX_LINE:,} bytes."}
        line = line.strip()
        if not line:
            return {"ok": False, "why": "Empty."}
        try:
            command = json.loads(line, parse_constant=_no_constant)
        except (ValueError, RecursionError) as err:
            # `JSONDecodeError` is a `ValueError`; so is a refused NaN. A
            # line of 60,000 open brackets is a `RecursionError`.
            return {"ok": False, "why": f"Not JSON: {err}"}
        return self.handle(command)

    def handle(self, command: dict) -> dict:
        if not isinstance(command, dict):
            return {"ok": False, "why": "A command is an object."}
        token = command.get("token")
        if not isinstance(token, str) or not secrets.compare_digest(
                token.encode(), self.token.encode()):
            return {"ok": False, "why": "Bad or missing token."}

        verb = command.get("verb")
        if verb == "verbs":
            return {"ok": True, "verbs": describe()}
        if verb == "snapshot":
            with self.lock:
                return {"ok": True, "snapshot": snapshot(self.game)}
        if verb == "seat":
            return self._seat(command)
        if verb == "bye":
            return {"ok": True, "closed": True}
        with self.lock:
            return dispatch(self.game, command)

    # ── seats ──────────────────────────────────────────────────────────────

    def _seat(self, command: dict) -> dict:
        """Claim or release a seat: a named role an outside caller speaks for.

        A seat is how a second captain joins and how an agent holds a rival.
        Claiming one is a declaration, not a lock on the game — the autonomous
        driver keeps playing an unclaimed seat, which is what makes somebody
        stepping away survivable.
        """
        args = command.get("args") or {}
        if not isinstance(args, dict):
            return {"ok": False, "why": "args is an object of named arguments."}
        name = str(args.get("name") or "").strip()[:80]
        if not name:
            return {"ok": True, "seats": self.seats}
        if args.get("release"):
            self.seats.pop(name, None)
            return {"ok": True, "released": name, "seats": self.seats}
        self.seats[name] = {"held_by": str(args.get("by") or "agent")[:80],
                            "since": self.game.day}
        return {"ok": True, "claimed": name, "seats": self.seats}


def serve(game, host: str = HOST, port: int = PORT) -> Bridge:
    """Start a bridge and tell the caller where it is."""
    bridge = Bridge(game, host, port).start()
    return bridge
