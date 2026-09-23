"""Flying her down, rather than being charged for it.

`sim/descent.py` answers *whether* a craft may set down on a world and what
she carries when she does; `sim/fieldwork.launch_expedition` has always put
the party on the ground by spending three days of the calendar. That is an
order given to an officer, and it is a perfectly good way to run a ship —
but a player asked the obvious question of a game with a cockpit in it:

    How does the player pilot a ship down to the surface of a planet?

They could not, and this is the answer. A descent is a flight, flown in the
cockpit that already exists, on the flight model that already exists: a
`sim/conn.Conn` opened on the *world* as its target and fitted with the
craft's own numbers (`sim/craft._fit`), so every instrument, the stick, the
throttle, the collision guard and the fuel accounting are the ones written
for every other flight in this game.

**Where it ends is the interesting part.** A conn's tick is sixty seconds
and the drive is an impulse at the start of it, and that is not an accident
— it is why `sim/landing.py` can prove a starship never lands on a world.
Run the same arithmetic for a touchdown: to end a tick at `SET_DOWN` on a
world pulling 10.4 m/s², the tick has to *begin* within 0.77 m of the
ground. No craft in any game flies that, and a rule nothing can satisfy is
a rule that only ever produces wrecks.

So the flown part of a descent is the part that is worth flying, and it is
judged at a gate:

- **The gate** is one tick of free fall above the surface (`gate_km`) — the
  finest height this clock can say anything about, and on a rocky world
  about where a real lander stops flying and starts landing anyway.
- **Coming through it with no more speed than her drive cancels in one
  burn** (`catch_rate`), with the drive able to hold the fall at all
  (`landing.can_hold`), is a landing. She is down.
- **Coming through it faster** is a crash, and it costs her hull, her pilot
  and everybody who rode down with her.

Which makes the descent exactly the manoeuvre it ought to be: kill the
orbital velocity, hold the fall, arrive slow. Fly it badly — or simply let
her fall, which on a rocky world is four times what the drive can take off
her — and you have put a lander into a planet with the party aboard.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

from .conn import MAIN_COST, TICK
from . import landing

#: The mode name the flight computer knows a descent by
#: (`sim/flightdeck.computer`).
MODE = "down"

#: What she is falling at when the cockpit opens, in m/s. The de-orbit burn
#: is behind her — see `begin` — and this is the way it left on her, the
#: same way `sim/conn_open.start` opens every other approach with the drift
#: the transfer left rather than at rest.
OPEN_DRIFT = 20.0

#: The lowest a gate is ever set, in km above the surface, and how many
#: ticks of free fall it stands at above that.
#:
#: The three is measured, not chosen. However slowly a descent is flown, the
#: last ticks of it end at about one tick of the world's own gravity —
#: `g · TICK` — because the drive fires once at the top of the minute and
#: the world has the other fifty-nine seconds, and a tick that *starts*
#: slow and ends at `g · TICK` carries her something over twice a free
#: fall's distance. A gate thinner than that is a gate she steps over:
#: measured at 1.5, six worlds went from ten kilometres up to the surface
#: inside one tick, `sim/outcome` wrote "aground" on a landing flown
#: perfectly, and the arrival was reported as a crash at 190 m/s.
GATE_LEAST_KM, GATE_FALL = 2.0, 3.0

#: The rate the law asks for when there is no room left to ask for more, in
#: m/s. Under `landing.SET_DOWN`, so a descent that is merely patient still
#: arrives rather than hovering for ever.
TOUCH_RATE = 2.4

#: How much of what her drive could cancel the law will let her carry, and
#: how much of the room below her one tick may spend. Both are needed: the
#: first keeps her inside what the gate will accept, the second keeps a tick
#: from crossing the whole of the room left, which is the one error this
#: clock cannot correct afterwards.
#: `TICK_SHARE` is under a half on purpose: at a half a tick lost to
#: swinging the nose round carries her exactly as far again, and the gate is
#: gone. Under it, a lost tick is survivable, which matters because this
#: clock loses one whenever the burn changes ends.
CARRY_SHARE, TICK_SHARE = 0.5, 0.3

#: How far under the ceiling she is allowed to dawdle before the drive is
#: used to push her down. A band, not a rate: it is what keeps the nose from
#: swinging end for end every few ticks, and without it a descent to an
#: asteroid — where nothing accelerates her — coasted the whole three
#: hundred kilometres at the twenty metres a second she cast off with, two
#: hundred and thirty ticks of a pilot watching a number not change.
FALL_BAND = 0.5

#: What an arrival that was not a landing takes off her, as a share of her
#: hull per multiple of the gate rate she was over it by, and what it does
#: to everybody aboard (`game.wounds`, the same door `sim/craft_battle`
#: puts a shot-down pilot through).
CRASH_SHARE, CRASH_HURT = 0.55, 5.0


@dataclass
class Descent:
    """A lander on her way down, and what she is taking with her.

    Transient, like the engagement and the sortie it rides beside: a
    chronicle saved mid-descent comes back with the craft on her cradle,
    which is the same thing that happens to a flight in progress.
    """

    craft_id: int
    body_index: int
    cell: tuple = ()
    load: int = 1
    officer_ids: tuple = ()
    #: What she came through the gate at, once she has.
    gate_rate: float = 0.0


# ── where she is ───────────────────────────────────────────────────────────

def under_way(game):
    """The descent being flown, or None."""
    return getattr(game, "descent", None)


def height_km(conn) -> float:
    """How far she is above the surface, in km."""
    radius = float(getattr(conn.target, "radius_km", 0.0) or 0.0)
    return max(0.0, conn.range_km - radius)


def gate_km(conn) -> float:
    """The height a descent is judged at, in km above the surface.

    **One tick of falling from rest**, which is the finest this clock can
    resolve. A descent cannot be judged below the distance a minute of the
    world's own gravity carries her, because nothing the pilot does inside
    that minute exists: the drive is an impulse at the top of the tick.

    On a small body that is a few hundred metres and `GATE_LEAST_KM` stands
    instead; on a rocky world it is eighteen kilometres, which is about
    where a real lander stops flying and starts landing anyway.
    """
    from . import landing as landing_sim
    pull = landing_sim.surface_g(getattr(conn, "target", None))
    return max(GATE_LEAST_KM, GATE_FALL * pull * TICK * TICK / 2.0 / 1000.0)


def catch_rate(conn) -> float:
    """The most she may be carrying at the gate, in m/s.

    What her drive cancels in one burn — `main_dv` — because below the gate
    that is the only move left, and a craft that arrives with more than the
    drive can take off her arrives with the rest of it.

    It is always a rate she can make. `data/craft.LIFT_RESERVE` will not let
    her set down anywhere her thrust is under 1.35 times the pull, so the
    drive is always at least a third stronger than a tick of free fall — and
    the margin that decides which worlds she may land on turns out to be the
    same margin that makes the descent flyable. Fly it badly, carry the
    orbital velocity in, or let her simply fall, and she is over it.
    """
    return max(TOUCH_RATE, float(getattr(conn, "main_dv", 0.0) or 0.0))


def under_control(conn) -> bool:
    """Is she coming down as something that is going to land?"""
    return landing.can_hold(conn) and conn.speed <= catch_rate(conn)


# ── the law she is flown by ────────────────────────────────────────────────

def ceiling(conn) -> float:
    """The fastest she may be making at this height, in m/s.

    Two things in one statement, and the order matters.

    **While she is carrying more than the drive takes off in one burn, the
    law asks for a dead stop** — which at five kilometres a second across
    the line of sight is exactly a de-orbit burn, and is the whole of what a
    lander does first. Asking for a descent rate at the same time is what
    the first draft did, and it flew every rocky world into the ground: she
    was told to come down while she was still going round, so she spent the
    height killing the orbit and met the gate at three kilometres a second.

    **After that it is a rate**, and two things bound it. The room is the
    room *above the gate*, not above the ground, because a tick that carries
    her past the gate and into the surface is judged by `sim/outcome` as a
    hull meeting a world — which it is, and which is not what she was
    flying. And the rate asked for is the rate she should be making at the
    *end* of the tick, so what the world adds during it comes off first:
    the drive fires once, at the top of the minute, and a law that ignores
    the fifty-nine seconds after it is a law that is always one tick behind.
    Measured with it ignored, every mid-gravity world came through the gate
    about `g · TICK` too fast — 476 m/s where 144 was asked for — and nine
    worlds in twelve sectors were wrecks that should have been landings.
    """
    if conn.speed > catch_rate(conn):
        return 0.0
    room = max(0.0, height_km(conn) - gate_km(conn)) * 1000.0
    rate = min(catch_rate(conn) * CARRY_SHARE, room / TICK * TICK_SHARE)
    return max(TOUCH_RATE, rate - landing.surface_g(conn.target) * TICK)


def wanted(conn) -> list:
    """That ceiling as a velocity: straight down the radius."""
    r = conn.range_km
    if r < 1e-9:
        return [0.0, 0.0, 0.0]
    rate = ceiling(conn)
    return [-c / r * rate for c in conn.pos]


def step(game, conn) -> tuple:
    """What the computer does this beat with `down` armed.

    `(axis, main, throttle)`, the shape every other mode returns, because
    `sim/flightdeck.computer` is the one dispatcher.

    **A ceiling, trimmed against — never a rate chased.** A law that flies
    *to* a descent rate burns to speed her up whenever she is under it, and
    the burn that does that points the other way: measured, the nose swung
    round every few ticks, each swing cost a whole tick with no thrust in
    it, and the tick she lost at ten kilometres was the one that put her
    into the ground at 454 m/s. Falling is free and the world does it for
    you. The drive is asked for a burn only when she is over the ceiling or
    dawdling well under it (`FALL_BAND`), which on any real descent is a
    push at the top and trims from there on.
    """
    from . import autopilot as auto_sim
    rate = ceiling(conn)
    if rate * FALL_BAND <= conn.speed <= rate:
        return None, False, 1.0
    return auto_sim.hold(conn, wanted(conn))


def watch(game, conn) -> None:
    """Has she reached the gate? Called every tick of a descent.

    Not `sim/outcome`'s business: that resolves a contact with the *surface*,
    which on a world is always a crash and is the right answer for a hull.
    A craft built to land stops being flown a couple of kilometres up.
    """
    plan = under_way(game)
    if plan is None or conn is None or conn.over:
        return
    if height_km(conn) > gate_km(conn):
        return
    plan.gate_rate = round(conn.speed, 2)
    if under_control(conn):
        conn.outcome = "down"
        conn.log.append(
            f"Through {gate_km(conn):,.1f} km at {conn.speed:,.0f} m/s — "
            "the drive has that, and she is on her legs.")
        return
    conn.outcome = "aground"
    conn.log.append(
        f"Through {gate_km(conn):,.1f} km at {conn.speed:,.0f} m/s, and the "
        f"drive takes {catch_rate(conn):,.0f} off her. She is not going to "
        "stop.")


# ── beginning one ──────────────────────────────────────────────────────────

def contact_for(game, body_index: int):
    """The world as something a conn can be opened on."""
    from . import track as track_sim
    return next((c for c in track_sim.contacts(game)
                 if c.kind == "body" and c.body_index == body_index), None)


def can_fly(game, craft, body) -> tuple:
    """May this craft be flown down to that world? `(ok, why)`."""
    from . import descent as descent_sim
    ok, why = descent_sim.can_land(game, craft, body)
    if not ok:
        return False, why
    from . import craft as craft_sim
    if craft_sim.flying(game) is not None:
        return False, "Another craft is out; the cradle deck is busy."
    if under_way(game) is not None:
        return False, "Something is already on its way down."
    if getattr(game, "battle", None) is not None:
        return False, "Not in the middle of an engagement."
    if not descent_sim.in_orbit(game, body):
        return False, (f"She is not in orbit of {body.name}. A descent "
                       "starts from orbit.")
    return True, ""


def begin(game, craft, body_index: int, cell=(), load: int = 1,
          officer_ids=(), pilot: str = "") -> dict:
    """Off the cradle and on her way down, flown from the cockpit."""
    from . import craft as craft_sim
    from . import conn_open
    body = game.system.bodies[body_index]
    ok, why = can_fly(game, craft, body)
    if not ok:
        return {"ok": False, "why": why}
    contact = contact_for(game, body_index)
    if contact is None:
        return {"ok": False, "why": f"{body.name} is not on the plot."}
    pilot = pilot or craft_sim.who_flies(game, craft)
    if not pilot:
        return {"ok": False, "why": "Nobody aboard holds her certificate."}
    conn = conn_open.start(game, contact)
    craft_sim._fit(conn, craft)
    spent = _deorbit(conn)
    # **She opens in the orbit the ship is holding, and that is not an
    # outcome.** `conn_open.start` sets `opened_orbiting` for exactly this:
    # left to itself `sim/outcome` writes "orbit" on the first tick and the
    # descent is over before a control is touched — measured, every rocky
    # world ended one tick in with the lander still 320 km up.
    who = craft_sim.name_of(game, pilot)
    conn.log.append(
        f"{craft.name} away for the surface, {who} at the stick. The "
        f"retrograde burn is behind her: {height_km(conn):,.0f} km up, "
        f"falling at {conn.speed:,.0f} m/s, and the world coming up.")
    game.sortie = conn
    game.descent = Descent(craft_id=craft.id, body_index=body_index,
                           cell=tuple(cell) if cell else (),
                           load=int(load),
                           officer_ids=tuple(int(o) for o in officer_ids))
    craft.state, craft.pilot = "out", pilot
    craft.sorties += 1
    from ..data import craft as table
    craft.fuel = max(0.0, craft.fuel - table.LAUNCH_T - spent)
    conn.rcs = conn.opening_rcs = craft.fuel
    game.add_log(f"{craft.name} is on her way down to {body.name} — "
                 f"{who} flying.", "")
    return {"ok": True, "conn": conn, "pilot": pilot, "who": who,
            "craft": craft}


def _deorbit(conn) -> float:
    """Spend the orbital velocity before the cockpit opens, and say what it
    cost her in tonnes.

    **The de-orbit is not the descent, and it must not be flown against this
    clock.** Measured with it left in: a lander cast off from a 320 km orbit
    of a heavy world is carrying five kilometres a second across the line of
    sight, the drive takes 1,294 of it off a tick and the world puts 780
    back, so she spends the whole of the sky turning the orbit round and
    meets the gate at three thousand metres a second. Eleven of the
    thirty-eight worlds in twelve sectors were unlandable for that reason
    alone, including every world a party would actually want to walk on.

    It is a burn, not a dispensation: it comes out of her tank at the rate
    every other burn in this game is paid for, and what is left is what she
    has to hold the fall with.
    """
    r = conn.range_km
    was = math.dist(conn.vel, (0.0, 0.0, 0.0))
    conn.vel = [-c / r * OPEN_DRIFT for c in conn.pos]
    conn.nose = [-c / r for c in conn.pos]
    spent = was / max(1e-9, float(conn.main_dv)) * MAIN_COST
    conn.rcs = max(0.0, conn.rcs - spent)
    conn.opening_rcs = conn.rcs
    return round(spent, 3)


# ── and ending one ─────────────────────────────────────────────────────────

def arrive(game) -> dict:
    """The descent is over: put the party down, or count what it cost.

    Called from `sim/craft.beat` the tick the flight ends, so a descent
    flown in the cockpit and one flown by a check end the same way.
    """
    plan, conn = under_way(game), getattr(game, "sortie", None)
    if plan is None:
        return {"ok": False, "why": "Nothing is on its way down."}
    from . import craft as craft_sim
    craft = next((c for c in craft_sim.aboard(game) if c.id == plan.craft_id),
                 None)
    how = (getattr(conn, "outcome", "") or "aground") if conn else "aground"
    game.descent = None
    game.sortie = None
    if craft is None:
        return {"ok": False, "why": "She is not aboard."}
    if how == "down":
        return _down(game, plan, craft)
    return _crash(game, plan, craft, conn, how)


def _down(game, plan, craft) -> dict:
    """She is on her legs: the party is on the ground (`sim/fieldwork`)."""
    from . import descent as descent_sim
    from . import fieldwork as fieldwork_sim
    craft.state, craft.pilot = descent_sim.DOWN, craft.pilot
    body = game.system.bodies[plan.body_index]
    got = fieldwork_sim.launch_expedition(
        game, plan.body_index, list(plan.officer_ids), load=plan.load,
        at=plan.cell or None, flown=True)
    if not got.get("ok"):
        # She is down and the party is not: whatever refused it — supplies,
        # a survey — is the captain's to fix, and she can be brought up.
        game.add_log(f"{craft.name} is down on {body.name}, and the party "
                     f"is not: {got.get('why', '')}", "warn")
        return {"ok": True, "down": True, "party": False,
                "why": got.get("why", "")}
    game.add_log(f"{craft.name} is down on {body.name} at "
                 f"{plan.gate_rate:,.1f} m/s.", "good")
    return {"ok": True, "down": True, "party": True,
            "rate": plan.gate_rate}


def _crash(game, plan, craft, conn, how: str) -> dict:
    """She is not. What that costs her, her pilot and her passengers."""
    from . import craft as craft_sim
    kind = craft_sim.kind_of(craft)
    body = game.system.bodies[plan.body_index]
    rate = plan.gate_rate or (conn.speed if conn is not None else 0.0)
    over = rate / max(1.0, catch_rate(conn)) if conn is not None else 2.0
    harm = int(round(kind.hull * CRASH_SHARE * max(1.0, over)))
    hurt = dict(getattr(game, "wounds", None) or {})
    for key in [craft.pilot or "captain"] + [f"officer:{o}"
                                             for o in plan.officer_ids]:
        who = "captain" if key == "captain" else key.split(":")[-1]
        hurt[who] = round(float(hurt.get(who, 0.0)) + CRASH_HURT, 1)
    game.wounds = hurt
    craft.hp -= harm
    if craft.hp <= 0:
        craft.state, craft.hp, craft.pilot = "lost", 0, ""
        game.add_log(f"{craft.name} went into {body.name} at "
                     f"{rate:,.0f} m/s. She is gone, and everybody who rode "
                     "her down is hurt.", "bad")
        return {"ok": True, "down": False, "lost": True, "harm": harm}
    craft.state, craft.pilot = "cradled", ""
    game.add_log(f"{craft.name} is back on the cradle with {harm} off her "
                 f"hull — {rate:,.0f} m/s through the gate at {body.name} "
                 "was not a landing.", "bad")
    return {"ok": True, "down": False, "lost": False, "harm": harm}


def says(game) -> str:
    """One line for a screen: how the descent is going."""
    plan, conn = under_way(game), getattr(game, "sortie", None)
    if plan is None or conn is None:
        return ""
    body = game.system.bodies[plan.body_index]
    return (f"Down to {body.name}: {height_km(conn):,.0f} km up at "
            f"{conn.speed:,.0f} m/s, and the drive takes "
            f"{catch_rate(conn):,.0f} off her at the gate.")
