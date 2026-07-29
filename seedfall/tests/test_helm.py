"""The burn board: whether the numbers on it are accounted for.

A quoted burn carries a risk, and that risk is the profile's own plus two
surcharges the helm applies on top — `hot_risk` for the heat already in the
hull, and `_heat_risk` for working close to the star. Both were charged
silently in cases the screen had no words for:

- **The heat you are carrying.** A captain fresh off a run of hard burns saw
  coast quoted at 0.34 where its profile says 0.06, with nothing anywhere on
  the screen accounting for the other 0.28.
- **The star at your back.** `_heat_risk` takes the *nearer* of the two ends
  of a leg, so a hull parked at 0.40 AU paid the surcharge on every departure
  — including one nine AU outward — while `path_note` only ever described the
  arrival. Somebody had already fixed the note to talk about the destination,
  for the good reason that a warning identical across every choice is
  furniture; the risk was never brought into line with it.

The claim that matters is the general one, and it is the one that would have
caught both at once: **nothing on the board costs more than its profile says
without the screen saying why.**
"""

from __future__ import annotations

import math

from ..core.state import new_game
from ..data.crossings import CROSSINGS
from ..sim import flight
from ..sim.actions import jump_quote
from ..world.galaxy import distance
from .harness import Suite


def _hot(seed: str, legs: int = 6):
    """A hull fresh off a run of hard burns."""
    game = new_game(seed)
    for leg in range(legs):
        game.ship.cargo["volatiles"] = 9999
        flight.travel_to(game, leg % len(game.system.bodies), "hard")
    return game


def _parked_deep(seed: str):
    """A hull sitting inside the star's heat, wherever it goes next."""
    game = new_game(seed)
    game.ship.cargo["volatiles"] = 9999
    inner = min(range(len(game.system.bodies)),
                key=lambda i: flight.orbit_radius(game.system.bodies[i]))
    flight.travel_to(game, inner, "economy")
    return game


