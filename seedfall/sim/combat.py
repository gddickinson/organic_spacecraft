"""Tactical combat on a five-band range track.

Two things make this different from the usual exchange of fire. First, damage
lands on a stack of named layers — a grown hull sheds its epidermis, gives up its
rind, and only really cares once the pneumostat opens. Second, killing the other
ship is not the only way to win: every combatant has a resolve, and a hull that
simply refuses to die will break the other side's will to keep paying for the
ammunition. TESTUDO doctrine, fitted as a mechanic.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from ..core.util import clamp
from ..data.part_types import BANDS
from ..data.parts import part
from .ship import (Ship, Stats, add_cargo, hull_pct, is_breached, is_destroyed,
                   stats)

VARIANCE = (0.82, 1.18)
MAX_TURNS = 40
GRIND_TURN = 9      # turns of clean fighting before either side starts wanting out

#: personality -> (close preference, fire chance, flee chance)
STYLES = {
    "aggressive": (0.55, 0.90, 0.05),
    "balanced": (0.35, 0.80, 0.18),
    "cautious": (0.15, 0.65, 0.40),
    "feral": (0.80, 0.95, 0.00),
}


@dataclass
class Side:
    ship: Ship
    st: Stats
    personality: str = "balanced"
    resolve: float = 100.0
    blind: int = 0
    jammed: int = 0
    grappled: int = 0
    interpose: int = 0
    braced: bool = False
    cd: dict = field(default_factory=dict)
    dealt: float = 0.0
    taken: float = 0.0


@dataclass
class Battle:
    player: Side
    enemy: Side
    enemy_name: str
    enemy_faction: str | None
    band: int = 3
    turn: int = 1
    over: bool = False
    result: str | None = None
    log: list = field(default_factory=list)
    intro: str = ""
    loot: dict = field(default_factory=dict)
    no_parley: bool = False
    fleeable: bool = True
    rep: float = 0.0
    bonuses: dict = field(default_factory=dict)
    officers: list = field(default_factory=list)
    game: object | None = None      # for Bloom adaptation; never saved


def start(player_ship, player_stats, enemy, *, bonuses=None, officers=(),
          rep=0.0, no_parley=False, band=3, game=None) -> Battle:
    b = Battle(
        player=Side(player_ship, player_stats, "player"),
        enemy=Side(enemy["ship"], enemy["stats"], enemy.get("personality", "balanced")),
        enemy_name=enemy.get("name", "Unknown contact"),
        enemy_faction=enemy.get("faction"),
        band=band, no_parley=no_parley, rep=rep,
        bonuses=dict(bonuses or {}), officers=list(officers), game=game,
        loot=dict(enemy.get("loot", {})),
    )
    b.enemy.resolve = enemy.get("resolve", 100)
    _say(b, f"{b.enemy_name} closes to {BANDS[b.band].lower()} range.", "warn")
    return b


def _say(b: Battle, text: str, kind: str = "") -> None:
    b.log.append((b.turn, text, kind))
    if len(b.log) > 220:
        b.log.pop(0)


def _who(b: Battle, s: Side) -> str:
    return b.player.ship.name if s is b.player else b.enemy_name


# ── shooting ───────────────────────────────────────────────────────────────

def _fire(b: Battle, frm: Side, to: Side, weapon_id: str, rng) -> None:
    w = part(weapon_id)
    if w is None or w.wpn is None:
        return
    pen = w.wpn.bears_at(b.band)
    if pen > 0.6:
        _say(b, f"{_who(b, frm)} cannot bring the {w.name} to bear at this range.", "dim")
        return

    if w.wpn.ammo:
        cid, per = w.wpn.ammo
        if frm.ship.cargo.get(cid, 0) < per:
            _say(b, f"{_who(b, frm)}: the {w.name} is dry — no {cid} in the hold.", "dim")
            return
        add_cargo(frm.ship, cid, -per)

    frm.ship.heat += w.wpn.heat
    seeking = "seeking" in w.wpn.traits

    if seeking and to.st.flak > 0 and rng.chance(clamp(0.22 * to.st.flak, 0, 0.72)):
        _say(b, f"{_who(b, to)}'s point defence swats the {w.name} round out of the sky.",
             "dim")
        return

    evade = 0.0 if seeking else to.st.evade + (0.08 if to.braced else 0)
    acc = (frm.st.accuracy + w.wpn.acc - pen - frm.blind * 0.3 - frm.jammed * 0.25
           + (frm.ship.morale - 0.7) * 0.15)
    if not rng.chance(clamp(acc - evade, 0.05, 0.95)):
        _say(b, f"{w.name} misses {_who(b, to)}.", "dim")
        return

    dmg = w.wpn.dmg * rng.float(*VARIANCE)
    if to.braced:
        dmg *= 0.72
    if to.interpose > 0:
        dmg *= 0.45
        to.interpose -= 1
        _say(b, f"{_who(b, to)} interposes its carapace.", "dim")
    # Armour soaks, but never entirely: something always gets through, or two
    # well-armoured hulls would shoot at each other until the sun went out.
    dmg = max(w.wpn.dmg * 0.15, dmg - to.st.armour)

    # Bloom tissue remembers what killed the last lineage. Keep using one kind
    # of weapon and it stops working; vary the loadout and the memory fades.
    if b.game is not None and b.enemy_faction == "bloom" and to is b.enemy:
        from . import bloom as bloom_sim
        resist = bloom_sim.resistance(b.game, w.family)
        if resist > 0:
            dmg *= 1 - resist
            if rng.chance(0.25):
                say(b, f"The tissue shrugs off much of the {w.name} — it has "
                       f"seen this before.", "warn")

    dealt = _apply_to_layers(b, to, dmg, w.wpn.traits, rng)
    if b.game is not None and b.enemy_faction == "bloom" and to is b.enemy:
        from . import bloom as bloom_sim
        bloom_sim.record_damage(b.game, w.family, dealt)
    frm.dealt += dealt
    to.taken += dealt
    to.resolve -= dealt * 0.10
    frm.resolve += dealt * 0.03
    _say(b, f"{w.name} hits {_who(b, to)} for {round(dealt)}.",
         "good" if frm is b.player else "bad")
    _apply_traits(b, frm, to, w, rng)


def _salvo(b: Battle, frm: Side, to: Side, rng) -> None:
    """Everything that can bear, fired together.

    This is what weapon mounts are for: a battleship's five hardpoints only
    matter if they all speak at once. The cost is heat and ammunition, which is
    why a single aimed shot stays a real option.
    """
    bearing = [w for w in frm.st.weapons if w.wpn.bears_at(b.band) <= 0.5]
    if not bearing:
        _say(b, f"{_who(b, frm)} has nothing that will bear at this range.", "dim")
        return
    _say(b, f"{_who(b, frm)} fires everything that will bear — "
            f"{len(bearing)} mount(s).", "dim")
    for w in bearing:
        if is_destroyed(to.ship):
            break
        _fire(b, frm, to, w.id, rng)


def _apply_to_layers(b: Battle, to: Side, dmg: float, traits, rng) -> float:
    layers = to.ship.layers
    idx = next((i for i, l in enumerate(layers) if l.hp > 0), -1)
    if idx < 0:
        return 0.0
    if "pierce" in traits:
        nxt = next((i for i, l in enumerate(layers) if i > idx and l.hp > 0), -1)
        if nxt > 0:
            idx = nxt

    left, total, first = dmg, 0.0, True
    while left > 0.5 and idx < len(layers):
        L = layers[idx]
        if L.hp <= 0:
            idx += 1
            continue
        mult = 2 if (first and "ablate" in traits) else 1
        applied = min(L.hp, left * mult)
        L.hp -= applied
        total += applied / mult
        left -= applied / mult
        if L.hp <= 0:
            _say(b, f"— {L.name} of {_who(b, to)} is gone.", "warn")
            if L.critical:
                _breach(b, to, rng)
            if L.life:
                _say(b, f"— {_who(b, to)} is on bottled air.", "warn")
        first = False
        idx += 1
    return total


def _breach(b: Battle, to: Side, rng) -> None:
    lost = max(1, round(to.ship.crew * rng.float(0.04, 0.14) * (1 - to.st.crew_guard)))
    to.ship.crew = max(0, to.ship.crew - lost)
    to.resolve -= 18
    to.ship.morale = max(0.0, to.ship.morale - 0.12)
    _say(b, f"PRESSURE BREACH on {_who(b, to)} — {lost} lost to vacuum.", "bad")


def _apply_traits(b: Battle, frm: Side, to: Side, w, rng) -> None:
    t = w.wpn.traits
    if "blind" in t:
        to.blind = 2
        _say(b, f"{_who(b, to)} is dazzled.", "dim")
    if "grapple" in t:
        to.grappled = 2
        _say(b, f"Tendrils have hold of {_who(b, to)}.", "dim")
    if "emp" in t:
        to.ship.heat += 8
        if rng.chance(0.35):
            _disable(b, to, rng)
    if "board" in t and rng.chance(0.42):
        _disable(b, to, rng, "Spores have rooted in")
    if "plunder" in t:
        carried = [(cid, n) for cid, n in to.ship.cargo.items() if n > 0]
        if carried:
            cid, n = rng.pick(carried)
            take = min(n, max(1, round(n * 0.3)))
            add_cargo(to.ship, cid, -take)
            add_cargo(frm.ship, cid, take)
            _say(b, f"{round(take)} t of {cid} torn out of {_who(b, to)}'s hold.", "warn")


def _disable(b: Battle, to: Side, rng, verb: str = "A surge knocks out") -> None:
    live = [pid for pid in to.ship.fitted if pid not in to.ship.disabled and part(pid)]
    if not live:
        return
    victim = rng.pick(live)
    to.ship.disabled.append(victim)
    to.st = stats(to.ship, b.bonuses, b.officers if to is b.player else ())
    _say(b, f"{verb} {_who(b, to)}'s {part(victim).name}.", "warn")


# ── abilities ──────────────────────────────────────────────────────────────

def use_ability(b: Battle, s: Side, ability_id: str, rng) -> bool:
    if s.cd.get(ability_id, 0) > 0:
        return False
    if not any(p.ability.id == ability_id for p in s.st.abilities):
        return False
    ab = next(p.ability for p in s.st.abilities if p.ability.id == ability_id)
    s.cd[ability_id] = ab.cd

    if ability_id == "regrow":
        healed = 0.0
        for L in reversed(s.ship.layers):
            if L.hp >= L.max:
                continue
            gain = min(L.max - L.hp, L.max * 0.30)
            L.hp += gain
            healed += gain
            break
        _say(b, f"{_who(b, s)} floods a blastema into the wound — "
                f"{round(healed)} regrown.", "good")
    elif ability_id == "seal":
        s.st.armour += 4
        _say(b, f"{_who(b, s)} irises its bulkheads shut and gives up the "
                "breached compartment.", "good")
    elif ability_id == "interpose":
        s.interpose = 2
        _say(b, f"{_who(b, s)} turns its carapace into the fire.", "good")
    elif ability_id == "shed":
        ep = s.ship.layers[0]
        ep.hp = min(ep.max, ep.hp + round(ep.max * 0.5))
        s.braced = True
        _say(b, f"{_who(b, s)} sheds its epidermis whole and grows the next one "
                "behind it.", "good")
    elif ability_id == "vent":
        s.ship.heat = max(0.0, s.ship.heat - 45)
        _say(b, f"{_who(b, s)} dumps its heat sinks. The hull glows.", "good")
    elif ability_id == "jam":
        (b.enemy if s is b.player else b.player).jammed = 2
        _say(b, f"{_who(b, s)} floods the guidance bands with nonsense.", "good")
    else:
        return False
    return True


# ── turn resolution ────────────────────────────────────────────────────────

def _enemy_turn(b: Battle, rng) -> None:
    e = b.enemy
    close, fire_p, flee_p = STYLES.get(e.personality, STYLES["balanced"])

    if e.resolve <= 0 or (hull_pct(e.ship) < 0.25 and rng.chance(flee_p)):
        if not e.grappled:
            _finish(b, "driven-off")
            return
        _say(b, f"{b.enemy_name} tries to break away and cannot — the grapple holds.",
             "good")

    if e.ship.heat > e.st.heat_cap and any(p.ability.id == "vent" for p in e.st.abilities):
        if use_ability(b, e, "vent", rng):
            return
    if hull_pct(e.ship) < 0.5 and rng.chance(0.55):
        for aid in ("regrow", "interpose", "seal"):
            if any(p.ability.id == aid for p in e.st.abilities) and not e.cd.get(aid):
                if use_ability(b, e, aid, rng):
                    return

    usable = [w for w in e.st.weapons if w.wpn.bears_at(b.band) <= 0.25]
    if usable and rng.chance(fire_p):
        # Hot or badly hurt, they pick one shot; otherwise they empty the broadside.
        restrained = e.ship.heat > e.st.heat_cap * 0.7 or rng.chance(0.25)
        if restrained or len(usable) == 1:
            _fire(b, e, b.player, rng.pick(usable).id, rng)
        else:
            _salvo(b, e, b.player, rng)
        return

    if e.st.weapons:
        want = round(sum((w.wpn.bands[0] + w.wpn.bands[1]) / 2
                         for w in e.st.weapons) / len(e.st.weapons))
    else:
        want = 4
    b.band = int(clamp(b.band + (-1 if want < b.band else 1), 0, 4))
    _say(b, f"{b.enemy_name} manoeuvres to {BANDS[b.band].lower()} range.", "dim")


def take_turn(b: Battle, action: dict, rng) -> Battle:
    """Run one full exchange. ``action`` is the player's choice."""
    if b.over:
        return b
    b.player.braced = False
    kind = action.get("type")

    if kind == "fire":
        _fire(b, b.player, b.enemy, action["weapon_id"], rng)
    elif kind == "salvo":
        _salvo(b, b.player, b.enemy, rng)
    elif kind == "ability":
        use_ability(b, b.player, action["id"], rng)
    elif kind == "move":
        if b.player.grappled:
            _say(b, "The grapple holds you at contact range.", "warn")
        else:
            b.band = int(clamp(b.band + action["dir"], 0, 4))
            _say(b, f"You manoeuvre to {BANDS[b.band].lower()} range.")
    elif kind == "brace":
        b.player.braced = True
        b.player.resolve += 6
        b.player.ship.heat = max(0.0, b.player.ship.heat - b.player.st.vent)
        _say(b, "You turn the thickest tissue into the fire and hold.", "good")
    elif kind == "hail":
        return _hail(b, rng)
    elif kind == "flee":
        return _flee(b, rng)

    if not b.over and is_destroyed(b.enemy.ship):
        return _finish(b, "destroyed")
    if not b.over:
        _enemy_turn(b, rng)
    if not b.over and is_destroyed(b.player.ship):
        return _finish(b, "lost")
    if not b.over:
        _end_of_turn(b, rng)
    return b


