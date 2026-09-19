# Stream B · interface — changes for the maps

Review items #21–#29, save slots with a chronicle picker, and four file
splits. This note is for Phase 3 to fold into `seedfall/INTERFACE.md` and
`IMPROVEMENTS.md`; neither was edited.

## New modules

| Module | What it holds |
|---|---|
| `ui/view_base.py` | `View` (moved from `widgets.py`, re-exported there lazily), `Pane` (a scrolling column that re-measures itself), `WrapRow` (side by side when it fits, stacked when not), and `View.keep()`, which lets a screen keep widgets across a rebuild |
| `ui/log_panel.py` | The ship's log, moved from `window.py`. It appends only new entries, folds below `FOLD_BELOW` = 1300 px, and puts a ✓/✕/! glyph in front of good, bad and warning lines |
| `ui/focus.py` | Remembers the focused control by `objectName` (or its text, and which one of that name) across `View.refresh`, and puts the focus back |
| `ui/flow.py` | `Flow`: widgets that wrap onto as many lines as the width needs, packed line by line |
| `ui/battle_orders.py` | The battle's orders, split from `battle_view._orders` (136 lines): `acts`, `fire_buttons`, `ability_buttons`, `other_buttons`, `consequences` |
| `ui/star_chart.py` | `StarChart`, `marker_radius`, `FACTION_COLOUR` and `place_name`, moved from `map_view.py` (which re-exports the first two). Star names are placed without overlapping |
| `ui/tech_tree.py` | `TechTree`: one branch's cards, changed in place; known technologies fold into one line |
| `ui/market_grid.py` | `MarketGrid`: the Port's price board, changed in place; the quantity you typed survives a purchase |
| `ui/layer_row.py` | One hull-layer row, shared by the Ship screen and both hulls in a battle; it adds "critical" and "gone" pills |
| `ui/viewport_target.py` | The target, its bracket and the boom, split from `viewport.py` |
| `ui/popout.py` | `open_one`/`keep`: every pop-out gets `WA_DeleteOnClose`, and `win.<name>` is cleared when it is destroyed |
| `ui/thrust_pad.py` | One `ThrustPad` for the bridge, the conn console and the flight controls |
| `ui/chronicle_picker.py` | The title screen's list of chronicles (Resume, Load, Delete, recovery, `.bak`), plus `save_as` for the menu |
| `core/slots.py` | Named slots under `<save dir>/slots/` (or `<stem>.slots/` for a save not called `save.json`); `save_as`, `delete`, `listing`, `read_summary`, `summary_of` (loading goes through `state.load_game(path)`) |
| `sim/commitments.py` | `take_contract`, `abandon_contract`, `plant_seed`: acts that used to log from `ui/` |

## Moved or reshaped

- `widgets.View` → `view_base.View`. The refresh loop skips anything returned by `keep()`.
- `window._build_log`, `_refresh_log` and `_settle_log` → `log_panel`. The window keeps `log_area`, `log_inner` and `log_col` as attributes, because `test_window` reads them.
- `window.resizeEvent` is new and folds the log.
- `hud.build`:
  - the meters are a 2×2 grid;
  - the position and the ship's name are `widgets.Elided`;
  - the Instruments and Help buttons are gone. The Instruments menu gains "Choose…", Help is on F1, and `MainWindow.instruments` still has a caller.
- `widgets`:
  - `button(..., why=)` gives a disabled button its reason as the tooltip;
  - `Card` takes focus, presses on Space and Enter (deferred), and gets an `accessibleName` and an `objectName` of `card:<name>`;
  - `Pill.set_tint` is new;
  - `Elided` is new.
- `theme`:
  - flat buttons use INK2 on LINE2;
  - disabled buttons use the new `INK_OFF` with a dashed border, and that rule comes last so it wins over every kind;
  - labels, rows and checkboxes inside panels and cards have transparent backgrounds, which removes the dark bands;
  - buttons, nav, tabs and cards show focus;
  - `QListWidget` is styled.
- Sector Chart:
  - the picked star's panel and a destination list (`PickList`; Enter picks on macOS as well) sit beside the chart;
  - the legend shows the powers' colours;
  - the reaction mass reads through `core.util.reaction_mass`.
