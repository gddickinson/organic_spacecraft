# INTERFACE.md — SEEDFALL navigation map

The top-level map of the game. Read this before opening any source file in
`seedfall/`.

## What this is

**SEEDFALL** is a native PyQt6 space exploration / trading / combat RPG built on
the GESTALT design programme in this repository — a modern Starflight with a
Civilization layer. You command a grown starship in the Verge, survey and trade,
fight or refuse to, research a fifty-eight-node tech tree, design hulls out of
grown organs and fabricated machinery, plant colonies, and deal with the Bloom.

The GESTALT documents supply one of the five technologies and all of the
physics: the grown hull classes from the Fleet Class Reference, the six-layer
hull from the Design Dossier, the phosphorus bottleneck and 9:1 ore ratio from
Metabolism, the wet/dry cyborg control stack from Nervous System, the cell types
from the Cell Atlas, and the reproduction-licence containment regime from the
Fleet Registry. The other four technologies exist so that the grown fleet has
something to be measured against.

**Combat is positional.** Ships carry a heading and a speed on a real plane.
The five range bands still exist — weapons are specified in them — but the band
is *derived* from an actual separation rather than stored, so closing is a
manoeuvre rather than a menu pick. Every mount has a firing arc (fore, broadside,
turret) and will refuse to fire outside it, which makes turning to bring a gun to
bear a real decision.

**And you can only sit in one seat.** Each turn you take one station personally —
Helm, Gunnery or Engineering — and your officers hold the other two at their own
level, which is competent and worse than you. Directed gunnery shoots markedly
better than automatic; engineering routes power, patches the outermost breach or
dumps heat; the helm decides what will bear next turn.

**The Bloom is an antagonist, not a timer.** Five named stages advanced by the
sector-wide burden: past Motile it keeps roaming instars in the field that prefer
your colonies to empty ground; past Adaptive it builds resistance (up to 55%) to
whatever weapon family you keep using, and forgets what you stop using. At
Kessel's Reach, found by surveying the origin system, is the First Instar — the
original husk with a Charter serial still on it. Containment requires the sector
clean *and* that husk dead, which takes about twenty burn passes from a
battleship.

**Diplomacy has two axes.** Your standing with each power, and how the powers
regard *each other* — a relations matrix that starts hostile in most pairs.
Tribute, intelligence and relief move the first; only brokering moves the second,
and brokering requires both parties to think well of you already. Concord needs
all four at Kin **and** all six pairs at peace, so it is a diplomatic achievement
rather than four grinds.

**Getting anywhere is a decision.** A jump drops you at the system edge, not
alongside anything. Bodies sit on real orbits that keep moving while you fly, so
the range to a target depends on when you leave. Four burn profiles trade
reaction mass against days — and *coasting is always free*, which is what stops
an empty tank from becoming a deadlock. Local work (survey, extract, dig, land)
flies the ship alongside first, so a player who never opens the helm still gets a
coherent transit; the helm is where you choose a better one.

**Two mini-games.** The **docking approach** is the control loop from the
nervous-system study — sense, compute, act, hold homeostasis — with three drifting
axes, one correction per pass, and readings blurred by how good your sensors are.
A clean approach earns standing; a botched one buys a tug. The **decoding bench**
takes a recording of something that was not speaking to you: four positions, a
hidden pattern, and feedback that tells you how many glyphs are exactly right and
how many are merely present, never which. Solving one is worth alien
understanding, and costs nothing but attempts.

**There is a game on the ground.** Landing a party opens a 7×7 zone map revealed
one tile at a time. Moving costs days of supply (known ground is cheap to
re-cross, which is what makes coming home survivable); terrain springs hazards
that officers' skills mitigate; site features offer choices resolved against a
named stat. Nothing is banked until the party is back on the lander, and running
out of supply in the field costs most of the haul. How much biomass you commit at
launch buys how long they can stay.

**Contracts are optional work with deadlines.** Six kinds, posted per port and
scaled by distance. They are checked on the clock and complete the moment their
terms are met rather than when you remember to hand them in. Nothing in the game
requires taking one — the five endings are open from turn one.

**Alien technology is a separate progression from research.** Four cultures —
the Abyssals, the Ossuary, the Weft and the Tessellate — left twelve
technologies scattered across the sector as buried sites. None can be reasoned
out. Understanding accumulates in study points from four sources: excavating a
site, taking relics apart in a laboratory, buying somebody's field notes at a
port, and seizing them off a hull you destroy. At full understanding the
technology is *incorporated* — its id is appended to `research.unlocked`, so the
shipyard and codex treat it like anything else you know, and it never appears in
the research tree because you could not have derived it.

**Thirty-five hulls and nineteen stations across five families:**

