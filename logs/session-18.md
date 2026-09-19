# Session log, part 18 of 31

Archived from the root `SESSION_LOG.md`. Dated entries here span 2026-07-29 to 2026-07-29; undated entries keep their original place.

## 2026-07-29 — SEEDFALL: an instrument that changed when you looked at it

Task #72, which I raised last cycle: the docking mini-game's forecast had
never been checked against its act. The premise was half wrong — there *is* a
suite for it, `test_approach_game`, which my grep for "minigames.forecast"
missed. Asking the question properly anyway turned up three faults in one
panel.

**The readout re-rolled on every look.** `reading()` blurred the true error
with a fresh die each call, and the screen called it from `game.rng("readout")`
— which advances the save's seed. Five consecutive paints of an axis nobody
had touched:

    -44   -49   -42   -47   -49

**The panel took its colour from the truth while printing the blur.** A
reading of +9 could sit in a green panel; measured at noise 5, 3% of readouts
contradicted their own colour.

**And every button's forecast quoted `d.error` outright** — so whatever the
instruments said, the tooltip knew exactly where the axis would end up. That
is the whole of what `noise`, and the sensor rating behind it, was for.

`Docking.shown` is the instrument now: read once when a pass begins, held
until the next correction, and used by the panel, the colours and the forecast
alike. The truth stays behind it.

**That left the rating still inert, which I only found by playing it.** `noise`
topped out at 5 against a `TOLERANCE` of 6 — null the reading and you were
inside tolerance whatever your hull carried. Flying on the instrument alone,
400 approaches at each level, noise 0 through 5 all docked **100%** in 3.2–3.5
passes; only past the tolerance does it cost anything. `NOISE_CEILING` is 9:
a bare hull (sensor 2) reads ±7, docks 92% and spends 5.2 passes; a well-found
one (sensor 7) reads ±3, docks 100% and spends 4.3. A fresh captain sits at
3.8, so the opening is barely touched.

Two existing checks in `test_approach_game` went red, and deserved to: both
compared the forecast against `d.error`, which passed only because the
forecast was reading the truth as well. They are stated against `d.reading`
now — the same claims, in the terms the pilot actually has.

Five mutations, all caught. Two needed a second pass: my forecast check only
asserted exactness where the instruments were clear (so the leak survived it),
and my screen check read the printed number but not its colour. Both are
asserted directly now — the forecast in instrument space, and the colour by
reading the label's own stylesheet against a state where truth and instrument
straddle the tolerance.

725 → 730 green.

## 2026-07-29 — SEEDFALL: the card said two officers and the game gave three

Last cycle's systematic sweep worked, so this one asked the same question of a
second family: the sim has nineteen functions that promise what an act will do
— `preview`, `forecast`, `quote`, `odds_for`. Most have a forecast-versus-act
check somewhere. **Three had none at all**: the docking mini-game's, and both
of the opening screen's.

The opening is the first thing a player sees, so I compared its card against
the chronicle it builds, across every stock, origin and posting. Credits,
cargo, standing and hull all matched. The bridge did not:

> **For 30 of 90 openings the card promises two officers and the game seats
> three.**

`CREW_SLOTS` says a Dry Choir stack sails with two — "a wet crew needs people;
a dry one is the ship, and takes fewer" — and it was read by `preview` and by
absolutely nothing else. `apply` only touched the officers when the player had
picked some, and no screen let them.

**I nearly shipped the wrong fix.** My first move was to make it a hiring cap
too, so a dry lineage could never hold more than two. Then I read the constant's
own comment — "Officers you may sign *at the start*" — and the berths board,
which says plainly that in play "you may keep as many as you can pay". It is an
opening complement, not a ceiling. I reverted that half; `can_hire` deliberately
does not consult it.

So `Choices.crew` has been honoured by `apply` since the day it was written and
no screen ever set it. The opening has a bridge picker now: six stations, take
as many as your lineage seats, and the card's number becomes a real decision —
which two, for a dry stack.

