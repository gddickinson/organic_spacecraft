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
