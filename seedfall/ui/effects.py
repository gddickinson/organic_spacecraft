"""How long a thing that happened stays on the glass, and how hard it lands.

The flight deck's eye. `sim/shock.py` says *what* passed between the hull and
something else; this says how long it is still worth seeing and how much of
the picture it may take. Nothing here imports Qt — it is a timeline and some
arithmetic, so a check can ask "how hard is the camera shaking 300 ms after a
55 m/s collision" without a display — and `ui/effect_paint.py` is the only
thing that touches a painter.

**The shape of it is `ui/soundmap.py`'s**, deliberately, because it is the
same problem solved once already: the sim leaves state behind, and something
that is not the sim has to notice the state changing. `watch` reads the
flight, compares it with what it saw last time, and spawns what is new. What
it saw last is kept on the *window* (`win.effect_eye`), never on the game —
the save codec refuses an attribute that is not a declared field, and a
half-finished animation is not something a chronicle should carry across a
reload anyway.

**One flight, one list.** Every window looks through the same `game.conn`, so
there is one `LIVE`, exactly as `viewport_hud` keeps one remembered path. Six
camera feeds and an outside view all paint the same collision; they must not
each own a copy of it, or they would each be shaking to a different beat.
"""

from __future__ import annotations

import math
import time
from dataclasses import dataclass

from ..core.rng import RNG
from ..sim import shock as shock_sim

#: The clock everything here is measured on. A check may put its own in, the
#: way `soundmap.clock` is replaced — an animation that can only be tested by
#: waiting is an animation nobody tests.
clock = time.monotonic

#: How long each kind stays on the glass, in seconds. A crash outlives a
#: berthing because there is more to look at and because the captain has a
#: decision to make about it; a cut pulses and goes, because the next one is
#: a quarter of a minute behind it.
LIFE = {
    "gunfire": 0.9,
    "collision": 3.4,
    "scrape": 1.2,
    "aground": 3.4,
    "ditched": 2.6,
    "down": 2.2,
    "alongside": 2.4,
    "orbit": 2.4,
    "captured": 1.8,
    "cut": 0.9,
    "ward": 1.1,
}
DEFAULT_LIFE = 1.5

#: The widest the camera is thrown off true, in pixels, and the least. The
#: floor is what a scrape is worth: felt, not watched. Measured against the
#: window rather than chosen — 18 px on a 360 px viewport is a twentieth of
#: the frame, which reads as a blow and still leaves the instruments legible.
SHAKE_MAX = 18.0
SHAKE_FLOOR = 2.0

#: How fast the shake dies away, and how fast it wobbles. Two frequencies a
#: little apart, so the picture moves on a figure rather than along a line —
#: one frequency on both axes is a diagonal twitch and reads as a glitch.
SHAKE_TAU = 0.26
SHAKE_HZ = (10.5, 13.5)

#: What an arrival is worth on the glass, whatever the arithmetic says.
#:
#: `power` is rooted damage, and a good arrival does no damage at all — so
#: coming alongside, making orbit and putting her down all computed to zero
#: and drew *nothing but a caption*. An arrival is not a small collision; it
#: is a different event, and this is how much of the frame it may have.
ARRIVAL_POWER = 0.5

#: How long the white core of a violent contact lasts, in seconds. Short: it
#: is the flash, not the fire, and a long one just looks like a broken screen.
FLASH_SECONDS = 0.11

#: The least of the white a contact may throw, at any size. Something that
#: costs the hull nothing at all still happened, and the eye should catch it.
FLASH_FLOOR = 0.18

#: The strongest the wash at the rim may get, for a contact that takes the
#: hull apart and for one that ends well, and how long it lasts.
#:
#: **Measured against being able to fly afterwards.** The first draft washed
#: the whole frame at 0.42 for the effect's whole life, and photographed at
#: 550 ms the picture was a red rectangle with a starfield in it: the pilot
#: could not see the structure they had just hit, or the one control that
#: would take them off it. A wash is a *reaction*, not a filter — short, and
#: at the edge of vision, where a real one is.
VEIL_HARD = 0.34
VEIL_SOFT = 0.16
VEIL_SECONDS = 1.1

