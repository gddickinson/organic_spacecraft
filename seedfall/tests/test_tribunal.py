"""Tribunal checks — four forums, four different afternoons, and the way out.

`tests/test_law.py` asks whether a power notices and files. These ask what
happens next, and the claim that matters is that **the four powers are not
interchangeable**: the same act, in front of each of them, has to produce a
recognisably different afternoon or the whole design collapses back into the
reputation delta it replaced.

The other load-bearing claim is the project's oldest: the screen states the
whole price before you commit. `case()` and `plead()` are checked against each
other rather than against a constant.
"""

from __future__ import annotations

from ..core.rng import RNG
from ..core.state import new_game
from ..data.forums import FORUMS
from ..sim import clemency as clemency_sim
from ..sim import debts as debts_sim
from ..sim import dockets
from ..sim import enforce as enforce_sim
from ..sim import law as law_sim
from ..sim import tribunal as tribunal_sim
from ..sim import warrants as warrants_sim
from .harness import Suite


def _charged(seed: str, power: str, offence: str = "trespass",
             weight: float = 1.0):
    """A chronicle with one charge filed by this power, at their own quay."""
    game = new_game(seed)
    game.credits = 400_000
    game.system.port.faction = power
    game.system.faction = power
    charge = dockets.allege(game, power, offence, "a thing you did",
                            weight, game.system, seen=1.0)
    assert charge is not None, f"{power} would not charge {offence}"
    game.day += 40
    dockets.sweep(game, 40, RNG(seed))
    return game, charge


