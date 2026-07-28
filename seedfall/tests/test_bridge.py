"""Bridge checks — driving the game from outside, without a window.

The protocol is separated from the transport precisely so most of this runs
in-process: verbs are plain functions over a `Game`, and a socket is a detail.
One check does open a loopback connection, because the thing that broke in the
first draft only breaks over a real one.

What broke: `survey` returns a `Lifeform` among its results, the reply was
merged straight into the envelope, and `json.dumps` raised *inside the
connection thread*. The socket died silently and the caller was left reading an
empty line. A boundary has to be total — a caller on a pipe can catch neither a
traceback nor a hang-up.
"""

from __future__ import annotations

import json

from ..bridge import describe, dispatch, snapshot
from ..bridge.protocol import VERBS, plain
from ..bridge.server import Bridge
from ..core.state import new_game
from .harness import Suite


def run(suite: Suite) -> None:
    check = suite.check

    @check("every verb answers, and every answer serialises")
    def _():
        game = new_game("bridge-all")
        calls = {
            "state": {}, "instruments": {}, "bodies": {}, "neighbours": {},
            "market": {}, "log": {"count": 5}, "minds": {}, "situation": {},
            "survey": {"index": 0}, "wait": {"days": 2},
            "extract": {"index": 0, "tonnes": 5},
            "buy": {"commodity": "ore", "tonnes": 1},
            "sell": {"commodity": "ore", "tonnes": 1},
            "jump": {"system_id": game.location_id},
            "speak": {"key": "port:z", "persona": "harbourmaster",
                      "name": "Vell"},
            "remember": {"key": "captain:z", "kind": "trade",
                         "text": "a cargo of ore", "name": "Z"},
            "answer": {"index": 0},
        }
        missing = set(VERBS) - set(calls)
        assert not missing, f"verbs nothing here calls: {sorted(missing)}"
        for name, args in calls.items():
            reply = dispatch(game, {"verb": name, "args": args})
            assert isinstance(reply, dict) and "ok" in reply, (name, reply)
            try:
                json.dumps(reply)
            except (TypeError, ValueError) as err:
                raise AssertionError(
                    f"{name} answered with something no pipe can carry: {err}")
        return f"{len(calls)} verbs, every reply JSON-safe"

    @check("the boundary never raises, whatever it is handed")
    def _():
        game = new_game("bridge-junk")
        rubbish = [
            None, [], "state", 42,
            {"verb": "nope"},
            {"verb": "survey"},                       # missing argument
            {"verb": "survey", "args": {"index": 9999}},
            {"verb": "survey", "args": {"index": "boom"}},
            {"verb": "buy", "args": {"commodity": "ore", "tonnes": "lots"}},
            {"verb": "jump", "args": {"system_id": -4}},
            {"verb": "state", "args": {"unknown": 1}},
        ]
        for command in rubbish:
            reply = dispatch(game, command)
            assert isinstance(reply, dict), (command, reply)
            assert reply.get("ok") is not None
            json.dumps(reply)
        assert not game.dead, "junk commands hurt the game"
        return f"{len(rubbish)} malformed commands, every one answered politely"

    @check("anything can be made safe to send")
    def _():
        # The specific failure: a sim result carrying a live object.
        from ..sim import actions as action_sim
        game = new_game("bridge-plain")
        raw = action_sim.survey(game, 0)
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
            from ..bridge.client import Client
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
                assert "second-captain" in seats
                assert line.send("seat", name="second-captain",
                                 release=True)["seats"] == {}
                snap = line.send("snapshot")
                assert set(snap["snapshot"]) == set(snapshot(game))

            refused = Client(where["host"], where["port"], "not-the-token")
            assert not refused.send("state")["ok"], "a bad token got in"
            refused.close()
        finally:
            bridge.stop()
        return f"a full session over 127.0.0.1:{where['port']}, bad token refused"

    @check("the bridge has a way in, and it stays on this machine")
    def _():
        # `serve()` is the documented entry point behind `python -m
        # seedfall.bridge`, so something has to exercise it — and the thing
        # worth asserting about it is where it binds.
        from ..bridge.server import HOST, serve
        assert HOST == "127.0.0.1", f"the default bind is {HOST}"
        bridge = serve(new_game("bridge-cli"))
        try:
            where = bridge.address()
            assert where["host"] == "127.0.0.1", "the bridge left the machine"
            assert where["port"] > 0
            assert len(where["token"]) >= 16, "the token is too short to matter"
            json.dumps(where)
            assert not bridge.handle({"verb": "state"})["ok"], (
                "a command with no token was served")
        finally:
            bridge.stop()
        return (f"binds {where['host']} only, {len(where['token'])}-character "
                f"token required, untokenised commands refused")

    @check("the protocol describes itself")
    def _():
        described = describe()
        assert len(described) == len(VERBS)
        for entry in described:
            assert entry["doc"], f"{entry['verb']} is undocumented"
            assert entry["verb"] in VERBS
            assert "game" not in entry["args"]
        return f"{len(described)} verbs, each with its arguments and a line"
