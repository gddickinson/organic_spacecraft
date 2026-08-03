"""Momentum, and what two things do to each other when they meet.

The docking model had one thing right and two things missing. Right: the conn
works in the *target's* frame, so `conn.vel` already is the relative velocity
and matching a station's motion is what flying it to zero means. Missing:

- **A collision was one-sided.** `outcome.impact_damage(speed)` took a number
  off the player's hull and that was the whole event. The station a hull hit
  at forty metres a second was neither moved nor marked. A quay could be used
  as a backstop.
- **Nothing had a mass.** Which meant nothing could be knocked off course by
  anything, and a hull moored to a station could fire its main drive without
  either of them going anywhere.

Both follow from one piece of physics, so there is one module for it.

**Contact is perfectly inelastic** — hulls do not bounce off quays; they
crumple, latch, or shear. Two masses meeting at a closing speed `v` end up
sharing a velocity, and the arithmetic gives everything that was missing:

    V   = m₁·v / (m₁ + m₂)              the pair's common velocity
    Δv₁ = −v · m₂/(m₁+m₂)               how hard the striker is stopped
    Δv₂ = +v · m₁/(m₁+m₂)               how hard the struck one is shoved
    μ   = m₁·m₂ / (m₁ + m₂)             reduced mass
    E   = ½ · μ · v²                    energy that has to go somewhere

`E` is the only energy there is: the rest of the kinetic energy is still in
the pair's shared motion, and cannot break anything. It is split between the
two structures **by mass**, because a tonne of hull absorbs what a tonne of
hull absorbs — which is why a courier hitting a hub is destroyed by an impact
the hub barely notices, without either of those being written down as a rule.

Nothing here knows what a ship or a station is. It takes masses and speeds and
gives back the same, so the conn, the damage model, the tactical plot and the
NPC hulls can all ask the same question.
"""

from __future__ import annotations

#: Points of hull per megajoule absorbed per tonne of structure.
#:
#: **Derived, not chosen.** `outcome.impact_damage` charged
#: `(speed / SAFE_CLOSING)² · IMPACT_BASE` — 6 points at 4 m/s — and the game's
#: written consequences are calibrated against it: 8 m/s is a scrape, 20 m/s
#: takes half the hull, 45 m/s ends the chronicle. So the reference case is a
#: 24,000 t NAVIS meeting a 400,000 t hub at 4 m/s, which absorbs 181.13 MJ
#: over 24,000 t — 0.007547 MJ/t — and must still cost 6 points:
#:
#:     K = 6.0 · 24,000 / 181.13 = 795.0
#:
#: Everything else follows from the physics rather than from a second table.
#: Note what the reference does *not* pin: against a target far heavier than
#: the striker the reduced mass tends to the striker's own, so specific energy
#: is ½v² whatever the hull weighs — a courier and a freighter hitting a hub
#: at 20 m/s lose the same *share* of themselves, which is right. The mass
#: ratio starts to matter when the two are comparable, which is the case the
#: old one-sided formula could not express at all.
HARM_PER_MJ_PER_T = 795.0

#: Below this the two are station-keeping, not colliding. A hull drifting onto
#: a quay at a few centimetres a second is berthing.
NUDGE = 0.05


def share(m_a: float, m_b: float) -> float:
    """`m_a`'s share of a shared velocity — how much of the pair it is.

    Guarded rather than clamped: a zero or negative mass is a caller's bug and
    the honest answer is "half each", not a division by zero half-way through
    an approach.
    """
    total = float(m_a) + float(m_b)
    if total <= 0.0:
        return 0.5
    return float(m_a) / total


def reduced(m_a: float, m_b: float) -> float:
    """The reduced mass — what the collision actually has to absorb.

    Against a wall (an infinite `m_b`) this tends to `m_a`, which is the
    lithobraking case: all of the striker's energy, none of the world's.
    """
    total = float(m_a) + float(m_b)
    if total <= 0.0:
        return 0.0
    return float(m_a) * float(m_b) / total


def collide(m_a: float, m_b: float, closing: float) -> dict:
    """Two masses meeting head-on at `closing` m/s, and what each takes.

    Returns the velocity change and the damage for both, in the frame where
    `b` was at rest — which is the conn's own frame, so nothing has to be
    converted at the call site.

    `energy_mj` is the reduced-mass energy in megajoules: masses are in tonnes
    (1,000 kg) and speeds in m/s, so ½·m·v² comes out in kilojoules and is
    divided by a thousand.
    """
    speed = abs(float(closing))
    if speed <= NUDGE:
        return {"speed": speed, "energy_mj": 0.0, "shared": 0.0,
                "dv_a": 0.0, "dv_b": 0.0, "harm_a": 0.0, "harm_b": 0.0,
                "gentle": True}
    a_share = share(m_a, m_b)
    shared = speed * a_share
    energy_mj = 0.5 * reduced(m_a, m_b) * speed * speed / 1000.0
    return {
        "speed": speed,
        "energy_mj": energy_mj,
        # The velocity both end up at, in the struck body's old frame.
        "shared": shared,
        # The striker is slowed to it; the struck one is shoved up to it.
        "dv_a": shared - speed,
        "dv_b": shared,
        "harm_a": harm(energy_mj, m_a),
        "harm_b": harm(energy_mj, m_b),
        "gentle": False,
    }