def _end_of_turn(b: Battle, rng) -> None:
    for s in (b.player, b.enemy):
        s.ship.heat = max(0.0, s.ship.heat - s.st.vent)
        if s.ship.heat > s.st.heat_cap:
            over = s.ship.heat - s.st.heat_cap
            _say(b, f"{_who(b, s)} is overheating — systems faulting.", "warn")
            s.resolve -= over * 0.3
            if rng.chance(0.25):
                _disable(b, s, rng, "Thermal shutdown takes")
        if is_breached(s.ship):
            s.resolve -= 6
        s.blind = max(0, s.blind - 1)
        s.jammed = max(0, s.jammed - 1)
        s.grappled = max(0, s.grappled - 1)
        for k in list(s.cd):
            s.cd[k] = max(0, s.cd[k] - 1)
        # Living hulls close wounds even mid-fight, slowly.
        if s.st.regen > 0:
            for L in reversed(s.ship.layers):
                if 0 < L.hp < L.max:
                    L.hp = min(L.max, L.hp + L.max * L.regen * s.st.regen * 0.5)
                    break

    b.turn += 1
    # Nobody fights forever. Past a dozen turns without resolution the
    # ammunition and the heat stop being worth it. It starts late deliberately:
    # a decisive hull should still be able to finish the job on its own terms.
    attrition = max(0, b.turn - GRIND_TURN) * 0.45
    b.player.resolve -= attrition * 0.5
    b.enemy.resolve -= attrition

    if b.enemy.resolve <= 0:
        _finish(b, "driven-off")
    elif b.player.resolve <= -40:
        _finish(b, "routed")
    elif b.turn > MAX_TURNS:
        _finish(b, "stalemate")


