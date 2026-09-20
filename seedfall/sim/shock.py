"""What just passed between this hull and something else, as a window can draw it.

The flight model already knows everything about a contact and shows almost
none of it. `sim/impulse` works out the energy, both sides' damage and both
sides' change of velocity; `sim/moorings` knows which fitting the hull was
nearest; `sim/landing` tells a descent from an arrival; `sim/control` knows
when a station is shooting. All of it reached the player as one line of italic
type along the bottom of a window — photographed, a **1,134-point collision at
55 m/s**, which is the end of a starting chronicle, and not one pixel of the
picture changed.

This is the door between the fact and the picture. It reads a flight and hands
back a `Shock`: what happened, which way it came from, how hard, and what it
cost both sides. It decides nothing and writes nothing — every number is one
the approach already carries — and it imports no Qt, so `ui/effects.py` is the
only thing that has to know what a second is.

**The bearing is the part a window cannot work out for itself.** A contact
happens along the line to whatever was struck, and by the time the picture is
drawn `berthing.commit` has moved the ship to a berth and `knock` has moved
the structure off station. A window asking "which way did that come from" a
beat later would have nothing left to ask. So it is taken here, in the frame
the approach is flown in, at the moment the outcome is read.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field

from . import bays
from .conn import IMPACT_BASE

#: The two pictures a contact can land in. The flight deck's cameras work in
#: the approach's own frame; the engagement is drawn from behind your own
#: hull in tactical coordinates. Nothing crosses between them.
FLIGHT = "flight"
BATTLE = "battle"

#: Every kind of contact a window is asked to draw. The first five are
#: endings that `sim/outcome` writes; the next three happen with the flight
#: still running, and are the ones a captain most needs to *see* rather than
#: read, because they are reversible while they are happening. `gunfire` is
#: the one that belongs to the other picture.
KINDS = ("collision", "scrape", "aground", "ditched", "down",
         "alongside", "orbit", "captured", "cut", "ward", "gunfire")

#: How far over the rate that berths a contact may be and still be a scrape
#: rather than a crash, and what that comes to in hull.
#:
#: **Derived, not chosen.** `conn.IMPACT_BASE` is what arriving at exactly
#: `conn.SAFE_CLOSING` costs, and a berthing is allowed to end at that rate,
#: so the bar is "half again the rate that berths" — a pilot who was a little
#: fast, rather than one who flew into something. Damage goes as the square
#: of the speed, so a rate of 1.5 is a harm of 2.25, and it is written that
#: way rather than as the 13.5 it comes to: a constant written twice is the
#: fault this project has been bitten by more than any other.
SCRAPE_OVER = 1.5
SCRAPE_HARM = SCRAPE_OVER * SCRAPE_OVER * IMPACT_BASE

#: What a hull has to lose in one contact before the glass cracks, as a share
#: of the whole structure. A third: enough that a scrape and a bad day look
#: different, low enough that the first real crash a captain has shows it.
CRACK_SHARE = 0.30


@dataclass(frozen=True)
class Shock:
    """One contact between the hull and something else, ready to be drawn.

    Not saved and not registered: a shock is a thing that *just happened*,
    read once by the effects layer and turned into a picture. What persists
    from it is already on the chronicle — the damage on the layers, the knock
    on the structure, the line in the log.
    """

    kind: str
    #: What was struck, and which fitting on it, where there was one.
    name: str = ""
    where: str = ""
    #: Unit vector from the ship toward it, in the approach's own frame. This
    #: is what a camera projects to put the flash in the right window.
    bearing: tuple = (0.0, 1.0, 0.0)
    #: Where the two actually touched, in km in the same frame, for the
    #: outside view — which draws the pair rather than looking out of one.
    at: tuple = (0.0, 0.0, 0.0)
    #: How fast, and the energy the pair had to absorb between them.
    speed: float = 0.0
    energy_mj: float = 0.0
    #: Off this hull, off the other one, and how hard the other one was shoved.
    harm: float = 0.0
    struck_harm: float = 0.0
    struck_dv: float = 0.0
    #: `harm` as a share of the whole structure this hull was built with —
    #: which is what decides how hard the picture shakes. Against the hull's
    #: *remaining* strength it would read the same for a scratch on a fresh
    #: hull and a scratch on a wreck, and the second is the louder event.
    severity: float = 0.0
    #: Whether this was the one that finished her.
    fatal: bool = False
    #: A stable key for the debris: two collisions must not throw the same
    #: sparks, and one collision must throw the same sparks every repaint.
    seed: str = ""
    #: The berths on the structure, in the same frame, for a berthing to run
    #: its lines to. Empty for anything without fittings — a world, a hull.
    berths: tuple = field(default_factory=tuple)
    #: Which picture this belongs in: the flight deck's cameras, or the
    #: engagement seen from the bridge. Two pictures in two frames of
    #: reference, and a bearing taken in one is meaningless in the other, so
    #: every painter asks for its own scene and is given only that.
    #:
    #: **Last in the list on purpose.** It went in second, after `kind`, and
    #: every positional `Shock("collision", "Fleet Hub", …)` in the checks
    #: quietly put the station's name in it — which filtered the shock out of
    #: the only picture that would have drawn it, and the check that measures
    #: the shake read zero.
    scene: str = FLIGHT

    @property
    def violent(self) -> bool:
        """Did this take something off her? A berthing is a contact too."""
        return self.kind in ("collision", "aground", "ditched", "ward",
                             "gunfire")

    @property
    def ends(self) -> bool:
        """Is the approach over? A boom closing on the hull is not.

        The difference decides whether a window may turn the pilot's camera
        round to show it. With the flight finished there is no manoeuvre left
        to spoil; with it still running, moving a pilot's chosen view mid-cut
        or mid-ward would be taking the wheel off them.
        """
        return self.kind not in ("captured", "cut", "ward", "gunfire")

    @property
    def cracks(self) -> bool:
        """Hard enough that the glass should still show it afterwards."""
        return self.violent and self.severity >= CRACK_SHARE


def hull_max(game) -> float:
    """Everything this hull was built with, in points. Never zero."""
    ship = getattr(game, "ship", None)
    layers = getattr(ship, "layers", ()) or () if ship is not None else ()
    total = sum(float(getattr(layer, "max", 0.0) or 0.0) for layer in layers)
    return total if total > 0.0 else 100.0


def bearing_to(conn) -> tuple:
    """Which way the thing being approached lies, from the ship.

    A unit vector in the approach's frame, where the target sits at the
    origin — so it is the ship's own position, negated. At zero range (which
    a contact very nearly is) there is no bearing to take and the nose is the
    honest answer: that is where she was going.
    """
    span = math.dist(conn.pos, (0.0, 0.0, 0.0))
    if span < 1e-9:
        nose = list(getattr(conn, "nose", None) or (0.0, 1.0, 0.0))
        length = math.dist(nose, (0.0, 0.0, 0.0)) or 1.0
        return tuple(c / length for c in nose)
    return tuple(-p / span for p in conn.pos)


def touched_at(conn) -> tuple:
    """Where the two met, in km in the approach's frame.

    On the solid part rather than at the centre — `bays.hull_km`, the same
    figure `sim/outcome` resolves contact against, so the flash is drawn on
    the skin the ship hit and not somewhere inside the structure.
    """
    span = conn.range_km
    if span < 1e-9:
        return (0.0, 0.0, 0.0)
    reach = min(bays.hull_km(conn.target), span)
    return tuple(p / span * reach for p in conn.pos)


def _berth_points(conn) -> tuple:
    """Every fitting on the structure, in this frame. Empty where there are
    none, which is most of the sky: a world is orbited, not moored to."""
    from . import moorings
    try:
        found = moorings.points(conn.target, moorings.spin_of(conn))
    except (AttributeError, TypeError):
        return ()
    return tuple((name, tuple(at)) for name, at in found)


def _at_berth(conn) -> tuple:
    """The fitting this approach is for: its name and where it is."""
    from . import moorings
    found = moorings.nearest(conn)
    if found is None:
        return "", None
    return found["name"], tuple(found["at"])


def _seed(conn, kind: str) -> str:
    """A key no two contacts share, and one contact never changes.

    The elapsed time is in it because a captain can strike the same quay
    twice in one chronicle and the second one must not throw the first one's
    debris; nothing here draws from `game.rng`, which would shift the save's
    stream every time a window repainted.
    """
    return (f"shock:{kind}:{getattr(conn.target, 'name', '?')}"
            f":{conn.elapsed:.0f}:{conn.speed:.2f}")


def of(game, conn) -> Shock | None:
    """The contact a resolved approach ended in, or None if it was not one.

    Called once the outcome is written and the chronicle has been charged, so
    `fatal` can be read off the hull rather than guessed at. Drifting away,
    running the tanks dry, breaking off and securing from a free flight are
    all endings and none of them is a contact: there is nothing to draw and
    this says so by handing back None.
    """
    if conn is None or not conn.over:
        return None
    outcome = conn.outcome
    harm = float(getattr(conn, "damage", 0.0) or 0.0)
    if outcome == "collision":
        kind = "scrape" if harm < SCRAPE_HARM else "collision"
    elif outcome in ("aground", "ditched", "down", "alongside", "orbit"):
        kind = outcome
    else:
        return None

    from . import impulse
    from .ship import is_destroyed
    speed = float(conn.speed)
    both = impulse.collide(float(getattr(conn, "mass_t", 24_000.0)),
                           float(getattr(conn, "target_mass_t", 60_000.0)),
                           speed)
    berth, at_berth = _at_berth(conn)
    # **A berthing is drawn at the fitting, a crash where the frames went.**
    # They are different places on the same structure, and the whole reading
    # of the picture depends on which: lines going across at a mast is an
    # arrival, a flash on the skin two hundred metres from it is not.
    gentle = kind in ("alongside", "orbit")
    at = at_berth if (gentle and at_berth is not None) else touched_at(conn)
    ship = getattr(game, "ship", None) if game is not None else None
    return Shock(
        kind=kind,
        name=getattr(conn.target, "name", ""),
        where=berth if kind in ("alongside", "collision", "scrape") else "",
        bearing=bearing_to(conn),
        at=at,
        speed=speed,
        energy_mj=0.0 if gentle else float(both["energy_mj"]),
        harm=harm,
        struck_harm=float(getattr(conn, "struck_damage", 0.0) or 0.0),
        struck_dv=float(getattr(conn, "struck_dv", 0.0) or 0.0),
        severity=min(1.0, harm / hull_max(game)),
        fatal=bool(ship is not None and is_destroyed(ship)),
        seed=_seed(conn, kind),
        berths=_berth_points(conn),
    )


def captured(game, conn) -> Shock:
    """The moment a standoff's boom closes on the hull.

    A real interaction between two objects that the pilot has spent ninety
    seconds holding station for, and the only sign of it was a number on a
    panel going from 0.99 to 1.00.
    """
    berth, at = _at_berth(conn)
    return Shock(kind="captured", name=getattr(conn.target, "name", ""),
                 where=berth, bearing=bearing_to(conn),
                 at=at if at is not None else touched_at(conn),
                 speed=float(conn.speed), severity=0.06,
                 seed=_seed(conn, "captured"), berths=_berth_points(conn))


def cutting(game, conn) -> Shock:
    """A cut into a berth that would not open — `sim/forcing.py`'s one act.

    Severity climbs with the cut, so the picture gets louder the further in
    she is: this is the one thing in the game that takes a hull somewhere it
    was refused, and it should not look like waiting.
    """
    berth, at = _at_berth(conn)
    through = min(1.0, max(0.0, float(getattr(conn, "cut", 0.0) or 0.0)))
    return Shock(kind="cut", name=getattr(conn.target, "name", ""),
                 where=berth, bearing=bearing_to(conn),
                 at=at if at is not None else touched_at(conn),
                 severity=0.05 + 0.15 * through,
                 seed=_seed(conn, f"cut:{through:.2f}"),
                 berths=_berth_points(conn))


def warded(game, conn) -> Shock:
    """Being fired on by the structure you are closing: point defence.

    The bite is `control.ward_bite`, the same figure the tick charges, so
    the picture is as hard as the hull's loss that minute actually was.
    """
    from . import control
    bite = control.ward_bite(conn)
    return Shock(kind="ward", name=getattr(conn.target, "name", ""),
                 bearing=bearing_to(conn), at=touched_at(conn),
                 harm=bite, severity=min(1.0, bite / hull_max(game)),
                 seed=_seed(conn, f"ward:{getattr(conn, 'warded_for', 0)}"))


def gunfire(game, battle) -> Shock | None:
    """What this turn of an engagement took off the hull, as a thing to feel.

    Combat has always *shown* what was fired — `ui/battle3d` draws every
    round from the muzzle and blooms the ones that landed — and has never
    shown what it was like to be on the receiving end. A volley that took a
    fifth of the hull moved nothing on the screen but a number in a panel.

    One shock for the turn rather than one per round: a volley is a moment,
    and four of these stacked would shake the picture four times over
    something the ship felt once. `at` is the player's own hull in tactical
    coordinates, because that is the frame `battle3d` draws in.
    """
    if battle is None:
        return None
    took = sum(float(getattr(shot, "damage", 0.0) or 0.0)
               for shot in getattr(battle, "shots", ()) or ()
               if not getattr(shot, "mine", False) and shot.landed)
    if took <= 0.0:
        return None
    body = battle.player.body
    return Shock(kind="gunfire", scene=BATTLE,
                 name=getattr(battle, "enemy_name", "") or "",
                 at=(float(body.x), float(body.y), 0.0),
                 harm=took, severity=min(1.0, took / hull_max(game)),
                 seed=f"shock:gunfire:{id(battle)}:{battle.turn}:{took:.1f}")


#: What each kind is called on the glass, in the words the log already uses.
CAPTION = {
    "collision": "COLLISION",
    "scrape": "SCRAPED THE SKIN",
    "aground": "AGROUND",
    "ditched": "PUT HER DOWN",
    "down": "DOWN AND INTACT",
    "alongside": "ALONGSIDE",
    "orbit": "ORBIT ESTABLISHED",
    "captured": "BOOM HAS HER",
    "cut": "CUTTING IN",
    "ward": "UNDER POINT DEFENCE",
    # Never painted as words — the engagement narrates itself in
    # `ui/battle_text` — but every kind has a caption, so that a table with a
    # hole in it is a failing check rather than a blank banner.
    "gunfire": "TAKING FIRE",
}


def banner(shock: Shock) -> tuple:
    """The caption, and the line under it. Two strings, both possibly empty.

    The words a window paints large at the moment of contact. They are here
    rather than in the window because every screen that draws a shock has to
    say the same thing about it, and because the figures in them — the
    energy, both sides' damage, the shove — are the sim's.
    """
    head = CAPTION.get(shock.kind, shock.kind.upper())
    if shock.name:
        head += f" · {shock.name.upper()}"
    if shock.kind in ("alongside", "captured"):
        return head, (f"Made fast at {shock.where}." if shock.where
                      else "Lines across.")
    if shock.kind == "orbit":
        return head, "The drive can rest."
    if shock.kind == "cut":
        return head, f"Into {shock.where}." if shock.where else ""
    if shock.kind == "ward":
        # No rate on this one. Being shot at has nothing to do with how fast
        # you are going, and "0.0 m/s" in the middle of the sentence read as
        # though the guns cared.
        return head, (f"{shock.harm:,.1f} off her, and they are still "
                      "shooting." if shock.harm else "Ranging shots.")
    # A tenth under ten metres a second, because that is the band the whole
    # difference between a berthing and a crash lives in: "4 m/s" for a 4.5
    # m/s scrape reads as the rate that would have berthed.
    rate = (f"{shock.speed:,.1f}" if shock.speed < 10.0
            else f"{shock.speed:,.0f}")
    said = [f"{rate} m/s"]
    if shock.energy_mj >= 1.0:
        said.append(f"{shock.energy_mj:,.0f} MJ")
    if shock.harm >= 0.5:
        said.append(f"−{shock.harm:,.0f} off her")
    if shock.struck_harm >= 0.5:
        said.append(f"−{shock.struck_harm:,.0f} off it")
    if shock.struck_dv >= 0.01:
        said.append(f"shoved {shock.struck_dv:,.2f} m/s")
    if shock.where and shock.kind in ("collision", "scrape"):
        said.append(f"{shock.where} missed")
    if shock.fatal:
        said.append("SHE IS GONE")
    return head, " · ".join(said)
