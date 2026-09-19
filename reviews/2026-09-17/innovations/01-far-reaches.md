# Innovation 1 — The Far Reaches (universe)

## Why

The Verge is 42 stars in a 74×52 ly field. The review's play-test measured the
cost of that:
- Once the reachable pocket is charted, explorer income stalls. One explorer
  made +22k in 2.5 years; another's money peaked on day 1,190 and fell.
- The mid-game has nowhere new to go.
- The Weave (`sim/weave.py`, `data/gates.py`) already says the gates are "older
  than anyone flying it". The Far Reaches are what those gates were built to
  reach.

## What the player gets

Three regions beyond the Verge, each behind a **deep anchor**: a dormant Weave
gate at the Verge's rim that has to be relit. Relighting is a mid-game project.
Each region plays differently:

| Region | Systems | Character | Distinct rules |
|---|---|---|---|
| **The Shoals** | 12 | An emission nebula, young stars in glowing gas | Sensor range ×0.5 and survey resolution lower; volatiles rich; new commodity **nebular condensate** (exotic gas, high value to the Concordat and Dry Choir); 2–3 independent Freehold havens (smuggler ports, contraband tolerated); lawlessness high |
| **The Hollow** | 10 | A void, sparse and dark | Long lanes (the median neighbour is about 9 ly, so you need a good drive or the region's own inner gates); **rogue planets** (sunless bodies: no photosynthesis, so a grown hull's intima makes no O₂ there and it runs on stores); ruins of a **fifth, extinct culture** (the Precursors), whose sites yield unique *relic fittings*, not xenotech; no ports except one derelict relay |
| **The Cradle** | 14 | A young, hot, dense cluster | New **O/B-class** stars (blue giants); high radiation (crew dose and faster hull heat); rich rare minerals (high ore and magnetite grades); unclaimed at first — home of the Kith (innovation 2, wave B), so leave hooks: systems may carry `faction=None` and no port |

The universe grows from 42 to about 78 systems.

## Design

### State (all defaulted fields, so old saves load)

- `System.region: str = "verge"`.
- `Galaxy.regions: list = []` of registered `Region(id, name, w, h, anchor_id,
  entry_id, opened_day)`. The anchor is the Verge rim system holding the deep
  gate. The entry is the region system on the far side.
- Region systems are **appended to `galaxy.systems`, with id == index**,
  because the code does `galaxy.systems[sid]` 72 times.
- A region's systems are **generated when its anchor is relit**, never before.
  Generation is deterministic from `RNG(f"{seed}:region:{region_id}")`, so any
  old save can open the Reaches and a new game pays nothing until then.
- x/y are **local to the region's own frame** (its own `w`, `h`).

### Distance and reach

`world/galaxy.distance(a, b)` returns `math.inf` when `a.region != b.region`.
That single change makes every existing reach, jump, piracy, Bloom-spread and
fleet computation treat regions as unreachable except through a gate. Within a
region, distance is Euclidean in the region frame.

### The deep gates

A new kind in the Weave, `kind="deep"`.
- Their sites are chosen deterministically on the Verge rim:
  - the Shoals anchor is the westmost Verge system;
  - the Hollow anchor is the northmost;
  - the Cradle anchor is the eastmost that is **not** Kessel's Reach (the
    Bloom origin).
- They link anchor ↔ entry and are dark until relit.

**Must not disturb the existing Weave.** `weave.sites()` and friends are
farthest-point samples over `galaxy.systems`, cached by `(seed,
len(systems))`. Restrict them to Verge systems and key the cache on the Verge
count. Otherwise opening a region re-samples every ancient gate in the save.

### Relighting (the project)

The gate is visible on the chart from the start as a dark anchor with a
tooltip, so the player has a goal. Relighting needs three things:
1. **Survey the anchor.** A deep scan at the anchor system; reuse the survey
   methods.
2. **Deep Weave technology.** A new tier-3 node in `data/tech.py`, fed by
   survey and specimen evidence.
3. **The relight itself.** Materials (for example 60 t magnetite, 40 t alloy,
   8 t xenolith) plus credits, paid at the anchor. It takes days, through
   `advance_days`.

The preview states all three and the Bloom risk. The act equals the preview.

