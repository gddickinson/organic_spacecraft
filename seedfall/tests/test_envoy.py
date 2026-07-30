"""An envoy's proposition: what each answer costs, and who else is watching.

`approach.answer` carries the comment "everything here must match `preview`
exactly". Three things did not.

The one that mattered: **signing a treaty was free if you waited to be
asked.** `diplomacy.perform` charges the signatory's enemies through
`sim/allegiance.py` when you propose one; `approach.answer` appended the
treaty and charged nobody. Measured with all four powers at −70 with each
other, the same instrument with the same signatory cost −6 with each of the
other three when proposed and **nothing at all** when accepted. A treaty is
the most public act in the game, and there was a door through which it was
invisible — which is exactly what the last diplomacy cycle set out to end.

Two smaller silences, both the same rule: accepting a denunciation drives the
two powers a further six apart, and refusing a levy is filed as a grievance.
Neither appeared in the preview the screen is built from.

The claims:

- **Both doors into a treaty charge the same.** The general one.
- **The preview is the answer**, swept over every kind and every answer.
- **The screen names every power an answer moves.**
- **Every kind of approach can actually be produced.**
"""

from __future__ import annotations

from ..core.rng import RNG
from ..core.state import new_game
from ..data.diplomacy import TREATY_WEIGHT
from ..sim import approach, diplomacy as dip
from ..sim.colony import Colony
from .harness import Suite

KINDS = ("denounce_rival", "warning", "treaty_offer", "requisition", "levy")


def _feuding(seed: str, rift: float = -70.0):
    """A sector where every power is at odds with every other."""
    game = new_game(seed)
    game.credits = 500_000
    for a in dip.POWERS:
        for b in dip.POWERS:
            if a != b:
                dip.shift_relation(game, a, b, rift - dip.relation(game, a, b))
    return game


def _envoy(game, kind: str, faction: str = "charter"):
    """Build one of each kind, with whatever it needs to be plausible."""
    rival = next(p for p in dip.POWERS if p != faction)
    game.rep[faction] = 80.0
    if kind == "requisition":
        game.ship.cargo["biomass"] = 400
    if kind == "levy":
        target = next((s for s in game.galaxy.systems if s.faction == faction),
                      None)
        if target is None:
            return None
        body = target.bodies[0]
        col = Colony(id=1, class_id="lichen_dome", name="Dome",
                     system_id=target.id, body_id=body.id, need=0,
                     online=True, pop=10000)
        game.colonies = [col]
        body.colony = col.id
    envoy = approach._build(game, faction, kind,
                            rival if kind in ("denounce_rival", "warning")
                            else None, RNG(f"b-{kind}"))
    game.envoy = envoy
    return envoy


def _snapshot(game) -> dict:
    return {"rep": {p: game.rep.get(p, 0.0) for p in dip.POWERS},
            "credits": game.credits,
            "cargo": dict(game.ship.cargo)}