**Building the picker exposed a third vocabulary.** `CREW_CHOICES` lists the
stations the opening may seat, and two of its six were *stat* names —
"engineering" and "medicine" against the roles "engineer" and "medic". And
`make_officer` answered an id it did not recognise by picking a role **at
random**. Measured: asking for "engineering" seated a science officer, a
navigator, a medic or anybody else, thirty times out of thirty. Nothing had
ever exercised it because nothing had ever set `Choices.crew` — the picker
would have been the first thing to, and choosing the engineer would have
seated somebody else. One vocabulary now, and an unknown station is a
`ValueError` rather than a shrug.

Four mutations, all caught.

723 → 725 green.

## 2026-07-29 — SEEDFALL: asking every gate whether it agrees with its own act

Two of the last few cycles found the same shape by accident: a function whose
job is to answer "may I?" disagreeing with the thing it guards. `is_stranded`
read a body's richness where `extract` reads its depletion. `quote` priced two
contract kinds where `check` completed three. So this cycle asked it on
purpose, across all seventeen `can_*`/`is_*` functions in the sim.

It found a third immediately. **`crew.hire` refuses a station that is already
crewed, and nothing on the berths board knew.** A fresh bridge holds science,
engineering and nav; the recruit pool draws evenly from all six roles. Measured
over sixty ports:

- **49% of candidates could not be signed** — 107 of 219
- 55 boards in 60 had at least one, and four had four
- every one of them drew a live "Sign on" that answered with a toast

The panel had the ingredients: a *different* button on the same screen already
gates itself on `lifespan.can_sign_on`. The officer cards simply had no
`enabled=` at all. `crew.can_hire` is the one door now — `hire` calls it, the
board calls it — and a closed berth says which officer holds the chair, so the
alternative (Pay off, already on the bridge panel) is legible.

**The check taught me its own limit, which is worth more than the bug.** Once
`hire` calls `can_hire`, mutating `can_hire` moves *both* answers and they
agree all the way down. Deleting the signing-fee rule entirely passed the
agreement sweep. So did making `can_build_here` return yes everywhere — and
that one passed **every check in the project**, which is a real hole the sweep
exposed rather than caused. Agreement guards the architecture; the rule needs
a check measured by outcome. There is one now: the fee is charged and refused
on its own terms, and 39 systems in a fresh sector will not take a keel.

