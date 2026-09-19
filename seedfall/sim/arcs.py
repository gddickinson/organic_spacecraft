"""Officer arcs: who wants what, when it comes round, and what finishing buys.

The stories are `data/arcs.py`; their words and costed answers are
`sim/arc_beats.py`; where they send the ship is `sim/arc_places.py`. This is
the door: dealing an arc, the daily turn of every story (`tick`, one line in
sector time), the answer (`answered`, which `sim/comms.answer` calls for a
beat's despatch — the existing machinery, so the Despatches screen and the
bridge's `answer_signal` both do it), lapses, and the signatures the rest of
the game reads.

A story moves through three states per beat, all on the officer
(`arc_state`): **scheduled** (`next`, the day it arms), **armed** (`due`,
the day it lapses if its place, event or loyalty never comes), and **open**
(`sig`, a despatch asking, and `until`). Nothing here draws the chronicle's
luck: dealing, gaps and places use the officer's own keys
(`{seed}:arc:{officer.id}…`), so a story is the same whenever it is looked
at, and looking at it — the crew tab, the Codex — changes nothing.

**Nobody leaves the ship from here.** A neglected last beat costs loyalty
(`data/arcs.LAPSE_LAST`); if that takes an officer below the walkout line,
`loyalty.tick` — the one path — lets them go.
"""

from __future__ import annotations

from ..core.rng import RNG
from ..data import arcs as data
from ..data.arcs import ARCS, ARCS_BY_ID, SIGNATURES
from . import arc_beats, arc_places
from . import loyalty as loyalty_sim

#: Who a beat's despatch is from, on the wire: `arc:<officer id>`.
SENDER = "arc:"
#: What a despatch nobody answered in time is marked with.
LAPSED = "lapsed"
#: Effect keys that are floors rather than lifts: two officers holding one
#: would not make the floor twice as high.
FLOORS = ("freehold_floor", "morale_floor")


def _state(officer) -> dict:
    held = getattr(officer, "arc_state", None)
    if held is None:
        held = officer.arc_state = {}
    return held


def _active(game) -> list:
    from . import lifespan
    return lifespan.active(getattr(game, "officers", None))


def _book(game) -> dict:
    """What outlives an officer: counters and the finished stories."""
    return game.flags.setdefault("arcs", {"fights": 0, "record": [],
                                          "answered": 0, "lapsed": 0})


# ── dealing ────────────────────────────────────────────────────────────────

def _draw(game, officer, taken: set) -> str:
    """This officer's story: their own shuffle of the twelve, the first not
    already on the bridge — two deserters on one bridge reads as a bug."""
    order = RNG(f"{game.seed}:arc:{officer.id}").shuffle([a.id for a in ARCS])
    return next((a for a in order if a not in taken), order[0])


def planned(game) -> dict:
    """officer id -> arc id: what each officer has, or will be dealt on the
    next tick. Pure — the crew tab reads this, so an officer from a save
    written before arcs existed shows the story they are about to get."""
    taken = {o.arc for o in game.officers if getattr(o, "arc", None)}
    out = {}
    for officer in game.officers:
        arc = getattr(officer, "arc", None)
        if not arc:
            arc = _draw(game, officer, taken)
            taken.add(arc)
        out[officer.id] = arc
    return out


def _gap(game, officer, beat: int) -> int:
    rng = RNG(f"{game.seed}:arc:{officer.id}:{beat}:gap")
    return rng.int(data.GAP_MIN, data.GAP_MAX)


def assign(game) -> list:
    """Deal a story to every officer without one. Returns who was dealt."""
    dealt = []
    for officer in game.officers:
        if getattr(officer, "arc", None):
            continue
        officer.arc = planned(game)[officer.id]
        officer.arc_beat = 0
        officer.arc_state = {"next": max(int(game.day), data.QUIET_DAYS)
                             + _gap(game, officer, 0), "chose": []}
        dealt.append(officer)
    return dealt


# ── the day ────────────────────────────────────────────────────────────────

def _tutorial_quiet(game) -> bool:
    """The curriculum's first chapters teach flying; a story would talk over
    the lesson, so its clocks stand still until then."""
    from . import tutorial
    if not tutorial.running(game):
        return False
    from ..data.lessons import first_step_of
    return tutorial.held(game).step < first_step_of(data.QUIET_CHAPTER)


def tick(game, n: float = 1, r=None) -> None:
    """Every story's day. Draws nothing from `r`: the chronicle's luck is the
    world's, and a story is keyed on its officer."""
    assign(game)
    quiet = _tutorial_quiet(game)
    for officer in _active(game):
        if officer.arc_beat >= len(ARCS_BY_ID[officer.arc].beats):
            continue
        st = _state(officer)
        if quiet:
            for key in ("next", "due", "until"):
                if st.get(key) is not None:
                    st[key] += n
            continue
        _step(game, officer, st, n)
    _close_orphans(game)
    _keep(game)


