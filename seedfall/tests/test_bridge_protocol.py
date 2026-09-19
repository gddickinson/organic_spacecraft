"""The bridge as a caller meets it: the protocol, the socket, the token.

Restored from `785db99`, where these were the bridge's own checks, after
`10fc22e` reused the name `test_bridge` for the Pilot screen's bridge — the
one with the helm on it — and the protocol and socket checks went with the
old file. Measured before this came back: `bridge/server.py`,
`bridge/client.py` and `bridge/attached.py` had 0% coverage, and the suite
key `bridge` ran the screen checks a second time under `bridge2`.

Hostile *arguments* (wrong types, huge numbers, missing fields) are
`test_bridge_guard`'s business. This file is about the transport: that a
session over a real loopback socket works end to end, that the token is
the only way in, that a bad line or an unserialisable reply costs one answer
rather than the connection, and that nothing touches the game off the
thread that owns it.

What first broke, and why a real socket is used at all: `survey` returned a
`Lifeform` among its results, the reply was merged straight into the
envelope, and `json.dumps` raised *inside the connection thread*. The socket
died silently and the caller was left reading an empty line. Only a real
connection shows that.
"""

from __future__ import annotations

import json
import os
import signal
import socket
import subprocess
import sys
import tempfile
import threading
import time

from ..bridge import describe, dispatch, snapshot
from ..bridge.client import Client
from ..bridge.protocol import VERBS, plain, verb
from ..bridge.server import HOST, Bridge, serve
from ..core.save import SAVE_ENV
from ..core.state import new_game
from .harness import Suite


def _protocol_verbs() -> dict:
    """The verbs `protocol.py` itself declares.

    `bridge/attached.py` adds six more (`go`, `shot`, ...) the moment it is
    imported, and in a serial run some earlier suite has usually imported it.
    Those need a window and are checked below with one.
    """
    return {n: e for n, e in VERBS.items()
            if e[0].__module__.endswith("bridge.protocol")}


def _after_close(line) -> dict:
    """Send on a line the far end has closed.

    `Client.send` answers "The bridge closed." when the read comes back
    empty, but lets a reset through: measured under `--coverage`, where the
    server's side closes a little earlier relative to the write, the same
    send raised `ConnectionResetError` — a caller on a pipe catching a
    traceback, which is what the protocol promises it never has to.
    Reported rather than fixed here; this asks only that nothing is served.
    """
    try:
        return line.send("state")
    except ConnectionError as err:
        return {"ok": False, "why": f"raised {type(err).__name__}"}


def _raw(where: dict):
    sock = socket.create_connection((where["host"], where["port"]), timeout=10)
    return sock, sock.makefile("rwb")


