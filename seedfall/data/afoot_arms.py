"""What a weapon or a coat of armour does when somebody is actually shooting.

`data/kit.py` has sold pistols, flak jackets and vacc suits since the
concourse opened, with a price, a tech level and a law level each — and not
one of them had ever been fired. This is the other half of those entries:
the numbers a deck plan needs, keyed by **the same ids**, so the autopistol
bought at a chandler is the autopistol in the corridor, and a railgun that is
four years in a cell at law 9 is the same railgun that goes through a
bulkhead.

The shape is Traveller's, squared off. A square is a metre and a half.

- **dice** and **plus**: damage, in d6s, before the attack's Effect is added
  and armour is taken off.
- **short** and **long**: the range bands in squares. Inside `short` is 0;
  out to `long` is -2; out to twice `long` is -4; beyond that it cannot be
  fired at all. Next to the target is +1 for a gun, which is how Traveller
  treats a pistol at arm's length.
- **stun** puts people down and never kills them. **laser** meets the extra
  protection ablative cloth was made for. **pierce** is armour ignored.
- **loud** is how many squares away a shot is heard, which is what brings a
  constable.

Nothing here is new content with no shelf behind it except the handful of
weapons nobody sells — the Bloom's, a machine's, a sentry's — which are
prefixed `npc_` and appear only on the other side.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Arm:
    """A weapon, as a tactical map needs it."""

    id: str
    dice: int
    plus: int = 0
    short: int = 1
    long: int = 1
    melee: bool = False
    stun: bool = False
    laser: bool = False
    pierce: int = 0
    #: Squares away a use of it is heard.
    loud: int = 10
    #: The skill it is used with. Kit says a blade is Gun Combat, and so it
    #: is here; bare hands are Athletics, which is Traveller's own answer.
    skill: str = "gun_combat"
    name: str = ""
    #: Traveller's Auto: a burst adds it to the damage, and a weapon with it
    #: can lay down suppressing fire. Nought for anything that fires once.
    auto: int = 0


#: Bare hands, which everybody has.
UNARMED = Arm("", 1, 0, 1, 1, melee=True, loud=3, skill="athletics",
              name="bare hands")

ARMS: tuple = (
    UNARMED,
    Arm("blade", 1, 2, melee=True, loud=2, name="blade"),
    Arm("cutlass", 2, 0, melee=True, loud=3, name="cutlass"),
    Arm("shock_baton", 2, 0, melee=True, stun=True, loud=3,
        name="shock baton"),
    Arm("cutting_torch", 3, 0, melee=True, pierce=2, loud=4,
        skill="mechanic", name="cutting torch"),
    Arm("stunner", 3, 0, 4, 8, stun=True, loud=4, name="stunner"),
    Arm("autopistol", 3, -3, 6, 12, loud=16, name="autopistol", auto=2),
    Arm("snub_pistol", 3, -3, 3, 6, loud=10, name="snub pistol"),
    Arm("laser_pistol", 3, 0, 8, 16, laser=True, loud=6,
        name="laser pistol"),
    Arm("shotgun", 4, 0, 3, 7, loud=20, name="shotgun"),
    Arm("carbine", 3, 0, 10, 20, loud=18, name="carbine", auto=2),
    Arm("rifle", 3, 0, 16, 40, loud=24, name="rifle"),
    Arm("laser_rifle", 5, 0, 16, 40, laser=True, loud=8, name="laser rifle"),
    Arm("gauss_rifle", 4, 0, 16, 40, pierce=3, loud=12, name="gauss rifle",
        auto=3),
    # ── the other side's ───────────────────────────────────────────────────
    Arm("npc_claws", 2, 0, melee=True, loud=2, skill="athletics",
        name="grown hooks"),
    Arm("npc_lash", 2, 0, 2, 3, stun=True, loud=2, skill="athletics",
        name="spore lash"),
    Arm("npc_manipulator", 2, 2, melee=True, loud=4, skill="athletics",
        name="manipulator"),
    Arm("npc_sentry", 3, 0, 10, 20, loud=16, name="sentry gun", auto=3),
    Arm("npc_singer", 2, 0, 5, 10, stun=True, loud=12, skill="athletics",
        name="a sung chord"),
)
ARM_BY_ID = {a.id: a for a in ARMS}


@dataclass(frozen=True)
class Guard:
    """Something worn: what it stops, what it costs to move in, what it seals."""

    id: str
    protect: int
    #: Extra protection against a laser only. Ablative cloth is the point.
    vs_laser: int = 0
    #: Squares off a round's movement.
    slow: int = 0
    #: Breathes where there is nothing to breathe.
    sealed: bool = False
    #: Keeps spores and a tainted atmosphere out of the lungs, but not vacuum.
    filters: bool = False


GUARDS: tuple = (
    Guard("jack", 1),
    Guard("mesh", 2),
    Guard("flak", 5, slow=1),
    Guard("cloth", 3, vs_laser=5),
    Guard("grown_weave", 6),
    Guard("carapace_suit", 12, slow=2),
    Guard("vacc_suit", 4, slow=1, sealed=True, filters=True),
    Guard("hostile_suit", 6, slow=2, sealed=True, filters=True),
    Guard("softsuit", 1, slow=1, sealed=True, filters=True),
    Guard("respirator", 0, filters=True),
    Guard("rebreather", 0, filters=True),
)
GUARD_BY_ID = {g.id: g for g in GUARDS}

@dataclass(frozen=True)
class Grenade:
    """Something thrown: what it does to the squares round where it lands."""

    id: str
    name: str
    #: Dice of damage to everybody in the burst (stun: nobody dies).
    dice: int = 0
    stun: bool = False
    #: Smoke: nobody sees through the burst for `SMOKE_ROUNDS`.
    smoke: bool = False
    #: Squares from where it lands that it reaches, and how far it is thrown.
    burst: int = 1
    reach: int = 6


GRENADES: tuple = (
    Grenade("frag_grenade", "fragmentation grenade", 4),
    Grenade("stun_grenade", "stun grenade", 3, stun=True),
    Grenade("smoke_grenade", "smoke grenade", smoke=True),
)
GRENADE_BY_ID = {g.id: g for g in GRENADES}
#: Rounds a smoke grenade's cloud hangs before it clears.
SMOKE_ROUNDS = 3
#: What being pinned by suppressing fire costs a shot of one's own.
PINNED = -2

#: Things a party can spend once in a walk, and what each does. The ids are
#: kit ids; a person who carries one can use it once per walk, whether it
#: came off the captain's own shelf or out of their own kit bag.
CONSUMABLES = {
    "medkit": "first aid at +1, twice",
    "trauma_pack": "first aid at +2, once",
    "stims": "back on their feet at 1 stamina, once",
    "breach_charge": "one locked door, blown",
    "lockpick": "+2 on a lock",
    "handcomp": "+1 on a console",
    "core_slate": "+2 on a console",
    "frag_grenade": "a burst of fragments, once",
    "stun_grenade": "a room put on the floor, once",
    "smoke_grenade": "a cloud nobody sees through, once",
}

#: How many squares a person moves in a round before anything slows them.
#: Six squares is nine metres in six seconds: a brisk walk, not a run.
BASE_MOVE = 6
#: Never fewer than this, however slow the armour and however bad the wound.
LEAST_MOVE = 2
#: What a load over `kit.CARRIED` costs in squares.
LOADED = 2


def arm(kit_id: str) -> Arm:
    """The weapon behind a kit id, or bare hands."""
    return ARM_BY_ID.get(kit_id or "", UNARMED)


def guard(kit_id: str):
    """The armour behind a kit id, or None for something that is not armour."""
    return GUARD_BY_ID.get(kit_id or "")


def band(arm_: Arm, squares: int) -> tuple:
    """The range band for a distance: (name, DM), or ("", None) if too far.

    One door, so the forecast on a screen and the roll use the same number.
    """
    if arm_.melee:
        return ("reach", 0) if squares <= 1 else ("", None)
    if squares <= 1:
        return ("point blank", 1)
    if squares <= arm_.short:
        return ("short", 0)
    if squares <= arm_.long:
        return ("long", -2)
    if squares <= arm_.long * 2:
        return ("extreme", -4)
    return ("", None)
