# Session log, part 19 of 31

Archived from the root `SESSION_LOG.md`. Dated entries here span 2026-07-29 to 2026-07-29; undated entries keep their original place.

## 2026-07-29 — SEEDFALL: the other side could not fight

Last cycle I noticed in passing that the enemy AI runs its helm but never its
engineering section, and said so without acting. Chasing it this cycle turned
up something much worse underneath.

**Enemy heat never rose above 0.14× its own cap, and usually sat at zero.**
Not because heat was exempt — `add_heat` is symmetric — but because NPCs were
barely firing. 684 "the gun is dry" messages across twenty fights.

`make_enemy` gave every hull a flat 4–20 tonnes of ore, alloy and biomass.
Those are *salvage*, meant to be worth pulling off a wreck, and they had been
quietly doing a second job as ammunition that nobody had ever sized against a
fight. Measured over forty engagements:

- mean **12 rounds** carried, against a **31-turn** fight
- dry in **35 of 40** fights, on **turn 11**
- **unarmed for 63% of every engagement**
- and so: *the player took no damage at all in 13 of 20 fights*

Every ammunition *type* was stocked — alloy, biomass and ore cover all
eighteen armed mounts — so the usual "is every declared thing consumed"
question came back clean. It was the quantity that had never been measured
against anything.

Fixing that left 7 of 24 fights still bloodless, so I looked at those rather
than loosening the threshold. **Every one was against a hull armed with
nothing but point-defence cannons** — a flak mount doing 8 damage against a
median of 30. `_weapon_pool` raises the tier until *some* weapon exists, and
for a fabricated hull the first to appear is the flak gun. **40% of NPC hulls
in the game were armed entirely with anti-missile guns**, Concordat warships
at difficulty two included.

`test_balance` had a check for exactly this and it passed happily, because it
asked whether the throw was above zero. A single flak gun clears that. Being
armed was never the claim worth making; being able to hurt somebody is. That
check asks the right question now.

And requiring a main gun exposed a third thing. The old difficulty curve was
a **cliff**, not a curve — scales 0.5, 1 and 2 all sat at 8–16 points of
throw because every one of them was carrying flak, then scale 3 jumped to 85.
My fix gave the bottom a floor and immediately created a new fault: a
fabricated hull's first main gun is tier three, and tier three holds the
breach torpedo, so a light patrol was drawing from a battleship's rack. The
balance suite caught it — an armed hull's win rate against a scale-0.5 patrol
fell from 99% to 75%. `_rack` widens the gun pool with difficulty. The curve
is 27 · 28 · 45 · 88 now, and the win rates 88% / 31% / 16%.

What this cost, honestly: combat is a different game. Mean damage to the
player went from **21 to 150–196**, and the player now loses 4 to 10
engagements in 40 where it had never happened once. Wrecks are worth more
too — unspent rounds are legitimate salvage — 31 tonnes recovered per kill
against 60 now.

Seven mutations, all caught. Two of my own checks needed a second pass: the
magazine check read its bar off `ROUNDS_MIN`, the constant it was guarding,
and passed without blinking on a three-round magazine; and the dry-share
threshold was loose enough that the salvage stores alone satisfied it. Both
measure against absolute numbers now.

692 → 698 green.

## 2026-07-29 — SEEDFALL: the order you give the drive arrives a turn late

Priority #3, positional combat with crew stations. I measured the system
before touching it, asking whether the captain's choice of seat matters at
all — if officers hold the other two competently, the whole idea is
decoration.

It matters, and it *reverses by hull*, which is the healthiest answer I could
have got. Over 40 engagements apiece:

| hull | captain at the helm | captain at the guns |
|---|---|---|
| navis, beam-armed | enemy at **46%** hull | enemy at 92% |
| bastion, heavy | enemy at 66% | enemy at **30%** |

Taking the gunnery seat costs you the helm, which repeats its last order at
seven-tenths turn rate. For a ship that must keep its beam on the target that
costs far more than the accuracy is worth; for a turret boat it costs nothing.
No dominant seat. That is now written into `INTERFACE.md` as something not to
"fix".

