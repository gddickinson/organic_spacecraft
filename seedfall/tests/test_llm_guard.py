"""The optional model cannot hang the game, crash it, or reach out unasked.

Review 2026-09-17 (#31), measured against an endpoint that accepted a
connection and never answered: `voice.speak` blocked for 12 s, and then 12 s
again on the next line, with no backoff — called from the comms window, on
the window's own thread. And `llm.complete`, which promises "a string or
None", raised `AttributeError` on `{"response": null}` and on a reply that
was a JSON list.

Every check here talks only to a server it starts itself on 127.0.0.1, or to
a socket it binds and never answers. The deadlines and cool-offs are shrunk
for the duration so the whole suite takes a few seconds, and everything —
environment, module settings, the breaker — is put back afterwards.
"""

from __future__ import annotations

import json
import os
import socket
import threading
import time
from contextlib import contextmanager
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from ..core import llm
from ..core.state import new_game
from ..sim import hail as hail_sim
from ..sim import track as track_sim
from ..sim import voice as voice_sim
from .harness import Suite

#: Shrunk for the checks: the real values are 12 s, 60 s and 600 s.
FAST = {"DEADLINE": 0.6, "TIMEOUT": 0.6, "COOL_OFF": 0.4, "COOL_OFF_MAX": 2.0}

_ENV = ("SEEDFALL_LLM", "OLLAMA_HOST", "SEEDFALL_LLM_PROVIDER",
        "SEEDFALL_LLM_MODEL", "OPENAI_API_KEY", "OPENAI_BASE_URL",
        "ANTHROPIC_API_KEY")


class _Server:
    """A loopback model that answers every POST with `body`, or never."""

    def __init__(self, body: bytes = b"", hang: bool = False):
        self.body, self.hang = body, hang
        self.gets = self.posts = 0
        self.released = threading.Event()
        owner = self

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *_a):
                pass

            def do_GET(self):
                owner.gets += 1
                self._send(b'{"models": []}')

            def do_POST(self):
                owner.posts += 1
                self.rfile.read(int(self.headers.get("Content-Length", 0)))
                if owner.hang:
                    owner.released.wait(10)
                    return
                self._send(owner.body)

            def _send(self, data: bytes):
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(data)))
                self.end_headers()
                self.wfile.write(data)

        self.httpd = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        self.httpd.daemon_threads = True
        self.port = self.httpd.server_address[1]
        threading.Thread(target=self.httpd.serve_forever, daemon=True).start()

    @property
    def requests(self) -> int:
        return self.gets + self.posts

    def close(self) -> None:
        self.released.set()
        self.httpd.shutdown()
        self.httpd.server_close()


@contextmanager
def _speech(port: int | None, *, permitted: bool = True, **env):
    """Point the game's model at a loopback port, fast, and put it all back."""
    saved_env = {k: os.environ.get(k) for k in _ENV}
    saved = {k: getattr(llm, k) for k in FAST}
    try:
        for k in _ENV:
            os.environ.pop(k, None)
        if permitted:
            os.environ["SEEDFALL_LLM"] = "1"
        if port is not None:
            os.environ["OLLAMA_HOST"] = f"http://127.0.0.1:{port}"
        os.environ.update(env)
        for k, v in FAST.items():
            setattr(llm, k, v)
        llm.forget()
        yield
    finally:
        for k, v in saved_env.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v
        for k, v in saved.items():
            setattr(llm, k, v)
        llm.forget()


def _timed(fn):
    t0 = time.monotonic()
    out = fn()
    return out, time.monotonic() - t0


