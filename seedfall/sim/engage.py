"""Opening fire from the pilot's seat, at the range you actually flew to.

**No new combat rules live here.** `sim/combat` is the only thing that builds a
`Battle`, `sim/firing` says which mounts can speak and why the rest cannot, and
`sim/gunnery` owns the gunner's station. This is the seam between flying and
fighting: it decides *whether* a pilot may open fire on a contact, and at *what
range the fight starts*, then hands both to `combat.start`. A thirteenth module
that resolved gunfire would be the defect this file exists to avoid.

**What the range means, measured.** The conn works in kilometres on its own
local frame and holds exactly one target; the system plane works in AU. Asked
through `sim/track`, every contact sharing a body with the hull reads as 0 km
away and everything else as hundreds of millions — measured on seed "engage",
the nearest other body was 429,631,101 km. So there is no local geometry for a
second hull, and there is no honest way to fire at "whatever is out there".

What there *is* is `conn.pos`: how far the hull has flown from where it let go.
A contact left behind at the quay recedes as you burn away from it and closes
as you come back, so the distance flown **is** the range to it. That makes the
flying matter — a captain who opens fire while still alongside fights at
Contact range, and one who has drifted eight thousand kilometres opens at
Extreme, where `sim/firing` will tell them most of their mounts cannot reach.

Nothing here is stored. The band is a reading of `conn.pos`, and whether a
contact may be fired on is a reading of the game.
"""

from __future__ import annotations

import math

from . import combat as combat_sim
from . import encounters as encounters_sim
from . import freeflight
from . import track as track_sim

#: The range at which a fight opens at the longest band, in km.
#:
#: **Its own number now.** It was defined as `freeflight.far_km()` — the
#: range past which the conn is the slow way to travel — on a "one door"
#: argument. But those are two different facts that happened to share a
#: value: one is *advice about flying*, the other is *how far a gun
#: engagement reaches*, and retuning the advice (`freeflight.FAR_SHARE`)
#: silently rebanded every weapon in the game. They start equal and are
#: equal today; moving either is now a decision about the thing it governs.
REACH_KM = 10_000.0


def reach_km() -> float:
    return REACH_KM


def range_km(game, conn, contact) -> float:
    """How far the hull is from this contact **now**, in kilometres.

    The ship's own position comes from `freeflight.where`, which is where it
    let go plus how far it has flown; the contact's comes from `sim/track`,
    the one door for where anything in a system is. So burning toward
    something closes this and burning away opens it, which is the whole point
    of flying by hand.

    **The first version read `conn.pos` alone** — the distance flown from
    where the conn was taken — because measured through both `track.at` and
    `traffic.position`, a hull sharing a body with the ship sat at that body's
    *exact* position, 0 km off. That was honest about a thing left behind at
    the quay and exactly backwards for one you were flying at: closing on a
    contact increased `conn.pos` and so opened the fight further away.
    `sim/traffic.STATION_KM` gives a hull holding station a place of its own
    now, so there is a range to close.
    """
    sx, sy = freeflight.where(game, conn)
    ax, ay = track_sim.at(game, contact, game.day)
    return math.dist((sx, sy), (ax, ay)) * freeflight.KM_PER_AU


def band_for(game, conn, contact, km: float | None = None) -> int:
    """Which of `combat.BANDS` a fight opened now would start at.

    0 (Contact) alongside, up to the last band at `reach_km`. Measured against
    the five bands, that is a two-thousand-kilometre step each.
    """
    bands = len(combat_sim.BANDS)
    step = reach_km() / bands
    if km is None:
        km = range_km(game, conn, contact)
    return max(0, min(bands - 1, int(km / step)))


