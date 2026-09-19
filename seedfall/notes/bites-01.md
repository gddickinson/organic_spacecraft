# The parts that will bite you (1 of 5)

Moved out of `seedfall/INTERFACE.md`, which is now only the map. Text unchanged.


- **`MainWindow.__init__` refreshes before it is fully built.** The tutorial bar
  is constructed forty lines into `__init__` and refreshes itself on
  construction, and it asks `win.current` — which was assigned *after* it. So
  opening a chronicle that already had a tutorial running raised
  `'MainWindow' object has no attribute 'current'`, which is the reload case: a
  save made mid-lesson. Every check built the window first and started the
  tutorial after, so none of them went through that door. `current` and `views`
  are initialised at the top now; anything a child widget asks about during
  construction has to exist before the child does.
- **Two true-sounding claims can contradict each other, and the answer is
  usually scale.** "A tutorial step that is already true should skip itself" and
  "a captain who did it already is not advanced for free" are irreconcilable
  from state alone — one incidental survey and two years of them are the same
  fact at different sizes. `tutorial.SETTLED_IN_DAYS` is the distinction: inside
  the first month everything is taught, after it what the chronicle can show you
  have done is stepped over. Both checks pass unchanged.
- **Price is not value, and the exchequer chose by price.** `_invest` took the
  cheapest work it could afford — and the equilibrium the upkeep curve is built on
  means the cheap works are the ones that never pay: promoting an outpost to a
  station adds 90 a day of yield and 90 a day of upkeep, *net nothing*, and
  promoting a station to a hub is 60 a day worse than not bothering. Founding a
  berth clears 60 a day; settling ground clears 32. So "take the cheapest" bought
  the two works with no return before either with one, and the powers planted
  **six settlements in year one and none in the seven years after**. It sorts by
  payback now, with never-pays last by cost — which is exactly what a Fleet Hub
  should be: what you buy with money you have nothing better to do with.
- **`Body.id` is the body's index within its system.** 155 bodies in a sector
  share **six** distinct ids, so anything keyed on `body_id` alone matches a body
  in every system at once. `Colony` has keyed on the `(system_id, body_id)` pair
  since it was written; `sim/settlement.py`'s first draft did not, and six
  settlements masked the whole sector — `sites_for` went from twenty-odd
  candidates per power to zero inside a year and nothing was settled again.
- **A quoted payback has to count the years the thing loses money.** A settlement
  manages 25% of its output on day one, which is 11.5 a day against 14 of upkeep:
  **−2.5**. Two fresh ones moved a power's income *down*, 724 a day to 720.
  Dividing cost by the mature rate reads 1,000 days where integrating the ramp
  gives **1,485**, and the difference decides whether settling looks better or
  worse than founding a berth. `settlement.payback_days` is the one door and
  `exchequer.payback` asks it.
- **A layer that cannot ask who is looking should not price what it finds.**
  `world/planets.survey_body` used to add `lf.value * 0.25` of research for every
  organism it catalogued — inside `world/`, which by the layer rule cannot see the
  `Game` and therefore cannot know whether anybody aboard can read a radiotroph.
  The grant moved to `sim/biology.harvest`, so the same body pays two captains
  differently: **116 points of research unread against 149 read** on the same
  catch. The constant went with it (`SPECIMEN_SHARE`), out of the middle of the
  survey arithmetic.
- **Grouping by a key is how you find out the key was lying.** `FORMS` is a pool
  of body plans — "jointed swimmer", "plated crawler" — and one entry was
  `"chemotrophic reef"`. The generator picks the form and the metabolism
  independently, so it cheerfully filed a chemotrophic reef as a photoautotroph,
  and nobody could see it until the catalogue put the two beside each other. There
  is a check now that no body plan contains a biochemistry stem.