What I did find was in the turn order. `_run_seats` ran the helm first and
engineering second — but **engineering is what sets `side.route`**, and its
two consumers sit on opposite sides of that:

- the guns read it when they fire, which is *after* both seats, so
  `route_guns` landed on the turn it was given;
- the helm reads it while steering, which is *before* engineering set it, so
  `route_engines` landed a turn late.

Measured by playing, ordering "power to the drive" on turn three:

    turn 3   route_engines   route=engines   speed  0.00
    turn 4   hold            route=None      speed 74.90

**The captain who ordered it saw nothing happen, and the ship leapt forward on
the turn they ordered *hold station*.** Engineering runs first now — whatever
allocates a resource has to run before whatever spends it.

The panel was the other half of it, and it was already wrong before the fix:
it said "takes effect next turn" for *both* routing orders, which was untrue
of the mounts even then. `ROUTE_ACCURACY`, `ROUTE_SPEED` and `ROUTE_ACCEL`
are named constants now, read by the act and by the forecast, and the panel
quotes them: "+12% to hit, this turn" and "+25% top speed and +60%
acceleration, this turn".

Combat outcomes are unchanged within noise across four hull/strength
combinations — the fix corrects the timing without moving the balance, which
is what I wanted to be able to say before committing it.

Seven mutations, every one caught. One needed a second attempt: I had asserted
the routed speed against `top * ROUTE_SPEED`, which is the tautology trap
again — both sides of that comparison come from the constant under test. It
measures the ratio of two played-out speeds now, and separately states the
design bound (routing is a lever on the ship you have, not a different ship).

687 → 692 green.

## 2026-07-29 — SEEDFALL: goodwill had no price curve, so the Concord was a shopping list

Priority #2, diplomacy. I measured before touching anything: ten years of
doing nothing, to see whether the powers move on their own account. They do —
164 improvements against 142 worsenings across twelve sectors and thirty
years, net mildly downward. Healthy. Every faction field is consumed too;
`buys` reaches the economy as a 0.62 supply multiplier, not just the codex.

Then I played the diplomacy screen as a captain with money and no scruples:
press the four buttons, never leave port, never take a risk.

**The Concord arrived on day 855.** Two and a third years for the sector's
whole political condition, at 460,000 credits and 1,270 tonnes of biomass.
Across three sectors it landed on day 855, 930 and 840 — a shopping list on a
cooldown timer, not a challenge. All four powers finished pinned at 100.

The cause: **nothing in diplomacy had a diminishing return.** `gain` was a
flat number on the action. Forty tonnes of biomass moved a power sitting at
95 exactly as far as one sitting at 0, so standing was a commodity bought at
a fixed price.

`courtship()` is the curve — squared, knee at 25, floor at 0.30. Chosen by
measuring candidate shapes against the climb, not by taste:

- 3 relief parcels still carry a stranger to Correct. The opening is untouched.
- Kin costs 11 parcels where a flat rate charged 7.
- 95 costs 8 more on top of that.

The same captain now takes **3.2 years**, spends 576,000–628,000 credits and
about 1,700 tonnes, and finishes with the powers sitting *at* Kin — 70 to 73
— rather than pinned at 100.

**The floor was nearly set too low, and the suite caught it.** I first chose
0.08 on the strength of the climb numbers alone. Two suites I had not been
running failed: a determined broker reached the Concord in two games of four,
and committing to one side of a feud topped out at 75. The cause is that
standing erodes on its own — the churn takes a power at 90 down to 83 inside
two years — so throttling gains to 8% at the top makes high standing
unholdable and the ending unreachable. That is a worse fault than the one I
set out to fix. Swept 0.08 / 0.15 / 0.22 / 0.30 against the climb, the
Concord playthrough and both suites; 0.30 is the first value that satisfies
all of them.

