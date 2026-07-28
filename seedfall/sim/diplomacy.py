"""Diplomacy — actions, treaties, and how the powers regard one another.

Your standing with a faction is one axis. The other is how the factions feel
about each other, which you can move by taking sides, by brokering, and by being
seen to be worth listening to. Concord requires both.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from ..core.save import register
from ..data.diplomacy import (ACTIONS_BY_ID, AGENDAS, CONCORD_RELATION,
                              CONCORD_STANDING, INITIAL_RELATIONS,
                              RELATION_BANDS)
from ..data.factions import FACTIONS_BY_ID

POWERS = ("charter", "concordat", "freeholds", "sanhedrin")


@register
@dataclass
class DiplomaticState:
    relations: dict[str, float] = field(default_factory=dict)
    treaties: list[str] = field(default_factory=list)
    cooldowns: dict[str, int] = field(default_factory=dict)   # "action|faction" -> day
    favours: dict[str, int] = field(default_factory=dict)


def _key(a: str, b: str) -> str:
    return "|".join(sorted((a, b)))


def ensure(game) -> DiplomaticState:
    """Created on first use so existing saves keep working."""
    if getattr(game, "diplomacy", None) is None:
        state = DiplomaticState()
        for (a, b), value in INITIAL_RELATIONS.items():
            state.relations[_key(a, b)] = float(value)
        game.diplomacy = state
    return game.diplomacy


# ── relations between the powers ───────────────────────────────────────────

def relation(game, a: str, b: str) -> float:
    return ensure(game).relations.get(_key(a, b), 0.0)


def shift_relation(game, a: str, b: str, delta: float) -> float:
    state = ensure(game)
    k = _key(a, b)
    state.relations[k] = max(-100.0, min(100.0, state.relations.get(k, 0.0) + delta))
    return state.relations[k]


def relation_band(value: float) -> tuple[str, str]:
    out = RELATION_BANDS[0]
    for band in RELATION_BANDS:
        if value >= band[0]:
            out = band
    return out[1], out[2]


def rivals_of(game, faction: str) -> list[str]:
    """Powers this one is currently on bad terms with."""
    return [p for p in POWERS
            if p != faction and relation(game, faction, p) < -15]


# ── treaties ───────────────────────────────────────────────────────────────

def has_treaty(game, faction: str) -> bool:
    return faction in ensure(game).treaties


def treaty_bonus(game) -> float:
    """Signed treaties make everyone slightly easier to trade with."""
    return 0.03 * len(ensure(game).treaties)


# ── acting ─────────────────────────────────────────────────────────────────

def available(game, faction: str) -> list[tuple]:
    """(action, ok, reason) for every diplomatic move against this faction."""
    state = ensure(game)
    rep = game.rep.get(faction, 0)
    out = []
    for action in ACTIONS_BY_ID.values():
        ok, why = True, ""
        ready = state.cooldowns.get(f"{action.id}|{faction}", -9999)
        if game.day < ready:
            ok, why = False, f"Not for another {ready - game.day} day(s)."
        elif rep < action.min_rep:
            ok, why = False, f"They will not hear it below {action.min_rep:g} standing."
        elif action.id == "treaty" and has_treaty(game, faction):
            ok, why = False, "Already signed."
        elif action.cost_credits and game.credits < action.cost_credits:
            ok, why = False, f"Costs {action.cost_credits:,} credits."
        elif action.cost_goods:
            cid, amount = action.cost_goods
            held = game.ship.cargo.get(cid, 0) + game.stores.get(cid, 0)
            if held < amount:
                ok, why = False, f"Needs {amount} {cid}."
        out.append((action, ok, why))
    return out


def _spend(game, action) -> None:
    if action.cost_credits:
        game.credits -= action.cost_credits
    if action.cost_goods:
        cid, amount = action.cost_goods
        from_ship = min(game.ship.cargo.get(cid, 0), amount)
        if from_ship:
            game.ship.cargo[cid] = game.ship.cargo.get(cid, 0) - from_ship
            if game.ship.cargo[cid] <= 0.0001:
                game.ship.cargo.pop(cid, None)
        rest = amount - from_ship
        if rest > 0:
            game.stores[cid] = max(0.0, game.stores.get(cid, 0) - rest)


def perform(game, action_id: str, faction: str, other: str | None = None) -> dict:
    """Carry out a diplomatic move. Returns what happened."""
    state = ensure(game)
    action = ACTIONS_BY_ID.get(action_id)
    if action is None:
        return {"ok": False, "why": "No such overture."}
    ok, why = next(((o, w) for a, o, w in available(game, faction)
                    if a.id == action_id), (False, "Unavailable."))
    if not ok:
        return {"ok": False, "why": why}

    _spend(game, action)
    state.cooldowns[f"{action_id}|{faction}"] = game.day + action.cooldown
    lines: list[str] = []
    gain = action.gain * (1 + game.ship_stats.diplomacy)

    if action_id == "denounce":
        if other is None:
            return {"ok": False, "why": "Denounce whom?"}
        game.adjust_rep(other, -14)
        # Everyone who dislikes the denounced thinks better of you.
        for power in POWERS:
            if power == other:
                continue
            if relation(game, power, other) < -15:
                game.adjust_rep(power, 6)
                lines.append(f"{FACTIONS_BY_ID[power].short} appreciated it.")
        shift_relation(game, faction, other, -8)
        lines.append(f"{FACTIONS_BY_ID[other].short} will remember this.")
    elif action_id == "broker":
        if other is None:
            return {"ok": False, "why": "Broker between whom?"}
        if game.rep.get(other, 0) < 40:
            return {"ok": False, "why": f"{FACTIONS_BY_ID[other].short} would not "
                                        "sit down at your invitation."}
        before = relation(game, faction, other)
        after = shift_relation(game, faction, other, 28)
        game.adjust_rep(faction, gain)
        game.adjust_rep(other, gain)
        lines.append(f"{FACTIONS_BY_ID[faction].short} and "
                     f"{FACTIONS_BY_ID[other].short}: {before:+.0f} → {after:+.0f}.")
    elif action_id == "treaty":
        state.treaties.append(faction)
        game.adjust_rep(faction, gain)
        # Signing with one power cools you slightly with its enemies.
        for rival in rivals_of(game, faction):
            game.adjust_rep(rival, -4)
        lines.append("Signed. Berthing, charts, and a clause about the Bloom.")
    else:
        game.adjust_rep(faction, gain)
        lines.append(f"{FACTIONS_BY_ID[faction].short} standing +{gain:.0f}.")

    game.add_log(f"{action.name} — {FACTIONS_BY_ID[faction].short}.", "good")
    return {"ok": True, "action": action, "lines": lines}


def agenda_bonus(game, faction: str, commodity: str) -> float:
    """Selling a power what it is chronically short of is worth extra standing."""
    agenda = AGENDAS.get(faction)
    return 1.6 if agenda and agenda.wants == commodity else 1.0


# ── the Concord condition ──────────────────────────────────────────────────

def concord_progress(game) -> dict:
    """Kin with four powers, and those powers not at each other's throats."""
    kin = [p for p in POWERS if game.rep.get(p, 0) >= CONCORD_STANDING]
    pairs = [(a, b) for i, a in enumerate(POWERS) for b in POWERS[i + 1:]]
    at_peace = [(a, b) for a, b in pairs if relation(game, a, b) >= CONCORD_RELATION]
    return {"kin": kin, "kin_need": len(POWERS),
            "peace": at_peace, "peace_need": len(pairs),
            "done": len(kin) == len(POWERS) and len(at_peace) == len(pairs)}


def summary(game) -> dict:
    state = ensure(game)
    return {"treaties": list(state.treaties),
            "relations": {f"{a}|{b}": relation(game, a, b)
                          for i, a in enumerate(POWERS) for b in POWERS[i + 1:]}}