def run(suite: Suite) -> None:
    check = suite.check

    @check("nothing reaches for a model unless SEEDFALL_LLM is set")
    def _():
        server = _Server(b'{"response": "Anyone there?"}')
        try:
            with _speech(server.port, permitted=False):
                # The options screen's switch, thrown: speech is *wanted*, and
                # without the environment's permission nothing is asked.
                llm.configure(enabled=True)
                assert llm.switched_on() and not llm.permitted()
                assert not llm.may_ask(), "a window would have asked"
                assert not llm.enabled()
                assert llm.complete("hello") is None
                assert not any(o["answering"] for o in llm.offer())
                game = new_game("hush")
                said = voice_sim.speak(game, "probe", name="Probe")
                assert said["source"] == "written", said
                for contact in track_sim.contacts(game):
                    hail_sim.greeting(game, contact)
                assert "SEEDFALL_LLM" in llm.describe(), llm.describe()
            assert server.requests == 0, (
                f"{server.requests} request(s) reached a model with "
                "SEEDFALL_LLM unset")
        finally:
            server.close()
        return "switch thrown, every door knocked on: no request arrived"

    @check("a malformed reply is None, never an exception")
    def _():
        bad_ollama = [b'{"response": null}', b"[]", b'"words"', b"null",
                      b'{"response": 7}', b"{", b"", b'{"response": "  "}',
                      b'{"reply": "wrong key"}']
        bad_openai = [b'{"choices": [null]}', b'{"choices": null}',
                      b'{"choices": [{"message": null}]}',
                      b'{"choices": [{"message": {"content": null}}]}',
                      b'{"choices": "none"}', b"[1, 2]"]
        tried = 0
        for bodies, env in ((bad_ollama, {}),
                            (bad_openai, {"SEEDFALL_LLM_PROVIDER": "openai",
                                          "OPENAI_API_KEY": "test"})):
            for body in bodies:
                server = _Server(body)
                try:
                    extra = dict(env)
                    if "OPENAI_API_KEY" in extra:
                        extra["OPENAI_BASE_URL"] = \
                            f"http://127.0.0.1:{server.port}/v1"
                    with _speech(server.port, **extra):
                        got = llm.complete("say something")
                        assert got is None, f"{body!r} gave {got!r}"
                        assert server.posts == 1, (body, server.posts)
                        assert llm.cooling(), f"{body!r} left the breaker shut"
                        tried += 1
                finally:
                    server.close()
        # The provider we cannot point at a loopback, read directly.
        for data in ({"content": None}, {"content": [None, 5, {"text": None}]},
                     {"content": "text"}, [], None, "x"):
            assert llm._text("anthropic", data) is None, data
        assert llm._text("anthropic", {"content": [{"text": " Hi. "}]}) == "Hi."
        # And the harness can tell a good reply from a bad one.
        server = _Server(json.dumps({"response": " Harbour here. "}).encode())
        try:
            with _speech(server.port):
                assert llm.complete("hi") == "Harbour here."
                assert not llm.cooling()
        finally:
            server.close()
        return f"{tried} malformed replies over the wire, every one None"

    @check("a dead endpoint costs one deadline, then nothing until it cools")
    def _():
        server = _Server(hang=True)
        try:
            with _speech(server.port):
                deadline = llm.DEADLINE
                got, first = _timed(lambda: llm.complete("hello?"))
                assert got is None
                assert first < deadline + 0.5, (
                    f"{first:.2f} s against a {deadline} s deadline")
                assert first >= deadline * 0.8, (
                    f"gave up in {first:.2f} s — before the deadline")
                got, again = _timed(lambda: llm.complete("hello?"))
                assert got is None and again < 0.05, again
                assert server.posts == 1, "the breaker let a second ask out"
                # The headline case: the voice itself, twice.
                game = new_game("dead-air")
                _said, speak1 = _timed(lambda: voice_sim.speak(game, "a"))
                _said, speak2 = _timed(lambda: voice_sim.speak(game, "b"))
                assert speak1 < 0.05 and speak2 < 0.05, (speak1, speak2)
                time.sleep(llm.COOL_OFF + 0.05)
                got, third = _timed(lambda: llm.complete("hello?"))
                assert server.posts == 2 and third >= deadline * 0.8, (
                    server.posts, third)
                assert llm._breaker["fails"] == 2
                # Doubled: still shut after the first cool-off has passed.
                time.sleep(llm.COOL_OFF + 0.05)
                assert llm.cooling(), "the second failure did not back off"
        finally:
            server.close()
        return (f"{first:.2f} s once, then {again * 1000:.1f} ms, and two "
                f"voices in {(speak1 + speak2) * 1000:.1f} ms")

    @check("a socket that listens and never answers is nothing, quickly")
    def _():
        dead = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        dead.bind(("127.0.0.1", 0))
        dead.listen(8)                   # accepted by the kernel, never read
        try:
            with _speech(dead.getsockname()[1]):
                live, took = _timed(llm.enabled)
                assert not live, "a mute socket was taken for a model"
                assert took < 2.5, f"the probe took {took:.2f} s"
                got, took2 = _timed(lambda: llm.complete("anyone?"))
                assert got is None and took2 < 0.05, took2
                game = new_game("mute")
                said, took3 = _timed(lambda: voice_sim.speak(game, "q"))
                assert said["source"] == "written" and took3 < 0.05, took3
        finally:
            dead.close()
        return f"probe gave up in {took:.2f} s; every call after was free"

    try:
        import PyQt6  # noqa: F401
    except ImportError as err:
        print(f"  (the window's half skipped: PyQt6 not available — {err})")
        return

    @check("the comms window never waits on a model, and takes its line late")
    def _():
        from PyQt6.QtWidgets import QApplication
        from ..ui.comms_window import CommsWindow
        from .test_pilot_screen import _bridge

        game, win, _view = _bridge("comms-late")
        app = QApplication.instance()
        hung = _Server(hang=True)
        good = _Server(json.dumps({"response": "Harbour control. Go ahead."})
                       .encode())
        try:
            with _speech(hung.port):
                speaking = next((c for c in track_sim.contacts(game)
                                 if hail_sim.opening(game, c)["ask"]), None)
                assert speaking is not None, "nothing here speaks in a voice"
                window, took = _timed(lambda: CommsWindow(win, speaking))
                assert took < 0.5, f"the window took {took:.2f} s to open"
                written = window.exchange.said[0][1]
                assert written, "no line while the model was thinking"
                # Let the worker reach its deadline *inside* these settings:
                # one still running after they are put back would trip the
                # breaker in the middle of the next half.
                for worker in threading.enumerate():
                    if worker.name == "seedfall-voice":
                        worker.join(5.0)
                assert window.exchange.said[0][1] == written, (
                    "a hung model's silence replaced the written line")
                window.close()
            with _speech(good.port):
                window = CommsWindow(win, speaking)
                end = time.monotonic() + 5.0
                while (window.exchange.said[0][1] != "Harbour control. Go "
                       "ahead." and time.monotonic() < end):
                    app.processEvents()
                    time.sleep(0.01)
                said = window.exchange.said[0][1]
                window.close()
            assert said == "Harbour control. Go ahead.", said
        finally:
            hung.close()
            good.close()
        return (f"opened in {took * 1000:.0f} ms against a hung model; the "
                "model's line replaced the written one when it came")