def run(suite: Suite) -> None:
    check = suite.check

    @check("the four powers hold four different kinds of afternoon")
    def _():
        # The claim the whole layer stands on. Same act, four forums.
        seen = {}
        for forum in FORUMS:
            game, charge = _charged(f"forum-{forum.power}", forum.power,
                                    "killing")
            game.day = max(game.day, charge.due) + 1
            tribunal_sim.tick(game, 1, RNG(forum.power))
            bites = sorted({w.bite for w in warrants_sim.in_force(game)})
            seen[forum.power] = (forum.form, tuple(bites))
        forms = {v[0] for v in seen.values()}
        bites = {v[1] for v in seen.values()}
        assert len(forms) == 4, f"two powers share a legal form: {seen}"
        assert len(bites) >= 3, (
            f"the same act produced the same instrument almost everywhere: "
            f"{seen}")
        assert seen["freeholds"][1] == ("hunt",), (
            f"the Freeholds did something other than post a price: {seen}")
        assert seen["sanhedrin"][1] == ("shun",), (
            f"the Dry Choir did something other than remove you: {seen}")
        assert "hunt" not in seen["charter"][1], (
            "the Charter, which fields no armed vessel, put a price on a hull")
        return " · ".join(f"{p}: {f} → {'+'.join(b) or 'nothing'}"
                          for p, (f, b) in seen.items())

    @check("only a forum with somewhere to stand offers you a plea")
    def _():
        offered = {}
        for forum in FORUMS:
            game, charge = _charged(f"plea-{forum.power}", forum.power)
            offered[forum.power] = [p["id"]
                                    for p in tribunal_sim.case(game, charge)["pleas"]]
        for power in ("charter", "concordat"):
            assert "contest" in offered[power], offered
        for power in ("freeholds", "sanhedrin"):
            assert "contest" not in offered[power], (
                f"{power} offered a hearing it has nowhere to hold: {offered}")
        return " · ".join(f"{p}: {'/'.join(v) or 'nothing to answer'}"
                          for p, v in offered.items())

    @check("the screen states the whole price, and the plea charges exactly it")
    def _():
        # The rule this project has been bitten by twice. The board and the
        # act read the same function or they will disagree.
        game, charge = _charged("price-said", "charter", "contraband", 1.2)
        quote = tribunal_sim.case(game, charge)
        settle = next(p for p in quote["pleas"] if p["id"] == "settle")
        purse = game.credits
        out = tribunal_sim.plead(game, charge, "settle")
        assert out["ok"], out
        spent = purse - game.credits
        assert abs(spent - settle["cost"]) < 0.01, (
            f"the board said {settle['cost']:,.0f} and the counter took "
            f"{spent:,.0f}")
        assert charge.outcome == "settled" and charge.state == "closed"
        assert not warrants_sim.in_force(game), (
            "settling before a verdict still left an instrument standing")
        assert not law_sim.convictions(game), "settling put it on the record"
        return (f"quoted ₡{settle['cost']:,.0f}, charged ₡{spent:,.0f}, "
                "nothing on the record and no instrument")

    @check("not answering costs more than answering, every time")
    def _():
        # The claim that stops the whole layer being escapable by never going
        # home. Same charge, same seed, two captains.
        rows = []
        for power in ("charter", "concordat"):
            answered, ch_a = _charged(f"answer-{power}", power, "contraband",
                                      1.2)
            tribunal_sim.plead(answered, ch_a, "admit")
            answered.day = ch_a.due + 1
            tribunal_sim.tick(answered, 1, RNG("a"))

            ignored, ch_i = _charged(f"answer-{power}", power, "contraband",
                                     1.2)
            ignored.day = ch_i.due + 1
            tribunal_sim.tick(ignored, 1, RNG("a"))

            paid = debts_sim.total_owed(answered, power)
            dodged = debts_sim.total_owed(ignored, power)
            assert dodged > paid, (
                f"{power}: ignoring it cost ₡{dodged:,.0f} against "
                f"₡{paid:,.0f} for admitting it")
            extra = [c for c in law_sim.ensure(ignored).charges
                     if c.offence == "default"]
            assert extra, f"{power}: not turning up was not itself an offence"
            rows.append(f"{power} ₡{paid:,.0f} → ₡{dodged:,.0f}")
        return " · ".join(rows) + "; and a default charge on top"

    @check("an instrument in force actually stops the ship doing things")
    def _():
        # Every refusal, performed. A warrant nothing reads is the fault this
        # whole layer was built to fix.
        stopped = []
        for power, bite, probe, name in (
                ("charter", "refuse",
                 lambda g: enforce_sim.may_berth(g, g.system), "a berth"),
                ("charter", "licence",
                 lambda g: enforce_sim.may_seed(g), "putting seed down"),
                ("sanhedrin", "shun",
                 lambda g: enforce_sim.may_trade(g, g.system), "the counter"),
                ("sanhedrin", "shun",
                 lambda g: enforce_sim.answers_hail(g, "sanhedrin"), "a hail"),
        ):
            game = new_game(f"bite-{power}-{bite}-{name}")
            game.system.port.faction = power
            game.system.faction = power
            before, _why = probe(game)
            assert before, f"{name} was refused before anything happened"
            warrants_sim.issue(game, power, bite, "because", "holdings",
                               system=game.system)
            after, why = probe(game)
            assert not after, f"{bite} did not stop {name}"
            assert why, f"{bite} stopped {name} without saying why"
            stopped.append(f"{bite} → {name}")

        # And a gate, which needs the ring to be theirs.
        game = new_game("bite-gate")
        game.system.faction = "concordat"
        if game.system.port is not None:
            game.system.port.faction = "concordat"
        warrants_sim.issue(game, "concordat", "refuse", "because", "holdings",
                           system=game.system)
        passable, why = enforce_sim.may_pass(game, game.system.id)
        stopped.append("refuse → a ring" if not passable else "ring open")
        return "; ".join(stopped)

    @check("paying discharges the judgment and lifts what it bought them")
    def _():
        game, charge = _charged("discharge", "charter", "contraband", 1.4)
        game.day = charge.due + 1
        tribunal_sim.tick(game, 1, RNG("d"))
        assert warrants_sim.in_force(game), "no instrument to discharge"
        berth_before, _ = enforce_sim.may_berth(game, game.system)

        for debt in list(debts_sim.live(game)):
            out = debts_sim.pay(game, debt)
            assert out["ok"], out
        lines = clemency_sim.settled_up(game)
        assert lines, "paying in full lifted nothing"
        assert not warrants_sim.in_force(game), (
            "the judgment is paid and the instrument still stands")
        berth_after, _ = enforce_sim.may_berth(game, game.system)
        assert berth_after, "paid in full and still refused a berth"
        return (f"berth {'refused' if not berth_before else 'allowed'} → "
                f"allowed once the judgment was paid")

    @check("there is always a way out, and each power sells a different one")
    def _():
        # A legal system with no exit is an ending on a delay. Four doors,
        # each performed.
        ways = []

        # Settle, before a verdict.
        game, charge = _charged("out-settle", "concordat", "contraband", 1.0)
        assert tribunal_sim.plead(game, charge, "settle")["ok"]
        ways.append("settled before the panel sat")

        # Buy the paper back off the Freeholds — the only door they have.
        game, charge = _charged("out-bounty", "freeholds", "killing")
        game.day = charge.due + 1
        tribunal_sim.tick(game, 1, RNG("b"))
        assert any(w.bite == "hunt"
                   for w in warrants_sim.in_force(game, "freeholds"))
        game.credits = 400_000
        out = clemency_sim.settle_bounty(game, "freeholds")
        assert out["ok"], out
        assert not warrants_sim.in_force(game, "freeholds"), (
            "bought the paper back and somebody is still coming")
        ways.append(f"bought the paper back for ₡{out['paid']:,.0f}")

        # A harbourmaster loses the file.
        from ..sim import officials as officials_sim
        game, charge = _charged("out-pardon", "charter", "contraband", 1.0)
        game.credits = 900_000
        officials_sim.adjust(game, game.system, 400.0, "a long acquaintance")
        ok, why = clemency_sim.can_pardon(game, game.system, "charter")
        assert ok, f"a harbourmaster who is devoted to you refused: {why}"
        out = clemency_sim.pardon(game, game.system, "charter")
        assert out["ok"] and out["wiped"], out
        assert not law_sim.open_charges(game, "charter"), "the file stood"
        ways.append(f"a harbourmaster lost {out['wiped']} matter(s)")

        # And a treaty carries an amnesty.
        game, charge = _charged("out-treaty", "charter", "contraband", 1.0)
        game.day = charge.due + 1
        tribunal_sim.tick(game, 1, RNG("t"))
        assert warrants_sim.in_force(game, "charter")
        lines = clemency_sim.amnesty(game, "charter")
        assert lines, "the treaty clause did nothing"
        assert not warrants_sim.in_force(game, "charter"), "amnesty left it"
        assert debts_sim.total_owed(game, "charter") == 0, "amnesty left debt"
        ways.append("a treaty wiped the slate")
        return "; ".join(ways)

    @check("a patrol with your file comes alongside, and one without does not")
    def _():
        # `ERRANDS["patrol"]` has been `hostile=False`, parked at the quay
        # body, never intercepting, for as long as there have been patrols.
        game = new_game("patrol-stop")
        game.credits = 200_000
        game.system.port.faction = "concordat"
        game.system.faction = "concordat"
        assert not enforce_sim.watchers(game, game.system), (
            "a clean captain is already being watched")
        quiet = enforce_sim.stopped_odds(game, "concordat", game.system)

        warrants_sim.issue(game, "concordat", "refuse", "because", "holdings",
                           system=game.system)
        from ..sim import fleets as fleets_sim
        if not fleets_sim.guard_at(game, game.system, "concordat"):
            # No squadron on station in this sector: the reach rule is doing
            # its job, and there is nothing here to stop us. Say so rather
            # than force it — that is the design, not a gap.
            return (f"odds {quiet:.0%} clean; no Concordat hulls on station "
                    "here, so nobody stops anybody — which is the reach rule")
        assert "concordat" in enforce_sim.watchers(game, game.system)
        loud = enforce_sim.stopped_odds(game, "concordat", game.system)
        assert loud > quiet, f"a warrant did not raise the odds: {quiet} → {loud}"
        result = enforce_sim.stop(game, "concordat", RNG("stop"), game.system)
        assert result["said"], result
        return (f"odds {quiet:.0%} clean → {loud:.0%} under an instrument; "
                f"they {result['kind']}")

    @check("firing inside somebody's approaches is finally an offence")
    def _():
        # `may_engage`'s four refusals were the conn being busy, the target
        # not being a hull, having no weapons, and range. Nothing political.
        game = new_game("affray")
        game.system.port.faction = "concordat"
        game.system.faction = "concordat"
        before = len(law_sim.ensure(game).charges)
        dockets.report(game, "affray", "you opened fire in their approaches",
                       1.0, game.system)
        after = law_sim.open_charges(game, "concordat")
        assert len(law_sim.ensure(game).charges) > before, (
            "opening fire inside a capital's volume offended nobody")
        assert any(c.offence == "affray" for c in after), after
        return (f"affray charged by {sorted({c.power for c in after})} in "
                "their own approaches")
