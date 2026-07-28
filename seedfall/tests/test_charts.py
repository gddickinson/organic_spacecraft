"""Chart checks — exploring has to be worth the flying.

Measured before any of this was written: charting the five-body home system
took 53 days and the chart sold for 1,510 credits, about 28 a day, against a
contraband run at some fifty times that. The whole forty-two-system sector,
charted and sold, came to 55,014 — roughly one run of unlicensed seed.
`survey_value()` was `460 + 210 * len(bodies)`, so a system with a buried
Abyssal site and ground worth crossing the sector for fetched exactly what five
bare rocks fetched. Meanwhile `intel.py`'s own docstring called the Charted
level "the only one worth anything to a buyer, and the reason to go back to
somewhere you have already been".

A chart is information. These hold it to being priced like information.
"""

from __future__ import annotations

from ..core.state import new_game
from ..data.charts import APPETITES, FRESH_DAYS, STALE_FLOOR
from ..data.factions import FACTIONS_BY_ID
from ..sim import charts as chart_sim
from ..sim import intel as intel_sim
from ..sim.actions import survey
from .harness import Suite


def _charted(game, system) -> None:
    for body in system.bodies:
        body.surveyed = True
    system.scanned = True
    chart_sim.stamp(game, system)


def _all_charted(seed: str):
    game = new_game(seed)
    for system in game.galaxy.systems:
        _charted(game, system)
    return game


