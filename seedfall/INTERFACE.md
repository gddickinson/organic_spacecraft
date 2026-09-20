# INTERFACE.md — SEEDFALL navigation map

Read this before opening any source file in `seedfall/`. It is short on
purpose, because the module-by-module maps are generated from the code (see
"The maps" below).

- **What is open:** [`IMPROVEMENTS.md`](IMPROVEMENTS.md), the live backlog.
- **Why each part is shaped as it is, and what bit us:**
  [`notes/`](notes/README.md), the design history from before 2026-09, text
  unchanged.

## What this is

**SEEDFALL** is a native PyQt6 space exploration, trading and combat RPG, a
modern *Starflight* with a *Civilization* layer. It is built on the GESTALT
design programme in this repository, which supplies the grown hulls, the
six-layer hull, the phosphorus bottleneck, the wet/dry control stack and the
licence regime.

You command a hull in the Verge. You survey, trade, fight or refuse to, and
research. You design hulls from five families. You plant colonies, answer to
four powers and their laws, and deal with the Bloom. Ten endings are reachable.

Since 2026-09 the Verge is also a larger place, with ten new systems:
- **The Far Reaches:** three regions behind relightable deep anchors.
- **The Kith:** a living alien people in the Cradle, met through a lexicon
  and a gift economy.
- **Stellar phenomena:** flares, comets, ion storms and a nova.
- **Nemeses and the hunt:** named rivals who remember you, a bounty board,
  and running dark.
- **The living hull:** grown hulls adapt to what they go through.
- **Freight lines:** a trading house whose haulers work the markets.
- **The Assembly:** four powers voting on resolutions that change the rules.
- **Officer arcs:** each officer's own three-beat story.
- **Renown and the Voyage:** ranks, milestones on every ending, the first
  officer's counsel, and a memoir kept in the Hall of Captains.
- **A synthesised soundscape.**

The designs are in `../reviews/2026-09-17/innovations/`, and what each
landed as is in `../reviews/2026-09-17/changes/`.

## Running

```
python -m seedfall                  # title screen: chronicles, slots, the Hall
python -m seedfall --new            # straight into a new chronicle
python -m seedfall --seed verge-7   # a specific sector
python -m seedfall --new --bridge   # and a loopback control socket
python -m seedfall --help           # every option (parsed before Qt loads)
python3 play.py                     # the same, from the repo root's launcher
pip install -e ".[dev]"             # from the repo root: pyproject.toml
```

The flags are `core/cli.py`'s, parsed before Qt is imported, so `--help`
and a mistyped flag are answered without opening a window. **A new
chronicle goes through `core/loading.begin_new`**, which keeps the one in play
as a "Set aside" slot before clearing it; a screen that calls `clear_save`
itself fails the `cli` suite.

The save is `~/.seedfall/save.json`, with named slots under
`~/.seedfall/slots/` and the Hall in `~/.seedfall/hall.json`. **Always ask
`core.save.save_path()`**, never a constant:
- It honours `SEEDFALL_SAVE`, which the test package sets per process.
- A process with no screen (Qt `offscreen` or `minimal`) gets a scratch file
  unless `SEEDFALL_SAVE` names one. An offscreen probe once overwrote a
  player's save.

## Tests

```
python -m seedfall.tests -j 8           # every suite, one process each (~3 min)
python -m seedfall.tests --fast -j 4    # the cheap ones, as CI runs on a push
python -m seedfall.tests sim combat     # just these;  --list names them all
python -m seedfall.tests --coverage     # per-suite coverage, module→suite map
pytest -k "combat or window"            # the same suites through pytest
python -m seedfall.tests.maps --write   # regenerate the package maps
```

- **Suites:** about 235, holding about 1,750 checks. `tests/runner.py` runs one
  process per suite.
- **The run's own honesty:** an unknown suite name exits 2, a suite that runs
  no checks is an error, and a suite that raises during setup is one failure,
  not the end of the run.
- **Read exit codes from the interpreter**, never through a pipe.
- **Under test**, `core/save.STRICT` refuses to save an attribute that is not
  a declared field.

## The maps

| Package | Map | What lives there |
|---|---|---|
| `core/` | [core/INTERFACE.md](core/INTERFACE.md) | the save and its registry, per-chronicle ids, loading and validation, the clock and its two phase modules (`shiptime`, `sectortime`), the guard for broad excepts |
| `data/` | [data/INTERFACE.md](data/INTERFACE.md) | content tables: hulls, parts, tech, factions, lore, help, lessons, the Reaches, the Kith, phenomena, milestones, sounds |
| `world/` | [world/INTERFACE.md](world/INTERFACE.md) | the sector, the regions beyond it, planets, markets |
| `sim/` | [sim/INTERFACE.md](sim/INTERFACE.md) | every rule, grouped by system |
| `ui/` | [ui/INTERFACE.md](ui/INTERFACE.md) | every screen and widget, grouped by screen |
| `bridge/` | [bridge/INTERFACE.md](bridge/INTERFACE.md) | driving a game from outside: protocol, argument checks, server, client |
| `tests/` | [tests/INTERFACE.md](tests/INTERFACE.md) | the suites and the kits they share |

