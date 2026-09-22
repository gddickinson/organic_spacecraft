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
- **Nothing from the pipe reaches a verb unchecked.** Every number is finite
  and in range, every index is inside its list, every string is a string —
  `bridge/checks.py`, which says what got through before it existed. And a
  verb that *acts* (`verb(..., acts=True)`) is refused once the chronicle
  has ended, or while an engagement is open (`bridge/battle.py`).
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
from . import checks
from .checks import Refused

VERBS: dict = {}

#: Verbs that change the chronicle, as opposed to reading it: refused once it
#: has ended, and while an engagement is waiting on an order.
ACTS: set = set()

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


def verb(name: str, doc: str, acts: bool = False):
    """Register a verb and the one line that describes it."""
    def keep(fn):
        VERBS[name] = (fn, doc)
        if acts:
            ACTS.add(name)
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
    # The counter's quotes, not the raw prices — the bot trades through
    # `sim.trade`, which charges `quote_*`, so anything else here is a board
    # quoting figures the counter will not honour.
    rows = {}
    for cid in list(system.market.stock):
        rows[cid] = {"buy": market_sim.quote_buy(game, system, cid),
                     "sell": market_sim.quote_sell(game, system, cid)}
    return {"ok": True, "port": system.port.name, "prices": rows}


@verb("log", "The last lines of the chronicle.")
def log(game, count: int = 20) -> dict:
    count = checks.whole(count, "count", 1, 300)
    return {"ok": True, "log": [
        {"day": entry[0] if isinstance(entry, (list, tuple)) else game.day,
         "text": entry[1] if isinstance(entry, (list, tuple)) and len(entry) > 1
         else str(entry)}
        for entry in list(game.log)[-count:]]}


@verb("despatches", "The inbox: what has arrived, and what asks an answer.")
def despatches(game, count: int = 20) -> dict:
    """Deliberately *not* part of `waiting`/`reply`: an unanswered despatch
    does not stop the clock or lock the window, and folding it into the
    blocked set would deadlock every driven session on the first bulletin."""
    from ..sim import comms as comms_sim
    rows = []
    for sig in comms_sim.inbox(game)[:checks.whole(count, "count", 1, 200)]:
        rows.append({"id": sig.id, "from": sig.name, "channel": sig.channel,
                     "subject": sig.subject, "body": sig.body,
                     "age": sig.note, "read": sig.read,
                     "asks": sig.asks,
                     "replies": [{"key": k, "says": w}
                                 for k, w in sig.replies] if sig.asks else []})
    return {"ok": True, "unread": comms_sim.unread(game),
            "asking": len(comms_sim.asking(game)), "despatches": rows}


@verb("answer_signal", "Answer a despatch by id and reply key; or mark it read.",
      acts=True)
def answer_signal(game, signal_id: str, key: str = "") -> dict:
    from ..sim import comms as comms_sim
    if isinstance(signal_id, int) and not isinstance(signal_id, bool):
        signal_id = str(signal_id)          # ids are strings; a number is one
    signal_id = checks.words(signal_id, "signal_id", 80, required=True)
    key = checks.words(key, "key", 80)
    if key:
        if comms_sim.answer(game, str(signal_id), str(key)):
            return {"ok": True, "answered": str(key)}
        return {"ok": False, "why": "Not being asked, or no such reply."}
    sig = comms_sim.read(game, str(signal_id))
    if sig is None:
        return {"ok": False, "why": "No despatch by that id."}
    return {"ok": True, "read": True}


# ── doing ──────────────────────────────────────────────────────────────────

#: The most tonnes one trade can name. Holds run to hundreds of tonnes; this
#: only has to be finite and far above any of them.
MOST_TONNES = 1e6
#: The longest single working or wait. A year of either is already more than
#: any screen offers; ten of waiting is a long time to sit on one call.
MOST_WORKING_DAYS = 365
MOST_WAIT_DAYS = 3650


@verb("survey", "Survey one body by index.", acts=True)
def survey(game, index: int) -> dict:
    result = action_sim.survey(game, checks.index(index, "body",
                                                  game.system.bodies))
    return {"ok": bool(result.get("ok", True)), **result}


@verb("jump", "Jump to a system by id; an ambush on arrival must be fought.",
      acts=True)
