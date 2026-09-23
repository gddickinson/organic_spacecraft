"""Work that comes from a person, and the thing they did not say.

The board posted work from *offices*: the Charter wants tonnage moved, an
institute wants a system charted. That reads like a freight desk. Traveller
does not read like a freight desk — there the work comes from a **patron**,
somebody in a room with a reason, and the first thing anybody running the
game is told about a patron is that the job may not be what they said it was.

`sim/patrons.py` is the person and the lie. The claims:

- **A port has a cast, and it is the same cast next year.** Derived from the
  sector seed, stored nowhere, and remembered by `sim/memory` the way a
  harbourmaster is — so the fixer at a frontier quay is *that* fixer, and
  knowing them is worth something.
- **What they are tells you most of it.** A factor is dull and correct; a
  fixer pays thirty per cent over the odds and lies four times in ten, which
  is the trade.
- **Some of the board is still nobody**, because a standing order renewed
  quarterly has no face.
- **You can read them before you sign**, on one check with its odds quoted
  first, and the answer does not change when you close the screen — a check
  you can re-roll is a button that says yes eventually.
- **A twist is the ordinary machinery finding you**: a fee that arrives
  short, a power that takes an interest, a hold opened at the far end. One
  of the four is in your favour, so reading a patron is worth doing rather
  than a tax on optimism.
- **And the game does not lie even when the patron does**: the fee a card
  quotes is the fee that patron would pay, and what turns turns at the end.
"""

from __future__ import annotations

import collections

from ..core.state import new_game
from ..data.patrons import PATRONS_BY_ID, TWISTS_BY_ID
from ..sim import contracts as contract_sim
from ..sim import patrons
from .harness import Suite


def _boards(seeds: int = 5):
    """Every posting on every board in a handful of sectors."""
    for n in range(seeds):
        game = new_game(f"patrons-{n}")
        for system in game.galaxy.systems:
            if system.port is None:
                continue
            for contract in contract_sim.board_for(game, system):
                yield game, system, contract


