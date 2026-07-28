"""Alien-technology checks.

Xenotech is not researched — it is dug up, bought or taken — so it needs its own
checks: that every technology is findable, that understanding accumulates and
gates correctly, that incorporating it changes the ship, and that a worked site
gives up less each time you return to it.
"""

from __future__ import annotations

from ..core.rng import RNG
from ..core.state import new_game
from ..data import chassis as chassis_data
from ..data import parts as parts_data
from ..data.xenotech import CULTURES, XENOTECH, XENOTECH_BY_ID
from ..sim import actions
from ..sim import xeno as xeno_sim
from ..world import galaxy
from .harness import Suite


def run(suite: Suite) -> None:
    check = suite.check

    @check("every alien technology is findable in a fresh sector")
    def _():
        worst = None
        for i in range(6):
            g = galaxy.generate_sector(f"relic-{i}", 42)
            placed = {b.relic for s in g.systems for b in s.bodies if b.relic}
            missing = [x.id for x in XENOTECH if x.id not in placed]
            if missing:
                worst = (f"relic-{i}", missing)
                break
        assert worst is None, f"sector {worst[0]} buried no site for {worst[1]}"
        g = galaxy.generate_sector("relic-0", 42)
        sites = sum(1 for s in g.systems for b in s.bodies if b.relic)
        return f"{len(XENOTECH)} technologies, {sites} sites, none unreachable"

    @check("understanding accumulates and prerequisites gate incorporation")
    def _():
        g = new_game("xeno-chain")
        deep = next(x for x in XENOTECH if x.requires)
        # Bank a full study on the deep technology before its prerequisite.
        xeno_sim.add_study(g, deep.id, deep.study * 1.5)
        assert not xeno_sim.is_incorporated(g, deep.id), "skipped its prerequisite"
        assert xeno_sim.study_of(g, deep.id) > 0, "banked study was lost"
        for req in deep.requires:
            r = XENOTECH_BY_ID[req]
            xeno_sim.add_study(g, req, r.study)
        g.advance_days(1)
        assert xeno_sim.is_incorporated(g, deep.id), (
            "banked study never settled once prerequisites were met")
        return f"{deep.name} held, then settled behind {len(deep.requires)} prereq(s)"

    @check("incorporating alien work changes the ship")
    def _():
        g = new_game("xeno-bonus")
        boon = next(x for x in XENOTECH if x.bonus.get("hull") and not x.requires)
        before = g.bonuses.get("hull", 0)
        xeno_sim.incorporate(g, boon.id)
        g.recompute()
        after = g.bonuses.get("hull", 0)
        assert after > before, f"{boon.name} granted no hull bonus"
        # and its part becomes fittable
        gated = [p for p in parts_data.PARTS if p.tech == boon.id]
        for p in gated:
            assert p.tech in g.research.unlocked, f"{p.id} still locked"
        return f"{boon.name}: hull {before:.2f} → {after:.2f}, {len(gated)} part(s) freed"

    @check("a dig yields understanding and wears the site out")
    def _():
        g = new_game("dig")
        site = next(((s, i) for s in g.galaxy.systems
                     for i, b in enumerate(s.bodies) if b.relic), None)
        assert site, "no relic site anywhere in the sector"
        sysm, idx = site
        g.location_id = sysm.id
        body = sysm.bodies[idx]
        body.relic_found = True
        first = actions.excavate(g, idx)
        assert first["ok"], first.get("why")
        assert first["points"] > 0, "a dig taught us nothing"
        assert body.digs == 1, "the site does not remember being worked"
        second = actions.excavate(g, idx)
        assert second["points"] < first["points"], (
            f"returning to a worked site paid the same: "
            f"{first['points']:.0f} then {second['points']:.0f}")
        return (f"{first['tech'].name}: {first['points']:.0f} then "
                f"{second['points']:.0f} points")

    @check("every alien part is gated and fits something")
    def _():
        from ..data.xenoparts import XENOPARTS
        for p in XENOPARTS:
            assert p.tech in XENOTECH_BY_ID, f"{p.id} gated on {p.tech}"
            homes = [c for c in chassis_data.CHASSIS
                     if c.slots.get(p.slot, 0) > 0
                     and chassis_data.accepts_family(c, p.family)]
            assert homes, f"{p.id} fits no hull"
        granted = {p.tech for p in XENOPARTS}
        orphan = [x.id for x in XENOTECH if x.id not in granted and not x.bonus]
        assert not orphan, f"technologies that grant nothing at all: {orphan}"
        return f"{len(XENOPARTS)} parts across {len(granted)} technologies"
