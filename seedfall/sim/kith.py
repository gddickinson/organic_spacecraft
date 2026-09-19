"""The Kith: first contact, the lexicon, and what understanding opens.

A living people of the Cradle (`data/kith.py`), met the first time a hull
enters it. Everything a captain can do with them is gated on **the lexicon**
— twenty-four signs in four domains, each understood from 0 to 1 — and every
act carries a **stated** chance of being misread, which costs standing and
sometimes brings the colony's bells out. The odds a screen shows are the odds
`roll` uses: `misread_odds` is the one door for both.

Four ways to learn, each one function here:

- **listening** at a gathering — days, the science officer and the array
  (`listen`, and the day's share in `tick`); it stops at `LISTEN_CAP`;
- **the decoding bench** (`sim/minigames.Decoding`) on a recording of a Kith
  phrase — a solve teaches that phrase's signs (`begin_decode`, `decoded`);
- **exchanges** — every gift teaches the signs it was answered in
  (`sim/kith_acts.offer`);
- **watching their stars** — a survey in the Cradle that sees something
  teaches the Place signs (`observe`, called by `sim/survey.perform`).

The gift economy itself — offers, asks, debts, berths, passage and the accord
— is in `sim/kith_acts.py`; where the gatherings are, in `sim/kith_world.py`.

**For a later milestone system:** `progress(game)` is the one reading of how
far a chronicle has come with the Kith.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from ..core.rng import RNG
from ..core.save import register
from ..data import kith as data
from . import kith_world as world


@register
@dataclass
class KithState:
    """Everything a chronicle knows about the Kith, and owes them."""

    #: The day of first contact, and where; -1 until then.
    met_day: int = -1
    met_at: int = -1
    #: Sign id → comprehension, 0..1. A sign not here is 0.
    lexicon: dict = field(default_factory=dict)
    #: Gathering (system id, as a string) → good → [reaction, "seen" or
    #: "told", the odds it was misheard at when it was told].
    known_prefs: dict = field(default_factory=dict)
    #: Gathering → [value owed, day it was incurred, insulted yet].
    debts: dict = field(default_factory=dict)
    #: Gathering → the worth of every gift it has taken from you.
    given: dict = field(default_factory=dict)
    #: Gathering → the day a gift there last earned standing.
    thanked: dict = field(default_factory=dict)
    #: Gathering → tonnes of songglass it is keeping for a full hold.
    held: dict = field(default_factory=dict)
    #: Gatherings the captain has been to or been told the way to.
    charted: list = field(default_factory=list)
    #: The day of the accord; -1 until then.
    accord: int = -1
    #: 0 none, 1 a pilot offered, 2 a pilot aboard.
    pilot: int = 0
    #: Recordings banked for the bench, and the listening in hand:
    #: [gathering id, days left, rate] or empty.
    recordings: float = 0.0
    session: list = field(default_factory=list)
    #: Counters: every act rolled (the key of its roll), exchanges made,
    #: misreadings suffered, recordings solved.
    acts: int = 0
    exchanges: int = 0
    misreads: int = 0
    decoded: int = 0
    #: [day, kind, words], newest last, capped.
    history: list = field(default_factory=list)


HISTORY_KEEP = 60


def ensure(game) -> KithState:
    if getattr(game, "kith", None) is None:
        game.kith = KithState()
    return game.kith


def met(game) -> bool:
    state = getattr(game, "kith", None)
    return state is not None and state.met_day >= 0


def standing(game) -> float:
    return float(game.rep.get(data.FACTION, 0.0))


def note(state: KithState, day: int, kind: str, words: str) -> None:
    state.history.append([int(day), kind, words])
    del state.history[:-HISTORY_KEEP]


# ── the lexicon ────────────────────────────────────────────────────────────

def comprehension(game, sign_id: str) -> float:
    state = getattr(game, "kith", None)
    if state is None:
        return 0.0
    return float(state.lexicon.get(sign_id, 0.0))


def domain(game, domain_id: str) -> float:
    """A domain's comprehension: the mean of its six signs.

    Rounded to nine places so six signs at 0.4 read 0.4 at the gate, not the
    0.39999999999999997 a float sum makes of them.
    """
    signs = [s for s in data.SIGNS if s.domain == domain_id]
    return round(sum(comprehension(game, s.id) for s in signs) / len(signs), 9)


def domains(game) -> dict:
    return {d: domain(game, d) for d in data.DOMAINS}


def teach(state: KithState, sign_id: str, share: float,
          cap: float = 1.0) -> float:
    """Close `share` of the gap between a sign and `cap`. Returns the gain."""
    have = float(state.lexicon.get(sign_id, 0.0))
    if have >= cap or share <= 0:
        return 0.0
    gain = (cap - have) * min(1.0, share)
    state.lexicon[sign_id] = have + gain
    return gain


# ── what is understood opens, and how likely a misreading is ───────────────

def _fitted(ship, part_id: str) -> bool:
    return part_id in ship.fitted and part_id not in ship.disabled


def _grasp(game, act: str) -> float:
    """The comprehension an act is read on."""
    if act in ("gift", "ask"):
        return domain(game, "exchange")
    if act in ("berth", "passage"):
        return min(domain(game, "place"), domain(game, "intent"))
    return min(domains(game).values())


def misread_odds(game, act: str) -> float:
    """The stated chance an act is misread. The roll uses this number."""
    gap = 1.0 - _grasp(game, act)
    odds = min(data.MISREAD_MAX, data.MISREAD_SCALE * gap * gap)
    from .adaptation import family
    odds *= data.WARINESS.get(family(game.ship), 1.0)
    if _fitted(game.ship, "light_throat"):
        odds *= data.THROAT_MISREAD
    return round(min(data.MISREAD_MAX, odds), 4)


def can(game, act: str) -> tuple[bool, str]:
    """May this act be attempted here? The gate every button greys on."""
    if not met(game):
        return False, "Nobody aboard has met the Kith."
    if not world.is_gathering(game.system):
        return False, "There is no Kith gathering in this system."
    if act in ("gift", "ask"):
        have = domain(game, "exchange")
        if have < data.TRADE_NEEDS:
            return False, (f"Exchange is understood to {have:.2f}; a gift "
                           f"needs {data.TRADE_NEEDS:.1f}. Listen, or work a "
                           "recording on the bench.")
        return True, ""
    if act in ("berth", "passage"):
        place, intent = domain(game, "place"), domain(game, "intent")
        if min(place, intent) < data.PASSAGE_NEEDS:
            return False, (f"Place {place:.2f} and Intent {intent:.2f}: "
                           f"asking for a {act} needs both at "
                           f"{data.PASSAGE_NEEDS:.1f}.")
        if act == "berth" and standing(game) < data.TOLERATED:
            return False, (f"They do not close round a hull they do not yet "
                           f"tolerate (standing {standing(game):+.0f} of "
                           f"{data.TOLERATED}).")
        return True, ""
    if act == "accord":
        if game.kith.accord >= 0:
            return False, "The accord is already sung."
        low = {d: v for d, v in domains(game).items()
               if v < data.ACCORD_NEEDS}
        if low:
            said = ", ".join(f"{data.DOMAINS[d]} {v:.2f}"
                             for d, v in low.items())
            return False, (f"An accord needs every domain at "
                           f"{data.ACCORD_NEEDS:.1f}: {said}.")
        if standing(game) < data.ACCORD_STANDING:
            return False, (f"An accord needs standing {data.ACCORD_STANDING}"
                           f" (Trusted); you have {standing(game):+.0f}.")
        return True, ""
    return False, f"No such act: {act}."


def roll(game, odds: float) -> bool:
    """Was this act misread? Drawn from the act's own key — never from
    `game.rng`, so a Kith act moves no other luck in the chronicle."""
    state = ensure(game)
    state.acts += 1
    missed = RNG(f"{game.seed}:kith:act:{state.acts}").next() < odds
    if missed:
        state.misreads += 1
    return missed


def fight(game, why: str) -> dict:
    """The colony answers a misreading with its bells out: an encounter."""
    from . import encounters
    rng = RNG(f"{game.seed}:kith:fight:{ensure(game).acts}")
    enemy = encounters.make_enemy(rng, data.FACTION,
                                  encounters.draw_threat(game, rng))
    # A stem is named for its song, not from the Freeholds' list of hulls.
    enemy["ship"].name = f"{rng.pick(data.NAME_FIRST)}-{rng.pick(data.NAME_LAST)}"
    enemy["name"] = (f"Kith {enemy['ship'].chassis_def.name} "
                     f"«{enemy['ship'].name}»")
    return {"enemy": enemy, "no_parley": False,
            "intro": (f"{why} The nearest bodies of the colony turn their "
                      "bells toward you, and every light on the stem goes "
                      "the same colour.")}


# ── first contact ──────────────────────────────────────────────────────────

def arrive(game) -> dict | None:
    """A hull has arrived somewhere. Called by `sim/flight.arrive_in_system`.

    In the Cradle: the gatherings are placed if an older save has none, the
    first arrival is the first sighting, and a gathering you reach is on
    your chart from then on.
    """
    system = game.system
    if getattr(system, "region", "") != data.CRADLE:
        return None
    world.ensure(game)
    said = None if met(game) else first_contact(game)
    if world.is_gathering(system) and system.id not in game.kith.charted:
        game.kith.charted.append(system.id)
    return said


def first_contact(game) -> dict:
    """The first sighting: once, on entering the Cradle."""
    from . import comms
    state = ensure(game)
    if state.met_day >= 0:
        return {"ok": False, "why": "They have been met."}
    state.met_day, state.met_at = int(game.day), game.system.id
    text = data.FIRST_SIGHTING.format(system=game.system.name)
    game.add_log(text, "good")
    note(state, game.day, "contact", text)
    comms.send(game, "kith:sighting", "The watch", "personal",
               "First sighting: the Kith", text)
    return {"ok": True, "day": state.met_day, "at": state.met_at,
            "text": text}


# ── listening ──────────────────────────────────────────────────────────────

def listen_rate(game) -> float:
    """A day's listening at full attention, before the domain weights."""
    sci = max((o.level for o in game.officers if o.stat == "science"),
              default=0)
    sensor = float(getattr(game.ship_stats, "sensor", data.SENSOR_REF))
    eyes = max(data.SENSOR_FLOOR, min(data.SENSOR_CAP,
                                      sensor / data.SENSOR_REF))
    rate = data.LISTEN_RATE * (1.0 + data.SCIENCE_WORTH * sci) * eyes
    if _fitted(game.ship, "light_throat"):
        rate *= data.THROAT_LISTEN
    return rate