def run(suite: Suite) -> None:
    check = suite.check

    @check("every verb answers, and every answer serialises")
    def _():
        game = new_game("bridge-all")
        calls = {
            "state": {}, "instruments": {}, "bodies": {}, "neighbours": {},
            "market": {}, "log": {"count": 5}, "minds": {}, "situation": {},
            "survey": {"index": 0}, "wait": {"days": 2},
            "extract": {"index": 0, "days": 5},
            "buy": {"commodity": "ore", "tonnes": 1},
            "sell": {"commodity": "ore", "tonnes": 1},
            "jump": {"system_id": game.location_id},
            "speak": {"key": "port:z", "persona": "harbourmaster",
                      "name": "Vell"},
            "remember": {"key": "captain:z", "kind": "trade",
                         "text": "a cargo of ore", "name": "Z"},
            "answer": {"index": 0}, "despatches": {"count": 5},
            "answer_signal": {"signal_id": "none"}, "waiting": {},
            "reply": {"choice": "accept"},
        }
        # Both ways round: a verb nothing here calls is untested, and a call
        # to a verb that has gone is a check of nothing.
        declared = _protocol_verbs()
        assert set(declared) == set(calls), (
            f"uncalled: {sorted(set(declared) - set(calls))}, "
            f"gone: {sorted(set(calls) - set(declared))}")
        answered = 0
        for name, args in calls.items():
            reply = dispatch(game, {"verb": name, "args": args})
            assert isinstance(reply, dict) and "ok" in reply, (name, reply)
            try:
                json.dumps(reply)
            except (TypeError, ValueError) as err:
                raise AssertionError(
                    f"{name} answered with something no pipe can carry: "
                    f"{err}") from err
            answered += bool(reply["ok"])
        # Measured: 19 of 21 say yes, in this order, to a fresh game. The ones
        # that say no have nothing to answer: a despatch id that does not
        # exist, and an envoy or aftermath that is not waiting.
        assert answered >= 17, f"only {answered} of {len(calls)} verbs worked"
        return f"{len(calls)} verbs, every reply JSON-safe, {answered} ok"

    @check("the protocol describes itself")
    def _():
        described = [d for d in describe() if d["verb"] in _protocol_verbs()]
        assert len(described) == len(_protocol_verbs())
        assert described, "describe() lists nothing"
        for entry in described:
            assert entry["doc"], f"{entry['verb']} is undocumented"
            assert "game" not in entry["args"]
        return f"{len(described)} verbs, each with its arguments and a line"

    @check("anything can be made safe to send")
    def _():
        from ..sim import actions as action_sim
        raw = action_sim.survey(new_game("bridge-plain"), 0)
        objects = [v for v in raw.values()
                   if not isinstance(v, (str, int, float, bool, type(None),
                                         list, dict, tuple))]
        assert objects, ("survey no longer returns an object, so this check "
                         "is no longer testing what it was written for")
        json.dumps(plain(raw))
        assert plain(objects[0]) != "", "an object flattened to nothing"

        class Awkward:
            def __init__(self):
                self.loop = self
        json.dumps(plain({"a": Awkward(), "b": {1: {2: {3: Awkward()}}}}))
        return f"{len(objects)} live object(s) in one survey, all made sendable"

    @check("a real connection carries a whole session")
    def _():
        game = new_game("bridge-live")
        bridge = Bridge(game).start()
        try:
            where = bridge.address()
            with Client(where["host"], where["port"], where["token"]) as line:
                assert line.send("verbs")["ok"]
                # The command that used to kill the socket.
                assert line.send("survey", index=0)["ok"], "survey hung up"
                after = line.send("state")
                assert after["ok"], "the connection died after a survey"
                assert line.send("wait", days=10)["to"] > after["day"]
                seats = line.send("seat", name="second-captain",
                                  by="agent")["seats"]
                assert seats["second-captain"]["held_by"] == "agent"
                assert line.send("seat")["seats"] == seats, (
                    "asking with no name should list the seats")
                assert line.send("seat", name="second-captain",
                                 release=True)["seats"] == {}
                snap = line.send("snapshot")
                assert set(snap["snapshot"]) == set(snapshot(game))
        finally:
            bridge.stop()
        return f"a full session over 127.0.0.1:{where['port']}"

    @check("the token is per bridge, and nothing is served without it")
    def _():
        game = new_game("bridge-token")
        one, two = Bridge(game).start(), Bridge(game).start()
        chosen = Bridge(game, token="chosen-by-the-caller-0001").start()
        try:
            a, b = one.address(), two.address()
            assert a["token"] != b["token"], "two sessions minted one token"
            assert len(a["token"]) >= 16, "the token is too short to matter"
            assert chosen.address()["token"] == "chosen-by-the-caller-0001"
            for token in ("", "not-the-token", b["token"], a["token"].upper()):
                with Client(a["host"], a["port"], token) as line:
                    reply = line.send("state")
                    assert not reply["ok"] and "token" in reply["why"], (
                        f"{token!r} got in: {reply}")
                    # Every verb, not only the protocol's: `seat` and
                    # `snapshot` are handled by the server before dispatch.
                    for name in ("seat", "snapshot", "verbs"):
                        assert not line.send(name)["ok"], f"{name} leaked"
            assert not one.handle({"verb": "state"})["ok"]
        finally:
            for bridge in (one, two, chosen):
                bridge.stop()
        return "tokens differ per session; 4 wrong ones and 3 server verbs refused"

    @check("a line that is not a command is answered, and the line stays up")
    def _():
        bridge = Bridge(new_game("bridge-junk")).start()
        try:
            where = bridge.address()
            sock, stream = _raw(where)
            with sock, stream:
                junk = [b"not json", b"", b"   ", b"[1, 2]", b"42",
                        b'{"verb": "state"}', b"\xff\xfe"]
                for raw in junk:
                    stream.write(raw + b"\n")
                    stream.flush()
                    reply = json.loads(stream.readline())
                    assert reply["ok"] is False and reply["why"], (raw, reply)
                good = json.dumps({"verb": "state", "token": where["token"]})
                stream.write(good.encode() + b"\n")
                stream.flush()
                assert json.loads(stream.readline())["ok"], (
                    "the connection did not survive its junk")
        finally:
            bridge.stop()
        return f"{len(junk)} bad lines, each refused in words, then served"

    @check("a reply that cannot be serialised costs one answer, not the socket")
    def _():
        class Careless(Bridge):
            def handle(self, command):
                if isinstance(command, dict) and command.get("verb") == "bad":
                    return {"ok": True, "thing": object()}
                return super().handle(command)

        bridge = Careless(new_game("bridge-careless")).start()
        try:
            where = bridge.address()
            with Client(where["host"], where["port"], where["token"]) as line:
                reply = line.send("bad")
                assert reply["ok"] is False
                assert "not serialisable" in reply["why"], reply
                assert line.send("state")["ok"], "the socket died with it"
        finally:
            bridge.stop()
        return "the reply was replaced with an error; the session went on"

    @check("two callers at once are served one command at a time")
    def _():
        # The server holds the `Game` behind one lock so two seats cannot
        # interleave halfway through a jump. Measured by a verb that notes
        # how many commands are inside it at once: with the lock, never two.
        inside, most, calls = [0], [0], [0]

        @verb("_overlap_probe", "test only")
        def _probe(game) -> dict:
            inside[0] += 1
            most[0] = max(most[0], inside[0])
            time.sleep(0.002)
            inside[0] -= 1
            calls[0] += 1
            return {"ok": True}

        bridge = Bridge(new_game("bridge-pair")).start()
        where = bridge.address()

        def hammer():
            with Client(where["host"], where["port"], where["token"]) as line:
                for _n in range(25):
                    assert line.send("_overlap_probe")["ok"]
        try:
            threads = [threading.Thread(target=hammer) for _n in range(3)]
            for t in threads:
                t.start()
            for t in threads:
                t.join(30)
        finally:
            bridge.stop()
            VERBS.pop("_overlap_probe", None)
        assert calls[0] == 75, f"{calls[0]} of 75 commands answered"
        assert most[0] == 1, f"{most[0]} commands were inside the game at once"
        return "3 callers × 25 commands, never two inside the game at once"

    @check("goodbye, or stopping the bridge, ends a session cleanly")
    def _():
        bridge = Bridge(new_game("bridge-bye")).start()
        where = bridge.address()
        line = Client(where["host"], where["port"], where["token"])
        assert line.send("bye") == {"ok": True, "closed": True}
        assert not _after_close(line)["ok"], "a line said goodbye and was served"
        line.close()                 # a second goodbye must not raise

        other = Client(where["host"], where["port"], where["token"])
        assert other.send("state")["ok"]
        bridge.stop()
        assert not _after_close(other)["ok"], "a stopped bridge kept serving"
        other.close()
        try:
            socket.create_connection((where["host"], where["port"]),
                                     timeout=2).close()
            raise AssertionError("a stopped bridge still accepts connections")
        except ConnectionRefusedError:
            pass
        return "bye closes one line; stop closes the rest and the port"

    @check("the bridge binds this machine only")
    def _():
        assert HOST == "127.0.0.1", f"the default bind is {HOST}"
        bridge = serve(new_game("bridge-serve"))
        try:
            where = bridge.address()
            assert where["host"] == "127.0.0.1", "the bridge left the machine"
            assert where["port"] > 0
            json.dumps(where)
        finally:
            bridge.stop()
        return f"binds {where['host']} only"

    @check("python -m seedfall.bridge serves a game to another process")
    def _():
        # The documented way in, and the only check that crosses a process
        # boundary. Its save is pointed at a scratch directory explicitly: a
        # bridge started with `--load` reads the player's chronicle otherwise.
        # The repository root — three levels up from this file. It was four,
        # which ran the child from the directory *above* the repository and
        # passed only where PYTHONPATH happened to name the tree.
        root = os.path.dirname(os.path.dirname(os.path.dirname(
            os.path.abspath(__file__))))
        with tempfile.TemporaryDirectory() as tmp:
            env = dict(os.environ, **{SAVE_ENV: os.path.join(tmp, "s.json")})
            nothing = subprocess.run(
                [sys.executable, "-m", "seedfall.bridge", "--load"], env=env,
                cwd=root, capture_output=True, text=True, timeout=60)
            assert nothing.returncode == 1, nothing
            assert json.loads(nothing.stdout)["why"] == "no save to serve"

            proc = subprocess.Popen(
                [sys.executable, "-m", "seedfall.bridge", "--seed", "bridge-cli"],
                env=env, cwd=root, stdout=subprocess.PIPE,
                stderr=subprocess.PIPE, text=True)
            try:
                where = json.loads(proc.stdout.readline())
                assert where["ok"] and where["seed"] == "bridge-cli", where
                with Client(where["host"], where["port"], where["token"]) as line:
                    moved = line.send("wait", days=3)
                assert moved["ok"] and moved["to"] == 3, moved
                proc.send_signal(signal.SIGINT)
                # Generous: under a full parallel run the machine can sit at a
                # load of 40+, and a clean SIGINT exit took over 20 s there.
                code = proc.wait(timeout=90)
            finally:
                if proc.poll() is None:
                    proc.kill()
                proc.stdout.close()
                proc.stderr.close()
        assert code == 0, f"interrupted, it exited {code}"
        return "served a wait across processes; --load with no save refused"

    @check("an attached bridge drives the window, on the window's thread")
    def _():
        from .harness import qt_missing
        if qt_missing():
            return "skipped: no PyQt6"
        return _attached()