**Two doors, one rule.** `preview` and `perform` each carried their own copy
of `action.gain * (1 + diplomacy)`. That is the arrangement that has already
produced a free treaty, an ungranted favour and a phantom haggle payment in
this same file. `offer_gain()` decides it once; the suite greps the source so
a third copy cannot appear.

**And the curve exposed a trap that had been sitting under it.**
`allegiance.price` computes what serving a power costs with its enemies, and
`BITE` calls itself "a share of what you gained with the issuer" — but there
was a flat `max(1.0, ...)` under it. Invisible while every act was worth five
or more. Once a gift to an old friend was worth 0.88, the floored penalty of
1.0 with each of two rivals meant **relief at 85 standing cost forty tonnes
of biomass to leave you 1.12 worse off overall.** The button was a trap.

The floor was also flattening the severity ramp that module exists to create
— its own docstring argues against "a flat penalty for anyone under some
line" — so removing it made a mildly-offended power (rift 0.09) charge 0.3
where it had charged a full point. One allegiance check failed on that, and it
deserved to: it asserted two flat thresholds, which a flat floor satisfies by
construction. It now asserts the ramp — a deeper rift costs strictly more —
which is the claim actually worth defending.

Eight mutations, every one caught. Two needed a second attempt: my floor check
read its expectation off `COURTSHIP_FLOOR` itself and passed happily with the
floor set to zero — the tautology trap again. It asks the panel's question
now: does any overture cost real resources and render nothing you can see?

Two smaller things fell out of the same work. The panel began printing
"−0 standing" once penalties got small enough to round to nothing — a figure
that reads as neither zero nor a quantity. And my first guard against it
tested `abs(delta) < 0.5`, which misses exactly −0.5: Python rounds a half to
even, so that formats as "−0" as well. `standing_figure` asks what the number
rounds to instead.

679 → 687 green: seven new courtship checks and one new allegiance check.

## 2026-07-29 — SEEDFALL: two of seven watches had no decision in them

Priority #4, the crossing. The panel prices every option's days, mass, hull,
heat, salvage and research — and then renders the risk as a bare "Might go
wrong: 30%". `risk_text` and `risk_damage` were in the data, read by
`sim/transit.py` when the risk fired, and referenced by no screen at all. So
holding through debris (30% of thirty off the hull) and running a bad slug
(35% of twenty-four) looked like the same gamble.

Fixing the display meant reading every risk, and one of them was empty:

- **`contact/hold` declared 45% — the largest risk in the table — and cost
  nothing.** It printed "They were not nobody." and that was the whole of it.

Which raised the general question, and the general question is the one that
paid. `data/watches.py` states its own design rule in its docstring: *"there
is no option that is simply best."* **Does any option dominate another** —
cost no more on every axis, and pay at least as much?

Four did, across two watches:

- `hulk/beacon` was free and paid 12 research + 3 components; `hulk/log` was
  free and paid 4. Logging it was never worth picking.
- On `contact`, all three collapsed. `hail` was free, riskless, and the only
  one that paid, so running dark (two days) and holding course (nothing) were
  both pointless.

**Two of seven watches contained no choice at all.** Every option now trades
something different: hailing tells a stranger who you are (25% of 48 off the
hull) and learns who they are; running dark costs two certain days; holding
course is free until they come alongside and take three days over you.
Stripping a hulk's beacon costs the day the blurb always said it did.

`risk_days` is new. A risk could only ever cost hull, which is precisely why
the contact could not be priced — being stopped and searched costs *time*.

**The hull regrows and the calendar does not**, and that nearly cost me the
fix. My first retune of `contact/hold` was ten off the hull plus two days —
and the two days healed the ten exactly, so the option's own cost cancelled
itself out. Measured: about 2.3 hull a day when badly hurt, faster near full.
The lesson generalises past this watch: **hull damage is a cheap currency and
days are an expensive one.**

