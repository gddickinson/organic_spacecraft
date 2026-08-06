"""What a power will actually do to you, and how far it will follow.

The survey's flattest finding: **nothing in the sector had ever hunted the
player except the Bloom.** "Hunted" was the bottom reputation band and read by
no code. `grudge.hostile_open` — the game's own definition of *this power
opens fire rather than hailing* — was called by nothing but its own test. Two
favours you could buy with a harbourmaster, "a berth regardless" and "a word
before it happens", were read by nothing at all. `encounters.roll_encounter`
could only fire on jump arrival, so the five-term lawlessness model had one
moment in the day to mean anything.

A warrant is the missing noun. It is issued by a verdict, it has a **bite**
(what they do) and a **reach** (where they can do it), and every one of those
dead readers now asks it.

Reach is the design's load-bearing idea and it is drawn straight from the
factions. The Charter's interdict runs to every quay it holds and stops dead
at the edge of its register, because the Charter has no way to touch you
anywhere else and would not use one if it had. A Freehold bounty reaches
*everywhere*, because it is not enforcement at all — it is a price, and a
price travels wherever somebody who wants money is. The most lawful power has
the shortest arm and the least lawful has the longest, which is the truest
thing this system says about the Verge.
"""

from __future__ import annotations

from ..data.factions import FACTIONS_BY_ID
from ..data.forums import SANCTIONS_BY_ID
from . import law as law_sim

#: How long an instrument stands before it needs the file looked at again.
#: `-1` means until it is answered, which is what a conviction gets.
STANDS = -1.0

#: Reaches, narrowest first. `worst` and the docket sort by this.
REACHES = ("system", "holdings", "everywhere")

#: What a bounty is worth to whoever collects it, per point of gravity.
BOUNTY_PER_GRAVITY = 5200.0


def issue(game, power: str, bite: str, why: str, reach: str = "holdings",
          charge_id: int = -1, system=None, price: float = 0.0,
          until: float = STANDS):
    """Put an instrument in force. Returns the `Warrant`.

    Idempotent per (power, bite): a second conviction does not stack a second
    interdict, it extends and re-words the one already standing. Two identical
    warrants would show twice on the docket and be lifted once.
    """
    state = law_sim.ensure(game)
    standing = next((w for w in state.warrants
                     if w.power == power and w.bite == bite and not w.lifted),
                    None)
    if standing is not None:
        standing.why = why
        standing.price = max(standing.price, float(price))
        if REACHES.index(reach) > REACHES.index(standing.reach):
            standing.reach = reach
        if until == STANDS or standing.until == STANDS:
            standing.until = STANDS
        else:
            standing.until = max(standing.until, until)
        return standing
    warrant = law_sim.Warrant(
        id=law_sim.next_id(game), power=power, bite=bite, reach=reach,
        since=float(game.day), until=float(until), why=why,
        charge_id=charge_id, price=float(price),
        system_id=int(getattr(system, "id", -1) or -1))
    state.warrants.append(warrant)
    return warrant


def in_force(game, power: str | None = None) -> list:
    """Every instrument still standing, worst first."""
    day = float(game.day)
    rows = [w for w in law_sim.ensure(game).warrants
            if not w.lifted and (w.until < 0 or w.until > day)]
    if power:
        rows = [w for w in rows if w.power == power]
    rows.sort(key=lambda w: -_weight(w))
    return rows


def _weight(warrant) -> float:
    sanction = next((s for s in SANCTIONS_BY_ID.values()
                     if s.bite == warrant.bite), None)
    return sanction.weight if sanction else 0.0


def reaches(game, warrant, system) -> bool:
    """Is this instrument in force *here*? The whole point of the file."""
    if warrant.reach == "everywhere":
        return True
    if system is None:
        return False
    if warrant.reach == "system":
        return int(getattr(system, "id", -2)) == warrant.system_id
    # "holdings" — anywhere this power keeps a quay or a register.
    port = getattr(system, "port", None)
    if port is not None and getattr(port, "faction", None) == warrant.power:
        return True
    return getattr(system, "faction", None) == warrant.power


def against(game, system=None) -> list:
    """Everything in force where the ship is standing."""
    system = system if system is not None else getattr(game, "system", None)
    return [w for w in in_force(game) if reaches(game, w, system)]


def bites(game, bite: str, system=None, power: str | None = None) -> bool:
    """**The query every enforcer asks.** Is there a warrant of this kind here?

    `clearance` asks for "refuse", `gates` asks for "refuse" and "shun",
    `colony` asks for "licence", `market` asks for "shun", and
    `encounters` asks for "hunt".
    """
    for warrant in against(game, system):
        if warrant.bite == bite and (power is None or warrant.power == power):
            return True
    return False


def holders(game, bite: str, system=None) -> list[str]:
    """Which powers are biting this way here, for a screen that must say who."""
    return sorted({w.power for w in against(game, system) if w.bite == bite})


def bounty(game, system=None) -> float:
    """What is posted on the hull, here. What a hunter is being paid."""
    return round(sum(w.price for w in against(game, system)
                     if w.bite == "hunt"), 2)


def worst(game, system=None):
    """The heaviest instrument in force here, or None."""
    live = against(game, system)
    return live[0] if live else None


def lift(game, warrant, why: str = "") -> None:
    warrant.lifted = True
    if why:
        warrant.why = why


def lift_for(game, power: str, bite: str | None = None) -> int:
    """Lift a power's instruments. Returns how many. Only `sim/clemency` calls
    this — an instrument that lifted itself would be a pardon nobody granted."""
    lifted = 0
    for warrant in in_force(game, power):
        if bite is None or warrant.bite == bite:
            warrant.lifted = True
            lifted += 1
    return lifted


def price_for(gravity: float, weight: float = 1.0) -> float:
    """What a posted claim is worth to whoever brings it in."""
    return round(BOUNTY_PER_GRAVITY * max(0.2, gravity) * max(0.3, weight), -2)


def note(game, system=None) -> str:
    """One line for the status bar and the hail screen."""
    live = against(game, system)
    if not live:
        return ""
    heaviest = live[0]
    who = FACTIONS_BY_ID.get(heaviest.power)
    short = who.short if who else heaviest.power
    sanction = next((s for s in SANCTIONS_BY_ID.values()
                     if s.bite == heaviest.bite), None)
    name = sanction.name if sanction else heaviest.bite
    if len(live) == 1:
        return f"{short}: {name.lower()} in force here."
    return f"{short}: {name.lower()} in force here, and {len(live) - 1} more."


def summary(game) -> list[dict]:
    """Every instrument anywhere, for the law screen."""
    out = []
    for warrant in in_force(game):
        sanction = next((s for s in SANCTIONS_BY_ID.values()
                         if s.bite == warrant.bite), None)
        who = FACTIONS_BY_ID.get(warrant.power)
        out.append({
            "id": warrant.id,
            "power": warrant.power,
            "who": who.short if who else warrant.power,
            "name": sanction.name if sanction else warrant.bite,
            "blurb": sanction.blurb if sanction else "",
            "bite": warrant.bite,
            "reach": warrant.reach,
            "why": warrant.why,
            "price": warrant.price,
            "here": reaches(game, warrant, getattr(game, "system", None)),
        })
    return out
