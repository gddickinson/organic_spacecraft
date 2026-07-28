"""Which of your mounts can actually shoot right now, and why the rest cannot.

Everything needed to answer that was already modelled and none of it was ever
shown. `tactical` knows each mount's arc and how far off the bearing is;
`Weapon.bears_at` knows the range band it works in; `combat._fire` knows
whether the magazine is dry. All three of those facts only reached the player
*after* they had spent the turn, as a line in the log saying the shot did not
happen:

    The Mag Lance will not train that far — 47° outside its broadside arc.

So the tactical plot drew rings and headings, and the one thing it never drew
was the thing the whole geometry exists for: what bears. A captain choosing
between *come about* and *present the broadside* was choosing blind, and then
being told afterwards which one had been right.

`solution()` answers per mount, before the turn: does it bear, is the range
right, is there ammunition — and if not, exactly how far the bow has to come
round or how many bands to close. `closing_rate()` is the other half of a
picture that was static: a range with no sign of which way it is going.

Nothing here mutates anything. It is a read of the plane, and `combat` remains
the only thing that fires a gun.
"""

from __future__ import annotations

from dataclasses import dataclass

from . import tactical as tac

#: Two thresholds, because the game has always had two and never named them.
#:
#: `combat._fire` refuses a shot above 0.6, while every automatic selector —
#: the salvo, the aimed shot, the enemy AI — picks only mounts at 0.5 or
#: better, and `assessment.mounts` called anything above 0.5 "out of range".
#: Three numbers, disagreeing.
#:
#: They never actually disagreed *in play*: `bears_at` steps 0.22 a band, so
#: the reachable penalties are 0, 0.22, 0.44, 0.66 and nothing lands in the
#: gap. This was a landmine rather than a live defect. Naming both makes the
#: distinction a design statement — it will fire, and it is not worth firing —
#: and `test_firing` holds the gap shut so it stays a decision.
CAN_FIRE = 0.6
WORTH_FIRING = 0.5

#: Kept for callers that only care whether a shot is possible at all.
UNUSABLE = CAN_FIRE


@dataclass
class Shot:
    """One mount's answer to "can you shoot, and if not what would fix it"."""
    mount_id: str
    name: str
    arc: str
    arc_name: str
    #: The target is inside this mount's arc.
    in_arc: bool
    #: Degrees the bow must come round to bring it on. 0 when it bears.
    gap: float
    #: The range band suits it.
    in_band: bool
    #: Bands to close (negative) or open (positive) to reach its envelope.
    band_shift: int
    #: Accuracy penalty from range.
    penalty: float
    #: A salvo or an aimed shot would actually choose this mount.
    worth_it: bool
    #: Magazine state.
    dry: bool
    ammo: str | None
    can_fire: bool
    why: str

    @property
    def blocked_by(self) -> str:
        """One word for a chart legend."""
        if self.can_fire:
            return "ready" if self.worth_it else "marginal"
        if not self.in_arc:
            return "arc"
        if self.dry:
            return "dry"
        return "range"


def _band_shift(weapon, band: int) -> int:
    low, high = weapon.bands
    if band < low:
        return low - band          # positive: open the range
    if band > high:
        return high - band         # negative: close it
    return 0


def solution(side, other, band: int | None = None) -> list:
    """Every mount, and whether it can shoot this turn.

    `band` defaults to the separation of the two hulls, so this can be asked
    without a Battle in hand.
    """
    if band is None:
        band = tac.band_for(tac.separation(side.body, other.body))
    rel = tac.relative_bearing(side.body, other.body)
    out = []
    for mount in getattr(side.st, "weapons", None) or []:
        weapon = mount.wpn
        if weapon is None:
            continue
        arc = tac.arc_of(mount)
        in_arc = tac.bears(arc, rel)
        gap = tac.arc_gap(arc, rel)
        penalty = weapon.bears_at(band)
        in_band = penalty <= 0.0001
        shift = _band_shift(weapon, band)

        dry, ammo = False, None
        if weapon.ammo:
            ammo, per = weapon.ammo
            dry = side.ship.cargo.get(ammo, 0) < per

        can = in_arc and penalty <= CAN_FIRE and not dry
        worth = can and penalty <= WORTH_FIRING
        if can and worth:
            why = ("Ready." if in_band else
                   f"Will fire, {penalty * 100:.0f}% off for the range.")
        elif can:
            # Fires if you name it, but no salvo will pick it up.
            why = (f"Marginal at this range — {penalty * 100:.0f}% off. It "
                   "will fire if you call it, but a salvo will not use it.")
        elif not in_arc:
            why = (f"{gap:.0f}° outside its "
                   f"{tac.arc_name(arc).lower()} arc.")
        elif dry:
            why = f"Dry — no {ammo} in the hold."
        else:
            low, high = weapon.bands
            way = "Close" if shift < 0 else "Open"
            why = (f"Wants band {low}–{high}; we are at {band}. "
                   f"{way} {abs(shift)}.")
        out.append(Shot(
            mount_id=mount.id, name=mount.name, arc=arc,
            arc_name=tac.arc_name(arc), in_arc=in_arc, gap=gap,
            in_band=in_band, band_shift=shift, penalty=penalty,
            worth_it=worth, dry=dry, ammo=ammo, can_fire=can, why=why))
    return out


