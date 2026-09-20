"""A contact is something you can see: crashes, berthings, and what they cost.

The gap this covers was photographed rather than argued. A hull was flown into
a Fleet Hub at 55 m/s — 1,134 points off a hull that has 336, the end of a
starting chronicle — and the only thing that changed on the screen was one
line of nine-point italic type along the bottom of the window. The structure
was not even in the camera the player was looking at, because the nose was
180° off and the whole event happened in the aft feed.

Four claims, and each of them has a check here that bites:

- **The picture is read out of the flight, not invented.** `sim/shock.py`
  takes its figures from the approach the sim has just resolved — the speed,
  both sides' damage, the shove, the fitting that was missed — so the words
  on the glass and the line in the log cannot disagree.
- **The glass actually changes**, measured in pixels, and it changes in the
  direction the thing was in.
- **A berthing does not look like a crash.** Arriving somewhere on purpose is
  a different event, not a small collision, and the two are drawn apart.
- **It goes out on its own clock, and that clock moves nothing.** A collision
  stops the flight clock, so the animation runs on a second timer that
  advances no calendar and draws no luck.
"""

from __future__ import annotations

import math
import time

from ..core.state import new_game
from ..sim import berthing as berth_sim
from ..sim import conn as conn_sim
from ..sim import shock as shock_sim
from ..sim import track as track_sim
from .harness import Suite
from .qtkit import app as _app
from .qtkit import main_window

#: A frozen clock, so a check can ask what the picture looks like 300 ms after
#: a collision without waiting 300 ms for it. The one hook `ui/effects` leaves
#: for exactly this, the way `soundmap.clock` does.
NOW = [1_000.0]


def _at(when: float) -> float:
    NOW[0] = 1_000.0 + when
    return NOW[0]


def _deck(seed: str, kind: str = "anchorage"):
    """A window with the conn open on something that can be flown into."""
    from ..ui import effects
    from ..ui.conn_window import open_conn
    keep = _app()
    effects.clock = lambda: NOW[0]
    effects.clear()
    _at(0.0)
    game = new_game(seed)
    win = main_window(game, (1200, 820))
    target = next(c for c in track_sim.contacts(game)
                  if c.kind == kind and berth_sim.can_conn(game, c)[0])
    window = open_conn(win, target)
    window.resize(1000, 700)
    keep.processEvents()
    return win, window, win.conn


def _shut(win, window) -> None:
    keep = _app()
    window.close()
    keep.processEvents()
    win.close()
    keep.processEvents()


def _fly_into(win, conn, speed: float, beats: int = 3_000) -> None:
    """Point her at it, take the safeties off, and let the clock run."""
    conn.safeties = False
    span = conn.range_km
    conn.vel = [-p / span * speed for p in conn.pos]
    for _ in range(beats):
        win.fly_beat()
        if conn.over:
            return


def _fly_gently(win, conn, beats: int = 4_000) -> None:
    """Let the flight computer berth her, which is what it is for."""
    conn.auto = "close"
    win.set_conn_clock(True)
    for _ in range(beats):
        win.fly_beat()
        if conn.over:
            return


def _changed(feed, a: float, b: float) -> int:
    """How many sampled pixels differ between two instants of one camera."""
    _at(a)
    first = feed.grab().toImage()
    _at(b)
    again = feed.grab().toImage()
    w, h = feed.width(), feed.height()
    return sum(1 for y in range(0, h, 3) for x in range(0, w, 3)
               if first.pixel(x, y) != again.pixel(x, y))


