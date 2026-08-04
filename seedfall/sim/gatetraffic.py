"""Who gets through a gate, when, and how long the queue is.

`sim/weave` says where the anchors are and which burn. `sim/gates` says what
using one costs. This is the third question, and the one a busy system makes
you ask: **is there room, and is there a slot?**

Two refusals and one delay:

* **The bore.** A ring has a throat. A hull heavier than it does not pass, and
  no fee or standing changes that — it is a size, not a toll.
* **The queue.** A gate clears so many transits a day and a busy system wants
  more than that. Utilisation is read off the sector rather than invented:
  the port's level and the hulls `sim/traffic` already puts in the system.
* **The courier reserve.** Despatch traffic is small and expected, so a share
  of every gate's slots is kept for it. That is why news out of a busy system
  is fast while the crossing is slow, and it is the whole reason a mail
  service is a service.

Nothing here is stored. A queue is a reading of the system as it stands, the
way `sim/traffic` is, so it cannot drift from the sector it describes.
"""

from __future__ import annotations

from ..data import gate_traffic as rings


def ring_of(gate):
    """The sort of throat this anchor has."""
    return rings.of(getattr(gate, "kind", "") or "")


def demand(game, system_id: int) -> float:
    """Transits a day this system wants, before the gate has a say."""
    system = next((s for s in game.galaxy.systems if s.id == system_id), None)
    if system is None:
        return rings.DEMAND_BASE
    port = getattr(system, "port", None)
    level = float(getattr(port, "level", 0) or 0) if port else 0.0
    from . import traffic as traffic_sim
    try:
        hulls = len(traffic_sim.in_system(game, system))
    except Exception:                                          # noqa: BLE001
        hulls = 0
    return (rings.DEMAND_BASE + level * rings.DEMAND_PER_LEVEL
            + hulls * rings.DEMAND_PER_HULL)


def pressure(game, gate) -> float:
    """How hard this ring is being worked, as a share of what it can clear."""
    ring = ring_of(gate)
    slots = max(1e-6, ring.slots_per_day)
    return demand(game, getattr(gate, "system_id", -1)) / slots


def wait_days(game, gate, courier: bool = False) -> float:
    """How long before a slot, in days.

    The shape is the one queueing has: nothing until the ring is near its
    capacity, then it climbs. `ρ/(1−ρ)` is the standard form and it goes to
    infinity, which a gate does not — a ring keeps working and a harbour
    keeps sequencing — so it is capped (`MAX_WAIT_DAYS`) at "come back
    tomorrow" rather than allowed to become a wall.
    """
    ring = ring_of(gate)
    rho = pressure(game, gate)
    if courier:
        # **A reserve helps only if the traffic it holds back slots for is a
        # smaller share of the demand than of the cycle.** Despatches are
        # about a tenth of what a ring is asked for and a Charter gate keeps
        # a third of its slots for them, so a courier feels roughly a third
        # of the pressure a freighter does. The first draft subtracted a
        # whole cycle and divided by the share, which made a despatch wait
        # *longer* than the hulls it was supposed to overtake.
        rho = rho * rings.COURIER_DEMAND_SHARE / max(1e-6, ring.courier_share)
    if rho <= 0.0:
        return rings.COURIER_HANDLING_DAYS if courier else 0.0
    held = min(rings.MAX_WAIT_DAYS, rho / max(1e-6, 1.0 - min(0.97, rho))
               / max(1e-6, ring.slots_per_day))
    return held + (rings.COURIER_HANDLING_DAYS if courier else 0.0)


def may_pass(game, gate, mass_t: float) -> tuple[bool, str]:
    """Will this ring take a hull of this mass? A size, not a toll."""
    if gate is None:
        return False, "There is no anchor here."
    ring = ring_of(gate)
    if mass_t > ring.bore_t:
        return False, (
            f"{getattr(gate, 'name', 'The anchor')} is a {ring.name} — "
            f"{ring.bore_t:,.0f} t through the throat, and you are "
            f"{mass_t:,.0f}. No fee changes a bore.")
    return True, ""


def note(game, gate) -> str:
    """One line about the state of a ring, for a board to print."""
    if gate is None:
        return "No anchor here."
    ring = ring_of(gate)
    rho = pressure(game, gate)
    held = wait_days(game, gate)
    busy = ("clear" if rho < 0.6 else "working" if rho < 0.9
            else "busy" if rho < 1.2 else "backed up")
    when = ("no wait" if held < 0.05
            else f"about {held * 24:,.0f} h" if held < 1.0
            else f"about {held:,.1f} d")
    return (f"{ring.name.capitalize()} · {ring.bore_t:,.0f} t bore · "
            f"{busy}, {when}")