def _hear(lexicon: dict, rate: float, share: float) -> None:
    """One day of the song, into a lexicon (a real one or a preview's copy)."""
    for sign in data.SIGNS:
        have = float(lexicon.get(sign.id, 0.0))
        if have >= data.LISTEN_CAP:
            continue
        step = min(1.0, rate * data.LISTEN_WEIGHT[sign.domain] * share)
        lexicon[sign.id] = have + (data.LISTEN_CAP - have) * step


def listen_preview(game, days: int) -> dict:
    """What `listen` will teach, day by day as the clock will run it."""
    ok, why = (False, "Nobody aboard has met the Kith.") if not met(game) \
        else (True, "")
    if ok and not world.is_gathering(game.system):
        ok, why = False, "Listening needs a gathering to listen to."
    days = max(0, int(days))
    rate = listen_rate(game)
    state = getattr(game, "kith", None)
    now = dict(state.lexicon) if state is not None else {}
    after = dict(now)
    for _ in range(days):
        _hear(after, rate, 1.0)
    shift = {d: 0.0 for d in data.DOMAINS}
    for sign in data.SIGNS:
        shift[sign.domain] += (after.get(sign.id, 0.0)
                               - now.get(sign.id, 0.0)) / 6.0
    return {"ok": ok and days > 0, "why": why or ("" if days else
                                                   "Listen for how long?"),
            "days": days, "rate": rate, "gain": shift,
            "recordings": days / data.DAYS_PER_RECORDING}