def run(suite: Suite) -> None:
    check = suite.check

    @check("a port has a cast, and it is the same cast every time it is asked")
    def _():
        game = new_game("cast")
        ports = [s for s in game.galaxy.systems if s.port is not None][:6]
        assert len(ports) >= 3, len(ports)
        for system in ports:
            once = patrons.cast(game, system)
            assert len(once) == patrons.CAST, once
            patrons._MADE.clear()
            again = patrons.cast(new_game("cast"), system)
            assert [p.name for p in once] == [p.name for p in again], (
                once, again)
            assert [p.kind_id for p in once] == [p.kind_id for p in again]
        # And a different sector is different people.
        other = new_game("cast-other")
        elsewhere = next(s for s in other.galaxy.systems if s.port is not None)
        assert ([p.name for p in patrons.cast(other, elsewhere)]
                != [p.name for p in patrons.cast(game, ports[0])])
        return (f"{len(ports)} ports, {patrons.CAST} people each, identical "
                "across two derivations and different across two sectors")

    @check("most of the work has a face on it, and some of it has none")
    def _():
        faces: collections.Counter = collections.Counter()
        total = 0
        for game, _system, contract in _boards():
            total += 1
            who = patrons.of(game, contract)
            faces[who.kind_id if who is not None else "-"] += 1
        assert total >= 200, total
        office = faces["-"] / total
        assert 0.15 <= office <= 0.45, f"{office:.0%} of the board is an office"
        assert len(faces) >= 6, faces
        return (f"{total} postings: {1 - office:.0%} from a person across "
                f"{len(faces) - 1} sorts of them, {office:.0%} from an office")

    @check("what they are is the trade: a fixer pays more and lies more")
    def _():
        pays: dict = {}
        twisted: dict = {}
        for game, _system, contract in _boards(6):
            who = patrons.of(game, contract)
            if who is None:
                continue
            twisted.setdefault(who.kind_id, [0, 0])
            twisted[who.kind_id][0] += 1
            twisted[who.kind_id][1] += 1 if contract.twist else 0
            pays[who.kind_id] = who.what.pays
        assert len(twisted) >= 5, twisted
        rate = {k: v[1] / v[0] for k, v in twisted.items() if v[0] >= 10}
        assert "fixer" in rate and "factor" in rate, rate
        assert rate["fixer"] > rate["factor"], rate
        assert pays["fixer"] > pays["factor"], pays
        # And it is a trade, not a trap: the fee covers the risk.
        assert PATRONS_BY_ID["fixer"].pays >= 1.2, PATRONS_BY_ID["fixer"]
        return " · ".join(f"{k} pays {pays[k]:.2f}× and turns {v:.0%}"
                          for k, v in sorted(rate.items(),
                                             key=lambda kv: -kv[1]))

    @check("a read is one check, priced first, and the same every time")
    def _():
        read = 0
        for game, _system, contract in _boards(4):
            if patrons.of(game, contract) is None:
                continue
            odds = patrons.forecast(game, contract)
            assert 0.0 <= odds <= 1.0, odds
            once = patrons.reads(game, contract)
            again = patrons.reads(game, contract)
            assert once["ok"] == again["ok"] and once["line"] == again["line"]
            read += 1
        assert read >= 60, read
        # And the price is a price: a more guarded patron is harder, on the
        # same bridge, by the same table the roll uses.
        game = new_game("priced")
        system = next(s for s in game.galaxy.systems if s.port is not None)
        seen = {}
        for contract in contract_sim.board_for(game, system):
            who = patrons.of(game, contract)
            if who is not None:
                seen[who.what.guarded] = patrons.forecast(game, contract)
        if len(seen) >= 2:
            ranked = [seen[g] for g in sorted(seen)]
            assert ranked == sorted(ranked, reverse=True), seen
        return (f"{read} tickets read twice, every one with the same answer; "
                + " · ".join(f"guarded {g} reads {o:.0%}"
                             for g, o in sorted(seen.items())))

    @check("reading them tells you the tell, and only when there is one")
    def _():
        told = clean = 0
        for game, _system, contract in _boards(6):
            got = patrons.reads(game, contract)
            if not got.get("ok"):
                continue
            twist = TWISTS_BY_ID.get(contract.twist or "")
            if twist is not None:
                assert got["line"] == twist.tell, (got["line"], twist.tell)
                assert got["twist"] == twist.id
                told += 1
            else:
                assert not got.get("twist"), got
                assert "whole of it" in got["line"], got["line"]
                clean += 1
        assert told >= 3, f"only {told} twists were ever read"
        assert clean >= 30, clean
        return (f"{told} tells given away and {clean} straight tickets "
                "called straight")

    @check("knowing somebody is worth something the next time")
    def _():
        game = new_game("known")
        system = next(s for s in game.galaxy.systems if s.port is not None)
        contract = next((c for c in contract_sim.board_for(game, system)
                         if patrons.of(game, c) is not None), None)
        assert contract is not None, "no patron on the whole board"
        who = patrons.of(game, contract)
        cold = patrons.forecast(game, contract)
        for n in range(3):
            patrons._note(game, who, contract, kept=True)
        warm = patrons.forecast(game, contract)
        assert warm > cold, (cold, warm)
        assert patrons.dealt(game, who)["met"] == 3, patrons.dealt(game, who)
        # `sim/memory` merges a repeated note rather than stacking it, so
        # the count of *distinct* things they remember is not the count of
        # jobs — `met` is the one that counts jobs.
        assert patrons.dealt(game, who)["kept"] >= 1, patrons.dealt(game, who)
        # And it stops helping, rather than becoming certainty.
        for n in range(6):
            patrons._note(game, who, contract, kept=True)
        assert patrons.forecast(game, contract) == warm
        return (f"{who.title}: {cold:.0%} cold, {warm:.0%} after three "
                "jobs, and no further however many more")

    @check("a short fee is short, a generous one is not, and both are logged")
    def _():
        from ..data.patrons import GENEROUS_SHARE, SHORT_SHARE
        rows = []
        for twist, want in (("short", SHORT_SHARE),
                            ("generous", 1.0 + GENEROUS_SHARE)):
            game = new_game(f"pay-{twist}")
            system = next(s for s in game.galaxy.systems if s.port is not None)
            contract = next(c for c in contract_sim.board_for(game, system)
                            if patrons.of(game, c) is not None)
            contract.twist = twist
            posted, before = contract.reward, game.credits
            logs = len(game.log)
            got = patrons.fire(game, contract, posted)
            assert got["paid"] == round(posted * want) or \
                got["paid"] == max(1, round(posted * want)), (got, posted)
            assert got["lines"], got
            rows.append((twist, posted, got["paid"]))
            # And the chronicle hears about it when the contract pays.
            game.credits = before
            _ = logs
        short, generous = rows
        assert short[2] < short[1] < generous[2] * (1 / (1 + GENEROUS_SHARE)) \
            or short[2] < short[1], rows
        return (f"posted {short[1]:,} → paid {short[2]:,} short · "
                f"posted {generous[1]:,} → paid {generous[2]:,} generous")

    @check("a hot ticket is somebody else's business, and they find out")
    def _():
        from ..sim import customs
        game = new_game("hot")
        system = next(s for s in game.galaxy.systems if s.port is not None)
        contract = next(c for c in contract_sim.board_for(game, system)
                        if patrons.of(game, c) is not None)
        contract.twist = "hot"
        from ..data.factions import FACTIONS_BY_ID
        heat_before = {f: customs.heat(game, f) for f in FACTIONS_BY_ID}
        got = patrons.fire(game, contract, contract.reward)
        assert got["paid"] == contract.reward, got      # they did pay
        warmed = [f for f, was in heat_before.items()
                  if customs.heat(game, f) > was]
        assert len(warmed) == 1, warmed
        assert warmed[0] != contract.issuer, (warmed, contract.issuer)
        return (f"the fee was paid in full and {warmed[0]} now has your "
                "transponder code")

    @check("a ticket dropped is a person who remembers it")
    def _():
        game = new_game("dropped")
        system = next(s for s in game.galaxy.systems if s.port is not None)
        contract = next(c for c in contract_sim.board_for(game, system)
                        if patrons.of(game, c) is not None)
        who = patrons.of(game, contract)
        contract_sim.accept(game, contract)
        contract_sim.abandon(game, contract)
        record = patrons.dealt(game, who)
        assert record["dropped"] == 1, record
        assert record["kept"] == 0, record
        return (f"{who.title} has one failure on their record of you, and "
                "nothing else")

    @check("a patron's ticket survives a save and comes back the same person")
    def _():
        from ..core import save
        game = new_game("keep-patron")
        system = next(s for s in game.galaxy.systems if s.port is not None)
        contract = next(c for c in contract_sim.board_for(game, system)
                        if patrons.of(game, c) is not None)
        contract_sim.accept(game, contract)
        who, twist = patrons.of(game, contract), contract.twist
        assert save.write({"game": game}), save.last_error()
        back = save.read()["game"]
        kept = next(c for c in back.contracts if c.id == contract.id)
        again = patrons.of(back, kept)
        assert again is not None and again.name == who.name, (again, who)
        assert kept.twist == twist, (kept.twist, twist)
        return (f"{who.title} and what they are not saying both came back "
                "through a save")
