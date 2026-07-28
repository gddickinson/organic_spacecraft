"""The vocabulary: what an outside caller may ask a running game to do.

Deliberately separate from any socket. Every verb is a plain function over a
`Game`, so the suite drives the whole protocol in-process and the transport is
a detail that can be swapped or removed.

Three rules:

- **A verb does exactly what the equivalent control in the window does**, by
  calling the same `sim/` function. There is no second implementation of
  anything here, because a second implementation is a second set of bugs.
- **Every verb answers `{"ok": …}`** and never raises across the boundary. A
  caller on the other end of a pipe cannot catch a traceback.
- **Nothing here writes the ledger directly.** Same rule the UI lives under.
"""

from __future__ import annotations

import inspect

from ..sim import actions as action_sim
from ..sim import legacy as legacy_sim
from ..sim import memory as memory_sim
from ..sim import market as market_sim
from ..sim import telemetry
from ..sim import trade as trade_sim
from ..sim import voice as voice_sim
from ..sim.ship import cargo_used, hull_pct
from ..world.galaxy import distance

VERBS: dict = {}

#: What may cross the boundary untouched.
PLAIN = (str, int, float, bool, type(None))


def plain(value, depth: int = 0):
    """Anything, made safe to serialise.

    The boundary has to be total. `survey` returns a `Lifeform` object among
    its results, and merging that into a reply made `json.dumps` raise *inside
    the connection thread* — which killed the socket silently and left the
    caller reading an empty line with no idea why. A caller on a pipe cannot
    catch a traceback, and it cannot catch a hang-up either.
    """
    if isinstance(value, PLAIN):
        return value
    if depth > 6:
        return str(value)
    if isinstance(value, dict):
        return {str(k): plain(v, depth + 1) for k, v in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [plain(v, depth + 1) for v in value]
    for attribute in ("name", "id", "title"):
        named = getattr(value, attribute, None)
        if isinstance(named, str):
            return named
    return str(value)


def verb(name: str, doc: str):
    """Register a verb and the one line that describes it."""
    def keep(fn):
        VERBS[name] = (fn, doc)
        return fn
    return keep


def describe() -> list:
    """Every verb, its arguments and what it does — the protocol, self-served."""
    out = []
    for name, (fn, doc) in sorted(VERBS.items()):
        args = [p for p in inspect.signature(fn).parameters if p != "game"]
        out.append({"verb": name, "args": args, "doc": doc})
    return out


# ── looking ────────────────────────────────────────────────────────────────

@verb("state", "The whole situation, compactly: ship, place, purse, clock.")
def state(game) -> dict:
    system = game.system
    return {"ok": True, "day": game.day, "credits": round(game.credits),
            "system": {"id": system.id, "name": system.name,
                       "port": system.port.name if system.port else None,
                       "faction": system.faction,
                       "bloom": round(system.bloom, 3),
                       "bodies": len(system.bodies)},
            "ship": {"name": game.ship.name, "chassis": game.ship.chassis,
                     "hull": round(hull_pct(game.ship), 3),
                     "heat": round(game.ship.heat, 1),
                     "cargo": {k: round(v, 1) for k, v in game.ship.cargo.items()},
                     "hold": [round(cargo_used(game.ship), 1),
                              round(game.ship_stats.cargo, 1)],
                     "jump": round(game.ship_stats.jump, 2)},
            "officers": [{"name": o.name, "station": o.stat, "level": o.level}
                         for o in game.officers],
            "rep": {k: round(v, 1) for k, v in game.rep.items()},
            "victory": game.victory, "dead": game.dead,
            "epoch": legacy_sim.gauge(game).get("epoch").id
            if legacy_sim.in_epoch(game) else None}


@verb("instruments", "Every gauge reading, as the pop-out windows see them.")
def instruments(game) -> dict:
    readings = {}
    for name, reading in telemetry.all_readings(game).items():
        readings[name] = {k: v for k, v in reading.items()
                          if k in ("title", "note", "band", "fraction",
                                   "now", "cap")}
    return {"ok": True, "instruments": readings}


@verb("bodies", "What is in this system, and what is known about each.")
def bodies(game) -> dict:
    return {"ok": True, "bodies": [
        {"index": i, "name": b.name, "kind": b.kind,
         "surveyed": bool(b.surveyed), "depleted": round(b.depleted, 3),
         "relic": bool(b.relic), "colony": b.colony is not None}
        for i, b in enumerate(game.system.bodies)]}


@verb("neighbours", "Systems within one jump, with the fuel and days each costs.")
def neighbours(game) -> dict:
    here = game.system
    out = []
    for system in game.galaxy.systems:
        if system.id == here.id:
            continue
        span = distance(system, here)
        if span > game.ship_stats.jump:
            continue
        quote = action_sim.jump_quote(game, system)
        out.append({"id": system.id, "name": system.name,
                    "ly": round(span, 2), "days": quote["days"],
                    "fuel": quote["fuel"], "visited": bool(system.visited),
                    "port": bool(system.port)})
    out.sort(key=lambda row: row["ly"])
    return {"ok": True, "neighbours": out}


@verb("market", "Prices at this port, if there is one.")
def market(game) -> dict:
    system = game.system
    if not system.market or not system.port:
        return {"ok": False, "why": "No market here."}
    rep = game.rep.get(system.port.faction, 0)
    market_sim.note_prices(game, system, rep, game.ship_stats.trade)
    from ..world.economy import buy_price, sell_price
    rows = {}
    for cid in list(system.market.stock):
        rows[cid] = {"buy": buy_price(system.market, cid, rep,
                                      game.ship_stats.trade),
                     "sell": sell_price(system.market, cid, rep,
                                        game.ship_stats.trade)}
    return {"ok": True, "port": system.port.name, "prices": rows}


@verb("log", "The last lines of the chronicle.")
def log(game, count: int = 20) -> dict:
    return {"ok": True, "log": [
        {"day": entry[0] if isinstance(entry, (list, tuple)) else game.day,
         "text": entry[1] if isinstance(entry, (list, tuple)) and len(entry) > 1
         else str(entry)}
        for entry in list(game.log)[-int(count):]]}


# ── doing ──────────────────────────────────────────────────────────────────

@verb("survey", "Survey one body by index.")
def survey(game, index: int) -> dict:
    result = action_sim.survey(game, int(index))
    return {"ok": bool(result.get("ok", True)), **result}


@verb("jump", "Jump to a system by id.")
def jump(game, system_id: int) -> dict:
    return action_sim.jump_to(game, int(system_id))


@verb("extract", "Run the rig on a body: index, tonnes, method.")
def extract(game, index: int, tonnes: float = 30, method: str = "cut") -> dict:
    return action_sim.extract(game, int(index), float(tonnes), method)


@verb("buy", "Buy tonnes of a commodity at this port.")
def buy(game, commodity: str, tonnes: float) -> dict:
    return trade_sim.buy(game, commodity, float(tonnes))


@verb("sell", "Sell tonnes of a commodity at this port.")
def sell(game, commodity: str, tonnes: float) -> dict:
    return trade_sim.sell(game, commodity, float(tonnes))


@verb("wait", "Let days pass.")
def wait(game, days: float = 1) -> dict:
    before = game.day
    game.advance_days(float(days))
    return {"ok": True, "from": before, "to": game.day,
            "dead": game.dead, "victory": game.victory}


# ── talking ────────────────────────────────────────────────────────────────

@verb("speak", "Have somebody in the world say something, in their own voice.")
def speak(game, key: str, persona: str = "plain", situation: str = "greet",
          name: str = "", fact: str = "", kind: str = "captain") -> dict:
    """`kind` decides whose past they draw on — a ship is not a captain.

    Without it every speaker got the captain's backstory, so the ship's own
    computer said "before any of this, *they* were refused a berth".
    """
    said = voice_sim.speak(game, key, persona=persona, situation=situation,
                           name=name, fact=fact, kind=kind)
    return {"ok": True, **said}


@verb("remember", "Write a memory against somebody, as an event would.")
def remember(game, key: str, kind: str, text: str, salience: float = 1.0,
             name: str = "", entity: str = "captain") -> dict:
    made = memory_sim.note(game, key, kind, text, float(salience),
                           name=name, entity=entity)
    return {"ok": True, "id": made.id,
            "impression": memory_sim.impression_of(game, key)}


@verb("minds", "Who remembers you, and what they think.")
def minds(game) -> dict:
    return {"ok": True, "minds": [
        {"key": mind.key, "name": mind.name, "kind": mind.kind,
         "impression": round(impression, 1), "memories": len(mind.memories),
         "grudge": [m.text for m in mind.grudge()[:3]]}
        for mind, impression in memory_sim.summary(game)]}


@verb("situation", "The aftermath question waiting on an answer, if any.")
def situation(game) -> dict:
    waiting = legacy_sim.offer(game)
    return {"ok": True, "waiting": bool(waiting), **waiting} if waiting \
        else {"ok": True, "waiting": False}


@verb("answer", "Answer the waiting aftermath question by index.")
def answer(game, index: int) -> dict:
    return legacy_sim.answer(game, int(index))


# ── dispatch ───────────────────────────────────────────────────────────────

def dispatch(game, command: dict) -> dict:
    """Run one command. Never raises: a caller on a pipe cannot catch one."""
    if not isinstance(command, dict):
        return {"ok": False, "why": "A command is an object."}
    name = command.get("verb")
    entry = VERBS.get(name)
    if entry is None:
        return {"ok": False, "why": f"No such verb: {name!r}.",
                "verbs": sorted(VERBS)}
    fn, _doc = entry
    args = {k: v for k, v in (command.get("args") or {}).items()}
    allowed = {p for p in inspect.signature(fn).parameters if p != "game"}
    unknown = set(args) - allowed
    if unknown:
        return {"ok": False,
                "why": f"{name} does not take {sorted(unknown)}.",
                "args": sorted(allowed)}
    try:
        return plain(fn(game, **args))
    except TypeError as err:
        return {"ok": False, "why": f"{name}: {err}", "args": sorted(allowed)}
    except Exception as err:                      # noqa: BLE001 - boundary
        return {"ok": False, "why": f"{name} failed: {type(err).__name__}: {err}"}


def snapshot(game) -> dict:
    """Everything a remote seat needs to decide what to do next."""
    return plain({"state": state(game), "bodies": bodies(game),
                  "neighbours": neighbours(game),
                  "instruments": instruments(game),
                  "situation": situation(game)})