Each map is one row per module: the first sentence of the module's own
docstring. The `maps` suite fails when a map is missing a module.

## How the layers connect

```
data/  ──►  world/  ──►  sim/  ──►  ui/  ──►  __main__
                    core/ is available to everything
```

- **One clock.** `Game.advance_days(n)` is the only thing that writes the
  calendar. `core/clock` chops any span into single days, and each day runs
  as phases in the day's own order:
  - `core/shiptime` (the crew's clock: bench, hull, aboard, crew);
  - `core/sectortime` (the Verge's clock: holdings, economy, reckoning).

  The phases draw from one `game.rng("tick")` stream, so the order *is* the
  rules. A step with no whole day in it runs nothing and draws no luck. A
  nested advance raises `ClockReentered`.
- **New daily behaviour is one line** in the right phase function.
- **One clock, and one animation timer that is not a clock.** A collision
  *stops* the flight clock, so the picture of it would be painted once and
  then hold still. `ui/effect_clock.py` is a second 40 ms timer that repaints
  the flying surfaces while something is on the glass. It advances no
  calendar, bills nothing and draws no luck; `tests/test_shock` holds it to
  that.
- **What a contact looked like is `sim/shock.py`'s.** The one door between
  "the approach resolved" and "the window draws it": it reads the flight and
  hands back a `Shock` — kind, bearing, both sides' damage, the words — and
  `ui/effects.py` decides only how long it stays and how hard. A screen never
  works out what an impact cost; it asks.
- **`sim/` never imports Qt,** and `ui/` never decides anything.
  - A screen calls a sim act that returns `{ok, why, text}` and writes its own
    log line.
  - `tests/test_uirules` keeps `add_log(` and `.rng(` out of `ui/`, apart from
    an argued allow-list.
- **`ship.stats()` is the single source of derived ship numbers:** chassis,
  parts, research, officers, traits, arc signatures and adaptations.
- **Views subclass `ui/view_base.View`.** A screen that updates in place
  (Tech, Port, the log) says so through `View.keep()`, and one that can give
  room back before it is measured says so through `View.fit()` — the bridge
  is the only one, and what it gives is the camera.

## The rules that bite

Each rule has cost a real bug. The suite enforces most of them.

**Saving**
- **Anything you can be in the middle of lives on the `Game`, as a declared,
  defaulted field** of a `@register`'d dataclass:
  - `core/save.ensure_registry` imports every saved type before a read;
  - `encode` refuses an unregistered dataclass;
  - `STRICT` refuses an undeclared attribute;
  - old saves load, migrated by `save.MIGRATIONS`, and a bad file is moved
    aside as `.bad`, never deleted.
- **Ids come from `core/ids.next_id(kind, game)`.** Each chronicle keeps its
  own book, bound on new, on load and on every advance. A process-wide counter
  once let a new hull take the flagship's uid after a reload.
- **Cross a process boundary to test persistence** (`persistence`). An
  in-process round-trip passes on state that only the process holds.

**Rules and randomness**
- **A screen never draws luck,** and nothing drawn while viewing may move the
  chronicle's `game.rng` stream. Seed per-thing randomness from its own key,
  such as `RNG(f"{seed}:board:{sid}:{epoch}")`.
- **Preview equals act.** Every screen that offers a commitment states its
  consequence, and a check performs it and compares.
- **Efficacy.** Every feature that claims to move a number has a check that
  switches it off and sees the number move (`tests/efficacy.Lever`).
- **Nothing computed that nothing consumes** (`reachable`, `declared`).
- **Money is never conjured.** Every credit comes through a counter the
  market saw, or out of a named power's purse (`solvency`, and the house
  ledger's `reconcile`).
- **Materials come through `sim/stores`** (`held`/`take`), the one door, with
  the depot drawn first.
- **Battles end through `battle_state.finish` / `aftermath.resolve`.** A new
  result id breaks every outcome tally, and a loss kills in the sim.

**Where the ship is and what it hears**
- **Where the ship is** has two doors:
  - `flight.base_position` is the recorded place, written only by `hold_at`
    and `stand_off`;
  - `flight.ship_position` is where she is now.
- **`conn.pos` is not an offset from the ship.**
- **Distance across regions is infinite** except through a deep gate
  (`world/galaxy.distance`). What the endings count is Verge-only, through
  `world/galaxy.verge`. The Verge's generation and the ancient Weave sites
  must stay byte-identical when a region opens.
- **A despatch from somebody aboard** crosses no distance and no weather:
  `comms.send(..., aboard=True)`.

**Qt**
- **Every raw `paintEvent`** carries `painting.alive` and
  `@painting.safe_paint`. A signal handler must not destroy its own emitter:
  use `widgets.defer`, and look widgets up again when the deferred call runs.
- **`&` in a button label is an accelerator.** The Screens menu owns the
  screen keys, and the rail binds none (`screenkeys`).

**Code health**
- **Under 500 lines, every file** (`length`: 499 is the limit and no debts
  are recorded).
- **Every `module.name` read must exist** (`exports`). A re-export that a
  caller reads needs `# noqa: F401` on *its own line*.
- **Never kill test processes by pattern.** Other suites may be running.