def run(suite: Suite) -> None:
    check = suite.check

    @check("the buyers and the price list are coherent")
    def _():
        assert APPETITES, "nobody buys charts"
        for appetite in APPETITES:
            assert appetite.faction in FACTIONS_BY_ID, appetite.faction
            assert appetite.keen > 0 and appetite.line, appetite.faction
            assert appetite.prizes, f"{appetite.faction} prizes nothing"
        game = new_game("coherent")
        parts = chart_sim.components(game, game.system)
        for appetite in APPETITES:
            for prize in appetite.prizes:
                assert prize in parts, (
                    f"{appetite.faction} prizes {prize!r}, which is not "
                    "something a chart records")
        return (f"{len(APPETITES)} buyers, {len(parts)} things a chart says, "
                "every appetite naming one of them")

    @check("a chart is priced on what is in the system")
    def _():
        # The flat rate made a buried Abyssal site worth precisely as much as
        # an extra bare rock.
        game = _all_charted("priced")
        valued = sorted(
            ((chart_sim.best_buyer(game, s)[1], s) for s in game.galaxy.systems),
            key=lambda t: t[0])
        low, high = valued[0], valued[-1]
        assert high[0] > low[0] * 4, (
            f"the dearest chart is only {high[0] / low[0]:.1f}x the cheapest, "
            "so what is in a system barely matters")
        rich = chart_sim.components(game, high[1])
        bare = chart_sim.components(game, low[1])
        assert (rich["relic"] + rich["life"] + rich["anomaly"]
                > bare["relic"] + bare["life"] + bare["anomaly"]), (
            "the dearest chart is not the more interesting system")
        return (f"{low[0]:,} for {chart_sim.note(game, low[1])} · "
                f"{high[0]:,} for {chart_sim.note(game, high[1])}")

    @check("who you sell to is a real decision")
    def _():
        game = _all_charted("buyers")
        gaps, winners = [], {}
        for system in game.galaxy.systems:
            offers = chart_sim.offers(game, system)
            gaps.append(offers[0][1] / max(1, offers[-1][1]))
            winners[offers[0][0]] = winners.get(offers[0][0], 0) + 1
        mean = sum(gaps) / len(gaps)
        assert mean > 1.2, (
            f"best and worst buyer differ by only {mean:.2f}x on average")
        assert len(winners) >= 2, (
            f"one power is always the best buyer, so there is no choice: "
            f"{winners}")
        return (f"best/worst {mean:.2f}x on average; best buyer is "
                + ", ".join(f"{k} {v}x" for k, v in sorted(winners.items())))

    @check("every buyer has somewhere you can actually sell")
    def _():
        # A power that pays best for half the sector and holds no quay is an
        # offer the screen dangles and the player can never take.
        missing = []
        for index in range(6):
            game = new_game(f"quays-{index}")
            held = {s.port.faction for s in game.galaxy.systems if s.port}
            for appetite in APPETITES:
                if appetite.faction not in held:
                    missing.append(f"{appetite.faction}@quays-{index}")
        assert not missing, (
            f"buyers with no port to sell at: {sorted(set(missing))}")
        return "all four buyers hold a quay in six sectors"

    @check("a chart goes stale, and stops going stale")
    def _():
        game = _all_charted("stale")
        system = game.galaxy.systems[0]
        buyer = chart_sim.best_buyer(game, system)[0]
        game.register[f"chart:{system.id}"] = 0

        game.day = 0
        fresh = chart_sim.value_to(game, system, buyer)
        game.day = FRESH_DAYS // 2
        middling = chart_sim.value_to(game, system, buyer)
        game.day = FRESH_DAYS
        old = chart_sim.value_to(game, system, buyer)
        game.day = FRESH_DAYS * 4
        ancient = chart_sim.value_to(game, system, buyer)

        assert fresh > middling > old, (
            f"no decay: {fresh:,} → {middling:,} → {old:,}")
        assert old == ancient, "a chart keeps rotting past the floor"
        assert abs(old / fresh - STALE_FLOOR) < 0.02, (
            f"the floor is {old / fresh:.2f}, not {STALE_FLOOR}")
        return f"{fresh:,} fresh → {middling:,} at half-life → {old:,} floored"

    @check("the office does not lie about what it will pay")
    def _():
        game = _all_charted("honest")
        port = next(s for s in game.galaxy.systems if s.port)
        target = next(s for s in game.galaxy.systems if s.id != port.id)
        game.location_id = port.id
        quoted = intel_sim.survey_value(game, target, port.port.faction)
        before = game.credits
        res = intel_sim.sell_survey(game, target, port.port.faction)
        assert res["ok"], res.get("why")
        paid = game.credits - before
        assert abs(paid - quoted) < 0.01, f"quoted {quoted:,}, paid {paid:,}"

        again = intel_sim.sell_survey(game, target, port.port.faction)
        assert not again["ok"], "sold the same chart twice"
        return f"quoted {quoted:,}, paid {paid:,}, and refused a second time"

    @check("charting is a living rather than a gesture")
    def _():
        # The number that made this cycle worth doing: 28 credits a day.
        # Averaged over seeds rather than measured on one — the first version
        # of this check happened to draw a fast sector and read 1,127, which
        # is half again the median and would have set the band by luck.
        rates, bodies, spans = [], 0, 0
        for index in range(6):
            game = new_game(f"living-{index}")
            system = game.system
            start = game.day
            for body_index in range(len(system.bodies)):
                survey(game, body_index)
            days = max(1, game.day - start)
            _buyer, value = chart_sim.best_buyer(game, system)
            rates.append(value / days)
            bodies += len(system.bodies)
            spans += days
        rate = sum(rates) / len(rates)
        assert rate > 300, (
            f"charting still pays {rate:.0f} credits a day — the flat rate it "
            "replaced paid 28, and nothing else in the game pays under 1,000")
        assert rate < 1500, (
            f"charting now pays {rate:.0f} a day, which would make surveying "
            "the best-paying thing in the sector rather than a living")
        return (f"{bodies} bodies over {spans} days in 6 sectors — "
                f"{rate:,.0f} credits a day, was 28")

    @check("what a chart says matches what is in it")
    def _():
        game = _all_charted("says")
        checked = 0
        for system in game.galaxy.systems:
            said = chart_sim.note(game, system)
            parts = chart_sim.components(game, system)
            if parts["relic"]:
                assert "buried site" in said, f"{system.name}: {said!r}"
                checked += 1
            if parts["port"]:
                assert "quay" in said, f"{system.name}: {said!r}"
                checked += 1
            if not any(parts[k] for k in ("relic", "anomaly", "life", "port")) \
                    and parts["ore"] <= 1.5:
                assert "nothing remarkable" in said, f"{system.name}: {said!r}"
                checked += 1
        assert checked > 10, f"only {checked} claims were worth checking"
        return f"{checked} claims on the chart, all matching the system"
