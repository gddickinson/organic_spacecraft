"""The gunner's station: which mounts speak, and what that costs the hull.

There were two ways to shoot and nothing between them. One named mount, or
`combat._salvo` — "everything that can bear, fired together", whose own
docstring says the cost is heat and ammunition "which is why a single aimed shot
stays a real option".

Measured, that is not a trade. **A HAMMERFALL with five mounts puts 69 points of
heat into itself in one salvo, against a fault line of 40 and a vent of 6 a
turn.** It faults on turn one and never recovers: across ten turns resolve bled
from 92.9 to −34 on its own radiators, in a fight it was winning on damage. The
alternative on offer was one mount out of five. So buying armament made the
salvo button worse, which is the question this project asks of every good thing.

`sim/gunnery.py` is the middle that was missing. Played over twelve engagements
at two difficulties with the guns supplied, the advised volley won 6/12 and 4/12
against 1/12 and 2/12 for firing everything, and never faulted once.

The claims:

- **The fault line is one number.** `_end_of_turn` tests it and the board quotes
  it: `heat_cap`, not `heat_cap * HEAT_CEILING`, which is a different thing a
  factor of two away and which I read the wrong way round first.
- **The quote is the act**, measured by firing the volley and looking.
- **A volley fires what was chosen and nothing else.**
- **A selection is a multiset, capped at what the hull carries** — three Fusion
  Lances all answer to `fusion_lance`.
- **A mount that will not bear costs nothing**, since `_fire` returns before the
  heat goes in.
- **The advice never says hold fire**, which the first draft did on alternate
  turns.
- **The board drives the trigger**, checked by pressing it.
- **And a sight draws an arc on both sides of the bow**, which mine did not.
"""

from __future__ import annotations

from ..core.rng import RNG
from ..core.state import new_game
from ..sim import combat, encounters, firing, gunnery
from ..sim.ship import HEAT_CEILING, build_layers, make_ship, stats
from .harness import Suite

#: A hull with five mounts and enough heat in them to make the choice bite.
HOT = ("hammerfall", ["fusion_lance"] * 3 + ["railgun", "pdc"])

#: Nothing but heavy guns, so on a warm hull *no* mount fits under the line and
#: the advice has to fall back on its floor. With a 2-heat PDC aboard there is
#: almost always something addable, which is why a sweep found the hold-fire
#: mutation surviving: the case only appears when every gun is expensive.
HEAVY = ("hammerfall", ["fusion_lance"] * 3)

#: Mixed arcs, so a mount that will not train is a real state.
ARCS = ("hammerfall", ["slug_battery", "mag_lance", "fusion_lance", "pdc",
                       "railgun"])


def _battle(seed="gun", loadout=HOT, difficulty=1.0, supplied=True):
    chassis, parts = loadout
    game = new_game(f"g-{seed}")
    game.ship = make_ship(chassis, parts + ["reaction_organ", "opsin_eyes"])
    build_layers(game.ship, game.bonuses)
    if supplied:
        # Five of the eighteen weapons draw `alloy` and a new captain carries
        # none, so an unsupplied hull reports every one of them dry. A gunnery
        # comparison flown on a dry ship measures nothing — which is exactly
        # what my first one did, for two whole rounds of numbers.
        for cargo in ("alloy", "ore", "biomass"):
            game.ship.cargo[cargo] = 400.0
    game.recompute()
    rng = RNG(f"g-{seed}")
    return game, rng, combat.start(
        game.ship, stats(game.ship, game.bonuses),
        encounters.make_enemy(rng, "concordat", difficulty),
        rng=rng, game=game, officers=game.officers)


