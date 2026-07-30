"""Defensive abilities fired from the bridge mid-engagement.

Each is a fitted part earning its slot: a blastema flooding a wound, sphincter
bulkheads giving up a compartment to save the rest, a carapace turned into the
fire, an epidermis shed whole. They are on cooldowns because none of them is
free, and all of them are — in the documents — things a hull does once and then
needs time before it can do again.

These return their log line rather than writing it, so the module has no
dependency back on the battle's own plumbing.

**Two things were wrong, and the project's own standing questions found both.**

*Is it bounded?* `seal` did `side.st.armour += 4` with a four-turn cooldown and
nothing else, so a captain who pressed it whenever it came up went from **2
armour to 34 over eight firings**, and 43 over a long engagement, without limit.
Its own sentence says it "gives up the breached compartment" — which presupposes
a breach, and is finite, because a hull has six layers and can only give up the
ones it can afford to lose. The opening NAVIS carries the part, so this was
reachable in a captain's first fight.

*Does the screen say what it will do?* The button showed the part's flavour text
and a cooldown, so the one control on that panel with a permanent effect on the
hull was also the only one naming no number — on a screen where every helm order
prints its consequence. `preview` is the door now, and `use_ability` does what it
says.
"""

from __future__ import annotations

#: Armour gained per compartment irised off. Four, unchanged — what is new is
#: that it can be had once per compartment, so `SEAL_ARMOUR × the layers a hull
#: can afford to lose` is the whole of it rather than the opening instalment.
SEAL_ARMOUR = 4.0

#: What `regrow` puts back, as a share of the layer's own maximum.
REGROW_SHARE = 0.30

#: What `shed` puts back on the epidermis, as a share of its maximum.
SHED_SHARE = 0.5

#: Heat `vent` dumps.
VENT_HEAT = 45.0

#: Turns `interpose` and `jam` hold for.
HOLDS_FOR = 2


def sealable(side):
    """The compartment `seal` could give up, or None.

    The outermost layer that is holed through, is not the pressure vessel — you
    cannot iris off the compartment the crew is breathing — and has not been
    given up already. That last clause is the bound: `side.sealed` records what
    has gone, so the same compartment cannot be sold twice.
    """
    given = set(getattr(side, "sealed", None) or ())
    for layer in side.ship.layers:
        if layer.critical or layer.name in given:
            continue
        if layer.hp <= 0:
            return layer
    return None


def preview(battle, side, ability_id: str) -> dict:
    """What firing this would do, and whether it can be fired at all.

    **The one door.** `use_ability` asks this and then does what it said, so the
    button cannot promise what the bridge will not deliver — the same rule the
    helm orders, the ground options and the hail all follow.
    """
    ability = next((p.ability for p in side.st.abilities
                    if p.ability.id == ability_id), None)
    if ability is None:
        return {"can": False, "why": "Nothing aboard does that.", "lines": [],
                "cd": 0, "name": ability_id}
    told = {"can": True, "why": "", "lines": [], "cd": ability.cd,
            "name": ability.name}
    waiting = side.cd.get(ability_id, 0)
    if waiting > 0:
        told.update(can=False,
                    why=f"{ability.name} is recycling — {waiting} turn(s).")

    if ability_id == "regrow":
        hurt = next((l for l in reversed(side.ship.layers) if l.hp < l.max), None)
        if hurt is None:
            told.update(can=False, why="Nothing is damaged to regrow.")
        else:
            gain = min(hurt.max - hurt.hp, hurt.max * REGROW_SHARE)
            told["lines"].append(f"{hurt.name} +{round(gain)}")
    elif ability_id == "seal":
        gone = sealable(side)
        if gone is None:
            told.update(can=False,
                        why="No compartment is open to give up — this seals a "
                            "hole, it does not make armour.")
        else:
            told["lines"].append(f"gives up {gone.name}")
            told["lines"].append(f"armour {side.st.armour:.0f} → "
                                 f"{side.st.armour + SEAL_ARMOUR:.0f}")
    elif ability_id == "interpose":
        told["lines"].append(f"carapace into the fire, {HOLDS_FOR} turns")
    elif ability_id == "shed":
        skin = side.ship.layers[0]
        gain = min(skin.max - skin.hp, round(skin.max * SHED_SHARE))
        told["lines"].append(f"{skin.name} +{round(gain)}")
        told["lines"].append("braced this turn")
    elif ability_id == "vent":
        told["lines"].append(f"heat {side.ship.heat:.0f} → "
                             f"{max(0.0, side.ship.heat - VENT_HEAT):.0f}")
    elif ability_id == "jam":
        told["lines"].append(f"their fire control blind, {HOLDS_FOR} turns")
    else:
        told.update(can=False, why="Nothing aboard does that.")
    return told


def use_ability(battle, side, ability_id: str, rng) -> tuple[bool, str, str]:
    """Fire an ability. Returns ``(fired, message, kind)``.

    Asks `preview` first, and **only spends the cooldown if it fires**. The
    cooldown used to be set before anything was decided, so an ability that could
    do nothing still put itself out of action and returned quietly.
    """
    told = preview(battle, side, ability_id)
    if not told["can"]:
        return False, "", ""
    side.cd[ability_id] = told["cd"]

    if ability_id == "regrow":
        for layer in reversed(side.ship.layers):
            if layer.hp >= layer.max:
                continue
            gain = min(layer.max - layer.hp, layer.max * REGROW_SHARE)
            layer.hp += gain
            return True, (f"floods a blastema into the wound — {round(gain)} "
                          "regrown."), "good"
        return False, "", ""

    if ability_id == "seal":
        gone = sealable(side)
        if gone is None:
            return False, "", ""
        if getattr(side, "sealed", None) is None:
            side.sealed = []
        side.sealed.append(gone.name)
        side.st.armour += SEAL_ARMOUR
        return True, (f"irises its bulkheads shut and gives up {gone.name} — "
                      f"armour {side.st.armour:.0f}."), "good"

    if ability_id == "interpose":
        side.interpose = HOLDS_FOR
        return True, "turns its carapace into the fire.", "good"

    if ability_id == "shed":
        epidermis = side.ship.layers[0]
        epidermis.hp = min(epidermis.max,
                           epidermis.hp + round(epidermis.max * SHED_SHARE))
        side.braced = True
        return True, ("sheds its epidermis whole and grows the next one behind "
                      "it."), "good"

    if ability_id == "vent":
        side.ship.heat = max(0.0, side.ship.heat - VENT_HEAT)
        return True, "dumps its heat sinks. The hull glows.", "good"

    if ability_id == "jam":
        other = battle.enemy if side is battle.player else battle.player
        other.jammed = HOLDS_FOR
        return True, "floods the guidance bands with nonsense.", "good"

    return False, "", ""
