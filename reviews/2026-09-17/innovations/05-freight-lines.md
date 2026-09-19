# Innovation 5 — Freight lines (economy)

## Why

The play-test's money measurements:
- An honest all-in freight trader was broke by year 3 on 4 of 5 seeds.
- Mining is the worst-paid activity (129 cr/day; already on the backlog).
- The explorer stalls mid-game.
- Colonies are the only thing that earns while you are elsewhere, and they
  now have a ceiling.

There is no way to **scale** trading: every tonne moves in your own hold,
while you sit in it. The freight desk (`sim/freight.py`) already ranks runs
honestly by what the voyage clears, and the market already saturates
(`apply_sale`).

## What the player gets

**A trading house.** You charter it once, at a Station or Fleet Hub, for a
fee. It can then run **lines**: a hauler hull with a hired **master** that
works a route on its own, for as long as you keep it, trading through the real
markets.

- **Haulers are real hulls in your fleet.** Build or buy a cheap freighter
  class. The fabricated family already has cargo classes, and a grown one can
  serve. A hauler on a line is away: it can't escort, and it is marked on the
  Yard/fleet list.
- **Masters are hired like officers**, at a recruit desk, with a skill (a
  margin on buying and selling, and route judgement) and a loyalty that pay
  and losses move. A master who is paid late or loses a hauler may quit.
- **A line sets:**
  - an origin port and a destination port;
  - a buying rule: which good, the max unit price, and the tonnage (up to the
    hold);
  - a selling rule: the minimum unit price, or "whatever it fetches";
  - a cadence: continuous, or a fixed cycle.
- **Each trip resolves on the clock**, in sector time:
  - transit days come from the real distance and the hauler's drive;
  - the buy and sell go through `trade`/`market` (price impact via
    `apply_sale`, so a line that runs too often saturates its own route);
  - wharfage is paid through `sim/wharfage`;
  - risk comes from the systems crossed: piracy `lawlessness`, Bloom level,
    active war;
  - outcomes: completed, delayed, robbed (cargo lost, hull damaged) or lost
    (hauler destroyed; rare, on lawless or Bloom routes);
  - the hull wears and repairs at ports on the route for a cost.
- **The house keeps a ledger.** Per-line profit and loss, lifetime and last 90
  days. Money is swept to the captain's purse on a cycle, or kept in the house
  account for upkeep.
  - **Money sinks:** charter upkeep per month, master wages, hauler upkeep and
    repairs, insurance (optional; pays out on a loss).
  - **The forecast is honest:** each line shows the expected profit per trip
    and per 90 days, with risk shown as a probability of loss. A check runs 50
    seeded trips and compares with the forecast.
- **It feeds the rest of the game.** Lines keep the register's quotes fresh
  for the Cartel ending (a line's two ports count as "priced" while it runs).
  Heavy trade with a power's ports raises standing a little (capped per
  period, so it can't become the next churn exploit). A line through a war
  zone may be seized.

## Design

- **Rules:** `sim/freightlines.py` covers the house, lines and trip
  resolution, the forecast and the ledger. `sim/masters.py` covers hiring,
  wages, loyalty and quitting; keep officers and masters separate.
- **State:** `Game.house: object | None = None` holds a registered
  `TradingHouse` with `lines`, `masters`, `account`, `ledger`,
  `chartered_at` and `insured`. `Ship.line_id: int | None = None` on the hauler
  hull. Ids come from `core/ids.next_id("line")` and `next_id("master")`; add
  both kinds to `core/ids.KINDS`.
- **Clock:** `freightlines.tick(game, n, r)` from `core/clock._one_step`, in
  sector time. Trips advance in whole days.
- **No free money:**
  - Every credit that reaches the purse comes from a counter sale that
    `apply_sale` saw.
  - The costs are real.
  - Add an invariant check that the house ledger sums to the purse deltas
    (the project has a `solvency` suite: "money cannot be conjured"; extend it
    or mirror it).
- **Risk:** reuse `piracy.lawlessness(game, system)`, `system.bloom` and
  `war` for the systems a route crosses. The route is the straight hop list
  from `reach`/`flight` pathing, or the start and end systems if it is a
  single jump.

## UI

A "Trading house" tab on the Holdings screen (`ui/empire_view.py` hosts it;
the panel lives in a new `ui/house_panel.py`):
- **Charter the house:** the fee and the monthly upkeep are stated.
- **Lines table:** route, good, cadence, master, hull condition, last trip,
  and profit for 90 days and lifetime.
- **New line dialog:** pick a hauler, a master, the ports and the rules. It
  shows the forecast before you commit, drawn from the freight desk's
  ranking, and offers the top 3 suggested routes from `sim/freight`.
- **Masters:** hire, pay, dismiss.
- **Ledger** and the sweep to the purse.

Log lines for trips go through the sim (rich text in the log only on notable
events: a loss, a record profit, a master quitting).

## Balance targets (measure with bots)

- A house with 2 lines on good routes returns its charter plus haulers in
  about 8–14 months.
- 5 lines on one route saturate it until profit per trip falls by more than
  half.
- Lines on lawless routes lose 5–15% of trips; on policed routes under 2%.
- **The house must not make money from nothing:** no line earns if its buy and
  sell prices are equal after wharfage.

## Tests (new suite `test_freightlines`)

- The line forecast equals the realised mean over 50 seeded trips, within a
  stated tolerance.
- Saturation: margins fall as trips stack on one route.
- Risk: a lawless route loses more trips than a policed one; seeded, counted.
- Solvency: the house ledger reconciles with the purse.
- Master loyalty: unpaid wages lead to quitting.
- A hauler on a line can't sail as an escort (`consorts.can_sail` refuses
  with a reason).
- Cross-process save of a house with lines mid-trip.
- The previews on the panel equal the acts.
