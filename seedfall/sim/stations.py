"""Crew stations.

You are one person on a bridge with three seats that all need someone in them.
Each turn you take one personally and the officers hold the other two at their
own level — which is competent, and not as good as you. Choosing which seat to
sit in *this* turn is most of the tactical decision.
"""

from __future__ import annotations

from dataclasses import dataclass

from . import tactical as tac

STATIONS = [
    ("helm", "Helm", "nav", "Heading and throttle. Where you will be next turn "
                            "and what will bear when you get there."),
    ("gunnery", "Gunnery", "tactical", "What fires, and at what. A directed mount "
                                       "shoots markedly better than an automatic one."),
    ("engineering", "Engineering", "engineering", "Power, heat and damage control. "
                                                  "Nothing glamorous keeps working "
                                                  "without it."),
]
STATION_IDS = [s[0] for s in STATIONS]


@dataclass(frozen=True)
class Order:
    id: str
    station: str
    name: str
    blurb: str


ORDERS: list[Order] = [
    Order("close", "helm", "Close the range",
          "Turn onto the target and open the throttle."),
    Order("open", "helm", "Open the range",
          "Turn away and run. Long mounts keep working; short ones do not."),
    Order("hold", "helm", "Hold station",
          "Match the target's drift and keep the current aspect."),
    Order("comeabout", "helm", "Come about",
          "Swing the bow across as hard as the hull will take, to bring fixed "
          "mounts onto the target."),
    Order("broadside", "helm", "Present the broadside",
          "Turn beam-on. Everything on the flanks bears; you are also a wider "
          "target."),

    Order("salvo", "gunnery", "Fire everything that bears",
          "Every mount with the target in its arc. More damage, far more heat."),
    Order("aimed", "gunnery", "Aimed shot",
          "One mount, carefully. Better accuracy and less heat."),
    Order("hold_fire", "gunnery", "Hold fire",
          "Let the hull cool and the mounts stay loaded."),

    Order("damage_control", "engineering", "Damage control",
          "Patch the outermost breached layer. A living hull does it faster."),
    Order("vent", "engineering", "Vent heat",
          "Dump everything the radiators can take."),
    Order("route_guns", "engineering", "Route power to the mounts",
          "Accuracy up next turn, at the cost of everything else."),
    Order("route_engines", "engineering", "Route power to the drive",
          "Speed and turn rate up next turn; the guns run cold."),
]

ORDERS_BY_ID = {o.id: o for o in ORDERS}


def orders_for(station: str) -> list[Order]:
    return [o for o in ORDERS if o.station == station]


def officer_level(officers, stat: str) -> float:
    """The level the best-placed officer is actually working at.

    Loyalty is felt here rather than only on a roster screen: a devoted officer
    holds a station above their grade, a restless one goes through the motions.
    """
    from . import loyalty
    return max((loyalty.effective_level(o) for o in officers if o.stat == stat),
               default=0.0)


# ── helm ───────────────────────────────────────────────────────────────────

def run_helm(side, other, order_id: str | None, directed: bool, officers) -> str:
    """Set heading and throttle. Returns a line for the log."""
    turn_limit, accel, top = tac.manoeuvrability(side.st)
    skill = officer_level(officers, "nav")
    if not directed:
        # An officer holds the last order rather than improvising.
        order_id = side.helm_order or "hold"
        turn_limit *= min(1.0, UNATTENDED_TURN + TURN_PER_LEVEL * skill)
    side.helm_order = order_id

    rel = tac.relative_bearing(side.body, other.body)
    to_target = (tac.bearing_to(side.body, other.body) - side.body.heading + 540) % 360 - 180

    if order_id == "close":
        tac.steer(side.body, to_target, turn_limit)
        tac.throttle(side.body, top, accel)
        text = "closing"
    elif order_id == "open":
        tac.steer(side.body, to_target + 180, turn_limit)
        tac.throttle(side.body, top, accel)
        text = "opening the range"
    elif order_id == "comeabout":
        tac.steer(side.body, to_target, turn_limit * 1.35)
        tac.throttle(side.body, top * 0.45, accel)
        text = "coming about"
    elif order_id == "broadside":
        tac.steer(side.body, to_target + (90 if to_target >= 0 else -90), turn_limit)
        tac.throttle(side.body, top * 0.6, accel)
        text = "presenting the broadside"
    else:
        tac.throttle(side.body, side.body.speed * 0.75, accel)
        text = "holding station"

    if side.route == "engines":
        tac.throttle(side.body, top * 1.25, accel * 1.6)
    tac.advance(side.body)
    return text


