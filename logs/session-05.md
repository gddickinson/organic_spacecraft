# Session log, part 05 of 31

Archived from the root `SESSION_LOG.md`. Dated entries here span 2026-08-01 to 2026-08-01; undated entries keep their original place.

## 2026-08-01 — SEEDFALL: the sweep that should have been written first

Last cycle I said the right move was to stop discovering per-call ticks one at
a time and sweep all of them up front. This is that sweep, and it is the
artefact #116 has been missing for six cycles.

**Four of fourteen, named at once:**

    decision   ventures  exchequer  approach  loyalty
    rate       dormancy colony shipyard market lifespan upkeep
               robots threat memory legacy

Each tick called two ways on identical games — once for thirty days, once
thirty times for one — and the whole encoded game diffed. It is now
`test_ticks`, so the list cannot grow silently and cannot rot: one check
refuses a *new* per-call tick, and another refuses an entry that has quietly
been fixed, because a known-faults list that is wrong in either direction is a
guard spending a licence nobody needs.

**The instrument nearly lied, three times, and validating it is the story.**

The first version reported *all fourteen* as per-call — which should have been
unbelievable on its face, since a decay tick cannot be per-call. It was: two
fresh games from the same seed did not match each other, because `Ship.uid` and
`Officer.id` come from module counters that keep climbing across games. Five
fields, and every verdict was noise. I nearly wrote up fourteen false
positives.

Then the sensitivity control failed twice on its own account. Five days of
memory decay moves a salience by 0.27% and the print rounds floats to three
places, so it was below the instrument's resolution. Two hundred days did not
help either — a fresh game has no memories to decay, so the tick was a no-op. A
single credit is what finally proved the print can see anything at all.

Three mutations run, three red, and the third breaks the instrument rather than
the code: remove the id-stripping and the controls go red before the verdicts
do, which is the right order.

**What this means for #116.** The remaining work is four named ticks rather
than an unknown number found one per cycle. `lifespan` reads as a rate here
while #121 says ageing breaks under the honest clock — so that failure is
about how the *generator* is consumed across calls rather than the tick's
shape, which is worth knowing before anybody starts on it.

Full suite green at 1,227 checks.

## 2026-08-01 — SEEDFALL: the desk learns the journey

#120. **`Run.ly` was carried on every freight run and read by `reachable`
alone.** The desk knew how far each run was and priced none of it, so a thin
margin eleven days away ranked level with a fat one seven days away, and the
board recommended runs whose spread had closed before the hull arrived. The
module's own `MIN_SPREAD` note already said prices drift "several per cent over
a week's voyage" — written down, never applied.

Measured on the desk's own runs: 5.5 ly took 7 days, 8.5 took 9, 10.6 took 11.
The market closes about 1.8% of a gap a day. `Run.survives` is what is left of
the margin on arrival; `worth` is discounted by it; and — the part that
matters — `MIN_SPREAD` now tests **what survives the voyage** rather than what
is quoted at the desk. A spread only just over the floor when you load is under
it when you arrive, which is exactly the trade that floor exists to refuse.

    ly   days   margin   survives   on arrival
    5.5   7.0      112      88.1%         98.6
    8.5  10.0      102      83.3%         85.0
   10.6  12.1       56      80.3%         45.0

Two-year careers, 24 a side, on today's clock:

    before   91,896 blind   165,748 desk
    after   241,282 blind   375,908 desk

Not a rebalance — a filter. The desk stopped recommending the runs that lose
money. One knock-on: fewer runs are recommended, so `test_wharfage` fell to
seven sample rows against the eight it needs. Widened to the whole sector
rather than the first fourteen systems — 23 runs, the quays taking 13.1%.

**And the clock still did not land, for the fifth time.** With it in, the four
known checks all pass — freight now 108,865 blind against 139,184 with the desk
— and two *new* subsystems surface with the same per-call defect: officer
ageing (`test_time`: ten years passed and a wet officer aged 1.95) and the
career length that depends on it. Not the clock's fault, and not something to
rush at the end of a cycle. Tasks #121.