def harm(energy_mj: float, mass_t: float) -> float:
    """Damage a structure of this mass takes from absorbing this energy.

    Per tonne, so the same impact ruins a courier and scuffs a hub. Splitting
    the energy *between* the two and then dividing each share by that body's
    own mass would divide by mass twice; the energy is not divided, it is
    absorbed by both, and each pays for it in proportion to how little of it
    there is to spread the load over.
    """
    if mass_t <= 0.0 or energy_mj <= 0.0:
        return 0.0
    return round(energy_mj / float(mass_t) * HARM_PER_MJ_PER_T, 1)


def push(m_a: float, m_b: float, dv: float) -> dict:
    """A thrust applied while the two are attached.

    A hull moored to a station and firing its main drive is one body of
    `m_a + m_b`, so the burn that would have given the ship `dv` alone gives
    the pair `dv · m_a/(m_a + m_b)` — and the station goes with it. A NAVIS
    against a hub moves the pair at a seventeenth of what it would move
    itself, which is the honest answer to "can I push off a station with the
    main drive": yes, and slowly.
    """
    together = share(m_a, m_b) * float(dv)
    return {"pair_dv": together, "wasted": float(dv) - together,
            "ratio": share(m_a, m_b)}

#: What the things in the sky weigh, in tonnes, by the berth kinds
#: `sim/anchorage.py` names. Set against the hull that hits them: a NAVIS is
#: 24,000 t, so a quay is two and a half of it — a structure a freighter can
#: genuinely shift — and a capital hub is nearly seventeen, which a freighter
#: can nudge and not move. A holding is a moored yard rather than a built one
#: and lighter than either; a Weave gate is old, dense and effectively part of
#: the furniture of the system.
#:
#: These are the numbers that decide who gets knocked off course, so they are
#: stated as ratios to a working hull rather than picked to look large.
BERTH_MASS_T = {
    "quay": 60_000.0,
    "hub": 400_000.0,
    "holding": 18_000.0,
    "gate": 2_500_000.0,
}

#: A berth of a kind nobody has weighed. The quay is the ordinary case.
DEFAULT_BERTH_MASS_T = BERTH_MASS_T["quay"]

#: A world is not shoved by anything a captain can fly into it. Rather than
#: special-casing "this is a planet" in the arithmetic, it is given a mass
#: that makes the physics say so: the reduced mass tends to the striker's own
#: and the shove tends to zero, which is exactly lithobraking.
WORLD_MASS_T = 1e15


def mass_of(game, thing) -> float:
    """What a target weighs, whatever kind of thing it is.

    **One door**, because every consumer of a collision needs the same answer:
    the conn resolving contact, the damage that lands on the struck hull, and
    the pilot deciding whether pushing off is worth trying. A `Target` from
    `sim/conn.py`, a `Contact` from `sim/track.py` and a traffic `Hull` all
    answer here.
    """
    kind = getattr(thing, "kind", "")
    if kind in ("body", "star", "point"):
        # A star answered `DEFAULT_BERTH_MASS_T` — 60,000 t, the mass of a
        # quay — because it fell past every branch to the fallback. Nothing
        # can fly into one, so it never mattered; a fallback that quietly
        # weighs a star the same as a pier is the kind of thing that matters
        # the first time something does.
        return WORLD_MASS_T
    if kind == "anchorage":
        berth = getattr(thing, "berth", "") or ""
        return BERTH_MASS_T.get(berth, DEFAULT_BERTH_MASS_T)
    if kind == "hull":
        return hull_mass(game, getattr(thing, "hull_id", None))
    return DEFAULT_BERTH_MASS_T


def hull_mass(game, hull_id=None) -> float:
    """A hull's mass in tonnes, off its chassis.

    An NPC hull carries the class it was built as, so this is the same figure
    the yard quoted for it. Falls back to the player's own chassis, which is
    the only hull in the game whose mass is certain.
    """
    from ..data.chassis import CHASSIS_BY_ID
    from . import traffic
    if hull_id is not None and game is not None:
        found = next((h for h in traffic.in_system(game) if h.id == hull_id),
                     None)
        if found is not None:
            entry = CHASSIS_BY_ID.get(getattr(found, "kind", ""))
            if entry is not None:
                return float(entry.mass_t)
    return ship_mass(game)


def ship_mass(game) -> float:
    """The player's hull, in tonnes, off the chassis it was built on.

    The **registry mass** — what the hull weighs in a collision — as against
    `thrusters.mass_tonnes`, the handling mass the drives push. See the note
    there: the two differ by up to six orders of magnitude across the fleet
    and serve two different laws on purpose.
    """
    from ..data.chassis import CHASSIS_BY_ID
    if game is None:
        return 24_000.0
    entry = CHASSIS_BY_ID.get(getattr(game.ship, "chassis", ""))
    return float(entry.mass_t) if entry is not None else 24_000.0
