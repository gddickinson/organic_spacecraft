"""The remote bridge takes what a pipe can carry, and refuses what it must.

Review 2026-09-17 (#30) drove every verb with values no control in the window
can produce, and found the protocol trusted all of them: `buy` with `NaN`
tonnes wrote `NaN` into the purse and the save; `survey -1` surveyed the last
body and `jump -1` targeted the last system; a dead captain went on trading;
`extract` of zero days ran a working; `remember text=null` broke that
speaker's `speak` for the rest of the chronicle; `jump` threw its ambush
away; `shot` wrote wherever it was told; and a line could be any length.

The fuzz here runs every verb's every argument through a list of hostile
values and asserts two things of each call: it answers `{"ok": ...}` without
raising, and afterwards the chronicle is still finite — credits, cargo,
stores and the day — and still saves. The named cases then pin each finding.
"""

from __future__ import annotations

import inspect
import json
import math
import socket

from ..bridge import checks, protocol
from ..bridge.server import Bridge
from ..core import save as save_mod
from ..core.state import new_game
from ..sim import actions as action_sim
from ..sim import encounters as encounter_sim
from ..sim import memory as memory_sim
from ..world.galaxy import distance
from .harness import Suite

NAN, INF = float("nan"), float("inf")

#: Refused by every numeric argument, whatever its range.
BAD_NUMBERS = [NAN, INF, -INF, None, "nan", "inf", "", "x" * 100_000, [], {},
               True, [1, 2], {"a": 1}, 10 ** 18, 1e308, -10 ** 9, -1, "-1"]
#: Refused by every text argument.
BAD_TEXT = [None, 5, 3.5, NAN, True, [], {}, ["a"], "x" * 100_000]

#: What a required argument is set to while another one is being fuzzed.
BENIGN = {"signal_id": "no-such-despatch", "index": 0, "system_id": 0,
          "commodity": "ore", "tonnes": 1, "key": "fuzz", "kind": "gift",
          "text": "a kindness", "choice": "release", "order": "brace"}


def _numeric(fn, name: str) -> bool:
    annotation = inspect.signature(fn).parameters[name].annotation
    return annotation in ("int", "float", int, float)


def _sane(game) -> list:
    """Everything that a poisoned argument has been seen to reach."""
    wrong = []
    if not math.isfinite(game.credits):
        wrong.append(f"credits {game.credits!r}")
    for where, held in (("cargo", game.ship.cargo),
                        ("stores", getattr(game, "stores", {}) or {})):
        for cid, tonnes in held.items():
            if not isinstance(tonnes, (int, float)) or not math.isfinite(
                    tonnes) or tonnes < -1e-9:
                wrong.append(f"{where}[{cid}] {tonnes!r}")
    if not isinstance(game.day, int):
        wrong.append(f"day {game.day!r}")
    return wrong


def _call(game, verb: str, **args) -> dict:
    reply = protocol.dispatch(game, {"verb": verb, "args": args})
    assert isinstance(reply, dict) and "ok" in reply, (verb, args, reply)
    return reply


def _a_neighbour(game):
    here = game.system
    return next(s for s in sorted(game.galaxy.systems,
                                  key=lambda s: distance(s, here))
                if s.id != here.id and distance(s, here) <= game.ship_stats.jump)