So #120 lands on its own merit, which it has: the desk is worth 1.5x what
trading blind is, where before this it was worth less than nothing.

Four mutations run, four red. Full suite green at 1,224 checks.

## 2026-08-01 — SEEDFALL: the clock is down to one blocker, and it is a real one

Fourth run at #116. The list was finite this time — four red checks — and
three of them turned out to be the same story told four ways: **something that
looked like a cost was being erased for free, and the honest clock stopped
erasing it.**

`test_industry` wanted alloy 1.15× dearer away from where it is made and gets
1.13, because an honest market mean-reverts 365 times a year and the sector
drifts together. Replaced with a control no clock can move: the same berths,
same year, without the licence — 173→142 licensed against 173→169 not.

`test_mining` asserted a skim wears the hull **exactly zero**. It never did: a
mining ship carries no biomass, so once repair had to be paid for, the wear it
always inflicted stopped healing back. Measured over twenty runs a side the
ordering is intact and that is the claim worth making —

    leach 0.30%   skim 0.54%   cut 1.15%   bore 3.12%

`test_stranded` said a naive captain stalled on day 1605 with 51 credits. He
had not: he was standing at a market with 113 t of ore and 9 t of silicon,
quoted at 27 and 765 — about ten thousand credits of cargo. **The probe only
ever sold survey data.** When the bodies in reach ran out it starved beside
its own hold. That is the probe failing to take the move in front of it, not
the game dead-ending, which is the thing the check exists to detect. A captain
under 500 credits now sells what he is carrying, and all six runs finish —
run-a from 51 credits to 18,248.

**The fourth is real and it is now the only thing left.** `test_freight`
claims following the desk beats your own notes. Under the honest clock it does
not, and the check's own eight samples made it look like noise. Twenty-four a
side:

    on your own notes  47,910
    with the desk      44,627

Seven per cent worse. The cause is sound: the desk quotes a margin that exists
*now*, the captain spends days flying to it, and by arrival the price has
reverted. Under the broken clock the market barely moved during the journey,
so stale advice stayed good. That is a feature regression rather than a
threshold — the desk is sold to the player as worth following. Task #120.

So the clock is reverted a third time, and what lands is the three fixes that
stand on their own without it. #116 now has exactly one blocker instead of
four, and it is written down.

Full suite green at 1,224 checks.

## 2026-08-01 — SEEDFALL: the burn balance fixed itself, and the clock found two more

Third run at #116, and the instruction I left myself last cycle — *measure the
burn balance before tuning it* — was the right one.

**Binding feedstock had already fixed it.** A tour ship carries volatiles and
no biomass, so with `FEED_PER_HP` binding it cannot heal at all, and the cost
of a hard burn stops vanishing over a month — it *grows*:

    rest  0 days   coast 0.0272  economy 0.0138  standard 0.0272  hard 0.1099
    rest 30 days   coast 0.0272  economy 0.0138  standard 0.0272  hard 0.2413

Seventeen times economy's cost after a month, where last attempt every profile
healed to 0.0000. No tuning was needed at all — only the free lunch taken away
first, which was last cycle's work.

So the clock chunking went in, and it works: every step size from 1 to 900
gives identical margins (charter 489, concordat 256, freeholds 279, sanhedrin
385), and hard burning still costs 13.57% against economy's 2.90% after a
month. Five checks written for it, all green.

**And it turned up two failures that are not recalibration.** `test_mining`
says *skimming wore the hull* and `test_stranded` says *a naive captain ran
out of moves on day 1605 with 51 credits*. Both are the honest clock ticking
those subsystems thirty times where it used to tick once, and both are real
gameplay consequences rather than thresholds tuned against the defect. The
stranded one especially: a captain who cannot afford biomass now cannot
repair, and can get stuck.

So the clock is reverted again — deliberately, and with the remaining scope
now precisely known rather than guessed. What went in is the piece that stands
on its own: `test_settlement`'s control was "a market with no settlements at
all", which is the wrong control for a claim about *one good* and is unrelated
to the clock. It now compares markets where that good is not worked —
phosphate 312 against 393, ore 32 against 45.