- Battle:
  - two `Pane`s, with the orders pinned on the left and the readout on the right;
  - the last turn's report sits under the heading;
  - `BattleView.fills = True`.
- The research tree (`tech_view`) and the Port board (`port_view`) implement `keep()`.
- `pilot_panels.two_columns` is a `WrapRow`.
- The Pilot board's duplicate "Autopilot" row is gone; its narration is `sim/instruments.computer_note`.
- "Kill relative motion" goes through `flight_clock.computer_press`.
- `viewport_hud.world(conn)` caches `preview.track` and `collision.scan` once per flight state.
- Ground map: every feature's ring carries a letter (`expedition_view.MARK`), and there is a legend under the map.

## Rules moved from `ui/` to `sim/` (#28)

Each returns `{ok, why, text}` and writes its own log line.

| Where | New or changed function |
|---|---|
| `sim/rumours` | `board()`, keyed on seed, port and month; it no longer advances `game.rng` on every redraw |
| `sim/crew` | `pool_at`, `shore_leave`, `pay_off`, `SHORE_LEAVE_DAYS` |
| `sim/services` | `repair_quote`; `repair(game)` no longer takes a price from its caller |
| `sim/research` | `set_aside` |
| `sim/inquiry` | `begin_confirming` |
| `sim/industry` | `licence` now logs |
| `sim/shipyard` | `start_build` and `apply_refit` log |
| `sim/robots` | `build` and `scrap` log |
| `sim/hostiles` | `toggle` |
| `sim/engage` | `fire_on` |
| `sim/tribunal` | through `_entered` |
| `sim/clemency` | through `_written`, plus `pay_debt` |
| `sim/minigames` | `begin_decoding`, `finish_decoding` |
| `sim/dormancy` | `bring_up` |
| `sim/territory` | `answer` logs |
| `sim/berthing` | `break_off`, `stand_down` |
| `sim/flightdeck` | `lay_course`, `drop_course` |

`core/util.reaction_mass(tonnes)` is the one format for reaction mass ("19.4 t").

## Saved data

- **No new dataclass fields.**
- A save payload is now `{"version", "summary", "state"}`. `summary` comes second, within the first 4 KB, and holds seed, day, credits, ship, chassis, system, origin, ending and a save time.
- Saves without a summary still load and still list.
- `core/state.load_game(path=None)` takes a path, and a failed validation quarantines that path rather than the save in play.

## New suites

| Key | Module | What it pins |
|---|---|---|
| `fit` | `test_fit` | No screen overflows at 1040×680; the battle's orders are in view at 1360×880 and pinned at the minimum; the HUD fits and its captions don't overlap; the log folds; a no-op refresh draws nothing; the tech tree and the Port board change in place; `WrapRow` and `Flow` wrap; star names don't overlap; flat ≠ disabled |
| `keyboard` | `test_keyboard` | Space on a card sets a project; focus survives a rebuild; Enter on the destination list picks; accessible names; every disabled Port/Research button says why; unique ground-map letters |
| `uirules` | `test_uirules` | The #28 moves; AST scans for `add_log(` and `.rng(` in `ui/` against a reasoned allow-list |
| `slots` | `test_slots` | Named chronicles: redirected directory, round trip, head-only summary, old saves, delete, title picker, Save as… |
| `popouts` | `test_popouts` | Open/close cycles of every pop-out leave no widgets behind |
| `flightsame` | `test_flightsame` | Seven cameras in one beat fly the predicted path once |

## Checks updated because what they pin moved

- `test_length`: removed the `ui/widgets.py`, `ui/map_view.py` and `ui/viewport.py` rows. All three are now under 500 lines.
- `test_sights` reads `viewport_target.draw` in place of `Viewport._target`.
- `test_bridge`: the axis check finds the buttons by `thr_<axis>`, because the pad prints m/s under the name.
- `test_bridge_marks` asks `instruments.computer_note` (the duplicate row is gone).
- `tripwire_kin` gains a `slots` fast path.
- `suites.py`: six rows added, and `slots` is marked as a Qt suite.
