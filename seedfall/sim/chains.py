"""Running commissions — the work that leads somewhere.

A commission holds a place in a chain and a single live contract. Finishing
that contract advances the place and posts the next one; failing it closes the
commission for good. Everything the contract book already does — deadlines,
cargo, bounties, expeditions — happens without knowing a chain is involved.
"""

from __future__ import annotations

import itertools
from dataclasses import dataclass, field

from ..core.save import register
from ..data.chains import CHAINS, CHAINS_BY_ID
from ..data.contracts import KINDS
from ..data.tech import TECH_BY_ID
from . import contracts as contract_sim
from . import loyalty

_uid = itertools.count(9000)


@register
@dataclass
class Commission:
    chain_id: str
    stage: int = 0
    contract_id: int | None = None
    done: bool = False
    failed: bool = False
    #: Lines from stages already finished, kept for the log on the desk.
    history: list = field(default_factory=list)

    @property
    def definition(self):
        return CHAINS_BY_ID[self.chain_id]


def ensure(game) -> list:
    if getattr(game, "commissions", None) is None:
        game.commissions = []
    return game.commissions


def state_of(game, chain_id: str):
    return next((c for c in ensure(game) if c.chain_id == chain_id), None)


def active(game) -> list:
    return [c for c in ensure(game) if not c.done and not c.failed]


def completed(game) -> list:
    return [c for c in ensure(game) if c.done]


def blocked(game, chain_id: str) -> str | None:
    """The commission that has shut the door on this one, if any."""
    for other in ensure(game):
        if other.chain_id == chain_id or other.failed:
            continue
        if chain_id in other.definition.blocks:
            return other.definition.name
    return None


# ── being offered one ──────────────────────────────────────────────────────

def offered(game, system) -> list[tuple]:
    """(chain, ok, why) for commissions this port could put to you."""
    if not system.port:
        return []
    faction = system.port.faction
    out = []
    for chain in CHAINS:
        if chain.issuer != faction:
            continue
        held = state_of(game, chain.id)
        if held is not None:
            continue
        ok, why = True, ""
        shut = blocked(game, chain.id)
        if shut:
            ok, why = False, f"You are already committed to {shut}."
        elif game.rep.get(faction, 0) < chain.min_rep:
            ok, why = False, (f"They would want {chain.min_rep:g} standing "
                              "before putting this to anyone.")
        out.append((chain, ok, why))
    return out


def reward_tech_of(chain):
    """The technology a commission hands over, as a `Tech`, or None.

    A door rather than a lookup at the call site, because the id has to resolve
    and nothing checked that it did: the Reliquary named `xenolinguistics`, which
    exists in neither the research tree nor the xenotech table, and `_finish`
    appended it to `research.unlocked` anyway — a reward that granted no bonus and
    opened no node. See `data/chains.Chain.reward_tech`.
    """
    if not getattr(chain, "reward_tech", None):
        return None
    return TECH_BY_ID.get(chain.reward_tech)


def begin(game, chain_id: str, system) -> dict:
    """Take on a commission and post its first stage."""
    chain = CHAINS_BY_ID.get(chain_id)
    if chain is None:
        return {"ok": False, "why": "No such commission."}
    ok, why = next(((o, w) for c, o, w in offered(game, system) if c.id == chain_id),
                   (False, "Not on offer here."))
    if not ok:
        return {"ok": False, "why": why}

    held = Commission(chain_id=chain.id)
    ensure(game).append(held)
    contract = _post(game, held, system)
    if contract is None:
        game.commissions.remove(held)
        return {"ok": False, "why": "Nothing suitable to send you after."}
    game.add_log(f"{chain.name}: commissioned by "
                 f"{chain.issuer.title()}.", "good")
    return {"ok": True, "chain": chain, "contract": contract}


def _post(game, held: Commission, system):
    """Turn the current stage into a live, already-accepted contract."""
    chain = held.definition
    if held.stage >= len(chain.stages):
        return None
    stage = chain.stages[held.stage]
    rng = game.rng(f"chain-{chain.id}-{held.stage}")
    d = KINDS[stage.kind]
    contract = contract_sim.Contract(
        id=next(_uid), kind=stage.kind, issuer=chain.issuer,
        issued_at=system.id, title="", posting=stage.posting,
        rep=d.rep + 2, deadline=game.day + stage.days,
        chain=chain.id, stage=held.stage)
    if not contract_sim.shape(rng, game, system, contract, chain.issuer,
                              scale=stage.scale):
        return None
    contract.reward = round(contract.reward * stage.pay)
    contract.title = f"{stage.title} — {contract.title}"
    contract.accepted = True
    game.contracts.append(contract)
    held.contract_id = contract.id
    return contract


# ── the chain advancing ────────────────────────────────────────────────────

def on_contract_done(game, contract) -> list[tuple[str, str]]:
    """Called when a contract finishes. Advances its commission, if it has one."""
    chain_id = getattr(contract, "chain", None)
    if not chain_id:
        return []
    held = state_of(game, chain_id)
    if held is None or held.done or held.failed:
        return []
    chain = held.definition
    stage = chain.stages[min(held.stage, len(chain.stages) - 1)]
    held.history.append(stage.outcome)
    events = [("good", f"{chain.name}: {stage.outcome}")]

    held.stage += 1
    held.contract_id = None
    if held.stage >= len(chain.stages):
        events.extend(_finish(game, held))
        return events

    system = game.galaxy.systems[contract.issued_at]
    if _post(game, held, system) is None:
        held.failed = True
        events.append(("warn", f"{chain.name} has stalled — there is nothing "
                               "further they can send you after."))
    return events


def _finish(game, held: Commission) -> list[tuple[str, str]]:
    chain = held.definition
    held.done = True
    game.credits += chain.reward_credits
    game.adjust_rep(chain.issuer, chain.reward_rep)
    if chain.reward_tech and chain.reward_tech not in game.research.unlocked:
        game.research.unlocked.append(chain.reward_tech)
    for event in chain.feels:
        loyalty.record(game, event)
    loyalty.record(game, "commission_done")
    game.recompute()
    return [("good", f"{chain.name} is complete. {chain.reward_note}")]


def on_contract_failed(game, contract) -> list[tuple[str, str]]:
    chain_id = getattr(contract, "chain", None)
    if not chain_id:
        return []
    held = state_of(game, chain_id)
    if held is None or held.done or held.failed:
        return []
    held.failed = True
    held.contract_id = None
    game.adjust_rep(held.definition.issuer, -8)
    return [("bad", f"{held.definition.name} has been withdrawn. They will not "
                    "put it to you again.")]


def current_contract(game, held: Commission):
    if held.contract_id is None:
        return None
    return next((c for c in game.contracts if c.id == held.contract_id), None)


def summary(game) -> dict:
    held = ensure(game)
    return {"active": len(active(game)), "done": len(completed(game)),
            "failed": len([c for c in held if c.failed]), "total": len(CHAINS)}
