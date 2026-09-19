"""A beat as the captain meets it: the officer's words, and what each answer
does — stated before it is chosen, and then done exactly.

**Preview equals act.** `preview` works out every consequence of an answer
from the same numbers `perform` spends, clamps included: a gain paid out of
a power's purse is what the purse can cover, standing and loyalty stop at
their bounds, cargo taken aboard stops at the hold's room, and an officer
whose conviction is aligned with a power feels the standing move as well
(`loyalty.align`, which `Game.adjust_rep` calls). `tests/test_arcs` answers
every choice of every beat and compares.

The words are the officer's: `data/personas.py` gives the register — a
working officer's short sentences, or, for a Dry Choir lineage, the canon's
plural — and the story fills the rest.
"""

from __future__ import annotations

from ..core.rng import RNG
from ..core.util import credits as cr
from ..data.convictions import CEILING, FLOOR
from ..data.personas import PERSONAS_BY_ID
from . import arc_places
from . import loyalty as loyalty_sim


# ── what they say ──────────────────────────────────────────────────────────

def persona_of(officer):
    """The canon speaks in the plural; everybody else as an officer."""
    lineage = getattr(officer, "lineage", None) or ""
    return PERSONAS_BY_ID["choir" if lineage == "dry" else "officer"]


def _rival(game) -> str:
    """A rival the story can name — read defensively (`sim/nemeses`)."""
    try:
        from . import nemeses
        live = nemeses.live(game)
    except (ImportError, AttributeError):
        return ""
    return f"{live[0].name} was out there with us. " if live else ""


def _seat(game) -> str:
    """The Assembly's next sitting, if there is an Assembly to sit."""
    try:
        from . import assembly, assembly_session
        state = assembly.state(game)
        if state is None:
            return ""
        _power, system = assembly_session.seat(game, state)
    except (ImportError, AttributeError):
        return ""
    if system is None:
        return ""
    return (f"It goes before the Assembly at {system.name} on day "
            f"{int(state.next_day)}. ")


def _song(game) -> str:
    """The Cradle sings; with the Kith, it is the Kith singing."""
    if getattr(game, "kith", None) is not None:
        return ("The Kith are singing. To me, I think. I can almost follow "
                "it.")
    return ("The old stars are singing — the ones they told me about. I can "
            "almost follow it.")


def slots(game, officer, beat, place) -> dict:
    """Everything a beat's text may name, filled from the game as it is."""
    state = getattr(officer, "arc_state", None) or {}
    chose = list(state.get("chose", ()))
    before = chose[-1] if chose else ""
    return {"place": arc_places.name(game, place), "ship": game.ship.name,
            "hull": game.ship.chassis_def.name, "rival": _rival(game),
            "seat": _seat(game), "song": _song(game),
            "after": dict(beat.after).get(before, "")}


def words(game, officer, beat, place, beat_index: int) -> str:
    """The despatch's body, in their voice. The frame is drawn from their own
    key, so a reload says the same thing."""
    text = beat.text.format(**slots(game, officer, beat, place))
    persona = persona_of(officer)
    rng = RNG(f"{game.seed}:arc:{officer.id}:{beat_index}:voice")
    frame = rng.pick(list(persona.frames["greet"]))
    return frame.format(me=officer.name.split()[0], fact=text).strip()


def hint(game, officer, beat, place) -> str:
    return beat.hint.format(**slots(game, officer, beat, place))


# ── what an answer does ────────────────────────────────────────────────────

def _purse_left(game, power: str) -> float:
    """What a power's purse holds — read, not opened: a purse nobody has
    touched yet is the one `exchequer.ensure` would open, so asking must not
    be what opens it."""
    from . import diplomacy, exchequer
    if power not in diplomacy.POWERS:
        return 0.0
    books = getattr(game, "exchequer", None)
    held = books.purses.get(power) if books is not None else None
    return float(held.credits if held is not None
                 else exchequer.OPENING_PURSE)