The guard I added to catch my own duplicate-tripwire-key habit fired on the
first try, which is the first time in four that I have not had to be told by
the harness.

## 2026-08-01 — SEEDFALL: a grown hull that rebuilt itself out of nothing

Opening #116 again. The clock fix it needs is blocked on a balance problem —
hard burning stops costing anything once repair ticks honestly — and this cycle
went after *why*. **Repair was free.**

`ship.repair_tick` worked out what the healing should eat and then took
whatever happened to be aboard:

    fed = min(ship.cargo.get("biomass", 0), budget * 0.004)

`min` against the hold, and the healing went ahead regardless. Measured on a
hull at 60% going to 100% — 136 points:

    with 500 t aboard   healed 136.0
    with 20 t aboard    healed 136.0
    with none at all    healed 136.0

A cost that is calculated and does not constrain is not a cost. Same family as
a field declared and never read, one level up: the arithmetic was there and the
consequence was not.

And the rate made it moot regardless. A full rebuild of the starting hull is
336 points, which at 0.004 t a point is **1.3 tonnes and 89 credits** against a
340-tonne hold. `FEED_PER_HP` is 0.05 now — 16.8 t and about 1,100 credits,
roughly the 20.5 t a new ship sails with, 5% of the hold. What it buys:

    0 t aboard   nothing at all
    2 t          40 points   0.595 → 0.714
    5 t          100 points  0.595 → 0.893
    20.5 t       136 points  0.595 → 1.000, 13.7 t left
    500 t        136 points  — the drive rate caps it, not the larder

So a ship that has burned itself out with an empty hold does not heal, and one
that thought about it carries the tonnage to put itself back together.

**A check I wrote was wrong and the mutation found it.** I asserted repair
"still mends one layer and stops" — it never did: a layer that fills lets the
loop carry on, and six came back full in a sixty-day call before this change as
much as after. The claim that actually holds is that with feedstock to spare
the healing is identical to the old formula, which is what "I only added a
constraint" means. 169.0 points either way.

Deliberately not touched: the one-layer-per-*call* cadence. Making that a rate
heals a great deal more and is exactly what broke the burn-cost balance when
#116 was attempted — task #119, and it belongs with the clock.

Three mutations run, three red. And I made the duplicate-tripwire-key mistake
for the **third** time, then dropped the entry entirely while merging it. The
harness guard caught both.

Full suite green at 1,224 checks.

## 2026-08-01 — SEEDFALL: a fence is a distance, because it cannot be a place

#118, the half of #111 that was not built. Taken because #114 and #115 are
blocked on the clock, and **#119 is blocked the same way** — making repair a
rate heals more per rest, which is exactly the burn-cost problem that forced
the revert last cycle.

**The obvious design is impossible, and measuring said so before I wrote it.**
The task asks for raider presence to feed the local black market.
`piracy.lawlessness` counts a dock as law, so a system with a port is never
lawless enough for raiders — and a market *is* a port. Measured across six
sectors: 28 systems carry raiders and **not one has a port**. The two are
disjoint by construction. The local signal is flat too: every market in the
game sits at lawlessness 0.00 to 0.06.

What is not flat is the distance from a market to where hulls are actually
being taken — 5.3 to 44.6 across three sectors, median 16.9. Stolen cargo
travels, so `piracy.fence_pull` is a *reach*, not a reading.

What it buys, measured on one sector:

    pull 0.00  pays 7,800  absorbs 15.0  →  117,000 a visit
    pull 0.47  pays 6,509  absorbs 32.5  →  211,542 a visit

Seventeen per cent off the tonne, twice the tonnage, and the visit worth 1.8
times as much — so a full hold goes in one call instead of four, and a policed
capital pays top price for as much as it can quietly take, which is not much.
Across six sectors: 52 markets, 30 of them part-fenced, spanning 0.00 to 0.76.