- **Two guards can excuse each other, and one pair did for a whole feature.**
  `test_grants` asks whether every colony effect is read *by name* somewhere;
  `test_declared` asks whether every declared field is read. The `drift` effect
  passed the first because `sim/ship.py` mentioned `"drift"` — to set
  `Stats.has_drift` — and `has_drift` passed the second because it was on the
  allowed list as a flag waiting for a mechanic. So the colony effect was
  "consumed" by a dead ship stat and the stat was excused by a promise, and
  between them **a 21,000-credit module and an 18,000-credit colony did nothing
  at all**, with both descriptions promising it plainly. When you excuse a field,
  check that nothing else is leaning on the mention.
- **Traffic was always derivable anywhere and only ever asked about here.**
  `traffic.in_system` is a pure function of the sector and the day, so the hulls
  working *any* system have always been computable — and every caller passed the
  system the ship was in. `traffic.plotted` and `mesh_reaches` are the gate now:
  you see where you are, where a CHORUS Node aboard plus a visit lets the mesh
  report, and any system holding a Node colony of yours (`colony.drifting`,
  written beside `colony.watching` rather than as another published key nothing
  opens). The chart marks systems reporting hulls nobody claims, and
  `ui/mesh_panel` says which and what.
- **"Inline hints" turned off under four per cent of the hints.** `sim/options.py`
  opens with the rule that *an option that changes nothing is a lie*, and the
  setting was gated in exactly one place — `View.hint`, called **10** times
  against `widgets.note`'s **270**. The options page describes it as "the short
  explanations under panel headings", which is what `note` draws. Measured on the
  port screen: **89 labels with hints on, 89 with them off.** `note` reads
  `widgets.HINTS` now, pushed in by `MainWindow.apply_options` — the function
  whose docstring already said it exists to push settings into the parts of the
  window that hold their own, and the same arrangement `core/llm.py` uses for the
  speech settings. Two things to know if you touch it: a withheld note is a
  **hidden label, not `None`**, because fifteen places add one straight to a
  layout with `addWidget` and Qt answers `None` with "cannot add a null widget"
  (a hidden widget is excluded from its layout and takes no space); and
  `widgets.HINTS` is module state for the life of the process, so a check that
  turns hints off **must restore them in a `finally`** or every suite after it
  renders without explanations.
- **`conn.apply` takes `ticks` and `throttle` by keyword only, and that is a bug
  fix.** They used to be positional, and four checks called
  `apply(conn, axis, main, throttle)` — putting the throttle into `ticks`, where
  `max(1, ticks)` quietly rounded it to one, and leaving the throttle at its
  default. So every flight those checks flew had **the main drive wide open**,
  which is the one thing `pilot.usable_throttle` exists to prevent: an
  unthrottled drive made a bigger engine *worse*, because one tick of a fusion
  torch is 124 m/s and the computer would light it to trim ten. The checks were
  verifying a ship the game does not fly, and one of them —
  "a lopsided hull still makes orbit, slower and dearer" — was passing for that
  reason. Re-measured at a body where the drive does the work, one engine takes
  **2.32× the time and 1.91× the mass**; at a small body, where an orbit climb is
  thruster work, the same comparison comes out 0.79× and the cap has nothing to
  bite on. If you add a call to `apply`, the signature will not let you make
  this mistake.
- **An approach with nothing left to burn is over.** Every orbit check flew with
  `conn.rcs = 99999`, and `orbits.heights_for` offered a rung on `holdable` alone
  — whether the thrusters are *fine* enough — and never asked whether the
  tank was *big* enough (it does now: `test_climbs` flies the offer on the tank
  `conn.start` found, and the unlimited tank is what hid this for as long as the
  ladder has existed). Flown with the twenty tonnes a hull carries, the high
  rung of a 153 km asteroid spent the lot in about two thousand ticks and then
  ordered a burn every tick for another eighteen thousand, refused each time by
  `can_burn`: nothing moved, nothing was said, the approach never ended.
  `outcome.resolve` now ends it — as `orbit` if the hull is in a sound one, which
  it reports along with the height it actually reached, and as `dry` if it is not
  in orbit and no longer closing. Still closing is left alone: a dry hull can
  arrive on momentum, and taking the approach away from it would be wrong.
