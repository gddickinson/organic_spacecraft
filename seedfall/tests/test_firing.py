"""What bears, and whether the screen agrees with the gun.

Everything needed to answer "can this mount shoot right now" was modelled and
none of it was shown. It reached the player only afterwards, as a line in the
log explaining that the shot they had just spent a turn on did not happen.

Building the picture turned up something worse: the game held **three**
different opinions about whether a gun could fire, and never named any of
them.

- `combat._fire` refuses above a 0.6 range penalty.
- Every automatic selector — salvo, aimed shot, enemy AI — picks only 0.5.
- `assessment.mounts` reported anything above 0.5 as out of range.

A mount at 0.55 would fire when ordered personally, never be included in a
salvo, and be described on screen as unusable.

**In practice no mount is ever at 0.55.** `bears_at` steps 0.22 a band, so the
reachable penalties are 0, 0.22, 0.44, 0.66 — the gap between the thresholds
is empty and always has been. This was a latent inconsistency, not a live bug,
and saying otherwise would be a nicer story than the true one. Naming both
constants removes the landmine; a check pins the gap shut so that widening a
weapon's bands or changing the step has to be a decision rather than an
accident.
"""

from __future__ import annotations

from ..core.rng import RNG
from ..core.state import new_game
from ..sim import assessment, combat, encounters, firing, tactical as tac
from ..sim.ship import build_layers, make_ship, stats as ship_stats
from .harness import Suite

#: `lixiviant` is here on purpose: bands 0–1, so at long range it reaches a
#: 0.66 penalty — in arc and genuinely unusable. Without a mount that can be
#: both, "bearing" and "worth firing" never disagree and a check comparing
#: them passes with the two rules forked wide open.
_FIT = ["reaction_organ", "intima_bloom", "radiator_bloom", "silicon_core",
        "crew_girdle", "slug_battery", "mag_lance", "railgun", "photic_flash",
        "lixiviant"]


def _battle(seed: str, cargo: dict | None = None):
    game = new_game(f"fp-{seed}")
    ship = make_ship("navis", list(_FIT), "Test Hull")
    build_layers(ship, game.bonuses)
    ship.cargo = dict(cargo if cargo is not None
                      else {"ore": 200, "alloy": 60, "volatiles": 40})
    st = ship_stats(ship, game.bonuses, game.officers)
    enemy = encounters.make_enemy(RNG(f"e{seed}"), "freeholds", 1.2)
    battle = combat.start(ship, st, enemy, officers=game.officers,
                          rng=RNG(f"b{seed}"), game=game)
    return game, battle


