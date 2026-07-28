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

    @property
    def range_units(self) -> float:
        return tac.separation(self.player.body, self.enemy.body)

    @property
    def band(self) -> int:
        """Weapons are specified in bands; the band comes from real distance."""
        return tac.band_for(self.range_units)