- **Two fields were being written and read by nobody for as long as their
  features have existed.** `Rumour.heard_at` recorded the port you were told
  something at, and truth was a per-kind coin flip — so a story about the far
  side of the sector told at a lonely outpost was exactly as good as one about
  the next star over told at a Fleet Hub. `Mind.met` and `Mind.first_met` counted
  how often somebody had dealt with you and since when, while every decision in
  the game came from standing — what you have *done* — and nothing from
  acquaintance — who you *are* to them. Both are read now
  (`rumours.provenance`, `memory.acquaintance`), and the lesson for anything
  similar is that the field being present in the save is not evidence anybody
  consults it. `test_declared` catches a field nothing reads by *name*, which is
  why these two survived: `.met` and `.true` are read all over the codebase on
  other objects.
- **A distance constant has to be measured against the sector, not chosen.**
  Provenance grades a story by how far it has travelled, and the first draft used
  11 and 55 light-years for "local" and "far". Measured over 4,264
  port-to-system distances: median 27, 80th percentile 40, longest 69 — so 55 was
  the 96th percentile and **three per cent of stories ever reached the far end of
  the scale**. At 11 and 42 the bands come out 30/27/44%, and stories run from
  77% true down to 45%.
- **A stock can be genuinely untraded, and the drift must leave it that way.**
  `tick_market` adopted a baseline of 1.0 for any stock that had none, and the
  supply floor lifted a zero supply to 0.02 so that the shim then adopted *that*.
  Between them, a good `make_market` deliberately left out of a port was on sale
  there one day into the chronicle: unlicensed seed is stocked at **9 ports in
  21** and **all 21 sold it after a single day**, which is most of the point of
  contraband gone. A stock with no baseline *and* no supply is skipped now. It is
  the only way a market says "not here", so anything that writes supply or
  baseline has to preserve it — `sim.industry.industrialise` is the one thing
  allowed to open one, and it does so deliberately.
- **Technology reaches markets through `Stock.works`, not through prices.**
  A licensed process multiplies the *baseline* of one good at every berth its
  holder owns, so the daily drift settles onto it and the change is permanent —
  where a shock multiplies the price and lifts cleanly. Keeping the two apart is
  what lets a check tell an industry from a strike, and the first draft of that
  check could not: it read a 6% fall where four of five berths had fallen 11%,
  because the fifth had a strike on and its price had gone *up*.
- **A forecast quotes what the captain would be charged.** `industry.forecast`
  prices a copy of the stock through `buy_price` with the captain's standing and
  haggling in it. A check comparing it against a raw `buy_price(market, cid, 0)`
  read every berth as 40–50% out in the same direction — the signature of a
  scale factor, which here was a trade bonus of 0.48.
- **A port is not scenery any more, and things that cached one will break.**
  The powers keep treasuries (`sim/exchequer.py`): each berth pays its holder
  `level × 90` a day and costs `30 × level²`, so an outpost and a station both
  clear about sixty and a Fleet Hub very nearly pays for itself and no more. A
  surplus founds or promotes one up `world.galaxy.PORT_KINDS`; a deficit takes
  the cheapest one down a step, and an outpost that goes down a step **closes,
  taking its market with it**. Two things fell over the first time one did:
  `test_geography` crashed on `system.market.stock` for a berth it had listed
  eight years earlier, and the register cheerfully offered a two-year-old price
  at a port that no longer existed. Anything that holds a system, a port or a
  market across a passage of time must re-check that it is still there.
  `promote`, `found` and `demote` are the only writers of a port's level, and
  `demote` will not close the berth the player's own hull is sitting in.