def ready(side, other, band: int | None = None) -> list:
    """Mounts a salvo would actually use."""
    return [s for s in solution(side, other, band) if s.worth_it]



def closing_rate(side, other) -> float:
    """Units per turn the range is shrinking *if neither hull turns*.

    A plot that shows a range and not its sign tells you where you are and
    nothing about where you are going, which is the half that matters when
    deciding whether to turn now or next turn.

    This is the instantaneous rate, not a forecast of next turn's range: both
    hulls steer before they advance, so a hull under helm orders will beat it
    about a third of the time. Calling it a prediction would be the same
    defect this project keeps finding — a screen stating a consequence the
    simulation does not honour. It is what the range is doing *now*.
    """
    now = tac.separation(side.body, other.body)
    a, b = side.body.copy(), other.body.copy()
    tac.advance(a)
    tac.advance(b)
    return now - tac.separation(a, b)


def turn_to_bear(side, other) -> float:
    """The smallest turn that brings *something* onto the target.

    Zero when a mount already bears. This is the number behind "come about".
    """
    shots = solution(side, other)
    if not shots:
        return 0.0
    if any(s.in_arc for s in shots):
        return 0.0
    return min(s.gap for s in shots)


def summary(side, other, band: int | None = None) -> str:
    """One line: how much of the battery is live, and what is stopping it."""
    shots = solution(side, other, band)
    if not shots:
        return "No mounts fitted."
    live = [s for s in shots if s.worth_it]
    if len(live) == len(shots):
        return f"All {len(shots)} mounts bear."
    blocked: dict = {}
    for shot in shots:
        if not shot.worth_it:
            blocked[shot.blocked_by] = blocked.get(shot.blocked_by, 0) + 1
    parts = []
    if blocked.get("arc"):
        turn = turn_to_bear(side, other)
        parts.append(f"{blocked['arc']} outside their arc"
                     + (f" ({turn:.0f}° of turn)" if turn else ""))
    if blocked.get("range"):
        parts.append(f"{blocked['range']} out of range")
    if blocked.get("dry"):
        parts.append(f"{blocked['dry']} dry")
    if blocked.get("marginal"):
        parts.append(f"{blocked['marginal']} marginal")
    return f"{len(live)} of {len(shots)} mounts bear — " + ", ".join(parts) + "."


def danger(side, other, band: int | None = None) -> str:
    """What the *other* hull can bring to bear on you.

    Sitting in an enemy's forward arc is a decision, and the plot never said
    you were in one.
    """
    theirs = ready(other, side, band)
    if not theirs:
        return "Nothing of theirs bears on you."
    # Counted rather than listed: two identical mounts read as a stutter,
    # "Point-Defence Cannon, Point-Defence Cannon".
    tally: dict = {}
    for shot in theirs:
        tally[shot.name] = tally.get(shot.name, 0) + 1
    named = ", ".join(f"{n}" + (f" ×{c}" if c > 1 else "")
                      for n, c in list(tally.items())[:3])
    more = "…" if len(tally) > 3 else ""
    return f"{len(theirs)} of their mounts bear on you: {named}{more}."


def arcs_in_use(side) -> list:
    """The distinct arcs this hull has mounts in, for drawing.

    Drawing one wedge per mount stacked five identical broadsides on top of
    each other; the chart wants one wedge per arc that exists.
    """
    seen = []
    for mount in getattr(side.st, "weapons", None) or []:
        if mount.wpn is None:
            continue
        arc = tac.arc_of(mount)
        if arc not in seen:
            seen.append(arc)
    return seen


def arc_span(arc: str) -> tuple[float, float]:
    """The half-angles of an arc, in degrees either side of the bow."""
    low, high = tac.ARCS.get(arc, tac.ARCS["turret"])[:2]
    return float(low), float(high)


def bearing_degrees(side, other) -> float:
    """Where the target sits relative to the bow, signed: + is to starboard."""
    absolute = tac.bearing_to(side.body, other.body)
    return (absolute - side.body.heading + 540) % 360 - 180


def readout(side, other, band: int | None = None) -> dict:
    """Everything the plot's caption needs, in one call."""
    rate = closing_rate(side, other)
    return {
        "range": tac.separation(side.body, other.body),
        "band": band if band is not None
        else tac.band_for(tac.separation(side.body, other.body)),
        "closing": rate,
        "closing_word": ("closing" if rate > 0.5 else
                         "opening" if rate < -0.5 else "steady"),
        "bearing": bearing_degrees(side, other),
        "turn_to_bear": turn_to_bear(side, other),
        "summary": summary(side, other, band),
        "danger": danger(side, other, band),
    }


def compass(degrees: float) -> str:
    """A signed relative bearing as something a person would say."""
    if abs(degrees) < 8:
        return "dead ahead"
    if abs(degrees) > 172:
        return "dead astern"
    side_word = "starboard" if degrees > 0 else "port"
    return f"{abs(degrees):.0f}° to {side_word}"