def listen(game, days: int) -> dict:
    """Attend a gathering for `days`: the clock runs, and the song is heard."""
    said = listen_preview(game, days)
    if not said["ok"]:
        return {"ok": False, "why": said["why"]}
    state = ensure(game)
    before = domains(game)
    state.session = [game.system.id, said["days"], said["rate"]]
    game.advance_days(said["days"])
    state.session = []
    gain = {d: v - before[d] for d, v in domains(game).items()}
    game.add_log(f"{said['days']} days attending the gathering at "
                 f"{game.system.name}: the song is a little less strange.",
                 "good")
    return {"ok": True, "days": said["days"], "gain": gain}


def tick(game, n: int) -> None:
    """The day's share of the Kith: listening, recordings, and debts.

    One line in `core/sectortime.reckoning`. Cheap everywhere but the
    Cradle: a chronicle that has not met them pays one attribute read.
    """
    state = getattr(game, "kith", None)
    if state is None:
        if getattr(game.system, "region", "") == data.CRADLE:
            arrive(game)
        return
    if (state.session and state.session[0] == game.location_id
            and state.session[1] > 0):
        attended = min(float(n), float(state.session[1]))
        for _ in range(max(1, round(attended))):
            _hear(state.lexicon, float(state.session[2]), 1.0)
        state.session[1] -= attended
        state.recordings += attended / data.DAYS_PER_RECORDING
    elif met(game) and world.is_gathering(game.system):
        for _ in range(max(1, round(n))):
            _hear(state.lexicon, listen_rate(game), data.PASSIVE_SHARE)
    from .kith_acts import come_due
    come_due(game)


# ── the bench ──────────────────────────────────────────────────────────────

def phrases(game) -> list:
    """Every phrase with how well its signs are understood, least first."""
    rows = [(p, sum(comprehension(game, s) for s in p.signs) / len(p.signs))
            for p in data.PHRASES]
    return sorted(rows, key=lambda row: (row[1], row[0].id))