- **`tick_market` needs to be told how big the port is.** `make_market` scales
  the opening stock by the berth's level and the daily drift then pulled every
  commodity at every port toward the same `supply × 60` regardless — so within
  about a month a Fleet Hub held exactly as much cargo as an outpost, and the
  level was decorating the opening inventory and nothing else. It takes a
  `level` argument now and `core/clock.py` passes the port's own. Measured a
  year in: outpost 1,300 t, station 1,779 t, hub 2,832 t, holding steady
  instead of converging.

- **`HULL_SCALE` in `sim/ship.py`** converts the descriptive `hull` figures in
  `data/chassis.py` into combat hit points. Chassis numbers are written to read
  sensibly against each other; this constant tunes fight length. Change it and
  every engagement in the game changes.
- **`MAX_LANE` in `world/galaxy.py`** guarantees no star sits further from its
  nearest neighbour than a starting hull can jump. Without the relaxation pass
  that enforces it, some seeds strand the player on turn one. It does *not*
  guarantee the sector is traversable: flood-filling from the start at starting
  jump range reaches between 2 and all 42 systems depending on the seed, median
  13, with a quarter of sectors under eight. Opening the rest means a better
  drive. `sim/reach.py` computes that component, and `reach.plan()` costs the
  way out: the technologies still needed and their research points, the
  credits, and each material with the reachable ports that stock it. **A pocket
  is a long project and not a trap** — measured across 24 walled sectors, the
  smallest of them two systems, every one could supply its own way out. A check
  keeps asking rather than trusting that measurement.
- **One helper feeds the quote and the till.** `market.quote_buy` /
  `quote_sell` apply the grudge bias, and `note_prices`, `trade.buy/sell` and
  `contracts.cargo_cost` all read them. Pricing a contract's cargo with the raw
  `buy_price` while the counter charged the adjusted one put the board's quote
  nearly nine hundred credits out, which `test_cargo` caught the day grudges
  landed. If you add a place that shows a price, use the helper.
- **The tutorial never diverts navigation.** Everything else you can be
  part-way through — a battle, a trench, an aftermath question — is guarded in
  `window.go()`. The tutorial deliberately is not: a tutorial that stops you
  doing the thing it is describing is worse than none, in a game whose premise
  is that there is no track. A check walks all twelve screens with a lesson
  open and fails if any of them diverts.
- **Nothing may touch a widget after emitting a signal that could delete it.**
  Almost every card handler rebuilds its own screen, and `View.refresh`
  unparents the old widgets — which frees the C++ object immediately. `Card`
  emitted inline and then called `super().mousePressEvent(ev)` on a corpse,
  which aborted the process: clicking a body or a technology killed the game.
  `Card` defers the emit by one turn of the event loop. If you add a widget
  whose click rebuilds anything, do the same.
- **Clicking is not the same as pressing a button.** `test_verbs` drives every
  `QPushButton` on every screen, and Qt emits those safely after the press
  completes — so the crash above lived behind what read as full coverage.
  Auditing the rest found 14 line edits, 13 spin boxes and 5 combo boxes that
  nothing had ever touched, and the first one driven **segfaulted the
  process**: the manual's search field rebuilt its own view on `textChanged`,
  which fires mid-keystroke. `test_controls.py` drives every other kind of
  control there is — cards, combos, spinners, typing a character at a time,
  and the ship plan's drag and wheel.
- **`ui/widgets.defer()` is where the rule lives.** Anything wired to a signal
  whose handler rebuilds the emitting widget goes through it. A rebuild that
  replaces a field the player is typing into must also restore focus and the
  cursor, or the field silently accepts one character and no more.
- **`game.day` is a whole number, and `advance_days` is what keeps it one.**
  Callers pass fractions — a short transit, a burn quoted to a tenth of a day —
  and the clock used to take them, drifting `day` to a float. Everything
  downstream assumes an integer: `day % 365`, contract deadlines, chart dates,
  the day a memory formed. The heading bar crashed outright on the first
  fractional day. The fraction is carried rather than dropped, with an epsilon,
  because a hundred tenth-days sum to 9.999999999999998 and would lose a day
  every ten.