# ── engineering ────────────────────────────────────────────────────────────

def run_engineering(side, order_id: str | None, directed: bool, officers) -> str:
    skill = officer_level(officers, "engineering")
    side.route = None
    if not directed:
        # Left alone, engineering keeps the hull cool and nothing else.
        side.ship.heat = max(
            0.0, side.ship.heat
            - side.st.vent * (UNATTENDED_VENT + VENT_PER_LEVEL * skill))
        return ""

    if order_id == "vent":
        side.ship.heat = max(0.0, side.ship.heat - side.st.vent * 2.2 - 12)
        return "venting hard"
    if order_id == "route_guns":
        side.route = "guns"
        return "power to the mounts"
    if order_id == "route_engines":
        side.route = "engines"
        return "power to the drive"
    if order_id == "damage_control":
        healed = 0.0
        for layer in reversed(side.ship.layers):
            if layer.hp <= 0 or layer.hp >= layer.max:
                continue
            gain = layer.max * (0.06 + 0.02 * skill) * (1.6 if side.st.regen > 0 else 1.0)
            gain = min(gain, layer.max - layer.hp)
            layer.hp += gain
            healed = gain
            break
        return f"damage control patched {round(healed)}" if healed else "nothing to patch"
    side.ship.heat = max(0.0, side.ship.heat - side.st.vent)
    return ""


def accuracy_modifier(side, directed: bool, officers) -> float:
    """How much better the guns shoot for being personally directed."""
    mod = 0.0
    if directed:
        mod += 0.10
    else:
        mod -= 0.12 - 0.02 * officer_level(officers, "tactical")
    if side.route == "guns":
        mod += 0.12
    return mod


#: Turn rate an unattended helm keeps, before the navigator's skill.
UNATTENDED_TURN = 0.7

#: And what each level of nav buys back.
TURN_PER_LEVEL = 0.06

#: Heat an unattended engineering section sheds, as a share of the vent rate.
UNATTENDED_VENT = 0.5
VENT_PER_LEVEL = 0.08


def seat_value(side, officers) -> dict:
    """What taking each seat personally is worth this turn.

    The panel printed the officer's level and nothing about the consequence,
    so a captain could not tell that gunnery is worth +0.22 to hit with a
    green officer and +0.10 with a veteran, or that an unattended helm repeats
    its last order at seven-tenths of the turn rate.
    """
    nav = officer_level(officers, "nav")
    tactical = officer_level(officers, "tactical")
    engineering = officer_level(officers, "engineering")

    turn_share = min(1.0, UNATTENDED_TURN + TURN_PER_LEVEL * nav)
    vent_share = UNATTENDED_VENT + VENT_PER_LEVEL * engineering
    directed_vent = side.st.vent * 2.2 + 12
    idle_vent = side.st.vent * vent_share

    return {
        "helm": {
            "level": nav,
            "gain": 1.0 - turn_share,
            "says": (f"turn at full rate instead of {turn_share:.0%}, and pick "
                     "the order rather than repeating "
                     f"{ORDERS_BY_ID[side.helm_order].name.lower()}"
                     if side.helm_order in ORDERS_BY_ID
                     else f"turn at full rate instead of {turn_share:.0%}"),
        },
        "gunnery": {
            "level": tactical,
            "gain": accuracy_modifier(side, True, officers)
                    - accuracy_modifier(side, False, officers),
            "says": None,
        },
        "engineering": {
            "level": engineering,
            "gain": directed_vent - idle_vent,
            "says": (f"vent {directed_vent:.0f} heat instead of "
                     f"{idle_vent:.0f}, or route power, or patch a breach"),
        },
    }


def bears_on(side, other, part) -> tuple[bool, float]:
    """Does this mount have the target in its arc, and by how much is it off?"""
    rel = tac.relative_bearing(side.body, other.body)
    arc = tac.arc_of(part)
    return tac.bears(arc, rel), tac.arc_gap(arc, rel)
