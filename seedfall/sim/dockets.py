"""Being seen, being charged, and the difference between them.

**A law is only as long as the arm attached to it.** The whole design rests on
this file: an act out in the dark offends nobody, because nobody was there.
The same act at a quay is on a register before you have finished unloading.

Three stages, and a captain can be stopped at any of them:

1. **Witness.** `witness()` asks how well a power can know what you did, from
   what it actually has in that system — its quay, its register, its hulls,
   and its friends. It returns 0 for a power with nothing there, and nothing
   is recorded at all. This is the reward for working the frontier, and it is
   why the Verge's edge is worth having.
2. **The file.** A witnessed act sits *alleged*: they know, and have done
   nothing. `sweep()` is each power going through its file — periodically,
   not instantly, so there is a window in which leaving is a plan.
3. **Prescription.** An allegation nobody ever filed on ages out. Two things
   never do: destroying a hull and germinating without a licence, which are
   the two the powers keep permanent registers of.

The one door in is `report()`. Every place in the sim that produces a
criminal act calls it once — `customs` when you are boarded, `aftermath` when
a hull dies, `engage` when you fire inside somebody's approaches, `territory`
when you settle claimed ground — and it works out for itself which powers
would call that a crime and which of them could possibly have known.
"""

from __future__ import annotations

from ..data.factions import FACTIONS_BY_ID
from ..data.offences import LAWFUL, OFFENCES_BY_ID, charges_it
from . import law as law_sim

#: How often a power goes through its file. A month is long enough that a
#: captain who realises what they have done can be somewhere else, and short
#: enough that "somewhere else" has to be a decision rather than a drift.
SWEEP_DAYS = 30.0

#: What each thing a power has in a system is worth as an eye-witness. A quay
#: sees everything that ties up at it; a register is paperwork and sees less;
#: hulls on station see what happens in front of them.
QUAY_SEES = 0.85
REGISTER_SEES = 0.35
PER_HULL_SEES = 0.16
HULLS_CAP = 0.48

#: What an ally passes on. Powers close on the relations matrix tell each
#: other things — the same `CLOSE` threshold `sim/grudge` inherits on, because
#: it is the same friendship.
HEARSAY = 0.45

#: A power will not bother filing below this much certainty, whatever it
#: suspects. Nothing is ever charged on nothing.
FILE_FLOOR = 0.18

#: How long a power's own procedural complaint stands before it will raise
#: another. See `Offence.procedural`: without this the layer generates its own
#: work for ever, and it was measured doing exactly that.
PROCEDURAL_DAYS = 540.0


def witness(game, power: str, system) -> float:
    """How well this power can know what you did here. 0..1.

    Derived, never stored: it is a fact about where their institutions are
    *today*, so a power that loses a quay stops seeing that system, and one
    whose fleet moves in starts.
    """
    if system is None or power not in LAWFUL:
        return 0.0
    seen = 0.0
    port = getattr(system, "port", None)
    if port is not None and getattr(port, "faction", None) == power:
        seen = max(seen, QUAY_SEES)
    if getattr(system, "faction", None) == power:
        seen = max(seen, REGISTER_SEES)
    from . import fleets as fleets_sim
    hulls = fleets_sim.guard_at(game, system, power)
    if hulls:
        seen = max(seen, min(HULLS_CAP, PER_HULL_SEES * hulls))

    # And what their friends saw. A power with nothing in the system can
    # still be told, which is what stops a tight alliance having a blind spot
    # the size of everywhere neither of them happens to be standing.
    from . import diplomacy as dip_sim
    from . import grudge as grudge_sim
    for other in LAWFUL:
        if other == power:
            continue
        if dip_sim.relation(game, power, other) < grudge_sim.CLOSE:
            continue
        theirs = _own_eyes(game, other, system)
        seen = max(seen, theirs * HEARSAY)
    return min(1.0, seen)


def _own_eyes(game, power: str, system) -> float:
    """What a power sees itself, without being told. Breaks the hearsay loop:
    two allies each reporting the other's hearsay would ratchet for ever."""
    seen = 0.0
    port = getattr(system, "port", None)
    if port is not None and getattr(port, "faction", None) == power:
        seen = max(seen, QUAY_SEES)
    if getattr(system, "faction", None) == power:
        seen = max(seen, REGISTER_SEES)
    from . import fleets as fleets_sim
    hulls = fleets_sim.guard_at(game, system, power)
    if hulls:
        seen = max(seen, min(HULLS_CAP, PER_HULL_SEES * hulls))
    return seen


def allege(game, power: str, offence_id: str, detail: str,
           weight: float = 1.0, system=None, seen: float | None = None):
    """Record that this power has noticed this act. Returns the `Charge`.

    Returns None when there is nothing to record — the power does not call it
    a crime, or could not have known. Both are ordinary and neither is an
    error: most acts, most of the time, offend nobody who saw them.
    """
    if not charges_it(offence_id, power):
        return None
    system = system if system is not None else getattr(game, "system", None)
    strength = witness(game, power, system) if seen is None else float(seen)
    if strength < FILE_FLOOR:
        return None
    state = law_sim.ensure(game)
    offence = OFFENCES_BY_ID.get(offence_id)
    if offence is not None and offence.procedural:
        # **One "you are not answering us" per power at a time.** A power that
        # is already complaining about your silence does not start a second
        # complaint about the same silence; it reaches for a heavier
        # instrument instead, which `tribunal.severity` does off the count of
        # priors.
        recent = [c for c in state.charges
                  if c.power == power and c.offence == offence_id
                  and float(game.day) - c.day < PROCEDURAL_DAYS]
        if recent:
            return None
    charge = law_sim.Charge(
        id=law_sim.next_id(game), power=power, offence=offence_id,
        day=float(game.day), where=getattr(system, "name", "") or "",
        system_id=int(getattr(system, "id", -1) or -1),
        detail=detail, weight=max(0.1, float(weight)) * strength,
        state="alleged")
    state.charges.append(charge)
    return charge