def _flee(b: Battle, rng) -> Battle:
    if b.player.grappled:
        _say(b, "You are held fast. Nothing to do but cut loose or fight.", "warn")
        return b
    chance = clamp(0.22 + b.band * 0.13
                   + (b.player.st.speed - b.enemy.st.speed) * 0.35
                   + b.player.st.evade * 0.5, 0.05, 0.94)
    if rng.chance(chance):
        return _finish(b, "escaped")
    _say(b, "The burn is not enough — they are still with you.", "warn")
    _enemy_turn(b, rng)
    if is_destroyed(b.player.ship):
        return _finish(b, "lost")
    if not b.over:
        _end_of_turn(b, rng)
    return b


def _hail(b: Battle, rng) -> Battle:
    if b.no_parley:
        _say(b, "The Bloom has nothing to say. It has no one to say it with.", "bad")
        return b
    strength = hull_pct(b.player.ship) - hull_pct(b.enemy.ship)
    chance = clamp(0.18 + b.player.st.diplomacy + b.rep / 260 + strength * 0.3
                   + (0.25 if b.enemy.resolve < 45 else 0), 0.03, 0.92)
    if rng.chance(chance):
        return _finish(b, "parley")
    _say(b, "They hear you out and keep firing.", "warn")
    _enemy_turn(b, rng)
    if is_destroyed(b.player.ship):
        return _finish(b, "lost")
    if not b.over:
        _end_of_turn(b, rng)
    return b


_ENDINGS = {
    "destroyed": "{enemy} comes apart across three compartments.",
    "driven-off": "{enemy} breaks off. Whatever they came for, it was not worth this.",
    "escaped": "You break contact and run dark.",
    "parley": "They stand down. Somebody on that bridge wanted a reason to.",
    "routed": "You have nothing left to hold with. They let you go.",
    "stalemate": "Neither hull can finish the other. You drift apart, both of you "
                 "poorer and neither of you satisfied.",
    "lost": "{player} is lost.",
}


def _finish(b: Battle, result: str) -> Battle:
    b.over = True
    b.result = result
    line = _ENDINGS.get(result, result).format(enemy=b.enemy_name,
                                               player=b.player.ship.name)
    _say(b, line, "bad" if result == "lost" else "good")
    return b


__all__ = ["Battle", "Side", "start", "take_turn", "use_ability", "BANDS",
           "MAX_TURNS", "GRIND_TURN"]
