"""The battle computer: whether the seats you leave actually think.

You take one station a turn and the officers hold the other two. What "hold"
meant was literal — `order_id = side.helm_order or "hold"` — so an unattended
helm repeated your last order until you came back to it, and an unattended
gunner salvoed every turn whatever the heat and whatever bore.

These checks hold three things:

- **Without a computer, nothing changed.** The old behaviour is what every
  other check in the suite was written against, and the hull you launch with
  rates 0.15, below `MINIMUM`. If that drifts, everything else does.
- **With one, the seats choose** — measurably differently, turn by turn, and
  it says which and why before the turn resolves.
- **It is still worse than sitting there.** Handing a seat to the machine must
  not be as good as holding it, or where to spend your attention stops being
  a decision.
"""

from __future__ import annotations

from ..core.rng import RNG
from ..core.state import new_game
from ..sim import combat, doctrine, encounters, tactical as tac
from ..sim.ship import build_layers, make_ship, stats as ship_stats
from ..sim.stations import ORDERS_BY_ID
from .harness import Suite

#: A hull with a battery worth having opinions about.
_FIT = ["reaction_organ", "intima_bloom", "radiator_bloom", "silicon_core",
        "crew_girdle", "slug_battery", "mag_lance", "photic_flash"]


def _battle(seed: str, rating: float, seat: str = "gunnery"):
    game = new_game(f"bc-{seed}")
    ship = make_ship("navis", list(_FIT), "Test Hull")
    build_layers(ship, game.bonuses)
    ship.cargo = {"ore": 200, "volatiles": 60, "alloy": 40}
    st = ship_stats(ship, game.bonuses, game.officers)
    st.doctrine = rating
    enemy = encounters.make_enemy(RNG(f"e{seed}"), "freeholds", 1.3)
    battle = combat.start(ship, st, enemy, officers=game.officers,
                          rng=RNG(f"b{seed}"), game=game)
    battle.player.station = seat
    return game, battle


def _play(battle, order: str, turns: int = 14) -> list:
    rng = RNG("turns")
    seen = []
    for _ in range(turns):
        if battle.over:
            break
        combat.take_turn(battle, {"type": "station", "order": order}, rng)
        seen.append(battle.player.helm_order)
    return seen