def may_engage(game, conn, contact, km: float | None = None) -> tuple[bool, str]:
    """Whether the pilot may open fire on this contact, and why not.

    A refusal is an answer with a reason in it, the way `sim/clearance`
    answers a berth — the gunner's board should be able to print the sentence
    rather than grey a button out and say nothing.
    """
    if conn is None or not freeflight.is_free(conn):
        return False, ("The guns answer to the conn, and the conn is flying an "
                       "approach. Break off first.")
    kind = getattr(contact, "kind", "")
    if kind in ("body", "star"):
        return False, (f"{getattr(contact, 'name', 'It')} is a world. There is "
                       "nothing there to shoot at that would notice.")
    if kind != "hull":
        return False, (f"{getattr(contact, 'name', 'It')} is not a hull. "
                       "Opening fire on it is not a thing the board will do.")
    if not any(getattr(w, "wpn", None) for w in game.ship_stats.weapons):
        return False, "Nothing aboard is a weapon. There is nothing to fire."
    # **There was no range gate at all, and the picture found it.** Rendered,
    # the fire control offered to open fire on a hull 1,293,058,866 km away
    # and called it extreme range — because `band_for` clamps to the last
    # band, so everything past `reach_km` reads as merely far rather than as
    # out of the question. Measured on seed "fire": four of the five hulls in
    # the system were engageable, the worst of them 129,306 times past reach.
    #
    # `reach_km` is `freeflight.far_km()`, 10,000 km — the distance the
    # free-flight screens already call far from where she was let go. Past
    # that there is no fight to open, only a plot to lay.
    # `km` is the range if the caller has already measured it. **Not a second
    # door** — it is this one's own answer, handed back in. A screen listing
    # six contacts asked `range_km` three times per row (here, `band_for`, and
    # the sentence), and every ask rebuilds the system's traffic.
    if km is None:
        km = range_km(game, conn, contact)
    if km > reach_km():
        return False, (
            f"{getattr(contact, 'name', 'It')} is {km:,.0f} km off. The guns "
            f"reach {reach_km():,.0f}. Close the range first.")
    return True, ""


def open_fire(game, conn, contact, rng):
    """Begin an engagement from the conn. Returns `(battle, why_not)`.

    The band is where the flying put you; everything after that is
    `sim/combat`'s. The enemy is built by `sim/encounters.make_enemy`, the one
    door for what a hull of a given flag is carrying — inventing a second
    would let a conn engagement and an encounter disagree about the same ship.
    """
    from . import tutorial_watch
    tutorial_watch.deed(game, "fought")
    ok, why = may_engage(game, conn, contact)
    if not ok:
        return None, why
    faction = getattr(contact, "faction", None) or "unaligned"
    enemy = encounters_sim.make_enemy(rng, faction)
    enemy["name"] = getattr(contact, "name", enemy.get("name", "Unknown hull"))
    enemy["faction"] = faction
    # **Your escorts come with you.** `ui/battle_view.begin` passes
    # `consorts.escorts_of` when an encounter starts a fight, and the first
    # draft of this did not — measured, a captain sailing with one consort
    # opened fire from the conn and fought alone, while the same captain
    # jumped by the same enemy fought two-to-one. A hull that sails with the
    # flag sails with it whoever picked the fight.
    from . import consorts as consorts_sim
    battle = combat_sim.start(
        game.ship, game.ship_stats, enemy,
        bonuses=game.bonuses, officers=game.officers,
        rep=game.rep.get(faction, 0.0),
        band=band_for(game, conn, contact),
        game=game, rng=rng, fleet=consorts_sim.escorts_of(game))
    return battle, ""


def price(game, contact) -> list:
    """What killing this hull would cost, with its flag and with its friends.

    Quoted before the trigger, not discovered after it. `sim/aftermath` is
    what actually spends this — `KILL_COST` against the victim and
    `allegiance.charge_attack` against everyone fond of it — and this asks the
    same two doors at the same weight, so the board cannot promise a bill the
    fight will not send.
    """
    from . import aftermath as aftermath_sim
    from . import allegiance as allegiance_sim
    faction = getattr(contact, "faction", None)
    if not faction or faction == "bloom":
        return []
    weight = aftermath_sim.KILL_COST
    return ([(faction, -weight)]
            + [(other, -cost) for other, cost
               in allegiance_sim.price_attack(game, faction, weight,
                                              {faction})])


def note(game, conn, contact, km: float | None = None) -> str:
    """One line on what opening fire from here would mean, for a screen."""
    if km is None:
        km = range_km(game, conn, contact)
    ok, why = may_engage(game, conn, contact, km)
    if not ok:
        return why
    band = band_for(game, conn, contact, km)
    said = (f"Opening fire would begin at {combat_sim.BANDS[band].lower()} "
            f"range — {km:,.0f} km off {getattr(contact, 'name', 'it')}.")
    bill = price(game, contact)
    if bill:
        said += ("  Destroying her costs "
                 + ", ".join(f"{who} {cost:+.1f}" for who, cost in bill) + ".")
    return said