Before this the quiet word was **one price everywhere**: `premium` read the
regime and the heat and nothing about where the ship was standing, so a
Charter capital and a Charter outpost paid identically. One power now shows
five different prices for one good across its own berths, 7,338 to 9,256.

Graded on purpose rather than gated: making the reach a switch is one of the
three mutations, and it goes red. That is the mistake `piracy` itself made a
few cycles back — a cliff where a slope belonged — and it is not worth making
twice.

Three mutations run, three red. And I made the same tripwire mistake as two
cycles ago — a duplicate `customs` row where the later silently wins. The
harness guard caught it again, which is twice it has earned its keep on my
carelessness rather than on anybody else's code.

Full suite green at 1,220 checks.

## 2026-08-01 — SEEDFALL: #117 was wrong on both counts, and the sort it doubted was unguarded

Taken ahead of #114–#116 because those are blocked on the clock, and because
unbounded founding was one of the six things that broke when #116 landed —
fixing it would have shrunk that blast radius. It turns out there was nothing
to fix.

**"Founding is free" — false, and my own measurement was the mistake.** I read
it by calling `exchequer.found()` directly, which is the raw operation. The
game's own door is `_invest`, and it pays: `p.credits -= cost`. Founding costs
40,000 against a 12,000 reserve, so a power opening with 30,000 **cannot found
at all** until it saves — `_invest` returns None four times running on a fresh
sector. Measuring through the wrong door is how a feature looks broken when it
is not, and it is the same error as reading a mesh from a cache instead of the
object you were handed.

**"Promoting is neutral" — true, known, deliberate, and already handled.**
Measured across the levels of one berth:

    level    1     2     3     4     5
    yield   90   180   270   360   450
    upkeep  30   120   270   480   750
    net    +60   +60     0  −120  −300

Yield is linear and upkeep quadratic, so promotion clears nothing at level 2
and loses money above it. `exchequer.payback`'s docstring has said exactly this
since it was written — including the sector that "planted six settlements in
year one and none in the seven years after" when `_invest` chose by price — and
the fix was already there: `works_open` sorts by payback, so works that never
pay are what a power does with money it has nothing better to do with. Which is
what a Fleet Hub is.

**What was actually wrong, and it is small.** That design was unguarded —
nothing in the suite asked whether `payback` still says `inf`, or whether the
sort still puts the never-paying works last. And `payback` carried a dead
`if False: gain = 0.0` branch, left when #99 hoisted the `settle:` case into an
early return and neutered the condition instead of deleting the arm.

So: the dead branch is gone, and one check now pins the ordering. Three
mutations run, three red — payback not returning `inf`, the sort going back to
price, and the yield curve made superlinear so promotion pays.

Founding pays back in 667 days; promoting to levels 2, 3 and 4 never does.

## 2026-08-01 — SEEDFALL: the machines guard something, and the task was mis-scoped

#112, written as drone warfare — light-lag deciding engagements, the controller
as the thing to shoot. **Measured against the law that already exists, and the
premise is false at that scale:**

    halving a teleoperated hand needs 4.0 s round trip = 599,585 km
    the tactical arena is 1,400 units; a band is 240

At 1,400 km the round trip is 9.3 ms and an E1 hand keeps **99.77%** of
itself. Light-lag cannot decide a gunfight and no tuning would make it. It is a
strategic law, and the arena where it bites is one the game already had.

Machines can be posted to a holding, and `robots.effective` has priced them by
`grip` since the day they landed. But `colony.ward_at` — what defends a system,
read by `control` and `interdiction` for what a place may do about an
approaching hull — counted only **built works**. Twenty classes of machine,
four carrying a ground duty, defended nothing anywhere in the game.

The data held the whole design and never expressed it:

    loader      level 3, autonomy 1,  1,800 credits
    myrmidon    level 2, autonomy 2,  1,600 credits
    servitor    level 3, autonomy 4,  9,000 credits

Five times the price for autonomy. What it buys, measured in ward and in what
the world may do about you:

    loader     alongside 0.0900 rung 3 · across a system 0.0001 rung 2
    myrmidon   alongside 0.0600 rung 3 · across a system 0.0192 rung 2
    servitor   alongside 0.0900 rung 3 · across a system 0.0900 rung 3