Transit through a lit deep gate is instant and pays a toll to nobody (it is
nobody's gate). It reuses `sim/gates.py` transit where possible.

**The Bloom walks the Weave.** An infested anchor seeds the entry side at the
same pace as `sim/weave`'s "growth crosses a lit link in a season". This makes
relighting a real decision: containment gets harder if you open a door.

### Generation (`world/regions.py`, new)

- **Star classes are region-specific tables**, e.g. Shoals: M/K/F plus
  T-Tauri young stars; Hollow: M/D/N plus black hole; Cradle: B/O/A/F.
  **Never edit or reorder `galaxy.STAR_CLASSES`.** Any change to the Verge's
  RNG draw sequence shifts every existing seed and hundreds of pinned
  fixtures.
- New star classes go in `data/starclasses.py` for radii and luminosities,
  and `stars3d` so they render. `O`/`B` are blue giants.
- Bodies use `world/planets.make_body` with region modifiers. Hollow: add
  `rogue` bodies (a new body kind with no star-lit face) or mark existing ones
  as sunless. Update every table that keys on body kind: colony sites,
  surveys, mining, `worlds3d`.
- Ports: Shoals has 2–3 independent Freehold havens with markets; Hollow has
  one derelict relay (outpost, services = repair only); Cradle has none (wave
  B adds the Kith).
- **Nebular condensate** goes in `data/commodities.py`. Check every table that
  enumerates goods: economy equilibrium, faction buys/sells, contraband,
  freight, contracts. Condensate is sold only in the Shoals and bought
  strongly by the Concordat and Dry Choir, which makes a real trade route.

### Rules per region

- **Shoals:** a sensor/detection multiplier (read in `sim/detection` and the
  survey resolution).
- **Hollow:** no light at rogue bodies. The intima's O₂ and a grown hull's
  photosynthetic inputs read the star's `heat`, so a sunless body is treated
  as heat 0. Lanes are long.
- **Cradle:** a radiation dose per day aboard (crew health through
  `lifespan`/`upkeep`, or a morale hit) and extra hull heat. Shielding
  fittings and melanin tech reduce it.

Each of these is one function in `sim/regions.py` (new), read by the system
it affects, and each is measured by an efficacy check.

### Which loops include the Reaches

Audit **every** iteration over `galaxy.systems` (about 75 in 50 files) and
decide per site. Record the table in `CHANGES`.

- **Default: include the Reaches.** It is one living universe: markets tick,
  traffic moves, the Bloom spreads through gates, piracy applies.
- **Verge only:** ending conditions and their progress bars
  (`threat.victory_progress`: containment count, cartel market share,
  harbours, "sector lost") and the ancient Weave sites. The endings are about
  the Verge. Add `world/galaxy.verge(galaxy)` as the one door for that.

### UI

- **The chart gets region tabs:** Verge, Shoals, Hollow, Cradle. Unopened
  regions show as a dim silhouette with the requirement text. Each region
  draws in its own frame.
- **Deep anchors** get a distinct mark on the Verge chart.
- **Relight flow:** a panel on the System screen at an anchor system (or on
  the Helm screen) with the three-part preview and a button.
- **A codex entry per region.** Help/manual topics for regions and deep
  gates (`data/help.py`).
- **Ambience** is left to the soundscape (innovation 10), which may key off
  `System.region`.

### Balance targets (measure with bots)

- A focused mid-game captain can relight the first deep gate between day 400
  and day 900.
- A Shoals condensate route pays clearly better than the Verge median route
  after the relight investment: payback in under a year of trading.
- Opening a region does not raise Verge ms/day by more than about 60% with
  all three open.
- Endings are not trivialised. Containment stays Verge-only; if the Bloom
  crosses into a region, the region is lost ground, not a new requirement.

### Tests (new suite `test_reaches`)

- Regions generate deterministically, and opening them leaves the Verge
  byte-identical: hash every Verge system before and after.
- The Weave's ancient sites are unchanged after opening.
- Cross-region distance is infinite, so nothing is reachable without the gate.
- The relight preview equals the act: costs, days and materials.
- Transit through the deep gate works both ways, and the ship ends at the
  entry system.
- Each region rule moves its number, switched off by efficacy.
- A save with open regions round-trips across a fresh process.
- An old save (no `regions`) opens a region.
- Performance: ms/day with 0 and 3 regions open.
- The Bloom crosses a lit deep link on the stated schedule.

## Out of scope (hooks for later waves)

- The Kith, their ports and the lexicon (innovation 2).
- Phenomena that prefer regions, such as a nova in the Cradle or ion storms
  in the Shoals (innovation 7).
- Officer arcs that point into the Reaches (innovation 8).
- Renown milestones for opening regions (innovation 9).

Leave a small, documented API for these: `regions.region_of(system)`,
`regions.opened(game)` and `regions.rule(game, system, key)`.