def run(suite: Suite) -> None:
    check = suite.check

    @check("every verb refuses hostile numbers and wrong types, and nothing "
           "is poisoned")
    def _():
        game = new_game("bridge-fuzz")
        game.credits = 50_000.0
        tried = refused = 0
        for name, (fn, _doc) in sorted(protocol.VERBS.items()):
            params = [p for p in inspect.signature(fn).parameters
                      if p != "game"]
            for param in params:
                hostile = BAD_NUMBERS if _numeric(fn, param) else BAD_TEXT
                for value in hostile:
                    args = {p: BENIGN.get(p, 1)
                            for p in params
                            if inspect.signature(fn).parameters[p].default
                            is inspect.Parameter.empty}
                    args[param] = value
                    reply = _call(game, name, **args)
                    tried += 1
                    assert reply["ok"] is False, (
                        f"{name}({param}={value!r:.40}) was accepted: "
                        f"{str(reply)[:160]}")
                    refused += 1
                    wrong = _sane(game)
                    assert not wrong, (f"{name}({param}={value!r:.40}) "
                                       f"poisoned the chronicle: {wrong}")
        assert save_mod.write(game.to_save()), save_mod.last_error()
        back = save_mod.read()["game"]
        assert not _sane(back), _sane(back)
        return (f"{len(protocol.VERBS)} verbs, {tried} hostile calls, "
                f"{refused} refused, the purse finite and the save writing")

    @check("the review's cases, each refused where it used to act")
    def _():
        game = new_game("bridge-cases")
        game.credits = 40_000.0
        before = (game.credits, dict(game.ship.cargo))
        for tonnes in (NAN, "nan", INF, -3, 0):
            for verb in ("buy", "sell"):
                reply = _call(game, verb, commodity="ore", tonnes=tonnes)
                assert not reply["ok"], (verb, tonnes, reply)
        assert (game.credits, dict(game.ship.cargo)) == before
        last = game.system.bodies[-1]
        assert not _call(game, "survey", index=-1)["ok"]
        assert not last.surveyed, "survey -1 reached the last body"
        assert not _call(game, "jump", system_id=-1)["ok"]
        day = game.day
        for days in (0, -5, NAN):
            assert not _call(game, "extract", index=0, days=days)["ok"]
        assert game.day == day, "a working of no days took days"
        reply = _call(game, "remember", key="vell", kind="slight", text=None)
        assert not reply["ok"], reply
        assert _call(game, "speak", key="vell")["ok"]
        # And a save that already holds a text-less memory speaks anyway.
        memory_sim.note(game, "old", "slight", None)
        said = _call(game, "speak", key="old")
        assert said["ok"] and said["line"], said
        return "NaN trades, -1 indices, empty workings and null memories"

    @check("once the chronicle has ended, nothing acts in it")
    def _():
        game = new_game("bridge-dead")
        game.dead = True
        credits = game.credits
        for name, (fn, _doc) in sorted(protocol.VERBS.items()):
            params = inspect.signature(fn).parameters
            args = {p: BENIGN.get(p, 1) for p in params
                    if p != "game" and params[p].default
                    is inspect.Parameter.empty}
            reply = _call(game, name, **args)
            if name in protocol.ACTS:
                assert reply.get("ended"), (name, reply)
            else:
                assert not reply.get("ended"), (name, reply)
        assert game.credits == credits
        return (f"{len(protocol.ACTS)} acting verbs refused; the "
                f"{len(protocol.VERBS) - len(protocol.ACTS)} that look still "
                "answer")

    @check("an ambush on arrival is fought, not dropped")
    def _():
        game = new_game("bridge-ambush")
        game.ship.cargo["volatiles"] = 400.0
        target = _a_neighbour(game)
        real = action_sim.roll_encounter

        def ambush(g, system, rng):
            return {"enemy": encounter_sim.make_enemy(rng, "freeholds", 0.8),
                    "no_parley": False, "intro": "A hull without colours."}
        action_sim.roll_encounter = ambush
        try:
            arrived = _call(game, "jump", system_id=target.id)
        finally:
            action_sim.roll_encounter = real
        assert arrived["ok"] and arrived["encounter"], arrived
        assert arrived["encounter"]["orders"], "nothing to order"
        asked = _call(game, "waiting")
        assert asked["blocked"] and asked["battle"], asked
        held = _call(game, "wait", days=1)
        assert not held["ok"] and held.get("blocked"), held
        assert not _call(game, "fight", order="dance a jig")["ok"]
        turns = 0
        reply = {}
        while turns < 80:
            reply = _call(game, "fight",
                          order="flee" if turns > 30 else "salvo")
            assert reply["ok"], reply
            turns += 1
            if reply["over"]:
                break
        assert reply["over"], f"{turns} turns and still fighting"
        assert "aftermath" in reply, reply
        if reply["prize"]:
            assert _call(game, "prize", choice="release")["ok"]
        assert not _call(game, "waiting")["blocked"]
        assert not _sane(game), _sane(game)
        return (f"ambushed on arrival, fought {turns} turn(s) to "
                f"'{reply['result']}', and the aftermath paid out")

    @check("a line has a length, and NaN is not a number JSON allows")
    def _():
        game = new_game("bridge-lines")
        bridge = Bridge(game)
        try:
            token = bridge.token
            state = json.dumps({"verb": "state", "token": token})
            assert bridge.handle_line(state)["ok"]
            long = state[:-1] + ', "pad": "' + "x" * checks.MAX_LINE + '"}'
            assert not bridge.handle_line(long)["ok"]
            nan = ('{"verb": "buy", "token": "%s", "args": {"commodity": '
                   '"ore", "tonnes": NaN}}' % token)
            assert "Not JSON" in bridge.handle_line(nan)["why"]
            assert not bridge.handle_line("[" * 50_000)["ok"]
            assert not bridge.handle_line(json.dumps(
                {"verb": "state", "token": token, "args": [1]}))["ok"]
            assert not bridge.handle_line(json.dumps(
                {"verb": "state", "token": 12345}))["ok"]
            assert not bridge.handle_line(json.dumps(
                {"verb": "seat", "token": token, "args": "me"}))["ok"]
            # And over the wire: refused, and still in step for the next.
            bridge.start()
            with socket.create_connection((bridge.host, bridge.port),
                                          timeout=5) as conn:
                stream = conn.makefile("rwb")
                stream.write(b"x" * (3 * checks.MAX_LINE + 10) + b"\n")
                stream.write(state.encode() + b"\n")
                stream.flush()
                reply = json.loads(stream.readline())
                assert not reply["ok"] and "at most" in reply["why"], reply
                after = json.loads(stream.readline())
                assert after["ok"], f"out of step after a long line: {after}"
        finally:
            bridge.stop()
        assert not _sane(game)
        return f"{checks.MAX_LINE:,} bytes a line; NaN refused at parse"

    try:
        import PyQt6  # noqa: F401
    except ImportError:
        return

    @check("a picture is saved by name, into the temp folder only")
    def _():
        from ..bridge.attached import shot_name
        for bad in ("../x.png", "/tmp/x.png", "a/b.png", ".hidden.png",
                    "x.txt", "C:\\x.png", "x" * 80 + ".png", 5, "a.png\x00"):
            assert shot_name(bad, "map") is None, bad
        assert shot_name("", "map") == "seedfall-map.png"
        assert shot_name("run-3_b.png", "map") == "run-3_b.png"
        return "a directory, a dotfile or another suffix is refused"