| Family | Hulls | Character |
|---|--:|---|
| Grown | 12 | Gestated from a seed. Heals; eats phosphate; takes months. |
| Fabricated | 13 | Concordat of Yards. Welded in weeks, dear, and never mends. |
| Hybrid | 4 | Freehold grafts. Both bills, both gifts. |
| Synthetic | 4 | Dry Choir. Crewless, superb instruments, no self-repair. |
| Xeno | 2 | Not ours. It mends, and nobody has explained how. |

Which parts graft to which frame is `ACCEPTS` in `data/hull_types.py`: a grown
hull refuses a fusion lance, a Yards hull refuses an intima, a hybrid takes
either, and a synthetic frame takes fabricated and Dry Choir work but nothing
alive.

## Running

```
python -m seedfall                  # title screen
python -m seedfall --new            # straight into a new chronicle
python -m seedfall --seed verge-7   # a specific sector
python -m seedfall.tests            # simulation + interface suites
python -m seedfall.tests sim        # one suite
```

Requires **PyQt6** (`pip install PyQt6`). Nothing else — no network, no server,
no browser. Saves live in `~/.seedfall/save.json`.

## Layout

```
seedfall/
├── __main__.py         entry point: python -m seedfall
├── core/               engine primitives — no game rules, no Qt
│   ├── rng.py          seeded mulberry32 + pick/weighted/gauss/shuffle helpers
│   ├── util.py         formatting (credits, mass, stardate, duration) and clamp
│   ├── save.py         generic dataclass ⇄ JSON codec, @register, atomic write
│   └── state.py        the Game object, advance_days(), new_game(), load_game()
├── data/               static content tables — pure data, no logic
│   ├── commodities.py  14 tradeable goods
│   ├── chassis.py      the hull registry — assembles and re-exports the rest
│   ├── hull_types.py   layer stacks, the Chassis record, family rules (ACCEPTS)
│   ├── hulls_grown.py  the 12 GESTALT classes
│   ├── hulls_built.py  13 fabricated · 4 hybrid · 4 synthetic · 2 xeno
│   ├── part_types.py   Part / Weapon / Ability shapes, slots, range bands
│   ├── modules.py      drives, power, sensors, compute, utility organs
│   ├── armaments.py    weapons and defences
│   ├── parts.py        merged registry over modules + armaments
│   ├── tech.py         61-node research tree, 10 branches, 5 tiers
│   ├── colonies.py     19 colony and station classes
│   ├── factions.py     6 powers + reputation bands
│   ├── lifeforms.py    xenobiology generation tables + anomalies
│   └── lore.py         intro, victories, endings, name pools, glossary
├── world/              generated content
│   ├── galaxy.py       sector generation, lane relaxation, distance/transit
│   ├── planets.py      bodies, biomes, resource grades, survey resolution
│   └── economy.py      per-port supply/demand, prices, market drift
├── sim/                game rules — never import Qt
│   ├── ship.py         Ship model, stats(), layer stack, cargo, repair
│   ├── shipyard.py     design validation, costing, build queue, refit
│   ├── combat.py       turn resolution, firing, damage, endings
│   ├── battle_state.py the Side and Battle shapes, shared by resolver/AI/UI
│   ├── tactical.py     the plane: positions, headings, firing arcs, bands
│   ├── stations.py     helm / gunnery / engineering orders
│   ├── enemy_ai.py     how the other side fights — same geometry, no cheating
│   ├── abilities.py    defensive abilities, returning their own log lines
│   ├── colony.py       founding, daily yields, aggregate colony effects
│   ├── research.py     project selection and point accrual
│   ├── crew.py         officers, recruitment, experience, morale
│   ├── encounters.py   NPC generation and transit events
│   ├── threat.py       Bloom growth and spread, cleansing, victory checks
│   ├── xeno.py         study points, incorporation, alien passive bonuses
│   ├── bloom.py        stages, roaming instars, resistance, the First Instar
│   ├── contracts.py    generation, acceptance, progress, expiry
│   ├── diplomacy.py    standing, the relations matrix, treaties, brokering
│   ├── expedition.py   the ground game: zone map, movement, attempts, hauls
│   ├── fieldwork.py    everything done off the ship — digs, analysis, landings
│   ├── flight.py       the helm: orbits, transfer burns, in-system incidents
│   ├── minigames.py    the docking control loop and the decoding bench
│   └── actions.py      player actions spanning modules (jump/survey/mine/dive)
├── ui/                 PyQt6 presentation — never mutates state directly
│   ├── theme.py        palette, fonts, the global stylesheet
│   ├── widgets.py      Panel, Card, Bar, Pill, TabBar and the View base class
│   ├── window.py       MainWindow: hud, nav rail, view stack, log, dialogs
│   ├── title.py        title screen and the opening briefing
│   ├── app.py          QApplication bootstrap
│   ├── map_view.py     custom-painted sector chart and jump control
│   ├── system_view.py  bodies, survey, extraction, diving, colonising
│   ├── port_view.py    market, services, recruitment
│   ├── ship_view.py    layer stack, fittings, crew, hold
│   ├── yard_view.py    hull designer, build queue, fleet management
│   ├── tech_view.py    research tree
│   ├── empire_view.py  colonies, depot, victory progress, waiting
│   ├── codex_view.py   class reference, powers, glossary, about
│   ├── xeno_view.py    the xenology desk (hosted as a Research tab)
│   ├── expedition_view.py  the landing zone: fogged map, party, field log
│   ├── diplomacy_view.py   relations matrix and the overture desk
│   ├── helm_view.py    orbit chart and burn planner
│   ├── minigame_view.py    docking approach and decoding bench
│   └── battle_view.py  combat screen and post-engagement resolution
└── tests/              python -m seedfall.tests
    ├── harness.py      a tiny check runner (no pytest dependency)
    ├── test_sim.py     27 simulation checks
    ├── test_xeno.py    5 alien-technology checks
    └── test_ui.py      17 interface checks, rendered on Qt's offscreen platform
```