def run(suite: Suite) -> None:
    check = suite.check

    @check("signing a treaty costs the same whichever door you use")
    def _():
        # Proposing it charged the signatory's enemies; accepting the same
        # instrument charged nobody. Waiting to be asked was the way to sign
        # a treaty for free.
        proposed = _feuding("door-a")
        proposed.rep["charter"] = 80.0
        was = _snapshot(proposed)["rep"]
        res = dip.perform(proposed, "treaty", "charter")
        assert res.get("ok"), res
        by_proposing = {p: proposed.rep.get(p, 0) - was[p] for p in dip.POWERS}

        offered = _feuding("door-a")
        envoy = _envoy(offered, "treaty_offer")
        was2 = _snapshot(offered)["rep"]
        approach.answer(offered, envoy, "accept")
        by_accepting = {p: offered.rep.get(p, 0) - was2[p] for p in dip.POWERS}

        enemies = [p for p in dip.POWERS if p != "charter"]
        for power in enemies:
            assert by_proposing[power] < -0.5, (
                f"proposing a treaty cost {by_proposing[power]:+.1f} with "
                f"{power}, so there is nothing to compare against")
            assert abs(by_accepting[power] - by_proposing[power]) < 0.01, (
                f"{power}: proposing costs {by_proposing[power]:+.1f} and "
                f"accepting the same treaty costs {by_accepting[power]:+.1f} "
                "— the cheaper door is the one to use")
        assert "charter" in dip.ensure(offered).treaties
        return (f"both doors charge the signatory's enemies "
                f"{by_accepting[enemies[0]]:+.1f} at weight {TREATY_WEIGHT:g}")

    @check("what the preview promises is what the answer does")
    def _():
        # Swept over every kind and every answer, comparing standing, credits
        # and the manifest against the forecast the screen is drawn from.
        checked = 0
        for kind in KINDS:
            for choice in ("accept", "refuse", "push"):
                game = _feuding(f"fc-{kind}-{choice}")
                envoy = _envoy(game, kind)
                if envoy is None:
                    continue
                said = approach.preview(game, envoy, choice)
                if not said:
                    continue
                was = _snapshot(game)
                res = approach.answer(game, envoy, choice)
                if not res.get("ok"):
                    continue
                now = _snapshot(game)
                for power, delta in said.get("rep", {}).items():
                    moved = now["rep"][power] - was["rep"][power]
                    if abs(now["rep"][power]) >= 99.9:
                        continue          # clamped, nothing to compare
                    assert abs(moved - delta) < 0.05, (
                        f"{kind}/{choice}: promised {power} {delta:+.1f} and "
                        f"moved it {moved:+.1f}")
                    checked += 1
                if said.get("credits"):
                    moved = now["credits"] - was["credits"]
                    assert abs(moved - said["credits"]) < 1, (
                        f"{kind}/{choice}: promised {said['credits']:+,} "
                        f"credits and moved {moved:+,}")
                    checked += 1
                if said.get("goods"):
                    cid, amount = said["goods"]
                    moved = now["cargo"].get(cid, 0) - was["cargo"].get(cid, 0)
                    assert abs(moved - amount) < 0.01, (
                        f"{kind}/{choice}: promised {amount:+g} t of {cid} "
                        f"and moved {moved:+g}")
                    checked += 1
        assert checked > 15, checked
        return f"{checked} promised movements across five kinds, all landing"

    @check("accepting a denunciation drives the two powers apart, and says so")
    def _():
        game = _feuding("denounce", rift=-20.0)
        envoy = _envoy(game, "denounce_rival")
        said = approach.preview(game, envoy, "accept")
        assert said.get("relations"), (
            "the preview never mentions that this moves the two powers "
            "against each other")
        who, whom, delta = said["relations"]
        before = dip.relation(game, who, whom)
        approach.answer(game, envoy, "accept")
        after = dip.relation(game, who, whom)
        assert abs((after - before) - delta) < 0.01, (
            f"promised {delta:+.1f} between {who} and {whom}, moved "
            f"{after - before:+.1f}")
        return f"{who} and {whom}: {before:+.0f} → {after:+.0f}, as forecast"

    @check("refusing a levy is filed, and the screen says it will be")
    def _():
        game = _feuding("levy")
        envoy = _envoy(game, "levy")
        assert envoy is not None, "no system is held by the Charter here"
        said = approach.preview(game, envoy, "refuse")
        assert any("grievance" in line.lower() for line in said["lines"]), (
            f"refusing a levy is recorded as a grievance and the screen does "
            f"not say so: {said['lines']}")
        # **This check used to read a counter that did not exist.** It asked
        # `getattr(dip.ensure(game), "grievances", 0)`, which is how an
        # undeclared attribute passes for a field: `_apply_refusal` set
        # `state.grievances`, `DiplomaticState` never declared it, nothing read
        # it, and the next save dropped it on the floor. The counter went up and
        # the check was satisfied — the feature was still missing, and a `getattr`
        # with a default is what let the two look the same.
        #
        # A grievance is a memory now, which is the machinery that already turns
        # dated things into a price and into whether a power will deal with you,
        # and which persists.
        from ..sim import grudge as grudge_sim
        before = (grudge_sim.feeling(game, envoy.faction),
                  len(grudge_sim.because(game, envoy.faction)))
        approach.answer(game, envoy, "refuse")
        after = (grudge_sim.feeling(game, envoy.faction),
                 len(grudge_sim.because(game, envoy.faction)))
        assert after[1] > before[1], (
            "the grievance was promised and the power remembers nothing")
        assert after[0] < before[0], (
            f"the Charter feels {after[0]:.1f} against {before[0]:.1f} — a "
            "grievance nobody minds is not a grievance")
        assert not hasattr(dip.ensure(game), "grievances"), (
            "something is still writing an undeclared `grievances` attribute; "
            "it will not survive a save")
        return (f"filed as a memory, feeling {before[0]:+.1f} → {after[0]:+.1f}, "
                "and the screen warned of it")

    @check("haggling moves the offer and pays nothing yet")
    def _():
        # The screen printed "Treasury: +794" for a push. Pushing raises what
        # is on the table; the money arrives only if you then accept, and a
        # captain who read that row believed they had been paid for asking.
        game = _feuding("haggle", rift=-20.0)
        envoy = _envoy(game, "denounce_rival")
        said = approach.preview(game, envoy, "push")
        assert said.get("offer"), (
            f"pushing promises no better offer at all: {said}")
        assert not said.get("credits"), (
            f"pushing reports {said['credits']:+,} into the treasury, and "
            "nothing is paid until the offer is accepted")
        was_credits, was_offer = game.credits, envoy.credits
        res = approach.answer(game, envoy, "push")
        assert res.get("ok"), res
        assert game.credits == was_credits, (
            f"haggling moved the treasury by "
            f"{game.credits - was_credits:+,}")
        assert envoy.credits - was_offer == said["offer"], (
            f"promised the offer would rise {said['offer']:+,} and it rose "
            f"{envoy.credits - was_offer:+,}")
        # And accepting afterwards pays the improved figure.
        before = game.credits
        approach.answer(game, envoy, "accept")
        assert game.credits - before == envoy.credits, (
            f"accepted an offer of {envoy.credits:,} and was paid "
            f"{game.credits - before:,}")
        return (f"the offer rises {said['offer']:+,} to {envoy.credits:,}, "
                "paid only on accepting")

    @check("every kind of approach can actually be produced")
    def _():
        made = []
        for kind in KINDS:
            game = _feuding(f"live-{kind}")
            envoy = _envoy(game, kind)
            assert envoy is not None, f"{kind} could not be built at all"
            assert envoy.kind == kind
            assert approach.opening(game, envoy), f"{kind} has no opening line"
            assert approach.asking(game, envoy), f"{kind} asks for nothing"
            made.append(kind)
        # And the reasons that produce them go live when their conditions do.
        game = _feuding("reasons")
        game.rep["charter"] = 80.0
        live = {k for k, _r in approach.reasons(game, "charter")}
        assert "treaty_offer" in live, (
            f"standing of 80 and no treaty, and they do not offer one: {live}")
        return " · ".join(made)

    @check("the envoy screen names every power an answer moves")
    def _():
        from .test_ui import _use_offscreen
        _use_offscreen()
        from PyQt6.QtWidgets import QApplication, QLabel
        from ..ui.window import MainWindow

        app = QApplication.instance() or QApplication([])
        assert app is not None
        game = _feuding("screen")
        envoy = _envoy(game, "treaty_offer")
        said = approach.preview(game, envoy, "accept")
        assert len(said["rep"]) >= 3, said["rep"]

        win = MainWindow(game)
        win.toast = lambda *a, **k: None
        win.go("envoy")
        for _ in range(3):
            app.processEvents()
        rows = " ".join(lab.text() for lab in
                        win.views["envoy"].findChildren(QLabel) if lab.text())
        win.close()
        from ..data.factions import FACTIONS_BY_ID
        for power, delta in said["rep"].items():
            short = FACTIONS_BY_ID[power].short
            assert f"{short}: {delta:+.0f}" in rows, (
                f"the screen never says {short} moves {delta:+.0f} — "
                f"accepting quietly charges them")
        return f"{len(said['rep'])} powers named on the card, every one costed"