#: How long the banner holds at full strength before it starts to go, as a
#: share of the effect's life.
BANNER_HOLD = 0.55

#: How many effects may be live at once. A cut pulses every few ticks and
#: point defence fires every tick; without a ceiling a captain who sits under
#: a hub's guns accumulates a hundred of them and the frame rate goes.
MOST = 6

#: The whole-frame wash each kind puts on the glass, as a theme tint name.
VEIL_TINT = {
    "collision": "bad", "aground": "bad", "ward": "bad", "gunfire": "bad",
    "ditched": "osteo", "scrape": "osteo", "cut": "osteo",
    "down": "chloro", "alongside": "chloro", "orbit": "lumen",
    "captured": "lumen",
}


@dataclass
class Effect:
    """One shock, with a birthday. The thing a painter is handed."""

    shock: shock_sim.Shock
    born: float
    life: float

    def age(self, now: float) -> float:
        """How far through it is, 0 at the instant it happened to 1 at gone."""
        if self.life <= 0.0:
            return 1.0
        return min(1.0, max(0.0, (now - self.born) / self.life))

    def over(self, now: float) -> bool:
        return self.age(now) >= 1.0

    @property
    def power(self) -> float:
        """How much of the picture this is entitled to, 0..1.

        The square root of the severity, because damage is quadratic in the
        closing speed and a picture that is linear in damage spends its whole
        range on the last few metres a second. Rooted, a 10 m/s arrival is
        plainly worse than a 4 m/s one and a 40 m/s arrival is still worse
        than that — which is how the speeds actually feel to fly.

        An arrival has a floor, because it did no damage and the formula
        would otherwise give it nothing to be drawn with. See `ARRIVAL_POWER`.
        """
        got = min(1.0, math.sqrt(max(0.0, self.shock.severity)))
        if self.shock.violent:
            return got
        return max(ARRIVAL_POWER, got)


#: Everything on the glass right now. One flight, one list — see the module
#: note. Ordered oldest first, which is the order they are painted in.
LIVE: list[Effect] = []


def clear() -> None:
    """Forget everything. A new chronicle, a closed window, a check."""
    LIVE.clear()


def spawn(hit: shock_sim.Shock | None, now: float | None = None) -> Effect | None:
    """Put a shock on the glass. Hands back what was made, or None."""
    if hit is None:
        return None
    now = clock() if now is None else now
    made = Effect(hit, now, LIFE.get(hit.kind, DEFAULT_LIFE))
    LIVE.append(made)
    del LIVE[:-MOST]
    return made


def live(now: float | None = None,
         scene: str = shock_sim.FLIGHT) -> list:
    """What is still worth drawing in one picture, oldest first.

    Prunes as it goes — every caller is a repaint, so the list is swept on
    the way past rather than on a timer nobody owns. **The scene is not
    optional decoration**: an engagement's shocks are placed in tactical
    coordinates and a flight's in the approach's own frame, so a camera that
    painted the other picture's list would draw a blow in a direction that
    means nothing.
    """
    now = clock() if now is None else now
    LIVE[:] = [e for e in LIVE if not e.over(now)]
    return [e for e in LIVE if e.shock.scene == scene]


def loudest(now: float | None = None,
            scene: str = shock_sim.FLIGHT) -> Effect | None:
    """The one effect that speaks for the frame — the shake, the wash, the
    words. Worst first, and the newest of equals: a collision during a
    berthing is the thing that happened."""
    now = clock() if now is None else now
    got = live(now, scene)
    if not got:
        return None
    return max(got, key=lambda e: (e.power, e.born))


