# Innovation 5 — Freight lines (stream "lines")

A trading house, chartered at a Station or Fleet Hub, runs **lines**: a hauler
of your own, a hired master, two ports, a good, a buying rule, a selling rule
and a cadence. Every trip trades through the real counters on the sector's
clock (sector time), pays wharfage, moves both prices, and meets the risk of
every system it crosses.

## New files

| File | What it holds |
|---|---|
| `seedfall/data/freightlines.py` | fees, upkeep, risk tables, cadences, ledger kinds — every figure a house pays or risks |
| `seedfall/sim/freightlines.py` | the front door: `TradingHouse`, `FreightLine`, charter, deposit/withdraw/sweep, open/stop a line, `tick`, the month's `settle` |
| `seedfall/sim/linetrips.py` | a trip as a state machine (ferry → load → out → sell → home): the till (buy/sell through `quote_buy`/`quote_sell`, `wharfage.collect`, `apply_trade`/`apply_sale`, `trade._bought`/`trade.imported`), standing under a cap, insurance, wear and repair, the master's judgement (`judged`) |
| `seedfall/sim/lineroute.py` | the hop list (from `reach.routes_from` at the hauler's jump), legs (days, mass), risk from `piracy.lawlessness`, Bloom and `war.spoils`, and `roll` — one function prices risk, one rolls it on the same numbers |
| `seedfall/sim/lineforecast.py` | the forecast: throwaway twins of the two stock rows aged with `economy.tick_market` itself at mean dice, other lines' flows included; `suggest` = the freight desk's runs priced as lines |
| `seedfall/sim/lineledger.py` | the only writer of the house account; `reconcile` |
| `seedfall/sim/haulers.py` | which hulls may haul (`can_haul`), and used cargo hulls bought at a power's yard |
| `seedfall/sim/masters.py` | `Master`: the recruit-desk pool, hire, pay back wages, dismiss, payroll, loyalty, quitting |
| `seedfall/ui/house_panel.py` | the "Trading house" tab on Holdings: charter, lines table, account, masters, haulers, ledger |
| `seedfall/ui/house_dialog.py` | the new-line dialog: form, the desk's three suggestions, the forecast from `open_terms` |
| `seedfall/tests/test_freightlines.py` | suite `freightlines`, 15 checks |
| `seedfall/tests/lines_kit.py` | fixtures for it |

## Shared / other-owned files touched (one line per hunk)

- `core/ids.py`: `KINDS` gains `"line"` and `"master"` (3 lines, end of the dict).
- `core/state.py`: `house: object | None = None` appended after `crew_leaving` as ONE line with a trailing comment — **the file is now exactly 500 lines**, the limit; the next stream's field needs a line found elsewhere.
- `core/sectortime.py`: import `freightlines as lines_sim`; one-line hook `lines_sim.tick(game, n)` in `economy`, after `exchequer_sim.settle`.
- `sim/ship.py`: `Ship.line_id: int | None = None` appended after `launched_on`, under a comment.
- `sim/consorts.py`: `can_sail` refuses a hull on a line, with a reason.
- `sim/consorts.py`: `can_take_command` refuses a hull on a line, with a reason.
- `sim/shipyard.py`: `scrap` refuses a hull on a line.
- `ui/empire_view.py`: a `tab` class attribute, a two-tab `TabBar` ("Holdings", "Trading house") via `_tabs`/`_switch`, and an early return after the heading when the house tab is drawn. A later Voyage tab adds one tuple to the TabBar list.
- `ui/yard_view.py`: the fleet list shows a hull on a line as "away on a freight line" (no buttons).
- `tests/suites.py`: one row appended, `freightlines`.
- `tests/tripwire_kin.py`: three `KIN` rows appended (`freightlines`, `haulers`, `masters` → suite `freightlines`), as `test_harness_guard` requires of a module with tuning constants.
- `data/help.py`: one topic appended, `house` (screen `empire`).
- `sim/manual.py`: one fact appended at the end, `house`.

## Measurements

- **Forecast vs realised** (50 seeded trips, fixture route): at mean market dice, completed trips cleared 13,066 against a forecast 13,060, 34.4 days against 34.2; with live dice −0.9% of the cargo's cost.
- **Saturation**: one line 5 trips at 8,201 a trip (wages and upkeep in); five lines on the route 7 trips at 2,897 (−65%), the route clearing 20,276 against one line's 41,003 in 180 days.
- **Loss rates** (396 hauler routes, 8 sectors, steady master): lawless routes 6.0 / 7.8 / 13.4% (p10/median/p90); policed 0.5 / 0.5 / 1.0%, 2.05% at the single worst.
- **Payback**: s5, two new TENDERs from Marrow's Watch (62,100 out): 11 months. verge-7, the house bot's one used TENDER (27,231 out): +26,262 net in 13 months. verge-7, two CARAVELs on silicon (179,860 out): 3 months, on a 63,560 first trip, then flat.
- **Bots, 3-year purse** (trader / explorer / trader-house): verge-7 37 / 54,677 / 15,521 + 27,431 in the house + a hull; s5 3 / 41,819 / 34,840 (never chartered); alpha-1 1 / 48,737 / 49,933 (never chartered).

## Deviations

- `freightlines.tick(game, n)` takes no `r`: a trip rolls `RNG(seed:line:id:trip)` at departure, so a chronicle without a house draws exactly what it did.
- Used cargo hulls can be **bought** at a power's yard (`sim/haulers.py`, 70% of the full bill, 70% hull), because a new TENDER all-in (~31,000) left the bots no working capital.
- Masters refuse to sail a closed spread (judged on the projected arrival price), because without it two lines on one route lost 159,000 in fifteen months.
- The solvency guard is mirrored in `test_freightlines`, not added to `test_solvency`.
