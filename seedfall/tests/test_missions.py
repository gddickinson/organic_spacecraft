"""Mission checks — work that leads somewhere.

Contracts were a shopping list: independent jobs off a board, with nothing
following from finishing one. These hold commissions to the three things that
make them different — they escalate, they close doors, and failing one shuts
it for good.
"""

from __future__ import annotations

import re

from ..core.state import new_game
from ..data.chains import CHAINS, CHAINS_BY_ID
from ..data.contracts import KINDS
from ..sim import chains as chain_sim
from ..sim import contracts as contract_sim
from .harness import Suite


def _satisfy(game, contract) -> None:
    """Meet a contract's terms by whatever route it wants."""
    if contract.kind in ("deliver", "prospect", "relic"):
        game.ship.cargo[contract.commodity] = contract.amount + 5
        # A prospect wants the material *brought in*, so the hull has to have
        # been away since it was accepted (`Contract.travelled`) — otherwise
        # it is the issuing counter's own stock handed straight back.
        contract.travelled = True
        game.location_id = (contract.target_system if contract.kind == "deliver"
                            else contract.issued_at)
    elif contract.kind == "survey":
        for body in game.galaxy.systems[contract.target_system].bodies:
            body.surveyed = True
    else:                                    # expedition, bounty
        contract.progress = contract.amount
        if contract.kind == "bounty":
            contract_sim._pay(game, contract)


def _commissioned(chain_id: str, seed: str = "mission"):
    chain = CHAINS_BY_ID[chain_id]
    game = new_game(seed)
    game.credits = 200000
    # Put the player at a port belonging to the issuer.
    system = next((s for s in game.galaxy.systems
                   if s.port and s.port.faction == chain.issuer), None)
    assert system is not None, f"no {chain.issuer} port in this galaxy"
    game.location_id = system.id
    game.rep[chain.issuer] = max(game.rep.get(chain.issuer, 0), chain.min_rep + 10)
    return game, system