## How the layers connect

The dependency rule is one-directional and worth preserving:

```
data/  ──►  world/  ──►  sim/  ──►  ui/  ──►  __main__
                    core/ is available to everything
```

- **`core/state.Game` owns time.** `advance_days(n)` is the only clock: it ticks
  research, colonies, build slips, hull regrowth, every market, payroll, air,
  morale and the Bloom, then checks for victory. Nothing else advances a day.
- **`sim/` never imports Qt.** It takes a `game` and returns plain data. That is
  why the simulation suite can run headless and why the whole rules layer is
  testable without a display.
- **`ui/` never mutates state directly** — a view calls a `sim/` function, then
  `win.refresh()`, which recomputes derived values and redraws.
- **`ship.stats()` is the single source of derived numbers.** Chassis base +
  fitted parts + research bonuses + officer skills, with a power-brownout
  multiplier. Anything asking "how far can this ship jump" asks `stats()`.
- **Views subclass `ui.widgets.View`** and implement `build()`; the base class
  clears and rebuilds the column on every refresh. Simple and fast enough — a
  full screen is a few hundred widgets.

## The parts that will bite you

- **`HULL_SCALE` in `sim/ship.py`** converts the descriptive `hull` figures in
  `data/chassis.py` into combat hit points. Chassis numbers are written to read
  sensibly against each other; this constant tunes fight length. Change it and
  every engagement in the game changes.
- **`MAX_LANE` in `world/galaxy.py`** guarantees no star sits further from its
  nearest neighbour than a starting hull can jump. Without the relaxation pass
  that enforces it, some seeds strand the player on turn one.
- **`GRIND_TURN` / `MAX_TURNS` in `sim/combat.py`** stop two well-armoured hulls
  grinding forever. Armour is also floored at 15% damage leak-through for the
  same reason.
- **Save identity**: `game.ship` must be the same object as its entry in
  `game.fleet`. `load_game()` re-links them after decoding; damage would
  otherwise apply to a copy.
- **Transient fields**: anything on a dataclass marked
  `metadata={"transient": True}` is skipped by the save codec. `Game.ship_stats`
  holds references to the content tables and must never be written to a save.
- **Qt mnemonics**: an `&` in a button label becomes an accelerator underscore.
  Write "and".
- **Adding a hull family** means touching six places: `LAYER_SETS`, `ACCEPTS`,
  `FAMILY_LABEL`/`FAMILY_TINT`/`FAMILY_NOTE`, `BASE_POWER`, `BUILD_NEED`, and
  `NO_REGEN` if it cannot heal — all of them in `data/hull_types.py`. The test
  suite checks every family for all six, and that its layer weights sum to one.
- **Xenotech ids live in `research.unlocked` alongside real technologies.**
  Anything walking that list must tolerate ids that are not in `TECH_BY_ID` —
  `tech.bonuses()` already skips them, and the gate check in `test_sim.py`
  accepts either vocabulary. Alien passive bonuses are folded in separately by
  `Game.recompute()`.
- **Study banked past a prerequisite is kept, not lost.** You can dig up the
  Phase Loom before you understand the Null Seam; `xeno.settle()` runs on the
  clock and incorporates anything whose moment has arrived.
- **Colony effects are a closed vocabulary.** `test_sim.py` asserts that every
  key in a `ColonyClass.effects` is one the game actually reads, so a typo in a
  station definition fails the suite instead of silently doing nothing.

## Tests

`python -m seedfall.tests` — no dependencies beyond PyQt6 itself.

- **`test_sim.py`** drives the rules headlessly: sector generation and
  determinism, every chassis and part, tech-tree reachability, trade, colonies,
  building, combat outcome distributions, Bloom pacing, save round-trip.
- **`test_ui.py`** builds the real `MainWindow` on Qt's `offscreen` platform and
  paints every screen and every tab, including a live engagement. It stubs
  `win.dialog` because `QDialog.exec()` would block.