I also recorded what came back clean, because most of it did: `can_found`
against `found` over 1,805 states, `can_afford` against `extract` over 360,
`can_build_here` against `start_build` over 144 — no disagreements anywhere.
And before settling on gates I swept the whole suite for last cycle's pattern
(a check selecting its subjects with the code's own vocabulary) and found the
rest were content tables, where iterating every entry is the right thing.

Five mutations, all caught — two of them only after adding the outcome checks,
which is the point.

719 → 723 green.

## 2026-07-29 — SEEDFALL: the whitelist that was written three times

Breadth cycle into missions, the last area these cycles had not touched. Two
sweeps came back clean and are worth recording as such: the contract board
offers all six kinds every year for nine years running, and every kind has a
completion path that `check` can actually reach.

The finding was in what the board *says*. `quote()` — the function that tells
a captain what a contract's cargo will cost and what they would clear — opens
with `if contract.kind not in ("deliver", "prospect")`. But `check()`
completes a **relic in the same branch as a prospect**: both want the
commodity in the hold at the issuing port. One of two identical contracts was
priced and the other was not.

Worse, `shape()` had the same pair written out again. `deliver` and `prospect`
derive their fee from `cargo_cost(...)` — that is task #34's floor, which is
why neither can lose money. `relic` used a flat `rate × amount` that takes no
notice of what a xenolith costs, and a xenolith is dear and moves about.
Measured over 271 relic contracts against the market:

| kind | median net | worst | % losing | priced? |
|---|---|---|---|---|
| deliver | +15,797 | +2,020 | 0% | yes |
| prospect | +7,346 | +846 | 0% | yes |
| **relic** | **−402** | **−4,694** | **62%** | **no** |

**And the check that exists to prevent exactly this had the list a third
time.** `test_cargo` opens `CARGO_KINDS = ("deliver", "prospect")` — its own
copy of the code's whitelist, so "no cargo contract pays less than its own
cargo costs" could only ever confirm what `shape` already assumed. Xenolith is
stocked at all 20 ports, so buying really is the route it was pricing.

One list in the sim now, imported by the test. Relic's fee is derived from the
goods like the other two, with its rate on top because a relic is a find and
not merely freight: median net +7,267 against prospect's +7,005, and 0%
losing. The board card prints "clears ₡8,266" where it printed nothing.

The general check is the point though: **a check that shares the code's
whitelist proves nothing.** `test_cargo` derives the set by playing now — hand
each of the six kinds its completion state with an empty hold, then a full
one, and see which needs the cargo. It answers `deliver, prospect, relic`.

One existing check had to be re-aimed rather than re-thresholded: "distance
pays haulage on cargo" started sampling relics once the list grew, and a relic
has no destination — it goes back to the desk that asked — so it never takes
the haulage premium, and "per tonne" means nothing for 1–3 xenoliths worth
thousands each. It selects contracts that have somewhere to fly to now, which
is what the claim was always about.

Four mutations, all caught.

717 → 719 green.

## 2026-07-29 — SEEDFALL: skill moved the odds on screen and the prize in secret

Breadth cycle into surface expeditions, which these cycles had not touched.
Two hypotheses died first, and I want them recorded because discarding them
was most of the work:

- **The ground options are not dominated.** `monolith` offers the same reward
  at difficulty 4 and 5, and `wreck` offers a field note at 3 and at 4 — which
  looks like a dead option until you notice the *stat* differs. A fresh crew
  is always science, engineering and nav, never comms, medicine or tactical,
  in 40 of 40 games — so half the ground's options roll at skill zero. That
  looked damning too, until I checked the recruit pool: all six roles turn up
  evenly, ~16% each. It is progression, not dead content.

What was real is what the card says an option pays. `attempt` multiplies a
success by `1 + margin * 0.12` — a bare literal — while `odds_for` quoted the
`REWARD_SCALE` band the roll is drawn from *before* that multiplication.
Measured on "Cut a sample", 800 attempts a level:

    level 0   quoted 8–26 ore   paid up to 32.2
    level 3   quoted 8–26 ore   paid up to 41.6
    level 5   quoted 8–26 ore   paid up to 47.8   (mean up 38%)

**28 of 42 option-and-level pairs paid over their quoted ceiling.** The card
read identically for a green hand and a veteran. Skill moved the odds on the
screen and moved the prize in secret — half of what an officer is worth, and
the half nobody was told, which is exactly the decision "send them or keep
them aboard" turns on.

The quote is conditioned on the officer now: the smallest and largest margin
they can roll on a *success*, carried through. A seam reads 8–32 for a green
hand and 9–45 at level four. Swept over every priced option at three levels,
400 attempts each — every payout now inside its quote, and 17 options quote a
wider band for a veteran. The success chance was already accurate (worst 5%
over 500 rolls) and still is.

**An existing check was holding the card to the wrong number.**
`test_attempts` asserted `(low, high) == REWARD_SCALE[reward]` — the table the
roll is drawn from, not what the ground pays. It asserts the relationship now
(the quote is the table carried through the officer, never narrower) and
`test_prospect` plays out the exact figures.

`MARGIN_BONUS` is named, and it and the other three ground constants moved to
`data/expedition.py` — which also took `sim/expedition.py` back under five
hundred lines, where my change had pushed it to 501.

Five mutations, all caught. One needed a second pass: leaving the *floor* of
the band at the bare scale went unnoticed, because a check that only asks
"nothing paid below the quote" is satisfied by a quote that is too low. It
asserts the floor rises with skill now — skipping `sample` and `xenolith`,
which are counted in ones, where a pip of margin rounds straight back.

712 → 717 green.

## 2026-07-29 — SEEDFALL: two colony effects that a check said were alive

Breadth cycle into empire-building. I went looking with the question that paid
last time — does this system still work years in? — and had to discard three
leads honestly before finding anything:

- **Research** is clean. All 61 technologies have a reachable prerequisite
  chain, and all eight bonus keys are consumed. A "domination" sweep looked
  damning until I saw it was comparing empty dicts: most technologies gate a
  part rather than grant a bonus. No finding.
- **`victory=ruin` at day ~1500** in every long harness run is the Bloom
  drowning the sector while the captain does nothing. By design, and it also
  corrects what I said two cycles ago about it being starvation.

Then the colony effect vocabulary. `data/colonies.py` states the rule itself:
"Every key any class declares must appear here, and **must be read by the
sim**. `tests/test_grants.py` holds both halves." That suite exists because
`megastructure` was once declared and read by nothing.

Two more were in exactly that state, and the check said otherwise:

- **`watch`** — VESPER Picket, Monitor Station, Relay Choir. "Keeps an eye on
  this system whether or not you are in it."
- **`fabricate`** — Fabricator Yard (46,000 credits), Refinery Platform.
  "Fabricated parts can be made rather than bought."

`colony.effects()` copied them into a `watch_systems` set and a
`has_fabricator` flag that **no other line in the game ever opened**, and the
check counted those copies as consumers. *A mention inside a function whose
own output nobody reads is not a consumer; it is a place for a dead effect to
hide.* The aggregator gets no vote now — and because `vault` legitimately
reaches `state.py` through `has_vault`, the check follows one hop through the
aggregate rather than banning it outright.

Holding the aggregate to the same standard found four more dead keys, one of
them worse than the others: **`colony_fx["research"]` was always 0.0**, even
with five research-yielding colonies online, while `clock.py` and `tech_view`
both added it to the bench rate. Colony research goes through `banked`
instead. Six keys gone; the aggregate publishes four now, and something opens
all four.

Both effects do something now:

- A picket **gates the report**. The sector used to announce every new
  infestation anywhere, which is precisely why an eye on a system bought
  nothing — you already knew. Measured: 329 reports with pickets out against
  6 without.
- A yard takes 70% off the *credits* of fabricated fittings built or refitted
  in its system — 35,980 off an 89,400 hull. The metal is charged either way,
  grown fittings are untouched, and a yard one system over does nothing. The
  bill on screen goes through the same call, and says why it is smaller.

One test was proving the bookkeeping rather than the game: `test_empire`
probed `colony_fx["build_systems"]`, an aggregate the game never opened. It
asks the colony's own effect now, which is the granularity
`shipyard.can_build_here` consults.

Six mutations. Five caught outright; the sixth — removing the new guard —
catches nothing on its own now that both effects have real consumers, so I
reproduced the original bug (a `decoy` effect mentioned only by the
aggregator) and showed the guarded check catches it while the unguarded one
passes.

709 → 712 green.

## 2026-07-29 — SEEDFALL: after year one there was no trade in the game

Task #66, which I raised last cycle: surveying is break-even and tips on seed
luck. Chasing it reframed the question entirely and found something worse.

First I had to stop trusting my own instruments. Bots for surveying, mining,
trading and hauling all lost money — but so did the same bots in wide-open
sectors, so the bots were the problem, not the game. I threw out the "every
profession loses money" conclusion.

Then the real chain. A destitute run (run-a) turned out to have a jump range of
8.0 ly and **three reachable systems**; by year one it had zero unsurveyed
bodies within reach and 159 in a sector it could not get to. Surveying is a
*finite* resource — a body is surveyed once — so the profession that funds the
early game runs out. That is by design: the pocket is deliberate, and
`test_reach` has a check that a pocket "is a long project and not a trap".

That check proves the pocket can *supply* the way out — a yard, the materials.
It never asks whether a captain inside can **afford** the 78,000 credits. The
tightest pockets hold four to eleven bodies: 1,600 to 4,400 credits of survey
work, in total, forever. So I went looking for renewable income, expecting to
declare it a trap.

It is not a trap: **freight inside a two-system pocket pays 6,800 to 47,940
credits a round trip**, and every pocket I measured offered work in most years.
I was wrong, and said so rather than building on it.

But measuring that turned up the thing that matters. Watching prices year by
year across eighteen ports:

    year 0   ore 4   alloy 34   biomass 10   phosphate 52   silicon 533
    year 1   ore 0   alloy 21   biomass 17   phosphate -20  silicon -7
    year 2   ore -3  alloy -9   biomass 2    phosphate -8   silicon -10

**After year one the best arbitrage in the whole sector is zero or negative on
every commodity.** Buying at the cheapest port and selling at the dearest loses
money. The spread in ore supply across ports collapses from 0.431 to 0.117
inside a year.

`make_market` builds careful economic geography — a system rich in ore gives
its port up to 1.75x supply, a faction's exports 1.55x, the things it is short
of 0.62x. `tick_market` then dragged every commodity at every port toward
`1 + volatility * trend * 12`, which has nothing to do with the port. The
module's own opening line has always said each port drifts "toward **its own**
equilibrium". The arithmetic said 1.0.

`Stock.base` is what `make_market` decided; the drift reverts to that. Trends
still move a port around its own level, shocks still hit it, trade still pushes
it — but a mining world stays cheap in ore. Six years in, four of five staple
goods are still worth carrying, best margin 510 a tonne; the silicon run
between Quill Bight and Marrow's Deep is still worth 1,174.

**The suite then taught me something about itself.** The Concord broker check
went red. It runs four seeds and demands three — and measured over seventy-two
games the true rate is 56–68%, so that assertion had roughly an even chance of
failing on any given day and had been passing on luck. A fixed-length control
showed my change had no political effect whatever (same 322 ventures, standing
and relations within noise), and the apparent 53%-against-75% gap **vanished on
a fresh range of seeds**: 21/36 against 22/36. Twenty games and a floor at 35%
now, with the measurement recorded beside it.

Four mutations, all caught. Two of my first five were not defects at all — one
mutation did not actually freeze anything, and reverting the seed count is not
a bug the suite should catch — so I fixed the mutation rather than contorting
the check.

704 → 709 green.

## 2026-07-29 — SEEDFALL: told "you can still move" with nowhere to go

Breadth cycle — away from combat, into the economy. I set out to ask whether a
captain can make a living at each profession, and built bots for surveying,
mining, trading and hauling. All four lost money, which told me more about my
bots than about the game, so I switched to the project's own `captain_bot`:
the one whose docstring says it "catches deadlocks — when it cannot make
progress, the game has a hole a player would fall into".

Six five-year runs. **Two of them stopped short.** One at day 1406 of 1825,
moored at Amber Anchorage — a system with exactly one body — holding
**0 credits and 2.3 tonnes of reaction mass**. The body had 0.271 volatiles
and was worked out. `extract` refused it: *"there are other bodies."* There
were none. The captain called for a tow and the game answered:

> **You are not stranded — you can still move.**

`is_stranded` is the gate on `distress_call`, which is the only way back from
exactly that position, and it was answering a different question from the ones
that actually grant a way out. Two guesses in one function:

- **The ice test read abundance where mining reads depletion.**
  `resources["volatiles"] > 0.05` is how *rich* a body is; `worked_out` reads
  how much has been *taken*. Different quantities entirely, so a rich body
  worked to exhaustion counted as a fuel supply for ever.
- **The port test priced an empty shelf at 40.** `buy_price` returns None when
  the market holds none, and `or 40` turned that into "you can buy your way
  out". I checked and no port in a fresh sector is dry — 0 of 417 — which is
  why nothing had caught it. A *played* sector gets there: run-a found Nine's
  Crossing with no reaction mass on the board.

Both now ask the thing that owns the answer. And `nearest_port` no longer
answers a distress call with the berth you are already moored at.

Two of the six stalls turned out to be the bot, not the game, and I checked
rather than assumed: at Nine's Crossing it took the first body over a
threshold, got a worked-out one, and gave up beside four bodies that would
have answered. It picks the richest workable seam now, and calls for a tow
before giving up.

**And the check beside it was hiding this.** `test_play` asserts the naive
strategy "stays solvent for five years" on the *mean* treasury of six runs —
which was 12,159 while three individual runs ended at 0, 254 and 546 credits.
A mean cannot see ruin. There is a check now that every run reaches the end of
its five years with moves left.

Worth recording separately, measured and not fixed: surveying earns 41,579
credits over 4.6 years and spends 44,503 on fuel and rig time. The naive
strategy is *exactly* break-even and tips either way on seed luck. That is a
balance question rather than a bug, and it wants its own cycle.

Six mutations, all caught. One needed a second pass: disabling the jump escape
entirely went unnoticed, because every state in my sweep had a second way out
— I had never constructed one where jumping was the only answer.

698 → 704 green.
