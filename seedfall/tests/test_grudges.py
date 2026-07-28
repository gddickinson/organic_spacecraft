"""Grudge checks — a power must be able to say why it treats you as it does.

Standing is one number that decays. A grudge is a specific dated thing, and
these hold it to *changing behaviour* rather than colouring what an envoy
says: a quay prices you by its memory, a power that holds enough against you
stops posting work, and feeling travels between powers that are close on the
relations matrix.

The rule underneath all of it: `because()` must name the memories responsible
for whatever `feeling()` returns. Nothing in this game is allowed to dislike
you for a reason it cannot state.
"""

from __future__ import annotations

from ..core.rng import RNG
from ..core.state import new_game
from ..data.factions import FACTIONS_BY_ID
from ..sim import contracts as contract_sim
from ..sim import diplomacy as dip_sim
from ..sim import grudge as grudge_sim
from ..sim import market as market_sim
from ..sim import memory as memory_sim
from ..sim import trade as trade_sim
from .harness import Suite


def _at_port(seed: str):
    game = new_game(seed)
    port = next(s for s in game.galaxy.systems if s.port and s.market)
    game.location_id = port.id
    game.credits = 200_000
    return game, port


def run(suite: Suite) -> None:
    check = suite.check

    @check("a fresh chronicle is owed nothing and owes nothing")
    def _():
        # The default has to be exactly neutral or every existing measurement
        # in the suite quietly shifts.
        game, port = _at_port("grudge-fresh")
        for faction_id in dip_sim.POWERS:
            assert abs(grudge_sim.feeling(game, faction_id)) < 0.01
            assert grudge_sim.price_bias(game, faction_id) == 1.0
            assert grudge_sim.will_deal(game, faction_id)[0]
            assert not grudge_sim.hostile_open(game, faction_id)
        assert market_sim.quote_buy(game, port, "ore") is not None
        return f"{len(dip_sim.POWERS)} powers, all neutral, prices unbiased"

    @check("a quay prices you by what it remembers")
    def _():
        game, port = _at_port("grudge-price")
        faction = port.port.faction
        goods = [c for c in port.market.stock][:5]
        before = {c: (market_sim.quote_buy(game, port, c),
                      market_sim.quote_sell(game, port, c)) for c in goods}

        grudge_sim.note(game, faction, "kill",
                        "you destroyed one of ours off Vaux Deep", 1.5)
        after = {c: (market_sim.quote_buy(game, port, c),
                     market_sim.quote_sell(game, port, c)) for c in goods}
        dearer = [c for c in goods if after[c][0] > before[c][0]]
        meaner = [c for c in goods if after[c][1] < before[c][1]]
        assert dearer, f"a kill changed no buying price: {before} → {after}"
        assert meaner, f"a kill changed no selling price"

        # And the other way: a power that remembers you well is cheaper.
        kind, kind_port = _at_port("grudge-price")
        grudge_sim.note(kind, kind_port.port.faction, "rescue",
                        "you came for us when nobody else would", 1.5)
        cheaper = [c for c in goods
                   if market_sim.quote_buy(kind, kind_port, c) < before[c][0]]
        assert cheaper, "goodwill bought nothing"
        return (f"{len(dearer)}/{len(goods)} goods dearer after a kill, "
                f"{len(cheaper)} cheaper after a rescue")

    @check("what the quay quotes is what the till charges")
    def _():
        # The defect this project keeps finding: a screen quoting one number
        # and the ledger using another. One helper feeds both.
        game, port = _at_port("grudge-till")
        grudge_sim.note(game, port.port.faction, "betrayal",
                        "you ran our blockade at Kessel Gate", 1.4)
        cid = next(c for c in port.market.stock
                   if market_sim.quote_buy(game, port, c))
        quoted = market_sim.quote_buy(game, port, cid)
        before = game.credits
        result = trade_sim.buy(game, cid, 4)
        assert result["ok"], result.get("why")
        paid = (before - game.credits) / result["units"]
        assert abs(paid - quoted) < 0.51, (
            f"quoted {quoted}, charged {paid:.1f} each")

        got_quote = market_sim.quote_sell(game, port, cid)
        before = game.credits
        sold = trade_sim.sell(game, cid, result["units"])
        assert sold["ok"], sold.get("why")
        took = (game.credits - before) / sold["units"]
        assert abs(took - got_quote) < 0.51, (
            f"quoted {got_quote}, paid {took:.1f} each")
        return f"buying and selling {cid} both matched the quote to the credit"

    @check("a power that holds enough against you stops posting work")
    def _():
        game, port = _at_port("grudge-board")
        faction = port.port.faction
        assert contract_sim.generate(RNG("a"), game, port), "an empty board"

        grudge_sim.note(game, faction, "kill", "you destroyed the Steadfast", 1.6)
        grudge_sim.note(game, faction, "betrayal",
                        "you sold us out at Kessel Gate", 1.5)
        assert grudge_sim.feeling(game, faction) <= grudge_sim.COLD_SHOULDER
        assert not contract_sim.generate(RNG("a"), game, port), (
            "the board is still posting to somebody they will not deal with")

        deals, why = grudge_sim.will_deal(game, faction)
        assert not deals and why, "no reason given for the cold shoulder"
        assert "Steadfast" in why or "Kessel" in why, why
        return f"board closed, and it says why: {why[-46:]!r}"

    @check("a grudge travels to the powers who are close to them")
    def _():
        game, _port = _at_port("grudge-travel")
        state = dip_sim.ensure(game)
        state.relations[dip_sim._key("concordat", "charter")] = 80.0
        state.relations[dip_sim._key("concordat", "freeholds")] = -60.0

        alone = grudge_sim.feeling(game, "charter")
        grudge_sim.note(game, "concordat", "kill",
                        "you destroyed the Steadfast", 1.6)
        after = grudge_sim.feeling(game, "charter")
        assert after < alone - 5, (
            f"the Charter is close to the Concordat and did not notice: "
            f"{alone:+.1f} → {after:+.1f}")

        # And a power they are hostile to picks up none of it.
        assert abs(grudge_sim.feeling(game, "freeholds")) < 0.01, (
            "a grudge spread to somebody who is not close")

        named = [b for b in grudge_sim.because(game, "charter")
                 if b["kind"] == "inherited"]
        assert named, "the Charter is cooler and cannot say why"
        assert "Concordat" in named[0]["text"], named[0]
        return (f"the Charter went {alone:+.0f} → {after:+.0f} through a friend, "
                f"and the hostile power took nothing")

    @check("nothing dislikes you for a reason it cannot name")
    def _():
        game, _port = _at_port("grudge-why")
        for kind, text in (("kill", "you destroyed the Steadfast"),
                           ("theft", "you lifted a cargo that was ours"),
                           ("smuggling", "your hold was opened at our quay"),
                           ("trespass", "you refused us Ostrel to our face")):
            grudge_sim.note(game, "concordat", kind, text, 1.2)
        held = grudge_sim.feeling(game, "concordat")
        reasons = grudge_sim.because(game, "concordat")
        assert held < -20 and reasons, (held, reasons)
        assert reasons[0]["weight"] < 0, "the worst reason is not listed first"
        for entry in reasons:
            assert entry["text"] and entry["kind"], entry
        note = grudge_sim.standing_note(game, "concordat")
        assert "hold something against you" in note, note
        return f"{len(reasons)} reasons named for {held:+.0f}"

    @check("the political verbs write what a power would remember")
    def _():
        # A grudge system nothing writes to is dead content. These are the
        # ordinary political things a captain does.
        game, _port = _at_port("grudge-verbs")
        game.credits = 900_000
        wrote = {}
        for faction_id in ("charter", "concordat"):
            for action, ok, _why in dip_sim.available(game, faction_id):
                if not ok or action.id in ("broker", "denounce"):
                    continue
                before = len(grudge_sim.mind_of(game, faction_id).memories)
                dip_sim.perform(game, action.id, faction_id)
                after = len(grudge_sim.mind_of(game, faction_id).memories)
                if after > before:
                    wrote[action.id] = faction_id
        assert wrote, "no overture is remembered by anybody"
        assert grudge_sim.feeling(game, "charter") > 0, (
            "paying tribute left them feeling nothing")
        return f"{len(wrote)} overtures remembered: {sorted(wrote)}"

    @check("a denunciation lands on the power denounced")
    def _():
        game, _port = _at_port("grudge-denounce")
        game.credits = 900_000
        game.rep["freeholds"] = 60
        before = grudge_sim.feeling(game, "freeholds")
        result = dip_sim.perform(game, "denounce", "charter", "freeholds")
        if not result.get("ok"):
            return f"skipped: {result.get('why')}"
        after = grudge_sim.feeling(game, "freeholds")
        assert after < before, (
            f"the denounced power remembers nothing: {before:+.1f} → {after:+.1f}")
        reasons = grudge_sim.because(game, "freeholds")
        assert any("denounced" in r["text"] for r in reasons), reasons
        return f"the Freeholds went {before:+.0f} → {after:+.0f} and can say why"

    @check("what a power remembers survives a save")
    def _():
        import os
        import tempfile
        os.environ["HOME"] = tempfile.mkdtemp()
        from ..core import save as save_mod
        from ..core.state import load_game

        game, port = _at_port("grudge-save")
        grudge_sim.note(game, port.port.faction, "kill",
                        "you destroyed the Steadfast at Vaux Deep", 1.6)
        held = grudge_sim.feeling(game, port.port.faction)
        bias = grudge_sim.price_bias(game, port.port.faction)
        game.advance_days(3)
        save_mod.write({"game": game})
        back = load_game()
        assert back is not None
        assert abs(grudge_sim.feeling(back, port.port.faction) - held) < 2.0
        assert abs(grudge_sim.price_bias(back, port.port.faction) - bias) < 0.02
        assert any("Steadfast" in r["text"]
                   for r in grudge_sim.because(back, port.port.faction))
        return f"a feeling of {held:+.0f} and its reason both reloaded"