So the domination check does not read declared damage. It plays each option
from one shared state per watch, both branches of the risk, and compares what
is *still missing* once that option's own days have elapsed. A check that
reasoned from the numbers blessed a trade worth three hull as though it were
worth eighteen.

Five checks in `test_watches.py`, every one proven to bite by reintroducing
the bug it exists for. The domination check catches four of the five on its
own, which is the shape a good general question has.

Suite green.

## 2026-07-29 — SEEDFALL: all one hundred and fifty-three

Task #60 has been open since long before this run and I have twice said it
needed a cycle of its own. This is that cycle, and it is closed.

- **Every tuning constant in the game is pinned.** 53 modules, 153
  module-level numeric constants across `data/`, `sim/` and `core/`, each
  doubled, halved and zeroed. Every single one is noticed by at least one
  check. Nothing is unprotected.
- **The original "52" was an artefact.** It was counted when `tripwire.py`
  kept its own copy of the suite list, which went stale the moment a suite was
  added — constants protected by the newer suite read as unprotected. The
  tool's own docstring records that failure; `SUITES` derives from the
  canonical list now, and the count predates the fix.

**A pass/fail sweep that reports nothing but "all clear" is a poor use of
seventy minutes.** So the tool now says *where* each constant's protection
comes from: its own neighbourhood, or only the wide set. The second is worth
knowing — it means the constant is held up by a suite that happened to walk
past rather than by a check written for its subject.

One constant was in that state: **`consorts.WITHDRAW_AT`**, the hull fraction
below which an escort breaks off and falls out of the line. Something
somewhere noticed it moving; nothing in the combat suite did, which is where a
rule about consorts belongs. `test_combat` has a check for it now — in the
line at 60% and 35%, out of it at 10% and 5%, measured against fractions
written in the check rather than against the constant — and the sweep now
reports it caught by `combat` directly.

Three mutations bite it: never breaking off, breaking off at the first
scratch, and skipping the check entirely. A fourth mutation I tried aimed at
the tool's new reporting line and missed; that is a diagnostic rather than a
rule, and I am not going to pretend a print statement is load-bearing by
writing a check for it.

674 checks green, nothing over 500 lines.

## 2026-07-29 — SEEDFALL: what the order will cost you, before you give it

Priority three. The seats already say what taking one personally is worth —
`seat_value` has done that since task #40. The orders *inside* the seats were
bare buttons with a sentence of prose and no number anywhere.

That mattered most at gunnery, and more since the thermal work. A Bastion at
30 of a 50 cap presses **fire everything that bears**, makes seventy-four
more, and ends the turn pinned at the ceiling — where every penalty for
running hot is charged against it. Nothing said so until the turn resolved.

`stations.order_preview` says it now, and the panel prints a line under each
button:

- *Fire everything that bears* — 5 of 5 mounts bear · heat 30 → 100 of 50 —
  pinned at the ceiling  (in warn)
- *Aimed shot* — Standing Wave Projector, 52 damage · heat 30 → 48 of 50
- *Vent heat* — sheds up to 25 · heat 30 → 5 of 50
- *Damage control* — patches about 16 of Whipple Bumper

Helm orders are left deliberately silent: the firing picture already reports
what coming about would bring on, in degrees, and saying it twice is noise. A
check holds that both ways — no gunnery or engineering order may be a bare
button, and no helm order may start speaking here.

**I made the same mistake I was fixing, one layer up.** The first draft quoted
the raw sum: "heat 30 → 104 of 50" for a salvo that actually stops at 100,
because the ceiling clamps it. A forecast that does not clamp what the hull
clamps is exactly the defect this function exists to end. It now reports the
clamped figure and distinguishes *over the cap* from *pinned at the ceiling* —
which are different places to be — and the check measures the forecast against
`_salvo` itself from three starting heats: 0 → +74, 30 → +70, 95 → +5, every
one exact.

Six checks in a new `test_orderplan` suite, every one proven to bite.
673 checks green, nothing over 500 lines.

## 2026-07-29 — SEEDFALL: two buttons, one of them priced