def preview(game, officer, choice) -> dict:
    """Every consequence of `choice`, exactly as `perform` will do it.

    Returns credits (signed), rep {power: delta}, loyalty (this officer),
    bridge (each other officer), cargo {commodity: delta}, the signature it
    grants, what they will think, and `why` — non-empty when it cannot be
    said at all.
    """
    from . import stores
    from ..sim.ship import cargo_free
    out = {"credits": 0.0, "rep": {}, "loyalty": 0.0, "bridge": choice.bridge,
           "cargo": {}, "signature": "", "thinks": choice.thinks, "why": ""}
    if choice.credits < 0:
        out["credits"] = float(choice.credits)
        if game.credits < -choice.credits:
            out["why"] = (f"It costs {cr(-choice.credits)} and the treasury "
                          f"holds {cr(game.credits)}.")
    elif choice.credits > 0:
        out["credits"] = min(float(choice.credits),
                             _purse_left(game, choice.purse))
    room = cargo_free(game.ship, game.ship_stats)
    for cid, tonnes in choice.cargo:
        if tonnes < 0:
            if stores.held(game, cid) < -tonnes:
                out["why"] = out["why"] or (
                    f"It needs {-tonnes:g} t of {cid}, and there is "
                    f"{stores.held(game, cid):.1f} t to hand.")
            out["cargo"][cid] = float(tonnes)
        else:
            got = max(0.0, min(float(tonnes), room))
            room -= got
            out["cargo"][cid] = got
    mine = loyalty_sim.loyalty_of(officer)
    conviction = loyalty_sim.conviction_of(officer)
    for power, delta in choice.rep:
        was = float(game.rep.get(power, 0.0))
        moved = max(-100.0, min(100.0, was + delta)) - was
        out["rep"][power] = moved
        # `Game.adjust_rep` drags a partisan along with their power, by the
        # *asked* delta (see `loyalty.align`) — counted here so the preview
        # of their loyalty is the loyalty they end with.
        if conviction is not None and conviction.aligned == power:
            mine = max(FLOOR, min(CEILING, mine + delta * 0.25))
    mine = max(FLOOR, min(CEILING, mine + choice.loyalty))
    out["loyalty"] = mine - loyalty_sim.loyalty_of(officer)
    if choice.signature:
        from ..data.arcs import ARCS_BY_ID, SIGNATURES
        out["signature"] = SIGNATURES[ARCS_BY_ID[officer.arc].signature].name
    return out


def perform(game, officer, choice) -> dict:
    """Do it. Returns the preview it was promised, which is what it did."""
    from . import exchequer, stores
    from ..sim.ship import add_cargo
    said = preview(game, officer, choice)
    if said["why"]:
        return said
    for power, delta in choice.rep:
        # Through the one door, so a partisan's loyalty follows (`align`).
        game.adjust_rep(power, delta)
    if said["credits"] < 0:
        game.credits += said["credits"]
    elif said["credits"] > 0:
        # Out of a power's purse and into the captain's: nothing is conjured.
        exchequer.purse(game, choice.purse).credits -= said["credits"]
        game.credits += said["credits"]
    for cid, tonnes in said["cargo"].items():
        if tonnes < 0:
            stores.take(game, cid, -tonnes)
        elif tonnes > 0:
            add_cargo(game.ship, cid, tonnes)
    loyalty_sim.shift(officer, choice.loyalty)
    if choice.bridge:
        for other in game.officers:
            if other is not officer:
                loyalty_sim.shift(other, choice.bridge)
    return said


def summary(said: dict, name: str) -> str:
    """One line of what an answer does, for a button or a board."""
    bits = []
    if said["credits"]:
        bits.append(("+" if said["credits"] > 0 else "−")
                    + cr(abs(said["credits"])))
    for cid, tonnes in said["cargo"].items():
        if tonnes:
            bits.append(f"{'+' if tonnes > 0 else '−'}{abs(tonnes):g} t {cid}")
    for power, moved in said["rep"].items():
        if moved:
            bits.append(f"{power.title()} {_signed(moved)}")
    if said["loyalty"]:
        bits.append(f"{name} {_signed(said['loyalty'])}")
    if said["bridge"]:
        bits.append(f"bridge {_signed(said['bridge'])}")
    if said["signature"]:
        bits.append(f"signature: {said['signature']}")
    return " · ".join(bits) or "nothing but their opinion"


def _signed(value: float) -> str:
    return f"{'+' if value > 0 else '−'}{abs(value):.0f}"