def run(suite: Suite) -> None:
    check = suite.check

    @check("no burn costs more than its profile without the screen saying why")
    def _():
        # The general invariant. Both surcharges were live and unexplained,
        # and this catches either of them coming back — or a third one being
        # added without words.
        # Each surcharge is checked *separately*. Asking only "is there any
        # note at all" was too weak and I caught it being too weak: with the
        # star-arrival warning deleted, the distance note kept the quote
        # looking explained and nothing failed.
        states = [("a cold hull, well out", new_game("cold")),
                  ("fresh off hard burns", _hot("hot")),
                  ("parked inside the star's heat", _parked_deep("deep"))]
        silent, checked = [], 0
        for label, game in states:
            sx, sy = flight.ship_position(game)
            for body in game.system.bodies:
                for burn in flight.BURNS:
                    q = flight.quote(game, body, burn.id)
                    note = flight.path_note(game, body, burn.id) or ""
                    checked += 1
                    # Floors written here, not taken from the module: a
                    # surcharge small enough to be noise may go unsaid, and
                    # that is the point of the thresholds. Raising a threshold
                    # to hide a *large* one is caught by `unstated` below.
                    parts = [
                        ("distance", min(flight.LONG_LEG_CAP,
                                         q["au"] * flight.PER_AU),
                         0.03, "AU on this arc"),
                        ("the star", flight._heat_risk(sx, sy, *q["aim"]),
                         0.01, "from the star"),
                        ("carried heat", flight.hot_risk(game),
                         0.07, "carrying"),
                    ]
                    unstated = 0.0
                    for name, amount, floor, words in parts:
                        if words in note:
                            continue
                        unstated += amount
                        if amount >= floor:
                            silent.append(
                                f"{label}: {burn.id} to {body.name} is "
                                f"charged {amount:+.3f} for {name} and the "
                                f"screen says {note or 'nothing'!r}")
                    assert unstated < 0.09, (
                        f"{label}: {burn.id} to {body.name} carries "
                        f"{unstated:.3f} of risk that nothing on the screen "
                        "accounts for")
                    # And the total has to add up to what is quoted.
                    total = (burn.risk + sum(a for _n, a, _f, _w in parts))
                    assert abs(total - q["risk"]) < 1e-6, (
                        f"{burn.id} to {body.name}: quoted {q['risk']:.3f}, "
                        f"components sum to {total:.3f} — there is a fourth "
                        "surcharge nobody has named")
        assert checked > 30, checked
        assert not silent, (
            f"{len(silent)} unexplained surcharges: " + "; ".join(silent[:3]))
        return (f"{checked} quotes across three hulls, every component "
                "named and the total reconciled")

    @check("the heat in the hull is named, and so is what it costs")
    def _():
        game = _hot("named")
        cap = game.ship_stats.heat_cap
        assert game.ship.heat > cap, (
            f"six hard burns left the hull at {game.ship.heat:.0f} against a "
            f"cap of {cap:.0f} — this hull is not hot enough to test with")
        body = game.system.bodies[-1]
        note = flight.path_note(game, body, "coast") or ""
        added = flight.hot_risk(game)
        assert f"{added:.2f}" in note, (
            f"the note never states the {added:.2f} it is charging: {note!r}")
        assert f"{game.ship.heat:.0f}" in note, (
            f"the note never states how much heat is aboard: {note!r}")
        assert "cooking" in note, (
            f"the hull is over its cap and taking damage for it, and the "
            f"note does not mention it: {note!r}")
        return note[:96]

    @check("a cold hull well clear of the star is told nothing at all")
    def _():
        # A warning on every screen forever is furniture. This is the check
        # that stops the fix for silence becoming noise instead.
        game = new_game("quiet")
        here = math.hypot(*flight.ship_position(game))
        assert here > flight.HOT_RADIUS, here
        assert game.ship.heat < game.ship_stats.heat_cap * flight.WORTH_SAYING
        said = 0
        for body in game.system.bodies:
            for burn in flight.BURNS:
                note = flight.path_note(game, body, burn.id)
                if note and ("carrying" in note or "starting" in note):
                    said += 1
        assert said == 0, (
            f"{said} quotes warned a cold hull about heat it does not have")
        return "nothing said to a cold hull well out"

    @check("leaving from inside the star's heat is stated, not just arriving")
    def _():
        game = _parked_deep("depart")
        here = math.hypot(*flight.ship_position(game))
        assert here < flight.HOT_RADIUS, (
            f"parked at {here:.2f} AU, which is not inside the heat")
        outward = [b for b in game.system.bodies
                   if math.hypot(*flight.intercept(game, b, "economy")["aim"])
                   >= flight.HOT_RADIUS]
        assert outward, "no body in this system is outside the star's heat"
        for body in outward:
            quoted = flight.quote(game, body, "economy")["risk"]
            note = flight.path_note(game, body, "economy") or ""
            assert quoted > 0, quoted
            assert "starting" in note, (
                f"a burn from {here:.2f} AU out to "
                f"{math.hypot(*flight.intercept(game, body, 'economy')['aim']):.2f} "
                f"AU is surcharged and says only: {note!r}")
        return (f"parked at {here:.2f} AU — every outward burn says why it is "
                f"dearer ({len(outward)} of them)")

    @check("a crossing quote states both clocks and they disagree properly")
    def _():
        # The helm's other half: a jump is priced on sector time and lived on
        # ship time, and the two only agree on a steady transit.
        game = new_game("clocks")
        target = min((s for s in game.galaxy.systems
                      if s.id != game.location_id),
                     key=lambda s: distance(game.system, s))
        rows = []
        for crossing in CROSSINGS:
            q = jump_quote(game, target, crossing.id)
            assert q["days"] >= 1 and q["ship_days"] >= 1, q
            if crossing.dilation == 1.0:
                assert q["ship_days"] == q["days"], (
                    f"{crossing.id} does not dilate and the clocks still "
                    f"differ: {q['days']} against {q['ship_days']}")
            else:
                assert q["ship_days"] < q["days"], (
                    f"{crossing.id} dilates {crossing.dilation}x and the crew "
                    f"still lives {q['ship_days']} of {q['days']} days")
            rows.append(f"{crossing.id} {q['days']}/{q['ship_days']}d "
                        f"{q['fuel']}t")
        return " · ".join(rows)