def shake(now: float | None = None,
          scene: str = shock_sim.FLIGHT) -> tuple:
    """How far off true the picture is thrown, in pixels: `(dx, dy)`.

    A decaying wobble, summed over everything live, so two hits close
    together add rather than the second one replacing the first. The phases
    come from the shock's own seed, so one crash does not throw the picture
    the same way as the next and a repaint of one crash throws it the same
    way every time.
    """
    now = clock() if now is None else now
    dx = dy = 0.0
    for effect in live(now, scene):
        hit = effect.shock
        if not hit.violent and hit.kind != "captured":
            continue
        span = now - effect.born
        fall = math.exp(-span / SHAKE_TAU)
        if fall < 0.01:
            continue
        amp = SHAKE_FLOOR + (SHAKE_MAX - SHAKE_FLOOR) * effect.power
        rng = RNG(f"{hit.seed}:shake")
        phase_x, phase_y = rng.float(0.0, math.tau), rng.float(0.0, math.tau)
        dx += amp * fall * math.sin(span * math.tau * SHAKE_HZ[0] + phase_x)
        dy += amp * fall * math.sin(span * math.tau * SHAKE_HZ[1] + phase_y)
    return dx, dy


def veil(now: float | None = None,
         scene: str = shock_sim.FLIGHT) -> tuple:
    """The whole-frame wash: `(tint name, alpha 0..1)`. Alpha 0 is nothing.

    Two stages for anything violent. The first hundred milliseconds are white
    — the flash, which is what the eye actually catches — and what follows is
    the colour of the news. A berthing gets the second stage only, in green,
    and gently: arriving somewhere should not look like being hit.

    The wash goes out on its own clock, not the effect's. A collision's marks
    are worth three seconds and its colour is worth one — the words and the
    fractures have to be readable, and they are not readable through it.
    """
    now = clock() if now is None else now
    effect = loudest(now, scene)
    if effect is None:
        return "", 0.0
    hit = effect.shock
    span = now - effect.born
    if hit.violent and span < FLASH_SECONDS:
        # **Scaled by the blow, like everything else here.** It was not, and
        # photographed: a three-point ranging shot from a hub's point defence
        # whited out the frame exactly as hard as a 1,134-point collision, so
        # the loudest thing the picture can say was being said about the
        # quietest thing that can happen.
        return "ink", (FLASH_FLOOR + (1.0 - FLASH_FLOOR) * effect.power) * (
            1.0 - span / FLASH_SECONDS)
    ceiling = VEIL_HARD if hit.violent else VEIL_SOFT
    left = 1.0 - min(1.0, span / VEIL_SECONDS)
    return VEIL_TINT.get(hit.kind, "bad"), ceiling * effect.power * left ** 2


def banner(now: float | None = None,
           scene: str = shock_sim.FLIGHT) -> tuple:
    """The words for the frame: `(head, line, alpha)`, or `("", "", 0.0)`.

    The words themselves are `shock.banner`'s, because every screen drawing
    this contact has to say the same thing about it. What is decided here is
    only how long they hold and how they go.
    """
    now = clock() if now is None else now
    effect = loudest(now, scene)
    if effect is None:
        return "", "", 0.0
    age = effect.age(now)
    fade = 1.0 if age <= BANNER_HOLD else 1.0 - (age - BANNER_HOLD) / (
        1.0 - BANNER_HOLD)
    head, line = shock_sim.banner(effect.shock)
    return head, line, max(0.0, min(1.0, fade))


def pulse(now: float | None = None, hz: float = 1.7) -> float:
    """A 0..1 throb for anything that is *still happening* rather than over.

    The collision guard's warning box and the alarm border read this. It is
    here rather than in the painter so that every screen showing the same
    standing threat throbs together — three windows each keeping their own
    phase is how an alarm comes to look like a flicker.
    """
    now = clock() if now is None else now
    return 0.5 - 0.5 * math.cos(now * math.tau * hz)


# ── the eye: what has happened since the last look ─────────────────────────

#: How many steps a cut is split into for the eye. The cut runs over minutes;
#: five pulses says "this is going on" without one a tick.
CUT_STEPS = 5