def run(suite: Suite) -> None:
    check = suite.check

    @check("one rule decides whether a gun fires, and it has a name")
    def _():
        # Three thresholds, none of them named, one of them wrong depending on
        # which you asked.
        assert firing.WORTH_FIRING < firing.CAN_FIRE, (
            firing.WORTH_FIRING, firing.CAN_FIRE)

        _g, b = _battle("rule")
        side, other = b.player, b.enemy
        for shot in firing.solution(side, other, b.band):
            if shot.dry or not shot.in_arc:
                continue
            # What the screen says must be what `_fire` would do.
            assert shot.can_fire == (shot.penalty <= firing.CAN_FIRE), shot
            assert shot.worth_it == (shot.can_fire
                                     and shot.penalty <= firing.WORTH_FIRING)
        return (f"can fire at {firing.CAN_FIRE:.2f}, a salvo picks "
                f"{firing.WORTH_FIRING:.2f}, and both are named")

    @check("the two thresholds are a landmine, not a live difference")
    def _():
        # Being honest about what naming them actually bought. `bears_at`
        # steps 0.22 a band, so the reachable penalties are 0, 0.22, 0.44,
        # 0.66… — and *nothing lands between 0.5 and 0.6*. The three
        # disagreeing thresholds were a real inconsistency in the code with
        # no observable effect in play.
        #
        # It is still worth having fixed: change the step, widen a weapon's
        # bands, and the gap opens under a design that never intended it. This
        # check is the tripwire — when the marginal band becomes reachable it
        # fails, and whoever did it has to decide on purpose.
        from ..data.part_types import Weapon
        probe = Weapon(dmg=10, bands=(2, 3), heat=1)
        reachable = {round(probe.bears_at(b), 4)
                     for b in range(0, tac.MAX_BAND + 3)}
        between = {p for p in reachable
                   if firing.WORTH_FIRING < p <= firing.CAN_FIRE}
        assert not between, (
            f"penalties {sorted(between)} now fall between "
            f"WORTH_FIRING={firing.WORTH_FIRING} and "
            f"CAN_FIRE={firing.CAN_FIRE}: a mount there fires when ordered "
            "and is skipped by every salvo. Decide which you meant.")

        # And the code still distinguishes them, so the day it matters it works.
        assert firing.WORTH_FIRING < firing.CAN_FIRE
        return (f"reachable penalties {sorted(reachable)} — none between "
                f"{firing.WORTH_FIRING} and {firing.CAN_FIRE}, so the two "
                "rules coincide today and are named against the day they do not")

    @check("the panel and the gun agree about every mount")
    def _():
        # Drive real turns and compare what the picture claimed against what
        # `combat` actually did with the shot.
        _g, b = _battle("agree")
        rng = RNG("turns")
        compared = 0
        for _ in range(12):
            if b.over:
                break
            claimed = {s.mount_id: s for s in firing.solution(b.player,
                                                             b.enemy, b.band)}
            before = len(b.log)
            combat.take_turn(b, {"type": "station", "order": "salvo"}, rng)
            said = " ".join(str(line[1]) for line in b.log[before:])
            for shot in claimed.values():
                if not shot.in_arc and shot.name in said:
                    # If the log complains about the arc, we must have too.
                    assert "arc" in said, said
                if shot.dry and f"the {shot.name} is dry" in said:
                    assert shot.blocked_by == "dry", shot
                compared += 1
        assert compared > 0, "no turns were played"
        return f"{compared} mount-turns, the picture and the log agreeing"

    @check("assessment reads the same guns the picture does")
    def _():
        # `assessment.mounts` had its own copy of the rule with its own
        # threshold. It delegates now; if it ever forks again, this bites.
        # Checked across every band, and specifically at one where "in arc"
        # and "worth firing" disagree. At a single band they often coincide,
        # and a check that only looks there passes with the two functions
        # forked wide open — which is exactly what it is here to prevent.
        _g, b = _battle("assess")
        interesting = 0
        for band in range(0, tac.MAX_BAND + 1):
            # `band` is derived from separation, so move the hull rather than
            # assigning it — the property has no setter, which is right.
            b.player.body.x = b.player.body.y = 0.0
            b.player.body.heading = 0.0
            # Dead ahead: heading 0 runs up the screen, so forward is -y. The
            # fore mounts have to bear for the in-arc-but-unusable case to
            # exist at all.
            b.enemy.body.x = 0.0
            b.enemy.body.y = -(tac.BAND_UNITS * band + tac.BAND_UNITS * 0.5)
            assert b.band == band, (b.band, band)
            shots = firing.solution(b.player, b.enemy, band)
            read = assessment.mounts(b)
            assert read["total"] == len(b.player.st.weapons)
            assert len(read["bearing"]) == sum(1 for x in shots if x.worth_it), (
                f"band {band}: assessment says {len(read['bearing'])} bear, "
                f"the picture says {sum(1 for x in shots if x.worth_it)}")
            assert len(read["off_arc"]) == sum(1 for x in shots
                                               if not x.in_arc), band
            assert len(read["out_of_range"]) == sum(
                1 for x in shots if x.in_arc and not x.worth_it), band
            if any(x.in_arc and not x.worth_it for x in shots):
                interesting += 1
        assert interesting > 0, (
            "at no band does any mount bear but fail to be worth firing, so "
            "this seed cannot tell the two rules apart")
        return (f"{tac.MAX_BAND + 1} bands compared, {interesting} of them "
                "where bearing and worth-firing differ")

    @check("a dry magazine is visible before the turn, not after it")
    def _():
        _g, b = _battle("dry", cargo={"volatiles": 40})     # no ore, no alloy
        shots = firing.solution(b.player, b.enemy, b.band)
        dry = [s for s in shots if s.dry]
        assert dry, "nothing in this fit needs ammunition"
        for shot in dry:
            assert not shot.can_fire, shot
            assert shot.ammo, shot
        # A mount that is *also* out of arc reports the arc first, which is
        # right: turning fixes it and the hold does not. Only the ones that
        # would otherwise bear should complain about the magazine.
        in_arc_dry = [s for s in dry if s.in_arc]
        assert in_arc_dry, ("every dry mount also happened to be out of arc; "
                            "this seed proves nothing about the message")
        for shot in in_arc_dry:
            assert shot.blocked_by == "dry", shot
            assert shot.ammo in shot.why, shot.why
        return " · ".join(f"{s.name}: {s.why}" for s in in_arc_dry[:2])

    @check("the closing rate is what the range is doing right now")
    def _():
        # It is the instantaneous rate — what happens if neither hull turns —
        # not a forecast of next turn's range. Both hulls steer before they
        # advance, so measuring it against the turn's outcome had it "wrong"
        # five times in sixteen when it was doing exactly what it says.
        #
        # So check it against its own definition, which is falsifiable, and
        # separately check that it is not merely always zero.
        _g, b = _battle("closing")
        rng = RNG("turns")
        exact = seen = moving = 0
        for _ in range(16):
            if b.over:
                break
            said = firing.closing_rate(b.player, b.enemy)
            before = tac.separation(b.player.body, b.enemy.body)
            held_a, held_b = b.player.body.copy(), b.enemy.body.copy()
            tac.advance(held_a)
            tac.advance(held_b)
            actually = before - tac.separation(held_a, held_b)
            seen += 1
            exact += abs(said - actually) < 0.01
            moving += abs(said) >= 1
            combat.take_turn(b, {"type": "station", "order": "close"}, rng)
        assert seen >= 6, f"only {seen} turns played"
        assert exact == seen, (
            f"the rate disagreed with holding course on {seen - exact} of "
            f"{seen} turns — it is not the number it claims to be")
        assert moving >= seen * 0.5, (
            f"the rate was under a unit on {seen - moving} of {seen} turns; "
            "it is not saying anything")
        return (f"{seen} turns · exact against a held course every time · "
                f"{moving} of them moving a unit or more")

    @check("the plot names what bears and what is bearing on you")
    def _():
        from .test_ui import _use_offscreen
        _use_offscreen()
        from PyQt6.QtWidgets import QApplication, QLabel
        from ..ui.firing_panel import gunnery_picture
        from ..ui.tactical_plot import TacticalPlot
        from ..ui.widgets import label

        app = QApplication.instance() or QApplication([])
        assert app is not None

        class FakeView:
            def hint(self, text):
                return label(text, "", "dim", wrap=True)

        _g, b = _battle("ui")
        panel = gunnery_picture(FakeView(), b)
        texts = " ".join(w.text() for w in panel.findChildren(QLabel)
                         if w.text())
        for shot in firing.solution(b.player, b.enemy, b.band):
            assert shot.name in texts, f"{shot.name} is not on the screen"
        assert "bear on you" in texts or "Nothing of theirs" in texts, texts

        # And the plot paints with arcs without falling over.
        plot = TacticalPlot(b)
        plot.resize(plot.SIZE, plot.SIZE)
        plot.grab()
        arcs = firing.arcs_in_use(b.player)
        assert arcs, "the hull has mounts but no arcs to draw"
        return f"{len(arcs)} arcs drawn, every mount named on the panel"