def _window(beat) -> int:
    if beat.trigger == "place":
        return data.RACE_DAYS if beat.arg == "race" else data.PLACE_DAYS
    return {"event": data.EVENT_DAYS, "loyalty": data.LOYALTY_DAYS}.get(
        beat.trigger, 0)


def _count(game, event: str) -> float:
    """A counter that only rises, for an event beat to wait on."""
    if event == "fight":
        return float(game.flags.get("arcs", {}).get("fights", 0))
    if event == "burn":
        from . import responses
        return responses.fought(game)
    return float(max((c.id for c in game.colonies), default=0))


def _step(game, officer, st: dict, n: float) -> None:
    beat = ARCS_BY_ID[officer.arc].beats[officer.arc_beat]
    if st.get("sig"):
        if game.day > st["until"]:
            _lapse(game, officer, st)
        return
    if st.get("armed") is None:
        if game.day < st.get("next", 0):
            return
        _arm(game, officer, st, beat)
    if isinstance(st.get("place"), str):
        found = arc_places.resolve(game, st["place"], officer.id,
                                   officer.arc_beat)
        if isinstance(found, str):
            st["due"] += n              # past an unopened rim: it waits
            return
        st["place"] = found
    if _met(game, officer, st, beat):
        _open(game, officer, st, beat)
    elif beat.trigger == "place" and arc_places.beyond(game, st["place"]):
        st["due"] += n                  # out of the drive's reach: it waits
    elif game.day > st["due"]:
        _lapse(game, officer, st)


def _arm(game, officer, st: dict, beat) -> None:
    st["armed"] = int(game.day)
    st["place"] = (arc_places.resolve(game, beat.arg, officer.id,
                                      officer.arc_beat)
                   if beat.trigger == "place" else None)
    st["base"] = _count(game, beat.arg) if beat.trigger == "event" else 0
    st["due"] = int(game.day) + _window(beat)
    if beat.trigger != "date":
        # What they want, said once when it arms — the beat itself arrives
        # when the place, the event or their trust does.
        from . import comms
        arc = ARCS_BY_ID[officer.arc]
        said = (f"{officer.name.split()[0]} "
                f"{arc_beats.hint(game, officer, beat, st['place'])}.")
        if isinstance(st["place"], str) or arc_places.beyond(game,
                                                             st["place"]):
            said += " " + arc_places.waiting_for(game, st["place"])
        comms.send(game, f"{SENDER}{officer.id}", officer.name, "personal",
                   arc.title, said, aboard=True)


def _met(game, officer, st: dict, beat) -> bool:
    if beat.trigger == "place":
        return st["place"] is None or game.location_id == st["place"]
    if beat.trigger == "loyalty":
        return loyalty_sim.loyalty_of(officer) >= data.LOYAL_AT
    if beat.trigger == "event":
        return _count(game, beat.arg) > st.get("base", 0)
    return True


def _open(game, officer, st: dict, beat) -> None:
    """The beat arrives: a despatch from them, asking."""
    from . import comms
    arc = ARCS_BY_ID[officer.arc]
    replies = tuple((c.key, f"{c.words} ({_stated(c)})" if _stated(c)
                     else c.words) for c in beat.choices)
    sig = comms.send(game, f"{SENDER}{officer.id}", officer.name, "personal",
                     f"{arc.title}: {beat.title}",
                     arc_beats.words(game, officer, beat, st.get("place"),
                                     officer.arc_beat),
                     replies=replies, aboard=True)
    st["sig"] = sig.id
    st["until"] = int(game.day) + data.ANSWER_DAYS
    book = _book(game)
    book["opened"] = book.get("opened", 0) + 1


def _stated(choice) -> str:
    """The costs a button carries — the full preview is on the board."""
    bits = [("+" if choice.credits > 0 else "−") + f"₡{abs(choice.credits):,}"
            ] if choice.credits else []
    bits += [f"{'+' if t > 0 else '−'}{abs(t):g} t {cid}"
             for cid, t in choice.cargo]
    bits += [f"{p.title()} {'+' if d > 0 else '−'}{abs(d):g}"
             for p, d in choice.rep]
    return ", ".join(bits)


def _signal(game, sig_id):
    return next((s for s in getattr(game, "signals", ()) if s.id == sig_id),
                None)