def _eye(win) -> dict:
    """What this window saw of the flight last time. Kept on the window."""
    eye = getattr(win, "effect_eye", None)
    if eye is None:
        eye = {"conn": None, "outcome": "", "boom": 0.0, "cut": 0.0,
               "warded": 0, "battle": None}
        win.effect_eye = eye
    return eye


def _reset(eye: dict, conn) -> None:
    """Take the flight as it stands, with nothing to report about it.

    A window opened onto a ship already in orbit, or already alongside, must
    not announce an arrival that happened before anybody was looking — which
    is exactly what a bare "the outcome is not empty" test would do, and 8 of
    11 body approaches open resolved (`sim/outcome`, `opened_orbiting`).
    """
    eye.update({
        "conn": id(conn),
        "outcome": conn.outcome or "",
        "boom": float(getattr(conn, "boom", 0.0) or 0.0),
        "cut": float(getattr(conn, "cut", 0.0) or 0.0),
        "warded": int(getattr(conn, "warded_for", 0) or 0),
    })


def gunfire(win) -> Effect | None:
    """What this turn of an engagement did to the hull, once a turn.

    The same shape as `watch` and, deliberately, the same shape as
    `soundmap.battle`: a battle leaves its turn behind on `battle.shots`, and
    something that is not the sim notices it has changed.

    **Keyed on the shock itself, not on the turn and the log.** The log grows
    several times inside one turn — the forecast, the orders, the aftermath
    — and a key that counted its lines would have called the same volley new
    two or three times and shaken the picture for each. The shock's own seed
    already holds the battle, the turn and what was taken, so two calls about
    one volley produce one key and one picture.
    """
    battle = getattr(win, "battle", None)
    eye = _eye(win)
    if battle is None or getattr(battle, "over", False):
        eye["battle"] = None
        return None
    hit = shock_sim.gunfire(win.game, battle)
    key = hit.seed if hit is not None else (id(battle), battle.turn)
    if eye["battle"] == key:
        return None
    eye["battle"] = key
    return spawn(hit)


def watch(win) -> list:
    """Everything that has happened to the flight since the last look.

    Called from the one beat (`ui/flight_clock`) and from every redraw that
    follows a burn, so no path that flies the ship can fly it into something
    without the picture saying so. Idempotent: it spawns on a *change*, so
    two callers in one beat produce one collision.

    `fatal` on a contact is read off the hull, so this wants calling after
    `berthing.commit` has taken the damage — which is where `fly_beat` calls
    it. A release-with-the-clock-held that resolves an approach reaches here
    first and reports the crash without knowing it was the last one; the log
    and the aftermath screen still say so, and the alternative is a window
    that waits a beat before showing the thing that just happened.
    """
    conn = getattr(win, "conn", None)
    eye = _eye(win)
    if conn is None:
        eye["conn"] = None
        return []
    if eye["conn"] != id(conn):
        _reset(eye, conn)
        return []
    game = win.game
    fresh = []
    outcome = conn.outcome or ""
    if outcome != eye["outcome"]:
        eye["outcome"] = outcome
        made = spawn(shock_sim.of(game, conn))
        if made is not None:
            fresh.append(made)
    # A boom closing on the hull, a cut going through, and point defence: all
    # three happen with the flight still running, and all three were numbers
    # on a panel moving by hundredths.
    boom = float(getattr(conn, "boom", 0.0) or 0.0)
    if boom >= 1.0 > eye["boom"]:
        fresh.append(spawn(shock_sim.captured(game, conn)))
    eye["boom"] = boom
    cut = float(getattr(conn, "cut", 0.0) or 0.0)
    if 0.0 < cut < 1.0 and int(cut * CUT_STEPS) > int(eye["cut"] * CUT_STEPS):
        fresh.append(spawn(shock_sim.cutting(game, conn)))
    eye["cut"] = cut
    warded = int(getattr(conn, "warded_for", 0) or 0)
    if warded > eye["warded"]:
        fresh.append(spawn(shock_sim.warded(game, conn)))
    eye["warded"] = warded
    return [e for e in fresh if e is not None]