def report(game, offence_id: str, detail: str, weight: float = 1.0,
           system=None, against: str | None = None) -> list:
    """**The one door in.** Tell every power that would call this a crime.

    `against` names the power actually wronged, when there is one — a hull
    destroyed belongs to somebody, and its owner both cares more and is
    likelier to find out. Everyone else is charging you with the general
    offence, and only if they saw it.
    """
    offence = OFFENCES_BY_ID.get(offence_id)
    if offence is None:
        return []
    out = []
    for power in offence.powers:
        if power not in LAWFUL:
            continue
        seen = None
        if power == against:
            # The wronged party knows. Whether they can *do* anything about
            # it is a separate question, and the answer is `sim/warrants`.
            seen = 1.0
        charge = allege(game, power, offence_id, detail, weight, system, seen)
        if charge is not None:
            out.append(charge)
    return out


def prescribed(game, charge) -> bool:
    """Has this allegation aged out before anybody filed on it?"""
    offence = OFFENCES_BY_ID.get(charge.offence)
    if offence is None or offence.prescribes < 0:
        return False
    return (float(game.day) - charge.day) > offence.prescribes


def will_file(game, charge) -> bool:
    """Would this power actually prosecute this, today?

    Three things say no, and each of them is a way to play out of trouble: it
    aged out, they think too well of you to bother, or they cannot reach you
    to serve it. The third is the interesting one — a power with nothing
    within a jump of you can hold a file open for years.
    """
    if charge.state != "alleged":
        return False
    if prescribed(game, charge):
        return False
    offence = OFFENCES_BY_ID.get(charge.offence)
    if offence is None:
        return False
    standing = float(game.rep.get(charge.power, 0.0))
    # Kin get the benefit of the doubt on small things and no benefit at all
    # on the ones that never prescribe.
    if offence.prescribes >= 0 and standing >= 55.0 and offence.gravity < 0.6:
        return False
    return charge.weight * offence.gravity >= FILE_FLOOR


def file_charge(game, charge) -> list:
    """Move an allegation to a live prosecution. Returns log lines."""
    from ..data.forums import forum_of
    forum = forum_of(charge.power)
    if forum is None or charge.state != "alleged":
        return []
    offence = OFFENCES_BY_ID.get(charge.offence)
    charge.state = "filed"
    charge.filed_on = float(game.day)
    charge.due = float(game.day) + max(0.0, forum.notice)
    short = FACTIONS_BY_ID[charge.power].short
    if forum.form == "none":
        # There is no summons, because there is nobody to summon you. The
        # posting *is* the filing, and `tribunal.hear` will be along on the
        # same tick to price it.
        return [("bad", f"{short}: a claim has been posted against you for "
                        f"{offence.writ}. There is no hearing.")]
    return [("bad", f"{short} has filed against you — {offence.writ}. The "
                    f"{forum.occasion} is in {int(forum.notice)} days.")]


def sweep(game, days: float, rng) -> list:
    """Each power goes through its file. Returns log lines.

    Called from the clock. Deliberately periodic: a captain who has just done
    something stupid gets a window, and a window is what makes running a
    decision instead of an inevitability.
    """
    out: list = []
    state = law_sim.ensure(game)
    if not state.charges:
        return out
    for power in LAWFUL:
        last = float(state.swept.get(power, -9999.0))
        if float(game.day) - last < SWEEP_DAYS:
            continue
        state.swept[power] = float(game.day)
        for charge in [c for c in state.charges
                       if c.power == power and c.state == "alleged"]:
            if prescribed(game, charge):
                charge.state = "closed"
                charge.outcome = "spent"
                charge.verdict = "Nobody got round to it in time."
                continue
            if will_file(game, charge):
                out.extend(file_charge(game, charge))
    return out


def exposure(game, power: str) -> float:
    """Everything outstanding with this power, as summed gravity.

    What the docket screen leads with and what `sim/hail` quotes when you
    call them: one number for "how much trouble am I in here".
    """
    total = 0.0
    for charge in law_sim.open_charges(game, power):
        offence = OFFENCES_BY_ID.get(charge.offence)
        if offence is not None:
            total += offence.gravity * charge.weight
    return round(total, 3)


def note_for(game, power: str) -> str:
    """One line a screen can print about where you stand with this law."""
    live = law_sim.open_charges(game, power)
    if not live:
        return "Nothing outstanding."
    filed = [c for c in live if c.state == "filed"]
    if filed:
        return (f"{len(filed)} charge(s) filed, "
                f"{len(live) - len(filed)} more on the file.")
    return f"{len(live)} matter(s) noted, none filed."
