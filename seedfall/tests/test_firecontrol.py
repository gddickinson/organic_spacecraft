"""The fire control: the button `sim/engage` waited for, and the band it earns.

`sim/engage` decided who may be fired on and at what band from the moment it
landed, and nothing in `ui/` could reach it — the console offered the clock,
the orbit and the berth and not one word about weapons. This is that button.

Two things are worth checking and neither is cosmetic.

**A refusal is printed, not greyed.** `engage.may_engage` returns a sentence
because a grey button teaches nothing. The panel must show it.

**The band the flying earned is the band that gets fought.** `ui/battle_view`
has its own `begin`, which builds a `Battle` from an encounter dict with no
band at all, so routing a conn engagement through it would silently discard the
range the pilot worked for. The two-door risk named in #136.
"""

from __future__ import annotations

from ..sim import combat as combat_sim
from ..sim import engage as engage_sim
from ..sim import track as track_sim
from .harness import Suite


def run(suite: Suite) -> bool:
    try:
        import PyQt6  # noqa: F401
    except ImportError as err:
        print(f"── fire control ───\n  skipped: PyQt6 not available ({err})\n")
        return False

    from .test_pilot_screen import _bridge
    check = suite.check

    @check("every hull in view is offered a gun, with the band said first")
    def _():
        from PyQt6.QtWidgets import QPushButton
        from ..ui import fire_panel
        game, _win, view = _bridge("fire")
        labels = [b.text() for b in view.findChildren(QPushButton)]
        offered = [t for t in labels if t.startswith("Open fire on ")]
        assert offered, f"no gun offered at all: {labels}"

        contacts = track_sim.contacts(game)
        rows = fire_panel.ranged(game, view.conn, contacts)
        hulls = fire_panel.targets(rows)
        assert hulls, "nothing out there is a hull"
        for hull in hulls[:4]:
            assert f"Open fire on {hull.name}" in offered, (hull.name, offered)
        assert all(h.kind == "hull" for h in hulls), [h.kind for h in hulls]

        # **Nothing beyond the guns gets a trigger.** Rendered and read, the
        # first draft offered to open fire on a hull 1,293,058,866 km away and
        # called it extreme range, because `band_for` clamps to the last band.
        # Four of five hulls on this seed are like that. Printing a refusal is
        # for a plausible no, not for something half a system off.
        reach = engage_sim.reach_km()
        every = [c for c in contacts if c.kind == "hull"]
        far = [c for c in every
               if engage_sim.range_km(game, view.conn, c) > reach]
        assert far, "this seed has nothing out of reach; the check proves nothing"
        for hull in far:
            assert f"Open fire on {hull.name}" not in offered, (
                f"{hull.name} is "
                f"{engage_sim.range_km(game, view.conn, hull):,.0f} km off and "
                f"was offered a trigger; the guns reach {reach:,.0f}")
            ok, why = engage_sim.may_engage(game, view.conn, hull)
            assert not ok and "reach" in why, why
        assert len(hulls) == len(every) - len(far), (len(hulls), len(every))
        # And the board says what firing would mean, in `sim/combat`'s own
        # words, before anything is committed.
        line = engage_sim.note(game, view.conn, hulls[0])
        assert any(b.lower() in line.lower() for b in combat_sim.BANDS), (
            f"the board names no band: {line!r}")
        assert "km" in line, line
        return (f"{len(offered)} of {len(every)} hulls offered a gun; "
                f"{len(far)} beyond {reach:,.0f} km refused")

    @check("the pilot can mark a hull an enemy, and unmark it")
    def _():
        # The last piece of the original request: "set targets as enemies to
        # be targeted". The button is on the shared fire control, so any
        # screen that grows one gets it.
        from PyQt6.QtWidgets import QPushButton
        from ..sim import hostiles as hostiles_sim
        from ..ui import fire_panel
        game, win, view = _bridge("hostile")

        hull = fire_panel.targets(view.ranged())[0]
        labels = [b.text() for b in view.findChildren(QPushButton)]
        assert f"Mark {hull.name} hostile" in labels, labels
        assert not any("Clear the mark" in t for t in labels), labels

        fire_panel._flip(win, game, hull)
        assert hostiles_sim.is_marked(game, hull.hull_id)
        labels = [b.text() for b in view.findChildren(QPushButton)]
        assert f"Clear the mark on {hull.name}" in labels, (
            "the button still offers to mark a hull already marked")
        # The board says so too, in the row rather than only in the button.
        rows = view.ranged()
        panel = fire_panel.board(game, view.conn, rows)
        painted = panel.grab()
        assert painted.width() > 0
        # And the screen wrote it down, because the pilot pressed something.
        assert any("marked an enemy" in str(r) for r in game.log[-3:]), (
            "marking said nothing in the log")

        fire_panel._flip(win, game, hull)
        assert not hostiles_sim.is_marked(game, hull.hull_id)
        labels = [b.text() for b in view.findChildren(QPushButton)]
        assert f"Mark {hull.name} hostile" in labels, labels
        return f"{hull.name} marked from the bridge, and unmarked"

    @check("a refusal is printed with its reason, never greyed away")
    def _():
        from ..ui import fire_panel
        game, win, view = _bridge("fire")
        said = []
        win.toast = lambda msg, kind="": said.append(msg)

        body = next(c for c in track_sim.contacts(game) if c.kind == "body")
        assert not fire_panel.open_fire(win, game, view.conn, body), (
            "opened fire on a world")
        assert said and "world" in said[-1], said
        assert win.battle is None, "a refusal still started a fight"

        # Mid-approach the guns answer to the conn, and say so.
        quay = next(c for c in track_sim.contacts(game)
                    if c.kind == "anchorage")
        hull = next(c for c in track_sim.contacts(game) if c.kind == "hull")
        view.conn.target = quay
        assert not fire_panel.open_fire(win, game, view.conn, hull)
        assert "break off" in said[-1].lower(), said[-1]
        # The refusal is readable twice: the log keeps it, not just the toast.
        assert any(said[-1] in str(row) for row in game.log[-4:]), (
            "the refusal was toasted and never written down")
        return " · ".join(f"“{s.split('.')[0][:38]}”" for s in said[:2])

    @check("the band the flying earned is the band that gets fought")
    def _():
        # **The two-door risk.** `battle_view.begin` builds its own `Battle`
        # from an encounter dict and passes no band; `engage.open_fire`
        # returns one already opened at the range the pilot flew to. Handing
        # over what `engage` built is the only way the flying counts.
        from ..ui import fire_panel
        seen = {}
        for burns in (0, 150):
            game, win, view = _bridge("fire")
            hull = next(c for c in track_sim.contacts(game) if c.kind == "hull")
            if burns:
                view.fly_at(hull)
                view.use_main = True
                for _ in range(burns):
                    view.burn("forward")
            km = engage_sim.range_km(game, view.conn, hull)
            want = engage_sim.band_for(game, view.conn, hull)
            # **`not view.running` was tautological** and a mutation said so:
            # the clock was never started, so it read False whether or not
            # firing stopped it. Start it, then no time may pass while she is
            # being shot at.
            view.set_running(True)
            assert view.running and view._timer.isActive(), "the clock will not run"
            assert fire_panel.open_fire(win, game, view.conn, hull), "refused"
            assert win.battle is not None, "no fight began"
            assert win.battle.band == want, (
                f"flew to {km:,.0f} km, which opens at band {want} "
                f"({combat_sim.BANDS[want]}), and the fight opened at "
                f"{win.battle.band} ({combat_sim.BANDS[win.battle.band]})")
            assert win.battle.enemy_name == hull.name, win.battle.enemy_name
            assert win.current == "battle", win.current
            assert not view.running, "the clock ran on while under fire"
            assert not view._timer.isActive(), (
                "the beat timer is still live during an engagement")
            seen[burns] = (km, want)
        # And the band is not a constant wearing a measurement: flying changed
        # it. Without this the check above passes on any fixed band.
        assert seen[0][1] != seen[150][1], (
            f"at rest {seen[0][0]:,.0f} km and after burning "
            f"{seen[150][0]:,.0f} km, both fights opened at band "
            f"{seen[0][1]} — the flying bought nothing")
        return " · ".join(
            f"{km:,.0f} km → {combat_sim.BANDS[b]}" for km, b in seen.values())

    return True