That is "the controller is the objective", and the objective is your own hull
being in the system. Sized against the thing it stands beside: a `garrison`
work is 0.28, so three machines come to about one garrison — they supplement
infrastructure rather than replacing it.

**One defect this turned up, the old one in a new place.** Both callers tested
`ward_at(...) > 0.0`. Right while a ward could only come from a built work
worth 0.28; wrong the moment a continuous quantity fed it — a teleoperated
guard nine AU out is worth 1e-7, which is greater than zero, and it armed a
world with a hand that could not have lifted a spanner. Measured: with the
floor removed the loader keeps its world at rung 3 from anywhere.
`colony.is_warded` is the one door now, floored at 0.02 — below a third of one
machine standing there (0.09) and above what a preplanned one yields from
across a system (0.019).

Four mutations run, four red. And the harness guard caught a second thing on
the way out: I added a `colony` row to the tripwire fast-path table that
already had one, and in a dict literal the later wins silently. Merged.

Full suite green at 1,214 checks.

## 2026-08-01 — SEEDFALL: raiders where the law is not

#111. Raiders already existed — `traffic` gave one in ten systems an unmarked
hull and `encounters` made it the thing that jumps you. What did not exist was
any reason for them to be *where they are*. **One fact, two doors, both reading
the same field:**

    traffic:    hostile_ok = system.port is None or system.bloom > 0.15
    encounters: danger     = bloom*0.9 + (0.04 if port else 0.14) + 0.09·dark

Measured across 252 systems in six sectors: raiders in 25 of 127 portless
systems and 1 of 125 with a port. They already avoided a squadron — 17% at
nothing on station against 0–2% elsewhere — but that correlation was an
accident, because both questions read `port` and a fleet had nothing to do with
either.

`sim/piracy.lawlessness` is the one quantity now: a squadron on station, a
dock, a claim, the distance from the nearest capital, and the Bloom. Both doors
read it, so a system cannot be lawful enough to keep raiders out and dangerous
enough to jump you at the same time.

**Result: 28 systems of 252 against the old 26, and not one of them guarded or
docked.** Piracy did not get more common; it got somewhere for a reason.

**Two wrong turns, both from measuring.**

*The scale piled up against its own ceiling.* At `WILD = 0.72` the quantiles
ran p60 0.80 to p90 0.91 — thirty per cent of the sector inside a tenth of the
range — so the number carried almost no information and the raider threshold
had to sit at 0.92 to mean anything. At 0.45 it spreads: p25 0.03, p50 0.39,
p75 0.58, p90 0.64.

*A cliff placed piracy worse than the thing it replaced.* Gating on lawlessness
alone dropped raiders from 26 systems to **9** — because the least policed
systems are the portless ones and they carry about one hull each, so a yes/no
gate over thin traffic produces almost nothing. Scaling the chance *within* the
gate put it back to 28: the worst places carry more raiders rather than merely
being allowed one. That also subsumed the Bloom term, which had been counted
once in `lawlessness` and again in the raider roll.

And I introduced a two-door fault of my own on the way through and had to close
it: `traffic` compared `lawless >= piracy_gate()` while `piracy.raiders_work`
was the same expression, with the floor and the slope in different files.
`piracy.raider_chance` is the single door now, and `RAIDER_SHARE` lives with
piracy rather than with traffic, because it is a fact about piracy.

The dynamic that justifies connecting this to #110, measured: Amber's Wake at
guard 1 reads 0.04, and with every holding of its power gone independent it
reads **0.24** — a power that can no longer pay for hulls stops policing. It
does not become a haven, because the dock and the claim still hold it down,
which is right.

Four mutations run, four red. And the reachability guard I sharpened two
cycles ago earned its keep on my own code: it caught `piracy.raiders_work`,
sugar over `raider_chance > 0` that nothing called. Deleted.

Full suite green at 1,209 checks.