def bench_glyphs(tech_id: str | None) -> list | None:
    """The alphabet the bench shows for a Kith recording, or None.

    The phrase's four signs, then the next signs in the table that are not
    in it — six in all, enough for the widest alphabet the bench deals.
    """
    if not tech_id or not tech_id.startswith(data.BENCH_TAG):
        return None
    phrase = data.PHRASES_BY_ID.get(tech_id[len(data.BENCH_TAG):])
    if phrase is None:
        return None
    ids = list(phrase.signs)
    start = [s.id for s in data.SIGNS].index(phrase.signs[0])
    ring = [s.id for s in data.SIGNS[start:] + data.SIGNS[:start]]
    ids += [sid for sid in ring if sid not in ids][:6 - len(ids)]
    return [data.SIGNS_BY_ID[sid].glyph for sid in ids]


def begin_decode(game, phrase_id: str) -> dict:
    """Put a recording of a Kith phrase on the bench. Spends one recording."""
    from . import minigames
    if not met(game):
        return {"ok": False, "why": "Nobody aboard has met the Kith."}
    phrase = data.PHRASES_BY_ID.get(phrase_id)
    if phrase is None:
        return {"ok": False, "why": f"No such phrase: {phrase_id}."}
    state = ensure(game)
    if state.recordings < 1.0:
        return {"ok": False, "why": (
            f"No recording to work: attend a gathering "
            f"{data.DAYS_PER_RECORDING} days for one.")}
    state.recordings -= 1.0
    bench = minigames.begin_decoding(game, "a Kith song",
                                     data.BENCH_TAG + phrase.id)
    return {"ok": True, "decoding": bench, "phrase": phrase}


def decoded(game, tech_id: str, result: dict) -> dict:
    """The bench closed on a Kith recording: a solve teaches its phrase.

    Called by `sim/minigames.finish_decoding` for a Kith tag.
    """
    phrase = data.PHRASES_BY_ID.get(tech_id[len(data.BENCH_TAG):])
    out = {"back": "port", "kith": True, "taught": {}}
    if phrase is None or not result.get("won"):
        return out
    state = ensure(game)
    share = float(result["points"]) / data.DECODE_SCALE
    out["taught"] = {s: teach(state, s, share) for s in phrase.signs}
    state.decoded += 1
    out["text"] = (f"Decoded a Kith song: “{phrase.gloss}” "
                   f"({result['points']} points).")
    note(state, game.day, "bench", out["text"])
    game.add_log(out["text"], "good")
    return out


def observe(game, research: float) -> float:
    """A survey in the Cradle saw something: they sing about their stars.

    Called by `sim/survey.perform`. Returns what the Place signs gained.
    """
    if research <= 0 or not met(game) or \
            getattr(game.system, "region", "") != data.CRADLE:
        return 0.0
    state = game.kith
    return sum(teach(state, s, data.OBSERVE_TEACH)
               for s in data.OBSERVE_SIGNS)


# ── what other systems ask of the Kith ─────────────────────────────────────

def refusal(system) -> str:
    """Why a counter here will not buy or sell, or "" if it will.

    Asked by `sim/enforce.may_trade`, the one door every trade comes through.
    """
    market = getattr(system, "market", None)
    if market is None or not getattr(market, "gift_economy", False):
        return ""
    return ("The Kith post no prices and sell nothing over a counter. Offer "
            "a gift at the gathering instead.")


def synergy(ship) -> list:
    """A Kith graft set in a hull that grew the adaptation it answers: the
    extra effects. Read by `sim/adaptation.fx`, the one door for the body."""
    have = set(getattr(ship, "adaptations", ()) or ())
    return [effect for graft in data.GRAFTS
            if _fitted(ship, graft.part) and graft.pairs_with in have
            for effect in graft.bonus]


def grows(game, system, chassis) -> bool:
    """Will a gathering here grow this hull? Only a Kith hull, after the
    accord. Asked by `sim/shipyard.can_build_here`."""
    state = getattr(game, "kith", None)
    return (chassis.tech == data.ACCORD_GATE and state is not None
            and state.accord >= 0 and world.is_gathering(system))


def progress(game) -> dict:
    """How far this chronicle has come with the Kith, for a milestone system.

    `met` (first contact made), `comprehension` (domain → 0..1), `accord`
    (a treaty sung) and `exchanges` (gifts answered). The lexicon is
    complete when every domain reads 1.0.
    """
    state = getattr(game, "kith", None)
    return {"met": met(game), "comprehension": domains(game),
            "accord": bool(state is not None and state.accord >= 0),
            "exchanges": state.exchanges if state is not None else 0}
