"""Running dark: the captain's own transponder, and what switching it off buys.

`data/countermeasures.py` has described the signature of a transponding, a
dark, a shrouded and a cloaked hull since the sky was written, and only the
sky read it — every *other* hull could hide and the captain could not. The
backlog called it "let the captain hide too". This is that, and it is one
switch with three prices:

- **Fewer meetings.** Raiders, patrols, a warrant's hull and a rival roaming
  the lanes all have to see you before they can come for you (`exposure`).
- **A first volley** when a hunt finds its quarry (`sim/hunts.search`).
- **Suspicion where the law is.** A hull with no transponder at a power's
  quay is a question, and a patrol that finds one asks it (`suspicion`,
  `caught`).

**Seeing is only part of meeting**, which is why `exposure` is not the share
itself. Measured against the per-arrival encounter rate over 4,000 seeded
arrivals, the whole signature (0.28 dark) would take 72% of meetings away —
more than a switch that costs nothing should buy. `SEEN_SHARE` says how much
of a meeting is being seen first; the rest is two hulls working the same
volume, which no signature helps.
"""

from __future__ import annotations

from ..data import countermeasures as cm
from ..data.nemeses import SHROUD_IDS

#: How much of an encounter is being seen first. Dark (0.28) leaves 0.57 of the
#: meetings — 43% fewer — and shrouded (0.10) leaves 0.46.
SEEN_SHARE = 0.6

#: What docking dark adds to the odds of the hold being opened, before the
#: port's own relief. A quay squawks for a living and so does anybody it
#: wants to see again.
DOCKED_DARK = 0.25

#: Scrutiny a patrol puts on your file when it finds you running dark. A third
#: of what a smuggling bust costs (`customs.inspect` adds 0.45) — you were not
#: carrying anything, you were only hiding.
CAUGHT_HEAT = 0.15


def _state(game):
    from . import nemeses
    return nemeses.state(game)


def dark(game) -> bool:
    """Is the transponder off?"""
    held = getattr(game, "hunt", None)
    return bool(getattr(held, "dark", False))


def shrouded(game) -> bool:
    """A shroud fitted and working. It only counts dark — see `signature`."""
    ship = getattr(game, "ship", None)
    if ship is None:
        return False
    return any(pid in SHROUD_IDS and pid not in ship.disabled
               for pid in ship.fitted)


def signature(game) -> cm.Countermeasure:
    """What the captain's hull is doing about being seen."""
    if not dark(game):
        return cm.LOUD
    return cm.SHROUDED if shrouded(game) else cm.DARK


def exposure(game) -> float:
    """The share of meetings that still find you: 1.0 lit, less dark."""
    share = signature(game).share
    return (1.0 - SEEN_SHARE) + SEEN_SHARE * share


def suspicion(game) -> float:
    """What running dark adds to the customs odds at the quay you are at."""
    return DOCKED_DARK if dark(game) else 0.0


def caught(game, power: str) -> list:
    """A patrol has come alongside a hull with no transponder. It goes on
    the file as a question: scrutiny with that power, and a line to say so."""
    if not dark(game) or not power:
        return []
    from . import customs
    customs.add_heat(game, power, CAUGHT_HEAT)
    from ..data.factions import FACTIONS_BY_ID
    who = getattr(FACTIONS_BY_ID.get(power), "short", power)
    return [("warn", f"{who}: they found you running dark, and they "
                     "wrote it down.")]


def set_dark(game, on: bool) -> dict:
    """Switch the transponder. Logs itself; answers `{ok, why, text}`."""
    held = _state(game)
    on = bool(on)
    if held.dark == on:
        return {"ok": False, "why": "It is already " + ("off." if on else "on."),
                "text": ""}
    held.dark = on
    if on:
        text = ("Transponder off, drive banked. Running dark"
                + (" under the shroud." if shrouded(game) else "."))
    else:
        text = "Transponder on. Squawking and lit."
    game.add_log(text, "warn" if on else "")
    return {"ok": True, "why": "", "text": text}


def tradeoff(game) -> str:
    """The switch's price, in words, for the tooltip on both its doors."""
    lit = cm.LOUD.share
    now = signature(game)
    cut = 1.0 - ((1.0 - SEEN_SHARE) + SEEN_SHARE * cm.DARK.share)
    deep = 1.0 - ((1.0 - SEEN_SHARE) + SEEN_SHARE * cm.SHROUDED.share)
    return (f"Running dark: signature {cm.DARK.share / lit:.0%} of lit, about "
            f"{cut:.0%} fewer meetings ({deep:.0%} with a shroud fitted), and "
            "the first volley when a hunt finds its quarry. But a quay adds "
            f"{DOCKED_DARK:.0%} to the odds of opening your hold, and a patrol "
            f"that finds you dark writes it down. Now: {now.name}.")