- **A driven session must not open behind a modal dialog.** The briefing and
  the tutorial offer both block on `exec()`, so a watcher saw a pop-up while
  the bridge quietly played the game underneath it. `--bridge` skips them, and
  `blocked`/`dismiss` let a caller see and clear anything modal.
- **Anything that blocks needs neutralising before a session can drive it.**
  `QDialog.exec` is the obvious one; `QInputDialog.getText` is *static* and
  does not go through it — the shipyard asks a new hull's name that way, and a
  session that pressed *Lay down* waited ten minutes for an answer nobody was
  going to give.
- **`--bridge` serves the window you are looking at.** `bridge/attached.py`
  puts the protocol in front of a live `MainWindow` and marshals every command
  onto the Qt thread before it touches the game — the socket runs on another
  thread and the interface reads the `Game` from the main one, so anything else
  is a data race. Loopback and token-gated like the headless bridge.
- **`credits` is a builtin.** So is `id`, `type`, `input` and `format`. Calling
  one by mistake does not raise `NameError` — `credits(x)` calls the
  interpreter's easter-egg `_Printer` and fails two suites away as
  "`_Printer.__call__()` takes 1 positional argument but 2 were given". If you
  import `core.util.credits`, import it under its own name.
- **A screen's keys come from `data/screens.py`, not from its position.** The
  rail used to derive them as "1–9, then 0 for the rest", so the moment an
  eleventh screen was added the Codex and the Aftermath both bound `0` and one
  of them had no key at all. The table is read by the window *and* by
  `sim/manual.py`, which is on the other side of the layer rule, so the Keys
  page cannot drift from the rail.
- **The language model is off unless it is switched on, and nothing depends on
  it.** `SEEDFALL_LLM` gates it, `llm.complete()` returns `None` whenever there
  is nothing there, and every speaking path already had to work offline so
  `None` is the ordinary case rather than an error. Speech reads state and
  never writes it, which is what makes the whole feature removable. If you add
  a voice, the written path is the one that has to be good.
- **You hold the technology for everything bolted to your hull.**
  `parts_available` filters the shipyard by what you have unlocked, so a fitted
  part whose technology you lack can be removed and never put back. The shipped
  NAVIS carried three: a Reaction-Mass Organ, a Radiator Bloom and a Mining
  Root. Pulling the drive on day one emptied the slot permanently and left the
  drive dropdown offering nothing at all. `beginning.tech_of()` enforces the
  rule structurally — whatever `new_game` fits, it also grants — so no future
  hull or opening can reintroduce it, and `STARTING_TECH` names the three
  outright so the constant is honest about what a captain knows.
- **An index into `game.system.bodies` is not a location.** `Dig` used to hold
  only `body_index`, resolved against whatever system the ship was in *now*, so
  a trench worked from anywhere else read a different body's fatigue — or
  raised `IndexError` against a shorter body list. Digs are saved, so the wrong
  body outlived the session. `Dig.system_id` pins it and `dig.site_of()` /
  `dig.at_site()` are the only correct ways to reach the ground it is in.
  Anything else that stores a body index needs the same treatment.
- **`GRIND_TURN` / `MAX_TURNS` in `sim/combat.py`** stop two well-armoured hulls
  grinding forever. Armour is also floored at 15% damage leak-through for the
  same reason.
- **`sim/ship.py` owns the thermal rule; `combat` and `flight` both defer.**
  `HEAT_CEILING` and `cook()` live next to `cool()`, because the hull owns its
  own physics and both the guns and the helm put heat into it. `combat`
  re-exports them. Two copies of this rule existed briefly and drifted
  immediately — the guns were bounded and the helm was not, and a captain
  fresh off ten hard burns routed on turn three at 51% hull *holding fire the
  whole way*.
