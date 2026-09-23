"""Putting a party on a world: which craft can, where, and what it takes.

`sim/landing.py` proved the thing this module exists for. A starship cannot
land on a world — a rocky world pulls a hundred and forty times harder than
its drive can push — and that is *why* a landing party goes down in a lander
while the ship holds orbit. The lander itself was a noun with no object: a
word in the expedition's prose, a fixed pad square on its 7×7 zone, and some
biomass out of the hold. Nothing was ever built, bought, flown or lost.

Now it is a craft on the cradle (`data/craft.py`, `sim/craft.py`), and this
is the rule for taking her down:

- **She has to be built for it** (`CraftClass.lands`): legs, a sealed hull,
  something to keep the heat off. A WASP is; a MOTE is; a hull is not.
- **Her drive has to lift her off again.** The same arithmetic the ship's own
  landing uses, against the body's own gravity, with `LIFT_RESERVE` in hand
  for a full hold on the way up. A DORY manages moons and light worlds, a
  WASP anything short of a giant, and a CATAPHRACT the giants.
- **There has to be somewhere to stand** (`landing.kind_allows`) — no gas
  giant, nothing transient.
- **Somebody has to fly her**, on the same Pilot ticket a sortie asks for,
  and that seat is not a passenger's.

What she carries is what the party has: `seats` less the pilot decides how
many go down, `hold_t` what supplies fit, `days` how long she keeps them
alive, and `bays` how many vehicles ride down under the plates. The
expedition reads those instead of assuming them.
"""

from __future__ import annotations

from ..data.craft import LIFT_RESERVE
from . import craft as craft_sim
from . import landing

#: What state a craft is in while she is sitting on a world.
DOWN = "down"
#: The share of her tank a descent and the lift back off take.
DESCENT_SHARE = 0.25


def landers(game) -> list:
    """Every craft aboard built to set down, cradled or already down."""
    return [got for got in craft_sim.aboard(game)
            if craft_sim.kind_of(got).lands]


def on_the_ground(game):
    """The craft that is down on a world, or None."""
    return next((got for got in craft_sim.aboard(game)
                 if got.state == DOWN), None)


def lifts_from(craft) -> float:
    """The heaviest world this class can leave again, in g."""
    return craft_sim.kind_of(craft).thrust_g / LIFT_RESERVE


def party_room(craft) -> int:
    """How many go down besides the pilot."""
    return max(0, craft_sim.kind_of(craft).seats - 1)


def can_land(game, craft, body) -> tuple:
    """May this craft set down on this world? `(ok, why)`."""
    if craft is None:
        return False, "Nothing aboard to go down in."
    kind = craft_sim.kind_of(craft)
    if not kind.lands:
        return False, (f"A {kind.name} is not built to set down — no legs, "
                       "no shield, nothing to lift her off again.")
    if craft.state == DOWN:
        return False, f"{craft.name} is already on the ground."
    if craft.state != "cradled":
        return False, f"{craft.name} is not on the cradle."
    if not landing.kind_allows(body):
        return False, "Nothing to stand on down there."
    pull = float(getattr(body, "gravity", 0.0) or 0.0)
    if pull * LIFT_RESERVE > kind.thrust_g:
        return False, (f"{body.name} pulls {pull:.2f} g and a {kind.name} "
                       f"lifts off {lifts_from(craft):.2f}. She would go "
                       "down and stay down.")
    if craft.hp <= 0:
        return False, f"{craft.name} is wrecked."
    if craft.fuel <= kind.fuel_t * 0.2:
        return False, (f"{craft.name} has {craft.fuel:.1f} t in her — a "
                       "descent and a lift want more than that.")
    if not craft_sim.best_pilot(game, craft):
        return False, ("Nobody aboard holds the certificate for her "
                       f"(Pilot {kind.needs}).")
    if party_room(craft) < 1:
        return False, (f"A {kind.name} seats {kind.seats} — the pilot, and "
                       "nobody else.")
    return True, ""


def in_orbit(game, body=None):
    """The world the hull is in orbit of, or None.

    `flight.hold_at` writes `game.orbit_body` and the Helm's transfer is how
    a captain gets there, so this is a read of a state that has existed
    since the flight layer did — it had simply never been asked by anything
    that puts people on a world. With a body, True when it is *that* world.
    """
    here = getattr(game, "orbit_body", None)
    if body is not None:
        return here == getattr(body, "id", None)
    return next((b for b in game.system.bodies if b.id == here), None)


def says(game, body=None) -> str:
    """One line for a screen: where she is, and what that allows."""
    world = in_orbit(game)
    if world is None:
        return ("Not in orbit of anything. The Helm's transfer takes her to "
                "a world; a party goes down from there.")
    craft = best(game, world)
    if craft is None:
        return f"In orbit of {world.name}. " + why_none(game, world)
    return (f"In orbit of {world.name} — {craft.name} can take "
            f"{party_room(craft)} down.")


def best(game, body):
    """The craft a captain would send down: the one that can, with the most
    room in her. `None` if nothing aboard will do it."""
    able = [got for got in landers(game) if can_land(game, got, body)[0]]
    return max(able, key=party_room, default=None)


def why_none(game, body) -> str:
    """Why there is nothing to go down in — the nearest refusal to the act.

    A captain with a wrecked lander and a gas giant wants the reason that
    belongs to *their* craft, not a generic one, so the answer is the
    refusal of the best lander aboard rather than a sentence about landers
    in general.
    """
    aboard = landers(game)
    if not aboard:
        if craft_sim.aboard(game):
            return ("Nothing on the cradle is built to set down on a world. "
                    "A yard sells landers.")
        return "This hull carries no craft at all, and a hull cannot land."
    return can_land(game, max(aboard, key=party_room), body)[1]


def take_down(game, craft, pilot: str = "") -> dict:
    """She is on the world: off the cradle and on her legs.

    The flight down is not flown minute by minute — `sim/expedition.py` is
    the game that happens once she is down, and the descent is the three
    days `sim/fieldwork` has always charged for it.
    """
    # An officer, not the captain (`craft.who_flies`): a captain who flies
    # the lander is off the bridge for as long as the party is down, and an
    # engagement in those weeks has nobody to give it an order.
    pilot = pilot or craft_sim.who_flies(game, craft)
    craft.state, craft.pilot = DOWN, pilot
    craft.sorties += 1
    kind = craft_sim.kind_of(craft)
    craft.fuel = max(0.0, craft.fuel - kind.fuel_t * DESCENT_SHARE)
    return {"ok": True, "craft": craft, "pilot": pilot,
            "who": craft_sim.name_of(game, pilot)}


def bring_up(game) -> dict:
    """Back to the cradle, whatever happened down there."""
    craft = on_the_ground(game)
    if craft is None:
        return {"ok": False, "why": "Nothing is down."}
    craft.state, craft.pilot = "cradled", ""
    took = craft_sim.top_up(game, craft)
    return {"ok": True, "craft": craft, "fuelled": round(took, 2)}