def jump(game, system_id: int) -> dict:
    target = checks.index(system_id, "system", game.galaxy.systems)
    if target == game.location_id:
        return {"ok": False, "why": "You are already there."}
    result = action_sim.jump_to(game, target)
    # What the window does with it: `map_view._jump` hands an encounter to
    # the battle screen. Here it opens an engagement `fight` answers.
    if result.get("encounter") and not game.dead:
        from . import battle
        result["encounter"] = battle.begin(game, result["encounter"])
    return result


@verb("extract", "Run the rig on a body: index, days of working, method.",
      acts=True)
def extract(game, index: int, days: float = 30, method: str = "cut") -> dict:
    # The parameter was called "tonnes" and it was days all along —
    # `actions.extract` takes a spell length, and a caller asking for 30
    # tonnes got a 30-day working that raised ~99.
    body = checks.index(index, "body", game.system.bodies)
    days = checks.amount(days, "days", MOST_WORKING_DAYS)
    return action_sim.extract(game, body, days,
                              checks.words(method, "method", 40))


@verb("buy", "Buy tonnes of a commodity at this port.", acts=True)
def buy(game, commodity: str, tonnes: float) -> dict:
    return trade_sim.buy(game, checks.words(commodity, "commodity", 40, True),
                         checks.amount(tonnes, "tonnes", MOST_TONNES))


@verb("sell", "Sell tonnes of a commodity at this port.", acts=True)
def sell(game, commodity: str, tonnes: float) -> dict:
    return trade_sim.sell(game, checks.words(commodity, "commodity", 40, True),
                          checks.amount(tonnes, "tonnes", MOST_TONNES))


@verb("wait", "Let days pass.", acts=True)
def wait(game, days: float = 1) -> dict:
    days = checks.whole(days, "days", 1, MOST_WAIT_DAYS)
    before = game.day
    # The same door the Holdings screen uses: a wait stands down on news
    # that deserves a hand rather than running blind to the end.
    told = game.wait_days(days)
    return {"ok": True, "from": before, "to": game.day,
            "stopped": told["stopped"], "bad": told["bad"][-6:],
            "credits": told["credits"],
            "dead": game.dead, "victory": game.victory}


# ── talking ────────────────────────────────────────────────────────────────

@verb("speak", "Have somebody in the world say something, in their own voice.",
      acts=True)
def speak(game, key: str, persona: str = "plain", situation: str = "greet",
          name: str = "", fact: str = "", kind: str = "captain") -> dict:
    """`kind` decides whose past they draw on — a ship is not a captain.

    Without it every speaker got the captain's backstory, so the ship's own
    computer said "before any of this, *they* were refused a berth".
    """
    said = voice_sim.speak(game, checks.words(key, "key", 80, required=True),
                           persona=checks.words(persona, "persona", 40),
                           situation=checks.words(situation, "situation", 40),
                           name=checks.words(name, "name", 80),
                           fact=checks.words(fact, "fact", 300),
                           kind=checks.words(kind, "kind", 40))
    return {"ok": True, **said}


#: Salience runs from a passing remark to a lifelong grudge; events write
#: 0.3 to 2. Five is room for anything an event would, and finite.
MOST_SALIENCE = 5.0


@verb("remember", "Write a memory against somebody, as an event would.",
      acts=True)
def remember(game, key: str, kind: str, text: str, salience: float = 1.0,
             name: str = "", entity: str = "captain") -> dict:
    made = memory_sim.note(game, checks.words(key, "key", 80, required=True),
                           checks.words(kind, "kind", 40, required=True),
                           checks.words(text, "text", 400, required=True),
                           checks.amount(salience, "salience", MOST_SALIENCE,
                                         inclusive=True),
                           name=checks.words(name, "name", 80),
                           entity=checks.words(entity, "entity", 40))
    return {"ok": True, "id": made.id,
            "impression": memory_sim.impression_of(game, key)}


@verb("minds", "Who remembers you, and what they think.")
def minds(game) -> dict:
    return {"ok": True, "minds": [
        {"key": mind.key, "name": mind.name, "kind": mind.kind,
         "impression": round(impression, 1), "memories": len(mind.memories),
         "grudge": [m.text for m in mind.grudge()[:3]]}
        for mind, impression in memory_sim.summary(game)]}