def run(suite: Suite) -> None:
    check = suite.check

    @check("every commission is coherent and its stages are postable")
    def _():
        from ..data.factions import FACTIONS_BY_ID
        for chain in CHAINS:
            assert chain.issuer in FACTIONS_BY_ID, f"{chain.id} has no issuer"
            assert chain.stages, f"{chain.id} has no stages"
            assert len(chain.stages) >= 2, f"{chain.id} is not a chain"
            for stage in chain.stages:
                assert stage.kind in KINDS, f"{chain.id} wants unknown {stage.kind}"
                assert stage.outcome, f"a stage of {chain.id} says nothing"
                assert stage.days > 0, f"a stage of {chain.id} allows no time"
            # Escalation: the last stage must pay better than the first.
            assert chain.stages[-1].pay > chain.stages[0].pay, (
                f"{chain.id} does not escalate")
            assert chain.reward_credits > 0 and chain.reward_note, (
                f"{chain.id} completes to nothing")
            for other in chain.blocks:
                assert other in CHAINS_BY_ID, f"{chain.id} blocks unknown {other}"
        return f"{len(CHAINS)} commissions, {sum(len(c.stages) for c in CHAINS)} stages"

    @check("a commission runs to the end and pays out")
    def _():
        game, system = _commissioned("assay")
        res = chain_sim.begin(game, "assay", system)
        assert res["ok"], res.get("why")
        held = chain_sim.state_of(game, "assay")
        credits_before = game.credits

        seen = []
        for _ in range(len(CHAINS_BY_ID["assay"].stages)):
            contract = chain_sim.current_contract(game, held)
            assert contract is not None, f"no contract at stage {held.stage}"
            seen.append(contract.reward)
            _satisfy(game, contract)
            game.advance_days(1)

        assert held.done, f"commission stalled at stage {held.stage}"
        assert not held.failed
        assert len(held.history) == len(CHAINS_BY_ID["assay"].stages)
        assert game.credits > credits_before + CHAINS_BY_ID["assay"].reward_credits
        assert seen[-1] > seen[0], f"stages did not escalate: {seen}"
        return f"three stages, fees {seen[0]:,} → {seen[-1]:,}, then the payout"

    @check("what a stage asks for is what its title says")
    def _():
        # Scale was applied after the title was written, so a posting could
        # read "carry 62 t" and complete at 31 t.
        mismatches = []
        for chain in CHAINS:
            game, system = _commissioned(chain.id, seed=f"title-{chain.id}")
            if not chain_sim.begin(game, chain.id, system)["ok"]:
                continue
            held = chain_sim.state_of(game, chain.id)
            for _ in range(len(chain.stages)):
                contract = chain_sim.current_contract(game, held)
                if contract is None:
                    break
                found = re.search(r"(\d+(?:\.\d+)?)\s*(?:t|bodies|hull|intact)",
                                  contract.title)
                if found and abs(float(found.group(1)) - contract.amount) > 0.01:
                    mismatches.append(f"{chain.id}/{held.stage}: "
                                      f"{found.group(1)} vs {contract.amount:g}")
                _satisfy(game, contract)
                game.advance_days(1)
        assert not mismatches, "titles disagree with terms: " + ", ".join(mismatches)
        return "every stage title matches what it asks for"

    @check("taking one commission closes the door on its rival")
    def _():
        game, system = _commissioned("assay")
        rival = CHAINS_BY_ID["assay"].blocks[0]
        assert chain_sim.blocked(game, rival) is None, "shut before starting"
        assert chain_sim.begin(game, "assay", system)["ok"]
        assert chain_sim.blocked(game, rival), f"{rival} is still open"

        # And it is genuinely refused at the rival's own port.
        rival_chain = CHAINS_BY_ID[rival]
        rival_port = next((s for s in game.galaxy.systems
                           if s.port and s.port.faction == rival_chain.issuer), None)
        if rival_port is not None:
            game.rep[rival_chain.issuer] = 90
            offers = dict((c.id, (ok, why))
                          for c, ok, why in chain_sim.offered(game, rival_port))
            assert rival in offers, f"{rival} was not even listed"
            assert not offers[rival][0], f"{rival} was still on offer"
        return f"assay shuts {rival}, and the refusal holds at their own port"

    @check("a missed deadline withdraws the commission for good")
    def _():
        game, system = _commissioned("firebreak", seed="lapse")
        assert chain_sim.begin(game, "firebreak", system)["ok"]
        held = chain_sim.state_of(game, "firebreak")
        contract = chain_sim.current_contract(game, held)
        rep_before = game.rep.get("concordat", 0)

        game.advance_days(contract.deadline - game.day + 2)
        assert held.failed, "the commission survived a missed deadline"
        assert game.rep.get("concordat", 0) < rep_before, "no standing was lost"
        offers = dict((c.id, ok) for c, ok, _w in chain_sim.offered(game, system))
        assert "firebreak" not in offers, "it was offered again after lapsing"
        return "withdrawn, standing lost, not offered again"

    @check("commission stages do not eat the contract board's slots")
    def _():
        game, system = _commissioned("assay")
        assert chain_sim.begin(game, "assay", system)["ok"]
        board = contract_sim.active(game)
        assert not any(c.chain for c in board), (
            "a commission stage is sitting on the ordinary board")
        assert len(contract_sim.all_open(game)) == len(board) + 1, (
            "the commission stage is not open at all")
        return f"{len(board)} board contracts, commission stage held apart"

    @check("every reward a commission promises actually exists")
    def _():
        # **Task #38's shape, found again.** `annex` was gated behind a
        # technology nobody had written; the Reliquary *promised* one — 
        # `reward_tech="xenolinguistics"`, which is in neither the research tree
        # nor the xenotech table — and `_finish` appended the string to
        # `research.unlocked` regardless. The reward granted no bonus and opened
        # no node, and the offer screen never mentioned it, so nothing and nobody
        # could tell.
        #
        # **The guard has to know about both namespaces.** A first sweep checked
        # the research tree alone and reported thirty-seven phantoms: twelve xeno
        # parts naming ids that live in `data/xenotech.py` and are perfectly real,
        # gated behind studied alien technology rather than the bench. A check
        # that cried wolf about those would have been deleted inside a month.
        from ..data.factions import FACTIONS_BY_ID
        from ..data.tech import TECH_BY_ID
        from ..data.xenotech import XENOTECH_BY_ID
        from ..sim import chains as chain_sim

        granted = 0
        for chain in CHAINS:
            if not chain.reward_tech:
                continue
            granted += 1
            where = ("the research tree" if chain.reward_tech in TECH_BY_ID
                     else "the xenotech table"
                     if chain.reward_tech in XENOTECH_BY_ID else None)
            assert where, (
                f"{chain.id} promises the technology {chain.reward_tech!r} and "
                "it exists in neither the research tree nor the xenotech table")
            # And it has to be a *tree* node, because `_finish` grants it by
            # appending to `research.unlocked`. A xenotech id is a real id in the
            # wrong namespace: incorporating studied alien work goes through
            # `xeno.incorporate` and would need its own reward field, so naming
            # one here would put a string in the bench's list that the bench does
            # not know. Caught by mutation — pointing the Reliquary at
            # `vent_symbiosis`, which exists, still fails here.
            assert where == "the research tree", (
                f"{chain.id} promises {chain.reward_tech!r}, which is in "
                f"{where} — `_finish` grants rewards by appending to "
                "`research.unlocked`, so only a tree node can be handed over")
            node = chain_sim.reward_tech_of(chain)
            assert node is not None and node.cost > 0, (
                f"{chain.id}: {chain.reward_tech!r} is in {where} and "
                "`reward_tech_of` cannot hand it to a screen")

        # Every other id a commission names has to resolve too: the kinds its
        # stages post, and the rivals it shuts.
        for chain in CHAINS:
            for stage in chain.stages:
                assert stage.kind in KINDS, (
                    f"{chain.id} posts a {stage.kind!r} stage and the contract "
                    "book has no such kind")
            for other in chain.blocks:
                assert other in CHAINS_BY_ID, (
                    f"{chain.id} closes {other!r}, which is not a commission")
            assert chain.issuer in FACTIONS_BY_ID, chain.issuer
        return (f"{granted} commission(s) grant a technology, every one of them "
                f"real; {sum(len(c.stages) for c in CHAINS)} stages posting "
                "kinds the book knows, and every rival named")

    @check("the offer says what the technology is worth")
    def _():
        # #39's rule. One commission in four hands over a whole node of a
        # fifty-eight-node tree and the desk advertised it as credits and
        # standing, exactly like the three that hand over neither.
        from .test_ui import _use_offscreen
        _use_offscreen()
        from PyQt6.QtWidgets import QApplication, QLabel
        from ..sim import chains as chain_sim
        from ..ui.window import MainWindow

        app = QApplication.instance() or QApplication([])
        assert app is not None
        chain = next(c for c in CHAINS if c.reward_tech)
        node = chain_sim.reward_tech_of(chain)
        assert node is not None

        game = new_game("offer-tech")
        game.rep[chain.issuer] = 90.0
        system = next((s for s in game.galaxy.systems
                       if s.port and s.port.faction == chain.issuer), None)
        assert system is not None, f"nowhere issues {chain.id}"
        game.location_id = system.id
        offered = [c.id for c, _ok, _why in chain_sim.offered(game, system)]
        assert chain.id in offered, (offered, chain.id)

        win = MainWindow(game)
        win.toast = lambda *a, **k: None
        win.go("port")
        view = win.views["port"]
        view.tab = "contracts"
        view.refresh()
        for _ in range(3):
            app.processEvents()
        said = " ".join(lab.text() for lab in view.findChildren(QLabel)
                        if lab.text())
        win.close()
        assert node.name in said, (
            f"{chain.name} grants {node.name} and the desk does not say so: "
            f"{said[-400:]}")
        assert f"{node.cost:,} points" in said, (
            f"{node.cost:,} points of research handed over and the desk does "
            "not price it")
        return (f"the desk offers {chain.name} and names {node.name}, "
                f"{node.cost:,} points of research you do not have to do")

    @check("commissions survive a save and reload")
    def _():
        import json

        from ..core.save import decode, encode

        game, system = _commissioned("reliquary", seed="persist-mission")
        assert chain_sim.begin(game, "reliquary", system)["ok"]
        held = chain_sim.state_of(game, "reliquary")
        contract = chain_sim.current_contract(game, held)
        _satisfy(game, contract)
        game.advance_days(1)

        reloaded = decode(json.loads(json.dumps(encode(game))))
        back = chain_sim.state_of(reloaded, "reliquary")
        assert back is not None, "the commission was lost over a save"
        assert back.stage == held.stage, "progress was lost"
        assert back.history == held.history, "what happened was forgotten"
        live = chain_sim.current_contract(reloaded, back)
        assert live is not None, "the live stage contract was lost"
        assert live.chain == "reliquary", "the contract forgot its commission"
        return f"stage {back.stage + 1} and its contract came back intact"