def _lapse(game, officer, st: dict) -> None:
    arc = ARCS_BY_ID[officer.arc]
    index = officer.arc_beat
    cost = (data.LAPSE_FIRST, data.LAPSE_SECOND, data.LAPSE_LAST)[index]
    loyalty_sim.shift(officer, -cost)
    sig = _signal(game, st.get("sig"))
    if sig is not None and not sig.answered:
        sig.answered, sig.read = LAPSED, True
    st.setdefault("chose", []).append("")
    _book(game)["lapsed"] += 1
    game.add_log(f"{officer.name} stopped waiting on you — "
                 f"{arc.title.lower()}: {arc.beats[index].title.lower()}.",
                 "warn")
    _advance(game, officer, st)


def _advance(game, officer, st: dict) -> None:
    officer.arc_beat += 1
    for key in ("armed", "place", "due", "sig", "until", "base"):
        st.pop(key, None)
    if officer.arc_beat < len(ARCS_BY_ID[officer.arc].beats):
        st["next"] = int(game.day) + _gap(game, officer, officer.arc_beat)
        return
    st.pop("next", None)
    _book(game)["record"].append({
        "officer": officer.name, "id": officer.id, "arc": officer.arc,
        "signature": officer.signature or "", "day": int(game.day),
        "chose": list(st.get("chose", ()))})


def _close_orphans(game) -> None:
    """A question from somebody no longer standing a watch stops asking."""
    here = {o.id for o in _active(game)}
    for sig in getattr(game, "signals", ()):
        if sig.frm.startswith(SENDER) and sig.asks \
                and int(sig.frm[len(SENDER):]) not in here:
            sig.answered, sig.read = LAPSED, True


def _keep(game) -> None:
    """The signatures that are standing orders rather than lifts: a floor
    under the Freeholds' regard and the crew's morale, and a share's pay."""
    fx = signature_effects(game.officers)
    floor = fx.get("freehold_floor", 0.0)
    if floor and game.rep.get("freeholds", 0.0) < floor:
        game.rep["freeholds"] = floor
    low = fx.get("morale_floor", 0.0)
    if low and game.ship.morale < low:
        game.ship.morale = low
    for officer in _active(game):
        st = _state(officer)
        if officer.signature != "landed" or st.get("variant") != "claim":
            continue
        while game.day - st.get("paid", game.day) >= 30:
            st["paid"] += 30
            from . import exchequer
            purse = exchequer.purse(game, "freeholds")
            paid = max(0.0, min(float(data.LANDED_MONTHLY), purse.credits))
            purse.credits -= paid
            game.credits += paid
            st["earned"] = st.get("earned", 0.0) + paid


# ── the answer ─────────────────────────────────────────────────────────────

def officer_of(game, sender: str):
    """The officer a beat's despatch is from, if they are still aboard."""
    if not sender.startswith(SENDER):
        return None
    oid = int(sender[len(SENDER):])
    return next((o for o in _active(game) if o.id == oid), None)


def _open_beat(game, sig):
    """(officer, beat) for the despatch still waiting on an answer, or None
    — a beat that lapsed, or an officer who left."""
    officer = officer_of(game, sig.frm)
    if officer is None or _state(officer).get("sig") != sig.id:
        return None
    arc = ARCS_BY_ID[officer.arc]
    return officer, arc.beats[officer.arc_beat]


def preview(game, sig, key: str) -> dict:
    """What answering `sig` with `key` will do — `arc_beats.preview`, found
    from the despatch. {} for anything that is not an open beat."""
    held = _open_beat(game, sig)
    if held is None:
        return {}
    officer, beat = held
    choice = next((c for c in beat.choices if c.key == key), None)
    if choice is None:
        return {}
    said = arc_beats.preview(game, officer, choice)
    said["line"] = arc_beats.summary(said, officer.name.split()[0])
    return said


def answered(game, sig, key: str) -> dict:
    """The captain's answer to a beat — done, not merely recorded.

    Called by `sim/comms.answer` before it marks the despatch answered;
    refusing here (the treasury is short, the hold is short) refuses there.
    """
    held = _open_beat(game, sig)
    if held is None:
        return {"ok": False, "why": "That is no longer being asked."}
    officer, beat = held
    choice = next((c for c in beat.choices if c.key == key), None)
    if choice is None:
        return {"ok": False, "why": "They did not offer that."}
    said = arc_beats.perform(game, officer, choice)
    if said["why"]:
        return {"ok": False, **said}
    st = _state(officer)
    st.setdefault("chose", []).append(key)
    _book(game)["answered"] += 1
    arc = ARCS_BY_ID[officer.arc]
    game.add_log(choice.outcome or f"{officer.name}, {arc.title.lower()}: "
                 f"{choice.words.lower()}.", "good" if said["loyalty"] >= 0
                 else "warn")
    if choice.signature:
        _grant(game, officer, arc, key)
    _advance(game, officer, st)
    game.recompute()                    # a signature can move the stats
    return {"ok": True, "why": "", **said}


