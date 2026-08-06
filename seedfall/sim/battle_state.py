"""The mutable state of one engagement.

Split out so the resolver, the enemy AI and the interface can all refer to the
same shapes without importing each other. A Battle is transient — it is never
written to a save, because time does not pass while you are being shot at.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from . import tactical as tac
from .ship import Ship, Stats


@dataclass
class Side:
    ship: Ship
    st: Stats
    personality: str = "balanced"
    body: tac.Body2D = field(default_factory=tac.Body2D)
    helm_order: str | None = None
    route: str | None = None
    station: str = "gunnery"
    resolve: float = 100.0
    blind: int = 0
    jammed: int = 0
    grappled: int = 0
    interpose: int = 0
    braced: bool = False
    cd: dict = field(default_factory=dict)
    #: Compartments given up to `abilities.seal`, by layer name. This is what
    #: bounds it: each layer can be irised off once, so the armour it buys stops.
    sealed: list = field(default_factory=list)
    dealt: float = 0.0
    taken: float = 0.0


@dataclass
class Battle:
    player: Side
    enemy: Side
    enemy_name: str
    enemy_faction: str | None
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
    pending_order: str | None = None
    consorts: list = field(default_factory=list)
    #: Every shot attempted this turn, for the picture. Cleared each turn by
    #: `sim/gunfire.py` and never saved — a battle is transient and so is a
    #: muzzle flash.
    shots: list = field(default_factory=list)
    #: Set once `sim/aftermath.resolve()` has paid the engagement out. Both the
    #: screen and a headless driver can reach the end of a fight; neither
    #: should be able to collect the salvage twice.
    settled: bool = False
    #: What the captain did with a hull that struck its colours — "" until
    #: decided, then "taken", "stripped" or "released". One decision per
    #: engagement; `sim/prize.py` is the door.
    prized: str = ""

    @property
    def range_units(self) -> float:
        return tac.separation(self.player.body, self.enemy.body)

    @property
    def band(self) -> int:
        """Weapons are specified in bands; the band comes from real distance."""
        return tac.band_for(self.range_units)


#: How each way a battle can end reads in the log. Lives here rather than in
#: `sim/combat.py` so the resolver, `sim/parley.py` and `sim/prize.py` end an
#: engagement through the same door.
ENDINGS = {
    "destroyed": "{enemy} comes apart across three compartments.",
    "driven-off": "{enemy} breaks off. Whatever they came for, it was not worth this.",
    "escaped": "You break contact and run dark.",
    "parley": "They stand down. Somebody on that bridge wanted a reason to.",
    "struck": "{enemy} strikes their colours. The guns fall silent, and what "
              "happens to that hull is now yours to decide.",
    "routed": "You have nothing left to hold with. They let you go.",
    "stalemate": "Neither hull can finish the other. You drift apart, both of you "
                 "poorer and neither of you satisfied.",
    "lost": "{player} is lost.",
}


def finish(b: Battle, result: str) -> Battle:
    """End the engagement, one way. The one writer of `over` and `result`."""
    b.over = True
    b.result = result
    line = ENDINGS.get(result, result).format(enemy=b.enemy_name,
                                              player=b.player.ship.name)
    b.log.append((b.turn, line, "bad" if result == "lost" else "good"))
    return b