@verb("waiting", "Every question holding the game up: envoy, demand, aftermath.")
def waiting(game) -> dict:
    """What is on the bridge wanting an answer.

    A driven session used to have no way to see, let alone answer, an envoy
    or a territorial demand — and both stop the clock (`clock.wait_days`)
    and lock the window (`MainWindow.go`). So a power sending somebody round
    deadlocked the bridge: every wait returned nought days for ever, with
    nothing in the protocol able to clear it.
    """
    out = {"ok": True}
    envoy = getattr(game, "envoy", None)
    if envoy is not None and not envoy.over:
        out["envoy"] = {
            "kind": envoy.kind, "faction": envoy.faction,
            "rival": envoy.rival, "credits": envoy.credits,
            "goods": envoy.goods, "amount": envoy.amount,
            "expires": envoy.expires,
            "answers": ["accept", "push", "refuse"]}
    demand = getattr(game, "demand", None)
    if demand is not None and not demand.over:
        from ..data.territory import ANSWERS
        out["demand"] = {
            "system_id": demand.system_id, "power": demand.power,
            "worth": demand.worth,
            "answers": [a.id for a in ANSWERS]}
    spot = legacy_sim.offer(game)
    if spot:
        out["situation"] = spot
    from . import battle
    fighting = battle.waiting_on(game)
    if fighting is not None:
        out["battle"] = fighting
    out["blocked"] = any(k in out
                         for k in ("envoy", "demand", "situation", "battle"))
    return out


@verb("reply", "Answer the envoy or the demand: accept/push/refuse, or an id.",
      acts=True)
def reply(game, choice: str, what: str = "") -> dict:
    from ..sim import approach as approach_sim
    from ..sim import territory as territory_sim
    choice = checks.words(choice, "choice", 40, required=True)
    what = checks.words(what, "what", 20)
    envoy = getattr(game, "envoy", None)
    demand = getattr(game, "demand", None)
    if what == "envoy" or (not what and envoy is not None and not envoy.over):
        if envoy is None or envoy.over:
            return {"ok": False, "why": "No envoy is waiting."}
        return approach_sim.answer(game, envoy, choice)
    if demand is None or demand.over:
        return {"ok": False, "why": "Nothing is waiting on an answer."}
    system = game.galaxy.systems[demand.system_id]
    return territory_sim.answer(game, system, demand.power, choice)


@verb("situation", "The aftermath question waiting on an answer, if any.")
def situation(game) -> dict:
    waiting = legacy_sim.offer(game)
    return {"ok": True, "waiting": bool(waiting), **waiting} if waiting \
        else {"ok": True, "waiting": False}


@verb("answer", "Answer the waiting aftermath question by index.", acts=True)
def answer(game, index: int) -> dict:
    # From nought: `legacy.answer` checks the top of the range and a
    # negative index used to reach round to the last answer on the card.
    return legacy_sim.answer(game, checks.whole(index, "index", 0, 99))


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
    given = command.get("args")
    if given is None:
        given = {}
    if not isinstance(given, dict) or not all(isinstance(k, str)
                                              for k in given):
        return {"ok": False, "why": "args is an object of named arguments."}
    args = dict(given)
    allowed = {p for p in inspect.signature(fn).parameters if p != "game"}
    unknown = set(args) - allowed
    if unknown:
        return {"ok": False,
                "why": f"{name} does not take {sorted(unknown)}.",
                "args": sorted(allowed)}
    if name in ACTS:
        over = checks.ended(game)
        if over:
            return {"ok": False, "why": over, "ended": True}
        from . import afoot, battle
        if name not in battle.ORDERS_VERBS and battle.current(game) is not None:
            return {"ok": False, "blocked": True,
                    "why": "You are in an engagement: `fight` it through "
                           "first (`waiting` shows it)."}
        if name not in afoot.AFOOT_VERBS and afoot.blocking(game):
            return {"ok": False, "blocked": True,
                    "why": "A party is out on a deck: bring them back "
                           "first (`afoot_look`)."}
    try:
        return plain(fn(game, **args))
    except Refused as err:
        return {"ok": False, "why": str(err), "args": sorted(allowed)}
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


# The engagement's verbs, `fight` and `prize`, and a walk's (`bridge/afoot`)
# register themselves on import.
# Imported last because they register through `verb` above.
from . import battle as _battle  # noqa: E402,F401
from . import afoot as _afoot  # noqa: E402,F401