def run(suite: Suite) -> None:
    check = suite.check

    @check("the hull you launch with has no computer, and fights as it always did")
    def _():
        # Every other check in the suite was written against repeat-forever.
        game = new_game("stock")
        assert game.ship_stats.doctrine < doctrine.MINIMUM, (
            f"the starting hull now rates {game.ship_stats.doctrine:.2f} and "
            "would fight itself — every other check assumes it does not")
        assert not doctrine.fitted(game.ship_stats)
        assert doctrine.grade(game.ship_stats) == "none"

        _g, battle = _battle("stock", game.ship_stats.doctrine)
        battle.player.helm_order = "close"
        orders = _play(battle, "salvo", turns=8)
        assert set(orders) == {"close"}, (
            f"an unattended helm without a computer changed its mind: {orders}")
        return (f"stock hull rates {game.ship_stats.doctrine:.2f} · helm "
                f"repeated 'close' for {len(orders)} turns, exactly as before")

    @check("with a computer, the seats you leave choose rather than repeat")
    def _():
        # The claim is *choosing*, not variety. A hull already in its preferred
        # band should say "hold" every turn and be right to; demanding the
        # order change would fail the computer for being correct. So: does it
        # depart from what it was last told, and does it adapt across
        # situations rather than parroting one answer everywhere?
        departed = seeds = 0
        chosen: set = set()
        for seed in range(10):
            _g, dumb = _battle(f"choose{seed}", 0.15)
            dumb.player.helm_order = "close"
            without = _play(dumb, "salvo", turns=10)
            assert set(without) == {"close"}, (
                f"seed {seed}: an uncomputed helm changed its mind: "
                f"{sorted(set(without))}")

            _g2, smart = _battle(f"choose{seed}", 1.0)
            smart.player.helm_order = "close"
            with_it = _play(smart, "salvo", turns=10)
            chosen |= set(with_it)
            if set(with_it) != {"close"}:
                departed += 1
            seeds += 1

        assert departed > seeds * 0.5, (
            f"a computer-fitted helm went on repeating 'close' in "
            f"{seeds - departed} of {seeds} engagements")
        assert len(chosen) > 1, (
            f"the computer only ever picked {sorted(chosen)} — it is not "
            "reading the situation, it is parroting one answer")
        return (f"{departed}/{seeds} engagements where the helm departed from "
                f"the last order it was given · it used {sorted(chosen)}")

    @check("it says what it will do before the turn resolves")
    def _():
        # A system that acts on your behalf without stating its intent is the
        # defect this project keeps finding, wearing a uniform.
        _g, battle = _battle("say", 1.0, seat="gunnery")
        plan = doctrine.plan(battle)
        assert set(plan) == {"helm", "engineering"}, (
            f"planned for {sorted(plan)}; the seat you hold should be absent")
        for station, (order_id, why) in plan.items():
            order = ORDERS_BY_ID.get(order_id)
            assert order is not None, f"{station}: {order_id} is not an order"
            assert order.station == station, (
                f"{station} was handed {order_id}, which belongs to "
                f"{order.station}")
            assert len(why) > 20, f"{station}: no reasoning given ({why!r})"

        # And a hull with no computer plans nothing at all.
        _g2, bare = _battle("say", 0.15)
        assert doctrine.plan(bare) == {}
        return " · ".join(f"{s}: {ORDERS_BY_ID[o].name}"
                          for s, (o, _w) in sorted(plan.items()))

    @check("the computer holds fire rather than cooking the mounts")
    def _():
        _g, battle = _battle("hot", 1.0, seat="helm")
        side, foe = battle.player, battle.enemy
        cap = side.st.heat_cap

        side.ship.heat = cap * 0.95
        order, why = doctrine.gunnery(side, foe)
        assert order == "hold_fire", f"still firing at 95% heat: {order}"
        assert "heat" in why.lower(), why

        side.ship.heat = 0.0
        cool, _why = doctrine.gunnery(side, foe)
        assert cool != "hold_fire" or _bearing(side, foe) == 0, (
            "holding fire on a cold hull with mounts bearing")
        return f"hold_fire at 95% of a {cap:.0f} cap, {cool} when cold"

    @check("a seat run by the machine is worse than a seat you sit in")
    def _():
        # The whole design rests on this. If handing engineering to the
        # computer vents as much heat as sitting there, the choice of where to
        # spend your attention has quietly stopped mattering.
        from ..sim import stations as st_mod

        _g, battle = _battle("worse", 1.0)
        side, foe = battle.player, battle.enemy
        cap = side.st.heat_cap

        side.ship.heat = cap
        st_mod.run_engineering(side, "vent", True, battle.officers, foe)
        directed = cap - side.ship.heat

        side.ship.heat = cap
        st_mod.run_engineering(side, None, False, battle.officers, foe)
        machine = cap - side.ship.heat

        assert machine > 0, "the computer vented nothing at all"
        assert machine < directed, (
            f"the machine vented {machine:.0f} against your {directed:.0f} — "
            "sitting at the station buys nothing")
        return (f"venting: {directed:.0f} heat sitting there, {machine:.0f} "
                f"letting the computer do it ({machine/directed*100:.0f}%)")

    @check("a better computer fights the ship better")
    def _():
        # Outcome rather than behaviour, over enough fights to mean something.
        def damage(rating: float, fights: int = 24) -> float:
            done = 0.0
            for seed in range(fights):
                _g, battle = _battle(f"out{seed}", rating, seat="helm")
                _play(battle, "close", turns=24)
                total = sum(l.max for l in battle.enemy.ship.layers) or 1
                left = sum(l.hp for l in battle.enemy.ship.layers)
                done += 1.0 - left / total
            return done / fights

        bare = damage(0.15)
        best = damage(1.0)
        assert best > bare, (
            f"an excellent computer did {best*100:.1f}% damage against "
            f"{bare*100:.1f}% with none — it buys nothing")
        return (f"damage dealt over 24 fights: {bare*100:.1f}% with no "
                f"computer, {best*100:.1f}% with an excellent one")

    @check("the battle screen names the computer's intentions")
    def _():
        from .test_ui import _use_offscreen
        _use_offscreen()
        from PyQt6.QtWidgets import QApplication, QLabel
        from ..ui.doctrine_panel import intentions
        from ..ui.widgets import label

        app = QApplication.instance() or QApplication([])
        assert app is not None

        class FakeView:
            def hint(self, text):
                return label(text, "", "dim", wrap=True)

        _g, battle = _battle("ui", 1.0)
        panel = intentions(FakeView(), battle)
        texts = " ".join(w.text() for w in panel.findChildren(QLabel)
                         if w.text())
        for station, (order_id, _why) in doctrine.plan(battle).items():
            assert ORDERS_BY_ID[order_id].name in texts, (
                f"{station}'s order is not on the screen")
            assert station.capitalize() in texts, station

        # And the warning when there is none is at least as important.
        _g2, bare = _battle("ui", 0.15)
        warn = intentions(FakeView(), bare)
        bare_text = " ".join(w.text() for w in warn.findChildren(QLabel)
                             if w.text())
        assert "repeats its last order" in bare_text, bare_text
        return "intentions named for every unattended seat, warning shown "\
               "when there is no computer"


def _bearing(side, other) -> int:
    rel = tac.relative_bearing(side.body, other.body)
    return sum(1 for w in (side.st.weapons or [])
               if tac.bears(tac.arc_of(w), rel))