def run(suite: Suite) -> None:
    check = suite.check

    @check("what is drawn is what the approach actually did")
    def _():
        win, window, conn = _deck("shock-read")
        _fly_into(win, conn, 55.0)
        assert conn.outcome == "collision", conn.outcome
        hit = shock_sim.of(win.game, conn)
        assert hit is not None and hit.kind == "collision", hit
        # Every figure is the flight's own, not a second copy of the physics.
        assert abs(hit.speed - conn.speed) < 1e-6, (hit.speed, conn.speed)
        assert abs(hit.harm - conn.damage) < 1e-6, (hit.harm, conn.damage)
        assert abs(hit.struck_harm - conn.struck_damage) < 1e-6, hit
        assert abs(hit.struck_dv - conn.struck_dv) < 1e-6, hit
        # The bearing is a bearing: a unit vector at the thing that was hit.
        span = math.dist(hit.bearing, (0.0, 0.0, 0.0))
        assert abs(span - 1.0) < 1e-9, span
        toward = [-p / conn.range_km for p in conn.pos]
        assert math.dist(hit.bearing, toward) < 1e-6, (hit.bearing, toward)
        # And the words quote the figures rather than restating them.
        head, line = shock_sim.banner(hit)
        assert conn.target.name.upper() in head, head
        assert f"{hit.harm:,.0f}" in line, line
        assert f"{hit.struck_dv:,.2f}" in line, line
        _shut(win, window)
        return (f"{head} — {line}")

    @check("the picture is as hard as the blow, and it dies away")
    def _():
        from ..ui import effects
        got = {}
        for speed in (4.5, 12.0, 55.0):
            win, window, conn = _deck(f"shock-hard-{speed}")
            _fly_into(win, conn, speed)
            hit = shock_sim.of(win.game, conn)
            got[speed] = hit.severity
            _shut(win, window)
        assert got[4.5] < got[12.0] < got[55.0], got
        # And the shake follows it, then goes.
        effects.clear()
        _at(0.0)
        effects.spawn(shock_sim.Shock(kind="collision", name="Quay",
                                      severity=1.0, seed="check:hard"))
        early = math.dist(effects.shake(_at(0.02)), (0.0, 0.0))
        later = math.dist(effects.shake(_at(0.70)), (0.0, 0.0))
        assert early > effects.SHAKE_FLOOR, early
        assert later < early * 0.2, (early, later)
        assert not effects.live(_at(effects.LIFE["collision"] + 0.1)), \
            "the collision is still on the glass after its life"
        effects.clear()
        return (f"severity {got[4.5]:.3f} · {got[12.0]:.3f} · {got[55.0]:.3f}; "
                f"shake {early:.1f} px at 20 ms, {later:.1f} px at 700 ms")

    @check("the window turns to the camera that actually saw it")
    def _():
        from ..ui import viewport
        win, window, conn = _deck("shock-look")
        # Nose hard over, so the thing she is flying at is behind her: the
        # case that was photographed, and the one a bearing has to survive.
        conn.nose = [p / conn.range_km for p in conn.pos]
        _fly_into(win, conn, 40.0)
        hit = shock_sim.of(win.game, conn)
        want = viewport.best_view(conn, hit.bearing)
        # The named camera holds it; at least one other does not, or the row
        # of six is six copies of one picture and the answer means nothing.
        from ..ui.viewport_math import project
        sees = {}
        for vid, _label, vec in conn_sim.VIEWS:
            spot = project(hit.bearing, viewport.basis(vec, conn), 400, 300)
            sees[vid] = spot is not None and 0 <= spot[0] < 400 \
                and 0 <= spot[1] < 300
        assert sees[want], f"{want} cannot see what it was picked for"
        assert not all(sees.values()), sees
        window.refresh()
        assert window.main_view == want, (window.main_view, want)
        _shut(win, window)
        return (f"{want} of {len(conn_sim.VIEWS)}; "
                f"{sum(sees.values())} cameras hold it")

    @check("a berthing is not drawn as a small crash")
    def _():
        from ..ui import effects
        win, window, conn = _deck("shock-berth")
        _fly_gently(win, conn)
        assert conn.outcome == "alongside", conn.outcome
        hit = shock_sim.of(win.game, conn)
        assert hit.kind == "alongside" and not hit.violent, hit
        assert hit.where, "a berthing that names no fitting"
        effects.clear()
        _at(0.0)
        effects.spawn(hit)
        # No shake, a cool wash, and words that say what happened.
        assert effects.shake(_at(0.05)) == (0.0, 0.0), effects.shake(_at(0.05))
        tint, alpha = effects.veil(_at(0.05))
        assert tint == "chloro" and alpha > 0.0, (tint, alpha)
        head, line = shock_sim.banner(hit)
        assert "ALONGSIDE" in head and hit.where in line, (head, line)
        # An arrival still gets a picture: it did no damage, and the formula
        # would otherwise leave it with nothing to be drawn with.
        assert effects.LIVE[0].power >= effects.ARRIVAL_POWER
        effects.clear()
        _shut(win, window)
        return f"{head} — {line}; no shake, {tint} at {alpha:.2f}"

    @check("one contact makes one picture, however often anybody looks")
    def _():
        from ..ui import effects
        win, window, conn = _deck("shock-once")
        _fly_into(win, conn, 30.0)
        collisions = [e for e in effects.LIVE
                      if e.shock.kind in ("collision", "scrape")]
        assert len(collisions) == 1, [e.shock.kind for e in effects.LIVE]
        # Every window looking again, and another beat, add nothing.
        for _ in range(4):
            assert effects.watch(win) == [], "a second look invented a contact"
        window.refresh()
        win.beat_refresh()
        assert len([e for e in effects.LIVE
                    if e.shock.kind in ("collision", "scrape")]) == 1
        _shut(win, window)
        return f"{len(effects.LIVE)} live after six looks and a beat"

    @check("a window opened on a finished flight does not replay it")
    def _():
        from ..ui import effects
        from ..ui.conn_window import open_conn
        win, window, conn = _deck("shock-stale")
        _fly_into(win, conn, 45.0)
        assert conn.over and effects.LIVE, "nothing to go stale"
        effects.clear()
        _shut(win, window)
        # A second window onto the same, already-resolved flight.
        again = open_conn(win, None)
        _app().processEvents()
        assert effects.watch(win) == [], "an old crash was drawn again"
        assert not effects.LIVE, [e.shock.kind for e in effects.LIVE]
        again.close()
        _app().processEvents()
        return "a resolved approach reopened: nothing drawn"

    @check("the glass changes, and the flash is where the thing was")
    def _():
        from ..ui import effects, viewport
        from ..ui.viewport_math import project
        win, window, conn = _deck("shock-pixels")
        _fly_into(win, conn, 55.0)
        window.refresh()
        feed = window.screen
        # **The lit frame first.** `effects.live` prunes what it walks past,
        # so asking for a late instant before an early one throws the
        # collision away and the second picture is the same empty sky as the
        # first — which is a check that passes on nothing.
        _at(0.30)
        lit = feed.grab().toImage()
        _at(effects.LIFE["collision"] + 0.5)
        quiet = feed.grab().toImage()
        w, h = feed.width(), feed.height()
        moved = sum(1 for y in range(0, h, 3) for x in range(0, w, 3)
                    if lit.pixel(x, y) != quiet.pixel(x, y))
        assert moved > 400, f"a 55 m/s collision moved {moved} pixels"

        # And the flash is *at the bearing*, not merely somewhere. A wash and
        # a caption cover the whole frame, so "which half changed" answers
        # nothing — measured, 11,171 samples against 10,976. What separates
        # them is how much brighter it got, and where.
        hit = shock_sim.of(win.game, conn)
        _vid, _label, vec = feed.view
        spot = project(hit.bearing, viewport.basis(vec, conn), w, h)
        assert spot is not None, "the contact is behind the camera it picked"
        at = (int(spot[0]), int(spot[1]))

        def lift(x: int, y: int) -> float:
            a_px, b_px = lit.pixelColor(x, y), quiet.pixelColor(x, y)
            return float(a_px.red() + a_px.green() + a_px.blue()
                         - b_px.red() - b_px.green() - b_px.blue())

        near = [lift(min(w - 1, max(0, at[0] + dx)),
                     min(h - 1, max(0, at[1] + dy)))
                for dy in range(-30, 31, 3) for dx in range(-30, 31, 3)]
        # The control is the whole frame, not the opposite corner: the wash
        # is a vignette and the caption is a band, so both of those brighten
        # the rim — and when the window has turned to the camera that saw it,
        # "the opposite point" *is* the contact. Measured that way, the two
        # boxes came back equal to fifteen decimal places.
        across = [lift(x, y) for y in range(0, h, 7) for x in range(0, w, 7)]
        on_it = sum(near) / len(near)
        anywhere = sum(across) / len(across)
        assert on_it > anywhere * 1.5 + 20.0, (on_it, anywhere)
        _shut(win, window)
        return (f"{moved:,} of {(w // 3) * (h // 3):,} samples moved; "
                f"+{on_it:,.0f} of light on the bearing against "
                f"{anywhere:+,.0f} over the frame")

    @check("the same crash is drawn the same way twice, and two differ")
    def _():
        from ..ui import effects
        from ..ui.viewport import Viewport
        win, window, conn = _deck("shock-same")
        _fly_into(win, conn, 55.0)
        feed = Viewport(conn, window.main_view)
        feed.resize(420, 320)
        _at(0.30)
        first = feed.grab().toImage()
        again = feed.grab().toImage()
        assert first == again, "one crash draws two different pictures"
        # A second contact on the same structure throws different debris.
        held = list(effects.LIVE)
        effects.clear()
        other = shock_sim.Shock(kind=held[0].shock.kind,
                                name=held[0].shock.name,
                                bearing=held[0].shock.bearing,
                                severity=held[0].shock.severity,
                                seed=held[0].shock.seed + ":second")
        _at(0.0)
        effects.spawn(other)
        _at(0.30)
        differs = feed.grab().toImage()
        assert differs != first, "two contacts throw identical debris"
        effects.clear()
        _shut(win, window)
        return "one shock, one picture; a second shock, a different one"

    @check("the picture runs on its own clock, and that clock moves nothing")
    def _():
        from ..ui import effect_clock, effects
        win, window, conn = _deck("shock-clock")
        _fly_into(win, conn, 55.0)
        # The flight's clock is stopped by the crash; the frame clock is not.
        assert not conn.clock_on, "the flight clock ran on through a collision"
        assert win.effect_timer.isActive(), "nothing is animating the crash"
        was = (win.game.day, win.game.rng_seed)
        for step in range(12):
            _at(0.05 * step)
            win.effect_frame()
            _app().processEvents()
        assert (win.game.day, win.game.rng_seed) == was, (
            f"twelve frames moved the chronicle: {was} → "
            f"{(win.game.day, win.game.rng_seed)}")
        # And it stops itself once there is nothing left to draw.
        _at(effects.LIFE["collision"] + 1.0)
        win.effect_frame()
        assert not effects.live(), [e.shock.kind for e in effects.LIVE]
        assert not effect_clock.wanted(win), "the frame clock wants another"
        assert not win.effect_timer.isActive(), "the frame clock never stops"
        _shut(win, window)
        return f"12 frames, day {was[0]} and the seed untouched; then stopped"

    @check("a window closed mid-crash does not take the process with it")
    def _():
        from ..ui import effect_clock, effects
        keep = _app()
        win, window, conn = _deck("shock-closing")
        _fly_into(win, conn, 55.0)
        assert win.effect_timer.isActive(), "nothing is animating the crash"
        # Warm the found set the way a few frames of animation would, so it
        # is holding the conn window's own cameras when they are destroyed.
        win.effect_frame()
        held = list(getattr(win, "effect_surfaces", []) or [])
        assert held, "the frame clock found nothing to repaint"
        # Every pop-out is WA_DeleteOnClose: closing it destroys the widgets
        # in that set, and `update()` on one of them raises inside a timer
        # slot where PyQt cannot propagate it — exit 134, nothing failing.
        window.close()
        keep.processEvents()
        win.effect_frame()
        keep.processEvents()
        alive = list(getattr(win, "effect_surfaces", []) or [])
        assert len(alive) < len(held), (len(alive), len(held))
        win.close()
        keep.processEvents()
        assert not win.effect_timer.isActive(), \
            "the animation clock outlived the window it was drawing on"
        effects.clear()
        return (f"{len(held)} surfaces before the close, {len(alive)} after; "
                f"the clock stopped with the window "
                f"(refind every {effect_clock.REFIND_EVERY} frames)")

    @check("every kind of contact has words, a colour, a life and a sound")
    def _():
        from ..ui import effect_paint, effects, soundmap
        missing = {}
        for kind in shock_sim.KINDS:
            for name, table in (("caption", shock_sim.CAPTION),
                                ("life", effects.LIFE),
                                ("veil", effects.VEIL_TINT),
                                ("spark", effect_paint.SPARK_TINT),
                                ("cue", soundmap.STRUCK_CUE)):
                if kind not in table:
                    missing.setdefault(kind, []).append(name)
        assert not missing, missing
        # And the words are different words: a table of ten rows that all say
        # the same thing is a table nobody has filled in.
        said = {shock_sim.CAPTION[k] for k in shock_sim.KINDS}
        assert len(said) == len(shock_sim.KINDS), sorted(said)
        return (f"{len(shock_sim.KINDS)} kinds, each with a caption, a life, "
                f"two tints and a cue")

    @check("a volley you take is felt, in its own picture and no other")
    def _():
        from ..core.rng import RNG
        from ..sim import encounters, gunfire
        from ..ui import effects
        from ..ui.battle3d import Battle3D
        keep = _app()
        effects.clear()
        _at(0.0)
        game = new_game("shock-volley")
        win = main_window(game, (1200, 820))
        win.go("battle")
        win.views["battle"].begin(
            {"enemy": encounters.make_enemy(RNG("shock-volley"),
                                            "concordat", 1.6),
             "intro": "A Yards hull lights you up."})
        battle = win.battle
        keep.processEvents()
        # Nothing has landed on her yet, so there is nothing to feel.
        assert not [s for s in battle.shots if not s.mine and s.landed]
        assert effects.gunfire(win) is None, "a volley out of nothing"
        # A volley that lands on you, the way `sim/gunfire` records one.
        battle.shots = [gunfire.Shot(frm="Them", to=game.ship.name,
                                     weapon="slug", look=gunfire.ROUND,
                                     outcome=gunfire.HIT, damage=90.0,
                                     mine=False)]
        battle.turn += 1
        made = effects.gunfire(win)
        assert made is not None and made.shock.kind == "gunfire", made
        assert made.shock.scene == shock_sim.BATTLE, made.shock.scene
        assert abs(made.shock.harm - 90.0) < 1e-6, made.shock.harm
        # And the same volley, looked at again, is the same one picture: the
        # battle log grows several times inside a turn.
        battle.log.append("the orders are read out again")
        assert effects.gunfire(win) is None, "one volley shook the frame twice"
        # It is in the engagement's picture and nowhere near the flight deck.
        assert effects.live(_at(0.05)) == [], "a volley reached the cameras"
        assert effects.live(_at(0.05), shock_sim.BATTLE), "and not the bridge"
        assert effects.shake(_at(0.05)) == (0.0, 0.0), "the conn shook"
        felt = math.dist(effects.shake(_at(0.05), shock_sim.BATTLE),
                         (0.0, 0.0))
        assert felt > effects.SHAKE_FLOOR, felt
        # And the engagement's own picture moves with it.
        view = Battle3D(battle)
        view.resize(420, 320)
        _at(0.05)
        struck = view.grab().toImage()
        _at(effects.LIFE["gunfire"] + 0.5)
        calm = view.grab().toImage()
        moved = sum(1 for y in range(0, 320, 3) for x in range(0, 420, 3)
                    if struck.pixel(x, y) != calm.pixel(x, y))
        assert moved > 200, f"a 90-point volley moved {moved} pixels"
        effects.clear()
        win.close()
        keep.processEvents()
        return (f"90 off the hull: {felt:.1f} px of shake and {moved:,} "
                f"samples moved, none of it on the flight deck")

    @check("a contact still running is drawn, and does not steal the camera")
    def _():
        from ..ui import effects
        win, window, conn = _deck("shock-live")
        held = window.main_view
        # Point defence opening up on an approach that will not turn away.
        conn.told, conn.warded_for = 3, 1
        fresh = effects.watch(win)
        assert [e.shock.kind for e in fresh] == ["ward"], fresh
        assert not fresh[0].shock.ends, "a ward ended the approach"
        window.refresh()
        assert window.main_view == held, (
            "being shot at moved the pilot's camera mid-approach")
        # A cut going through pulses rather than firing once a tick.
        effects.clear()
        step = 1.0 / effects.CUT_STEPS
        conn.cut = step
        assert [e.shock.kind for e in effects.watch(win)] == ["cut"], conn.cut
        conn.cut = step * 1.4
        assert effects.watch(win) == [], "the cut pulsed twice in one step"
        conn.cut = step * 2.2
        assert [e.shock.kind for e in effects.watch(win)] == ["cut"], conn.cut
        effects.clear()
        _shut(win, window)
        return (f"a ward drawn without taking the camera off {held}; "
                f"a cut pulses {effects.CUT_STEPS} times through")

    # **The frozen clock belongs to this suite.** `tests/runner.py` gives each
    # suite a process of its own, but `tests/pytest_shim.py` does not — and a
    # later suite that paints a camera would otherwise find this one's
    # collision still on the glass, at age zero, for ever.
    from ..ui import effects
    effects.clock = time.monotonic
    effects.clear()
