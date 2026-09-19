"""What a trading house costs, and what a freight line risks.

Every tonne the captain moved used to move in the captain's own hold, with the
captain sitting in it: there was no way to scale trade at all. A house is the
way — a charter from a power, haulers of your own, masters hired to work them —
and every figure a house pays or risks is here, so the forecast on the panel
and the trip on the clock read one table.

The rules are in `sim/freightlines.py` (the house and its lines),
`sim/linetrips.py` (a trip, port to port), `sim/lineroute.py` (the route and
its risk), `sim/lineforecast.py` (what a line will clear),
`sim/lineledger.py` (the books), `sim/haulers.py` (the hulls) and
`sim/masters.py` (the people who sail them).
"""

from __future__ import annotations

# ── the charter ──────────────────────────────────────────────────────────────

#: What a power charges to register a house, by the level of the berth it is
#: chartered at. A house is a Station's or a Fleet Hub's business: an outpost
#: has no counting-house and no recruit desk to find a master at.
CHARTER_FEE = {2: 6_000, 3: 9_000}

#: What keeping the charter costs a month, paid into the same power's purse.
CHARTER_UPKEEP = 300

#: How often the books are done — upkeep, wages, the sweep.
SETTLE_DAYS = 30

#: What a sweep leaves behind in the house account by default, for the
#: payroll; cargoes are bought only with what is above it. A month of one
#: line — a steady master at about 400, a TENDER's five hands at 450, the
#: charter's 300 — is some 1,150, so this is two months of one line. The
#: captain can change it.
RESERVE = 2_500

# ── haulers ──────────────────────────────────────────────────────────────────

#: The hull classes that earn their keep carrying other people's goods: the
#: fabricated family's tug, freighter, refinery and liner, and the grown and
#: hybrid hulls that do the same work. Read by chassis tier, so a class added
#: to the table in one of these trades can serve without a second edit.
HAULER_TIERS = frozenset({"Tug", "Freighter", "Industrial", "Liner",
                          "Harvester", "Breaker"})

#: What a hauler's own hands cost a day each, fed and paid, while she works a
#: line. A berthed hull costs nothing (`upkeep.demand` counts only hulls in
#: company), and a hull that is working is not berthed.
HAND_A_DAY = 3.0

#: Days alongside at each end: working cargo, bunkering, paperwork.
PORT_DAYS = 2

#: Reaction mass a light year, in tonnes — the figure `actions.jump_quote`
#: bills a steady crossing, so a hauler burns what the flagship would.
FUEL_PER_LY = 0.9

#: What each jump takes out of the hull, as a share of its full integrity.
WEAR_PER_HOP = 0.012

#: Below this much hull the master puts her into the yard at the next call at
#: the home port, at the drydock's own rate (`services.REPAIR_RATE_*`).
REPAIR_BELOW = 0.85

#: Below this the master will not sail her at all until she is mended.
UNSEAWORTHY = 0.35

# ── the rules a line runs to ─────────────────────────────────────────────────

#: Cadences a line can keep: continuous (depart as soon as she is home) or a
#: fixed cycle in days, which is how a line is kept from flooding its route.
CADENCES = (0, 30, 45, 60, 90)

#: How long a master sits on a cargo waiting for the selling rule's price
#: before taking whatever it fetches. Nobody brings a cargo home.
WAIT_MAX = 10

# ── risk ─────────────────────────────────────────────────────────────────────

#: The chance of trouble in each system a laden hauler crosses: a little that
#: is always there, and what `piracy.lawlessness` adds above `LAW_FLOOR`. A
#: route crosses every system on its hop list, both ends included; raiders
#: take cargo, and a hauler in ballast is not worth the fuel of catching.
#:
#: Set against the targets, measured over 396 hauler routes (7 ly) in eight
#: sectors at day 200, sailed by a steady master (skill 0.35): routes that
#: cross a system at 0.40 or worse lose 6.0% / 7.8% / 13.4% of trips
#: (p10/median/p90), and routes kept under 0.20 throughout lose 0.5% / 0.5% /
#: 1.0%, 2.05% at the very worst. Linear in lawlessness with no floor, the
#: policed routes reached 3.4% at p90 and 7.0% at worst: a four-hop run
#: between capitals paid for every quiet system it crossed as if raiders
#: worked it.
INCIDENT_BASE = 0.003
INCIDENT_SLOPE = 0.19
LAW_FLOOR = 0.10

#: What share of those incidents end with the hauler gone rather than merely
#: robbed — and how much the Bloom adds to that share, because what the Bloom
#: takes it does not give back.
LOST_SHARE = 0.12
BLOOM_LOST = 0.8

#: The chance, per system crossed that a belligerent may take (`war.spoils`),
#: that a hauler is stopped and her cargo seized as contraband of war.
SEIZE_AT_WAR = 0.04

#: A delay: the chance of one on a perfectly kept route, what lawlessness adds
#: (hulls go the long way round), and how many days it costs.
DELAY_BASE = 0.05
DELAY_SLOPE = 0.25
DELAY_DAYS = (2, 6)

#: What a robbery does to the hull, as a share of its integrity.
ROBBED_DAMAGE = (0.12, 0.30)

#: What an underwriter charges over the expected claim. Above one, so
#: insurance is a price for certainty and never a way to make money.
INSURANCE_LOADING = 1.35

# ── standing ─────────────────────────────────────────────────────────────────

#: The most standing a house's trade can earn with one power in one period.
#: Line sales go through the counter's own rule (`trade.imported`: only goods
#: that counter did not sell you count), and then through this cap, because a
#: line trades on the clock without the captain and would otherwise make
#: standing a thing that accrues while you sleep.
LINE_REGARD_CAP = 1.0
REGARD_PERIOD = 90

# ── the books ────────────────────────────────────────────────────────────────

#: How long the itemised ledger keeps a row. Lifetime totals are kept for
#: ever; the rows are for "the last ninety days".
LEDGER_DAYS = 120

#: Ledger kinds, in the order the panel lists them, and what each is called.
KINDS = (
    ("sale", "Sales"), ("purchase", "Cargo bought"), ("fuel", "Reaction mass"),
    ("wharfage", "Wharfage"), ("distraint", "Distrained"),
    ("premium", "Insurance"), ("claim", "Claims paid"),
    ("repair", "Repairs"), ("upkeep", "Hauler upkeep"), ("wages", "Wages"),
    ("hire", "Signing fees"), ("severance", "Severance"),
    ("charter", "Charter upkeep"), ("deposit", "Paid in"),
    ("sweep", "Swept to the purse"), ("withdraw", "Drawn to the purse"),
)
KIND_NAMES = dict(KINDS)

#: The kinds a trip itself spends or earns, as against what time costs.
TRIP_KINDS = frozenset({"sale", "purchase", "fuel", "wharfage", "distraint",
                        "premium", "claim", "repair"})