def run(suite: Suite) -> None:
    check = suite.check

    @check("the fault line is one number, asked in one place")
    def _():
        # I read these the wrong way round first and built a quote on it. The
        # clamp is twice the line, so a board using the clamp would have called
        # a faulting volley safe every single time.
        _game, _rng, b = _battle()
        side = b.player
        assert gunnery.fault_line(side) == side.st.heat_cap
        assert gunnery.ceiling(side) == side.st.heat_cap * HEAT_CEILING
        assert gunnery.ceiling(side) > gunnery.fault_line(side), (
            "the clamp has to sit above the line or nothing could ever fault")

        # And the sim faults exactly where the board says: push the hull a
        # whisker either side of the line and see which turn hurts.
        line = gunnery.fault_line(side)
        for heat, want in ((line - 0.5, False), (line + 0.5, True)):
            _g2, rng2, b2 = _battle("edge")
            b2.player.ship.heat = heat + b2.player.st.vent
            before = b2.player.resolve
            combat._end_of_turn(b2, rng2)
            hurt = b2.player.resolve < before
            assert hurt == want, (
                f"at {heat:.1f} against a line of {line:.0f} the turn "
                f"{'hurt' if hurt else 'did not hurt'} the hull")
        return f"line {line:.0f}, clamp {gunnery.ceiling(side):.0f}"

    @check("the quote is what the volley does to the hull")
    def _():
        # Fired, not derived. The quote models the whole turn — heat in, clamp,
        # vent, then the fault test — so the only honest check is to take the
        # turn and look at the hull afterwards.
        looked, worst = 0, 0.0
        for seed in range(4):
            _game, rng, b = _battle(f"q{seed}")
            for picks in ("advise", "all", "one"):
                if b.over:
                    break
                live = [s.mount_id for s in gunnery.mounts(b) if s.can_fire]
                if not live:
                    break
                want = (gunnery.advise(b) if picks == "advise"
                        else live if picks == "all" else live[:1])
                said = gunnery.quote(b, want)
                b = combat.take_turn(b, {"type": "volley", "mounts": want}, rng)
                gap = abs(b.player.ship.heat - said["heat_after"])
                worst = max(worst, gap)
                assert gap < 1e-6, (
                    f"the board promised {said['heat_after']:.3f} heat and the "
                    f"hull came out at {b.player.ship.heat:.3f}")
                faulted = b.player.ship.heat > gunnery.fault_line(b.player)
                assert faulted == said["faults"], (
                    f"the board said faults={said['faults']} and the hull "
                    f"{'is' if faulted else 'is not'} faulting")
                looked += 1
        assert looked >= 8, looked
        return f"{looked} volleys, heat exact to {worst:g}"

    @check("a volley fires what was chosen and nothing else")
    def _():
        _game, rng, b = _battle(loadout=ARCS)
        live = [s.mount_id for s in gunnery.mounts(b) if s.can_fire]
        assert len(live) >= 3, live
        want = live[:2]
        out = gunnery.volley(b, want, rng)
        assert out["fired"] == want, (out["fired"], want)

        # Naming a mount that cannot bear is not a way to fire it.
        _g2, rng2, b2 = _battle("blocked", loadout=ARCS)
        blocked = [s.mount_id for s in gunnery.mounts(b2) if not s.can_fire]
        note = ""
        if blocked:
            held = b2.player.ship.heat
            out = gunnery.volley(b2, blocked[:1], rng2)
            assert out["fired"] == [], out
            assert b2.player.ship.heat == held, (
                "a mount that will not bear put heat into the hull anyway")
            note = f"; {len(blocked)} blocked mount(s) refused"
        return f"asked for {len(want)} of {len(live)} and fired those{note}"

    @check("a selection is a multiset, capped at what the hull carries")
    def _():
        # `Shot.mount_id` is a part id, so a hull with three Fusion Lances
        # reports three mounts under one name. Asking for two has to fire two;
        # asking for six has to fire three, and a first draft of `firing_set`
        # would have fired six and charged the heat for all of them.
        _game, _rng, b = _battle()
        ids = [s.mount_id for s in gunnery.mounts(b)]
        assert len(ids) > len(set(ids)), (
            f"this loadout is supposed to carry repeats: {ids}")
        many = max(set(ids), key=ids.count)
        held = ids.count(many)
        assert held >= 2, (many, held)

        live = sum(1 for s in gunnery.mounts(b)
                   if s.mount_id == many and s.can_fire)
        for asked in range(1, held + 4):
            got = gunnery.firing_set(b, [many] * asked)
            assert len(got) == min(asked, live), (
                f"asked for {asked} {many} off a hull with {live} that can "
                f"fire and got {len(got)}")
        # And the heat follows the count, not the name.
        one = gunnery.quote(b, [many])["heat_added"]
        two = gunnery.quote(b, [many, many])["heat_added"]
        assert abs(two - one * 2) < 1e-9, (one, two)
        return (f"{len(ids)} mounts under {len(set(ids))} names; {held}x "
                f"{many} capped at {live} and charged per mount")

    @check("the advice never tells the gunner to hold fire")
    def _():
        # The first draft could return nothing: on a hull already warm from last
        # turn no mount could be added without crossing the line, so the advice
        # was to sit still. Played, it said fire, hold, fire, hold — shooting
        # half as often as the enemy. `ship.py` records the same lesson beside
        # `HEAT_CEILING` from the last time it happened: they "lost to their own
        # radiators, in a fight they never shot in."
        empty, turns = [], 0
        for seed, loadout in ((0, HOT), (1, HEAVY), (2, HEAVY)):
            _game, rng, b = _battle(f"a{seed}", loadout=loadout)
            for turn in range(8):
                if b.over:
                    break
                bears = [s for s in gunnery.mounts(b) if s.can_fire]
                want = gunnery.advise(b)
                if bears and not want:
                    empty.append((seed, turn, round(b.player.ship.heat, 1)))
                turns += 1
                b = combat.take_turn(b, {"type": "volley", "mounts": want}, rng)
        assert not empty, (
            f"the advice was to fire nothing on {len(empty)} turn(s) with "
            f"mounts bearing: {empty[:3]}")
        # And the case the floor exists for: a hull too warm for any of its
        # guns still gets told to fire one.
        _g3, _r3, hot = _battle("warm", loadout=HEAVY)
        hot.player.ship.heat = gunnery.fault_line(hot.player) * 1.9
        bears = [s for s in gunnery.mounts(hot) if s.can_fire]
        assert bears, "the warm hull has nothing bearing, so this proves nothing"
        want = gunnery.advise(hot)
        assert want, (
            f"at {hot.player.ship.heat:.0f} heat against a line of "
            f"{gunnery.fault_line(hot.player):.0f} the advice was to fire "
            "nothing at all, with guns bearing")
        assert gunnery.quote(hot, want)["faults"], (
            "this case is supposed to be one where firing at all faults")
        return (f"{turns} turns of advice, never once a hold; and a hull at "
                f"{hot.player.ship.heat:.0f} of "
                f"{gunnery.fault_line(hot.player):.0f} still fires")

    @check("the advice stays under the line where firing everything does not")
    def _():
        # The measured finding as a check: one hull, one turn, one choice
        # faulting and the other not.
        _game, _rng, b = _battle()
        live = [s.mount_id for s in gunnery.mounts(b) if s.can_fire]
        assert len(live) >= 4, live
        everything = gunnery.quote(b, live)
        assert everything["faults"], (
            f"firing all {len(live)} mounts came to "
            f"{everything['heat_added']:.0f} heat against a line of "
            f"{everything['fault_line']:.0f} and did not fault — this loadout "
            "is supposed to be the hot one")
        advised = gunnery.quote(b, gunnery.advise(b))
        assert not advised["faults"], (
            f"the advice faults by {advised['over_by']:.0f} on a cold hull")
        assert advised["heat_added"] < everything["heat_added"]

        # And it is not merely the smallest thing that fires. Ordering by damage
        # *per point of heat* picked the pea-shooters and left the main armament
        # cold — 3 wins in 12 against 6 for firing one Fusion Lance every turn.
        # **Against the true optimum, brute-forced here**, because "beats one
        # mount" was too weak to tell the two orderings apart: on this loadout
        # damage-per-heat also includes a lance, so both passed. The
        # specification is "the most damage of any set that does not fault", so
        # check that and not a proxy for it.
        ready = [s for s in gunnery.mounts(b) if s.can_fire]
        assert len(ready) <= gunnery.SEARCH_LIMIT, len(ready)
        ids = [s.mount_id for s in ready]

        def hits(shot):
            w = next((x for x in b.player.st.weapons
                      if x.id == shot.mount_id), None)
            return 0.0 if not w or not w.wpn else (
                w.wpn.dmg * max(0.0, 1.0 - shot.penalty))

        best = 0.0
        for mask in range(1, 1 << len(ready)):
            pick = [ids[i] for i in range(len(ready)) if mask >> i & 1]
            if gunnery.quote(b, pick)["faults"]:
                continue
            best = max(best, sum(hits(ready[i]) for i in range(len(ready))
                                 if mask >> i & 1))
        assert best > 0, "no subset avoids faulting, so there is nothing to be best"
        assert advised["damage"] >= best - 1e-9, (
            f"the advice lands {advised['damage']:.1f} where the best "
            f"non-faulting volley lands {best:.1f} — it is leaving damage on "
            "the table, which is the fault the damage-per-heat ordering had")
        single = gunnery.quote(b, live[:1])
        assert advised["damage"] > single["damage"], (
            advised["damage"], single["damage"])
        return (f"all {len(live)}: +{everything['heat_added']:.0f} heat, faults "
                f"· advice {len(advised['mounts'])}: "
                f"+{advised['heat_added']:.0f}, {advised['damage']:.0f} damage")

    @check("the board drives the trigger, pressed through the window")
    def _():
        # Through the window, because the whole gap was that the sim could do
        # this and no seat could ask for it. A check that called
        # `gunnery.volley` directly would have passed throughout.
        from PyQt6.QtWidgets import QApplication

        from .test_ui import _use_offscreen
        _use_offscreen()
        from ..ui.gunner_window import open_gunnery
        from ..ui.window import MainWindow

        app = QApplication.instance() or QApplication([])
        assert app is not None
        # HOT rather than ARCS: on the mixed-arc hull only three mounts bear and
        # the advice takes all three, so a mutation replacing the trigger with a
        # full salvo fired exactly the same shots and nothing failed. The board
        # has to be checked where what it shows and what a salvo would do differ.
        game, _rng, b = _battle("win", loadout=HOT)
        win = MainWindow(game)
        win.toast = lambda *a, **k: None
        win.battle = b
        gw = open_gunnery(win)

        every = gw.chosen()
        assert len(every) >= 3, every

        # Hold one mount and the volley and the heat both follow.
        slot = next(i for i, s in enumerate(gunnery.mounts(b)) if s.can_fire)
        gw._toggle(slot)
        fewer = gw.chosen()
        assert len(fewer) == len(every) - 1, (every, fewer)
        assert (gunnery.quote(b, fewer)["heat_added"]
                < gunnery.quote(b, every)["heat_added"])

        # The advice is expressed as holds, and agrees with the sim.
        gw._advise()
        assert sorted(gw.chosen()) == sorted(gunnery.advise(b)), (
            gw.chosen(), gunnery.advise(b))

        # Hold everything and the trigger goes dead rather than firing all.
        gw._none()
        assert gw.chosen() == []
        gw.refresh()
        assert not gw.fire_btn.isEnabled(), (
            "with everything held the trigger is still live")

        # And pulling it spends heat on exactly what was shown — which has to be
        # less than a salvo would, or the check cannot tell the two apart.
        gw._advise()
        picked = list(gw.chosen())
        assert len(picked) < len(every), (
            f"the advice picked all {len(every)} bearing mounts, so this hull "
            "cannot distinguish the trigger from a full salvo")
        said = gunnery.quote(b, picked)
        assert said["heat_added"] < gunnery.quote(b, every)["heat_added"]
        gw._fire()
        assert abs(b.player.ship.heat - said["heat_after"]) < 1e-6, (
            f"the window promised {said['heat_after']:.2f} and the hull came "
            f"out at {b.player.ship.heat:.2f}")
        gw.close()
        win.close()
        return (f"{len(every)} bearing, held one → {len(fewer)}, advice "
                f"{len(picked)}, heat landed at {b.player.ship.heat:.1f}")

    @check("a sight draws its arc on both sides of the bow")
    def _():
        # My own bug, and one the screen hid: `arc_span` returns *half-angles* —
        # its docstring says so — and the first draft drew a single wedge from
        # `low` clockwise, putting a fore arc entirely to starboard. It looked
        # plausible because the target happened to be near dead ahead when I
        # looked at it. `ui/tactical_plot.py` had already been fixed for the same
        # thing and left the reason behind: "drawing only one of them is a lie
        # about the ship."
        from PyQt6.QtWidgets import QApplication

        from .test_ui import _use_offscreen
        _use_offscreen()
        from ..ui.mount_sight import MountSight

        app = QApplication.instance() or QApplication([])
        assert app is not None
        _game, _rng, b = _battle("sight", loadout=ARCS)
        shots = {s.arc: s for s in gunnery.mounts(b)}
        assert "broad" in shots and "fore" in shots, sorted(shots)

        def lit(shot):
            """Painted pixels either side of the centreline."""
            widget = MountSight(shot, 0.0)
            widget.resize(160, 160)
            image = widget.grab().toImage()
            left = right = 0
            for y in range(26, 134, 3):
                for x in range(10, 150, 3):
                    px = image.pixel(x, y)
                    bright = (px >> 16 & 255) + (px >> 8 & 255) + (px & 255)
                    if bright < 130:
                        continue
                    if x < 72:
                        left += 1
                    elif x > 88:
                        right += 1
            return left, right

        said = []
        for arc in ("broad", "fore"):
            left, right = lit(shots[arc])
            assert left > 6 and right > 6, (
                f"a {arc} arc drew {left} lit pixels to port and {right} to "
                "starboard — an arc is symmetric about the bow, so one side "
                "being empty means only half of it is drawn")
            lean = abs(left - right) / max(1, left + right)
            assert lean < 0.35, (
                f"a {arc} arc is {lean:.0%} lopsided: {left} port, "
                f"{right} starboard")
            said.append(f"{arc} {left}/{right}")
        return " · ".join(said) + " pixels port/starboard"

    @check("the sights and the solution agree about what bears")
    def _():
        # Two doors into one question. The sight marks the target inside or
        # outside the arc it draws; `firing.solution` decides whether the mount
        # can shoot. Both come from `arc_span`, and this is what keeps them
        # honest about the half-angle convention.
        _game, _rng, b = _battle("agree", loadout=ARCS)
        looked = 0
        for dx, dy in ((40, 120), (200, 120), (700, 120), (-700, 120)):
            b.enemy.body.x = b.player.body.x + dx
            b.enemy.body.y = b.player.body.y + dy
            bearing = firing.bearing_degrees(b.player, b.enemy)
            for shot in gunnery.mounts(b):
                low, high = firing.arc_span(shot.arc)
                off_bow = abs(bearing)
                inside = low - 1e-9 <= off_bow <= high + 1e-9
                assert inside == shot.in_arc, (
                    f"{shot.name} at {bearing:+.0f}° off the bow: {shot.arc} "
                    f"spans {low:.0f}–{high:.0f} either side, so inside="
                    f"{inside}, but the solution says {shot.in_arc}")
                if not shot.in_arc:
                    assert shot.gap > 0, (shot.name, shot.gap)
                looked += 1
        assert looked >= 16, looked
        return f"{looked} mount-and-bearing pairs, span and solution agreeing"