Back to diplomacy. The piece I had not measured is ventures — the powers
acting on their own account, which you may back, work against, or let happen.

The system itself is healthy: all six kinds fire, hundreds of them over twenty
chronicles. The screen was the problem.

- **Neither button said what it does to the odds.** The panel showed "Odds as
  things stand: 51%" and two buttons. Backing takes that to **81%** and
  opposing to **21%** — a thirty-point swing either way, which is the entire
  reason to intervene, and it was stated nowhere.
- **Only one of the two buttons was priced.** "Backing it costs ₡5,000" and
  "Backing buys +12 standing" were both there. "Work against it" had nothing
  beside it at all — not the −14 standing with the power, not the +8 with
  whoever they are against.
- **And being right pays again, silently.** Backing something that comes off
  is worth +8 more with the power; opposing something that fails is worth +5
  with every power that already disliked them. Both were bare numbers inside
  `_resolve`, mentioned on no screen.

`RIGHT_BACKED` and `RIGHT_OPPOSED` are in `data/ventures.py` now, and
`ventures.preview` reads the same constants `_resolve` does — the arrangement
`TREATY_WEIGHT` was extracted to get. The panel prints both stances in full:
odds before and after, credits, every power whose standing moves, and what it
pays if you turn out to be right.

Six checks in a new `test_ventures` suite, every one proven to bite —
including one that restores the old panel, pricing backing only, and one that
makes the forecast and the outcome read different numbers.

667 checks green, nothing over 500 lines.

## 2026-07-29 — SEEDFALL: the fifty-two that were not there

Task #60 — "pin the remaining 52 unprotected tuning constants" — has sat on
the list for many cycles. This cycle measured it instead of assuming it.

- **59 constants across 14 modules, and 0 of them unprotected.** ship, flight,
  expedition, colony, convictions, officials, diplomacy, plans, mining,
  stations, minigames, aftermath, assessment, ventures — every one pinned,
  including every constant the last ten cycles introduced: `HEAT_CEILING`,
  `QUIET_SHARE`, `TREATY_WEIGHT`, `STRANDED_SHARE`, `MEGASTRUCTURE_GUARD`,
  `PROMOTION_OWN`, `PER_AU`, `LONG_LEG_CAP`, `WORTH_SAYING`, `PATCH`.
- **The "52" is stale, and the tool records why it would be.** `tripwire.py`
  used to keep its own copy of the suite list; it went out of date the moment
  a suite was added, and constants protected by the new suite read as
  unprotected. `SUITES` is derived from the canonical list now. The count was
  taken before that fix.

**Two real defects in the tool itself, found by asking it the question it asks
of the game.** `KIN` maps a module to the cheap suites to try first, and it is
hand-written:

- **`memory` pointed at `voices`, which is in `SLOW`** — a suite the sweep
  deliberately excludes. A constant protected only by a slow suite therefore
  read as protected when its module had an entry and unprotected when it did
  not. The two stages have to agree on what counts.
- **21 modules with tuning constants had no fast path at all**, including
  `ship`, which holds the thermal rule the whole game reads. Every one of
  their constants paid the full wide run: measured, `ship`'s four took 240
  seconds without a fast path and 17 with. Fourteen times.
- And the entries that existed had gone stale against this run's newer, more
  specific suites — `charts` still pointed at `charts` rather than `charting`,
  `expedition` at `ground` rather than `landing`, `officials` at `officials`
  rather than `counter`.

All fixed, and `test_harness_guard` now holds the map: no entry may name a
suite that does not exist, none may point at a `SLOW` one, and every module
with constants must either have a fast path or be named as having no suite
that covers it. Four mutations, all biting.

Task #60 is rewritten with the measured figure and instructions for finishing
the sweep. The remaining ~92 constants are unswept; a full pass is about
eighty minutes even with the fast paths, because the fast stage only saves
time on constants it *catches* — anything genuinely unprotected still pays the
wide run, which is the right way round.

661 checks green, nothing over 500 lines.