def _grant(game, officer, arc, key: str) -> None:
    spec = SIGNATURES[arc.signature]
    officer.signature = spec.id
    st = _state(officer)
    st["variant"] = key
    st["paid"] = int(game.day)
    if spec.id == "dead_reckoning":
        # The chart they finished: every star of the Hollow, as a bought
        # chart is (`intel.ensure`).
        from ..world import regions as world_regions
        from . import intel
        charts = intel.ensure(game)
        charts.extend(s.id for s in world_regions.systems_of(
            game.galaxy, "hollow") if s.id not in charts)
    # The standing orders among them (a floor, a share's pay) take hold on
    # the next day's `_keep`, not inside the answer — so what the answer did
    # is exactly what its preview said.
    game.add_log(f"{officer.name} is {spec.name} now: {spec.blurb}", "good")


def witness(game, event: str) -> None:
    """Something an event beat can wait on has happened. `aftermath.resolve`
    reports every engagement it settles here."""
    if event == "fight":
        _book(game)["fights"] += 1


# ── what the rest of the game reads ────────────────────────────────────────

def signature_effects(officers) -> dict:
    """What the bridge's signatures add, by effect key — the parallel of
    `crew.trait_effects`, read by `ship.stats` and the named systems. Only
    officers still standing a watch; a floor is the highest, not the sum."""
    out: dict = {}
    for officer in officers or []:
        spec = SIGNATURES.get(getattr(officer, "signature", None) or "")
        if spec is None or getattr(officer, "retired", False):
            continue
        variant = (getattr(officer, "arc_state", None) or {}).get("variant")
        for key, value in spec.effects:
            if key == "landed" and variant != "claim":
                continue
            out[key] = (max(out.get(key, 0.0), value) if key in FLOORS
                        else out.get(key, 0.0) + value)
    return out


def comprehension(game) -> float:
    """What Light-tongued adds to understanding the Kith: the whole lift
    with the Kith in the game, nothing without them (the comms bonus is in
    `ship.stats` either way). For the Kith to multiply by `1 + this`."""
    if getattr(game, "kith", None) is None:
        return 0.0
    return signature_effects(game.officers).get("tongue", 0.0)


def status(game, officer) -> dict:
    """One officer's story for a screen: title, marks, what they want, how
    long is left. Pure."""
    arc = ARCS_BY_ID[planned(game).get(officer.id) or ARCS[0].id]
    st = getattr(officer, "arc_state", None) or {}
    beat_i = getattr(officer, "arc_beat", 0) if getattr(officer, "arc", None) \
        else 0
    chose = list(st.get("chose", ()))
    marks = "".join("●" if c else "×" for c in chose) + "○" * (3 - len(chose))
    out = {"arc": arc, "beat": beat_i, "marks": marks, "hint": "", "left": None,
           "waiting": "", "open": bool(st.get("sig")), "finished": beat_i >= 3,
           "signature": SIGNATURES.get(officer.signature or ""),
           "earned": st.get("earned", 0.0)}
    if beat_i >= 3:
        return out
    beat = arc.beats[beat_i]
    place = st.get("place")
    if st.get("sig"):
        out["hint"] = "has written to you — see Despatches"
        out["left"] = st["until"] - int(game.day)
    elif st.get("armed") is not None:
        out["hint"] = arc_beats.hint(game, officer, beat, place)
        out["left"] = st["due"] - int(game.day)
        if isinstance(place, str) or (beat.trigger == "place"
                                      and arc_places.beyond(game, place)):
            out["waiting"] = arc_places.waiting_for(game, place)
            out["left"] = None
    elif st.get("next") is not None:
        out["left"] = None
        out["hint"] = "has something on their mind"
    return out


def record(game) -> list:
    """Every story finished aboard, newest last."""
    return list(game.flags.get("arcs", {}).get("record", ()))


def progress(game) -> dict:
    """**For a renown system to read.** How much of the crew's stories this
    captain has lived through: officers holding a story now (`assigned`),
    beats answered in the whole chronicle (`beats_done`), stories finished
    with a signature (`finished`), and the signatures aboard now
    (`signatures`, names)."""
    book = game.flags.get("arcs", {})
    return {"assigned": sum(1 for o in game.officers
                            if getattr(o, "arc", None)),
            "beats_done": int(book.get("answered", 0)),
            "finished": sum(1 for row in book.get("record", ())
                            if row.get("signature")),
            "signatures": [SIGNATURES[o.signature].name
                           for o in _active(game)
                           if getattr(o, "signature", None) in SIGNATURES]}