def _attached() -> str:
    """The socket thread must never touch the game the window paints.

    `AttachedBridge` posts every command to the Qt event loop and blocks for
    the answer. Checked by a verb that notes which thread it ran on, with the
    main thread pumping events as the window's own loop would.
    """
    from . import qtkit
    from ..bridge import attached

    app = qtkit.app()
    game = new_game("bridge-attached")
    win = qtkit.main_window(game)
    threads = []

    @verb("_thread_probe", "test only")
    def _probe(game) -> dict:
        threads.append(threading.current_thread() is threading.main_thread())
        return {"ok": True}

    earlier = set(threading.enumerate())
    bridge = attached.attach(win)
    where, said = bridge.address(), {}

    def talk():
        with Client(where["host"], where["port"], where["token"]) as line:
            said["go"] = line.send("go", screen="port")
            said["screen"] = line.send("screen")
            said["nowhere"] = line.send("go", screen="nowhere")
            said["probe"] = line.send("_thread_probe")
            said["wait"] = line.send("wait", days=2)
    def serving() -> bool:
        return caller.is_alive() or any(
            t.is_alive() and t.name.endswith("(_talk)")
            for t in set(threading.enumerate()) - earlier)
    try:
        caller = threading.Thread(target=talk)
        caller.start()
        # Pumped until the *server* is done, not only the caller: the
        # goodbye `Client.close` sends unanswered still gets a window
        # refresh posted for it, and a loop that stopped pumping when the
        # caller left had that refresh time out in the connection thread
        # fifteen seconds later — a traceback, under pytest, in a later suite.
        t0 = time.monotonic()
        while serving() and time.monotonic() - t0 < 30:
            app.processEvents()
            time.sleep(0.002)
        assert not caller.is_alive(), "the attached bridge never answered"
    finally:
        bridge.stop()
        VERBS.pop("_thread_probe", None)
        attached._ATTACHED.clear()     # no stale window for a later suite
        win.close()
    assert said["go"] == {"ok": True, "screen": "port"}, said["go"]
    assert said["screen"]["screen"] == win.current == "port"
    assert not said["nowhere"]["ok"] and "screens" in said["nowhere"]
    assert threads == [True], f"the verb ran off the Qt thread: {threads}"
    assert said["wait"]["ok"] and game.day == said["wait"]["to"] >= 1
    return "screen opened over the socket; every command ran on the Qt thread"
