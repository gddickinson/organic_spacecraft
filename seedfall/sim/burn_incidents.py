"""What goes wrong on a burn: the incident table and its one roll.

Split out of `sim/flight.py` at 498 lines. `flight.travel_to` decides
*whether* something goes wrong (the burn's own risk); this decides *what*,
and makes sure what the log says was lost is what was actually lost.
"""

from __future__ import annotations

from .ship import add_cargo, add_heat, apply_damage


_INCIDENTS = [
    ("Dust at closing speed", "A stream of grains the survey did not plot. The "
     "epidermis takes it, which is what it is for.", "damage"),
    ("Radiator flutter", "A bloom lobe fails to deploy cleanly and the hull runs "
     "hot for a week.", "heat"),
    ("Attitude fault", "The platform drifts mid-burn and the correction costs "
     "reaction mass nobody budgeted.", "fuel"),
    ("Debris field", "Somebody else's bad day, spread across four hundred "
     "kilometres of the approach.", "damage"),
]


def _incident(game, rng, burn) -> dict:
    name, text, effect = rng.pick(_INCIDENTS)
    detail = ""
    if effect == "damage":
        dmg = rng.int(10, 40)
        apply_damage(game.ship, dmg)
        detail = f"{dmg} points off the hull."
    elif effect == "heat":
        add_heat(game.ship, rng.int(10, 26), game.ship_stats.heat_cap)
        detail = "The hull is running hot."
    else:
        # Report what was actually taken, not what was rolled. A hull with
        # three tonnes aboard and an eight-tonne fault was told "8 t of
        # reaction mass gone" and had lost three — one in five of these.
        want = rng.int(2, 8)
        lost = min(want, game.ship.cargo.get("volatiles", 0))
        add_cargo(game.ship, "volatiles", -lost)
        detail = (f"{lost:g} t of reaction mass gone."
                  if lost > 0 else "The tank was already dry.")
    game.add_log(f"{name}: {detail}", "warn")
    return {"name": name, "text": text, "detail": detail}
