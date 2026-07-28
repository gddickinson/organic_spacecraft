"""Defensive abilities fired from the bridge mid-engagement.

Each is a fitted part earning its slot: a blastema flooding a wound, sphincter
bulkheads giving up a compartment to save the rest, a carapace turned into the
fire, an epidermis shed whole. They are on cooldowns because none of them is
free, and all of them are — in the documents — things a hull does once and then
needs time before it can do again.

These return their log line rather than writing it, so the module has no
dependency back on the battle's own plumbing.
"""

from __future__ import annotations


def use_ability(battle, side, ability_id: str, rng) -> tuple[bool, str, str]:
    """Fire an ability. Returns ``(fired, message, kind)``."""
    if side.cd.get(ability_id, 0) > 0:
        return False, "", ""
    ability = next((p.ability for p in side.st.abilities
                    if p.ability.id == ability_id), None)
    if ability is None:
        return False, "", ""
    side.cd[ability_id] = ability.cd

    if ability_id == "regrow":
        healed = 0.0
        for layer in reversed(side.ship.layers):
            if layer.hp >= layer.max:
                continue
            gain = min(layer.max - layer.hp, layer.max * 0.30)
            layer.hp += gain
            healed = gain
            break
        return True, (f"floods a blastema into the wound — {round(healed)} "
                      "regrown."), "good"

    if ability_id == "seal":
        side.st.armour += 4
        return True, ("irises its bulkheads shut and gives up the breached "
                      "compartment."), "good"

    if ability_id == "interpose":
        side.interpose = 2
        return True, "turns its carapace into the fire.", "good"

    if ability_id == "shed":
        epidermis = side.ship.layers[0]
        epidermis.hp = min(epidermis.max, epidermis.hp + round(epidermis.max * 0.5))
        side.braced = True
        return True, ("sheds its epidermis whole and grows the next one behind "
                      "it."), "good"

    if ability_id == "vent":
        side.ship.heat = max(0.0, side.ship.heat - 45)
        return True, "dumps its heat sinks. The hull glows.", "good"

    if ability_id == "jam":
        other = battle.enemy if side is battle.player else battle.player
        other.jammed = 2
        return True, "floods the guidance bands with nonsense.", "good"

    return False, "", ""
