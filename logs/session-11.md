# Session log, part 11 of 31

Archived from the root `SESSION_LOG.md`. Dated entries here span 2026-07-30 to 2026-07-30; undated entries keep their original place.

## 2026-07-30 — SEEDFALL: a third of a colony's output, going nowhere (#politics)

Two more zeros from the tally — `territory.answer` and `territory.collect_tithe`
never fired in a played decade — and chasing the second one down found something
the first was only hiding.

`collect_tithe` skims the levy off a holding's output before it reaches the
captain's stores. `colony.tick` called it like this:

    territory.collect_tithe(game, col, produced, days)

**and threw the return away.** Measured on a RADIX Mine yielding 2.6 t of ore a
day: over thirty days the works turned out 78 t, the captain received **54.6** —
and the Charter's purse moved by **nothing at all**. No log line, no event, nobody
the richer. Thirty per cent of a holding, every month, simply ceasing to exist.

Both halves of that are rules this project has written down twice already. A share
taken off somebody is a share somebody else receives: `wharfage.collect` moves
both sides in one function for exactly this reason, and task #95 was a whole cycle
about powers who paid for nothing. And a deduction the captain cannot see is not a
cost, it is a mystery — task #100's whole point is that the harbour due is named on
the board, in the log, and on the desk's forecast.

So the levy lands in `Purse.levies`, beside the wharfage on the same panel, and
the clock writes: *"Charter took the levy off RADIX Mine · Mereth's Hollow I —
35.1 t ore, 1.5 t phosphate, worth about 1,089."* In warn tint, because a power
taking a third of your output is not neutral news.

**And there was a quieter third thing.** The demand screen has always quoted "a
levy would cost X a year", worked out as `base × 0.55` inside
`territory.yearly_worth` — a forecast with **no act behind it to be wrong
against**, since the levy credited nobody. Both read `territory.value_of` now, and
the quote turns out exact: **8,829 quoted for the year against a year that took
8,829**, to the credit. That is the first time that number has meant anything.

Checked by playing: the goods that leave equal the credits that arrive; the clock
really carries the line (not merely `colony.tick`'s return — a returned event
nobody logs is the same silence in a different place, so the check drives
`advance_days`); a defiant holding is skimmed for nothing and told nothing; and a
ceded holding pays nothing because it is not yours to levy.

Seven deliberate breakages, seven caught — the levy paying nobody again, the
return thrown away again, the goods left off the notice, the quote drifting from
the act, a defiant holding skimmed anyway, the purse panel's line dropped, and the
share halved without the quote noticing. My first attempt at the fourth was a
no-op — I added an unused constant and called it a mutation, which proved nothing
until I broke the shared door properly.

Five new checks, 984 across the suite, all green.

## 2026-07-30 — SEEDFALL: an ability that made armour out of nothing, for ever (#combat)

Another zero from the tally: `combat.use_ability` fired **not once** across
seventy engagements in a played decade. Seven fitted parts grant six abilities and
nothing had ever driven the module end to end, so I read it — and the project's two
standing questions found a fault each.

**Is it bounded?** No. `seal` was one line: `side.st.armour += 4`, on a four-turn
cooldown, with no other rule anywhere. A captain who pressed it whenever it came
up went **2 → 34 armour over eight firings**, and 43 over a long engagement, with
no ceiling of any kind. And the opening NAVIS carries `sphincter_seal`, so this
was available in a captain's first fight.

Its own sentence is the fix: it "irises its bulkheads shut and **gives up the
breached compartment**". That presupposes a breach, and it is finite — a hull has
six layers and can only give up the ones it can afford to lose. So the seal now
needs a layer holed through, spends that layer (`Side.sealed` records it, and the
same compartment cannot be sold twice), and never touches the pressure vessel,
because you cannot iris off the compartment the crew is breathing. Measured: five
compartments of six for **+20 armour**, and the next eight presses buy nothing.
On a whole hull it refuses, and says why — *"this seals a hole, it does not make
armour."*

**Does the screen say what it will do?** No. The button showed the part's flavour
text and a cooldown — on a panel where every helm order prints its consequence and
the hail now names its odds. `abilities.preview` is the door, `use_ability` asks it
and then does what it said, and the systems row reads "gives up Sacrificial
Epidermis · armour 2 → 6", "heat 62 → 17", "Melanised Rind +13", "their fire
control blind, 2 turns".

**And a third, found while wiring the door.** The cooldown was set *before*
anything was decided, so pressing a seal on an undamaged hull put it out of action
for four turns and returned quietly — the gate and the act disagreeing about
whether anything had happened. It only spends the cooldown if it fires now.

Honest about what I could not show: at the difficulties this harness fights,
**the player takes no hull damage at all**, so the seal exploit is latent rather
than decisive today — I could not demonstrate it winning a fight it would have
lost. It is fixed as a correctness matter, with the 2→34 measurement as the
evidence, and the note that a *player* pressing it deliberately is who it
mattered for.

Two mutations taught me something about the checks. Dropping the `critical` guard
survived at first, because holing only the *losable* layers leaves an intact
pressure vessel that the hp test skips anyway — the guard only bites on a hull
open all the way through, which is exactly when giving up the crew's compartment
would kill them. And one refusal masked another: with a single hole to seal, the
next press is refused for having no compartment left rather than for the cooldown,
so the check was reading the wrong reason and had to hole two.

Seven deliberate breakages, seven caught: the seal unbounded again, the pressure
vessel irised off, the same compartment sold twice, the cooldown burnt on a
refusal, the forecast quoting a different figure, the screen's rows removed, and
an ability that fires and does nothing.

Six new checks, 979 across the suite, all green.

## 2026-07-30 — SEEDFALL: the walk back to the lander had never been costed

Two zeros left in the tally of what a played decade reaches, and this pair told a
story: `expedition.attempt` fired **271** times and `expedition.lift_off` **zero**.
Chased down, a decade of chronicles ended **50 landings stranded, 32 aborted, and
not one returned.** The whole intended ending of an expedition — walk back to the
pad, lift, bank the haul — had never been driven by a played game.

Because the ground poses exactly one piece of arithmetic and **the screen never
showed it.** A party carries `supply` in days. A step spends one day on ground
already crossed and up to three on fresh, times whatever the weather is doing.
Reach the lander and the haul comes up, capped at what four people can lift. Run
out first and 40% comes home and the rest stays where it fell. The panel said
"Supply · 7 days" and **never said how far away the lander was** — 60% of a hold
riding on a subtraction nobody was shown.

`tests/ground_ai.py` had already written the consequence down, for the *driver*:
"the one decision the ground actually poses — how much supply to keep in hand for
the walk home — was invisible to a driver that never walked home." The captain was
in precisely the same position, and nobody had noticed the sentence applied to
both.

So `sim/wayhome.py`: Dijkstra over the tiles the party has *seen*, adding up
`expedition.step_cost` — which is now extracted as the one door and is the same
function `move` charges. The panel reads **"The walk home — 4 days over 4 steps of
known ground · 13 days to spare"**, and the route it draws follows the party's own
footprints, because ties go to visited ground. Without that tie-break the quote was
right and the line on the map wandered off through terrain nobody had set foot on.

**Two defects found by the checks, one of them a real trap.** The check that walks
the quoted route was refused at its first step: *"Katabatic gale: nothing moves in
this."* Some fronts pin a party where it stands, and the quote ignored them — so a
party held fast was told "4 days home, 3 to spare" while the days went by anyway.
A party with exactly enough supply would have stranded reading a clean forecast.
Pinned days are counted now, named on the panel, and measured: a gale for three
days took a 4-day walk to **19** — sixteen for the walk at gale rates and three
sitting still. The other was mine: I compared the weather at the two ends of the
walk to decide whether it had held, which is the same "at either end" mistake this
project made in the industry check two cycles ago. Every step now.

**And knowing the price is worth something**, which is the payoff. At the same
two-day margin, a party leader reading the costed walk brought **15 of 24 parties
home and stranded 5**; one counting tiles managed **9 home and 11 stranded** —
because four tiles of fresh scarp in a dust storm is twelve days and reads as
four. The chronicle uses it now and ends a decade **31 returned, 14 stranded**
where it was 0 and 50.

Two mutations survived the first draft of the suite and both taught me something
about writing them. Ignoring what ground costs, and planning over tiles nobody
has seen, both left the chosen route unchanged in a natural landing zone — the
reveal has usually seen everything nearby, and the cheapest way is usually also
the shortest. Catching them needed a zone built on purpose: a walked corridor
that is longer in steps, and an unseen shortcut that is **tempting** — cheap
ground, fewer steps. Making the shortcut dear as well proved nothing, since
avoiding it cost the router nothing either way.

Eight deliberate breakages, eight caught.

Eight new checks, 973 across the suite, all green.

## 2026-07-30 — SEEDFALL: the only two buttons in the game that named no number

Picked from last cycle's tally of what a played decade never reaches. Two of the
zeros were `parley.hail` and `parley.flee` — across **seventy engagements**,
nobody ever tried to talk their way out or run. Partly the driver's taste. But
opening the module explained the rest: **neither button said anything at all.**

Press "Hail them" and one of two things happens. The engagement ends, or the
enemy takes a free turn and shoots you for nothing. The probability was
`clamp(0.18 + diplomacy + rep/260 + strength*0.3 + ...)` and it was written down
**nowhere a captain could read it** — on the same panel where
`stations.order_preview` prints a line for every helm order, beside a gunnery
button that quotes the fall-off for the range. A ground option names its odds and
its prize. An overture says what it buys. This was a coin toss with the coin in
somebody's pocket.

**And it never asked what the power actually remembers.** `b.rep` is the standing
on the books; `grudge.feeling` is the memory behind it — the thing the game
already spends on prices, on whether a harbourmaster will do you a favour, on
whether a board carries work at all. Measured: a Charter that remembers a
destroyed hull sits at **-88**, and a hail's chance was completely unmoved by it.
You could burn their frigate on Tuesday and hail them on Wednesday at exactly the
same odds.

So `parley.odds` and `parley.escape_odds` are the one door, `hail` and `flee` read
them, and both return the chance **with its terms named**. The panel now reads:

    Hailing them: 42% they stand down — your standing with them +17 ·
    you have the upper hand +13 · what they remember of you -7.
    Refused, they fire anyway.

    Disengaging: 63% you shake them — the room you have +39 ·
    how hard you are to hold +10 · they are faster -8.
    Short, and they get the turn.

Memory is worth `0.002` a point, deliberately less than the standing term across
its range: the ledger is what a power will admit to and the memory is what it
feels, and a hail is conducted in the first. Measured end to end — **22% clean,
4% remembering a kill, 28% remembering a rescue.**

**A probabilistic forecast is checked by running it**, which is the shape the
docking mini-game's check has: state the number the panel shows, then hail four
hundred times and count. 22% said / 19% run · 45/45 · 60/64, each inside three
sigma. If the act ever rolls against a different number from the one on the
button, that check fails — and it does: halving the roll behind the panel is one
of the eight mutations this suite catches.

Two smaller things fell out of writing it. `st.diplomacy` — the "somebody aboard
who can talk" term — is a comms officer at 0.05 a level, and the opening crew has
none, so it reads **exactly zero on every starting hull**; that is now stated in
the check rather than left looking like a bug. And hailing the Bloom is not a
gamble but a category error: it returns mute with a reason, costs no turn, and the
screen says so *before* the button is pressed.

Eight deliberate breakages, eight caught: the act rolling a different number from
the panel, the memory term dropped, standing left out, the upper hand ignored, a
shaken nerve worth nothing, the panel's lines removed, the reasons hidden behind
the number, and the Bloom rolled against instead of refused.

Six new checks, 965 across the suite, all green.

## 2026-07-30 — SEEDFALL: seventy battles, no consort, and a fleet that ate nothing

No task for this one. I picked it by **counting which mechanics a played decade
ever reaches** — wrapping forty doors across politics, combat, the ground and the
bench, then playing ten years and reading the tally. Most of it fires plenty.
One block was flat zero:

    0  consorts.deploy      0  consorts.run      0  consorts.interception

...across **seventy engagements.** `deploy` runs only when `escorts_of` returns
something, and a chronicle never lays down a second hull, so the whole consort
subsystem — standing orders, screening, who draws fire, the interception share
that #86 measured so carefully — had never once been driven end to end by a game.
Nothing was broken. Nothing had been asked.

Two things were wrong underneath, and both are house specialities.

**The act was a screen.** `ui/yard_view._set_escort` wrote `ship.escort` and
`ship.docked_at` itself, so the rule about which hulls may be ordered out lived
in whether the button had been drawn — the same shape as `apply_refit` validating
the design and the cost and *nothing else*. The first thing I did through the new
door was order out a hull that **was not in the fleet at all**, which the screen
had prevented by only ever drawing rows from `game.fleet`. `consorts.can_sail` is
the rule now: yours, not the flag, not a wreck, somebody aboard, berthed *here*,
not already out. Five refusals, each with a sentence.

**And a fleet was free to keep.** Measured before touching anything: ordering a
thirty-crew escort out changed the day's demand **not at all**, the power draw not
at all, the wage bill not at all. `upkeep.complement` counted the flagship's crew
and the officers and stopped. A consort is the captain's own people in the
captain's own second hull, so the stores are the flag's: `complement(game,
company=True)` counts them and `demand` asks with them. **Air and power
deliberately do not** — `game.ship.o2` is *this hull's* tank and every hull has a
reactor, so only what comes out of the hold is shared. Measured: 30 more mouths
is +81% on the day's biomass, 45% of the fleet's stores, and a fortnight takes
exactly what the yard quoted.

Which is the other half: **the yard says what it costs before you commit.**
"In company · 1 hull(s) — 26 more mouths · 0.07 t biomass a day", and the log
reads "Wake of Ash will sail in company — 60 mouths in the fleet now."
`consorts.keep` is unrounded on purpose — a door that rounds is a door whose
figure no longer matches the act, and my first draft rounded to four places and
was caught by the check comparing it against what `upkeep.tick` really took.

**Two more found on the way.** The escort standing order promised "You own more
than one and only one of them is doing anything — order it to sail in company",
and its gate was "you own a hull that is not already out" — true of a hull
berthed six systems away, which cannot be ordered from here. It reads
`can_sail` now. And `test_orders`' own fixture built a second hull with
`docked_at = None`: neither berthed nor sailing, a state the game cannot produce,
since a launched hull is docked at the yard that built it and `sail` is the only
thing that clears it. Giving the fixture the berth it would really have made the
guard stricter, not weaker.

Played, at last: four engagements with a TESTUDO in company, four consorts
deployed, **73 turns with one interposed between the flag and the enemy**, and one
of them came away holed. The subsystem works. Nobody had asked it to.

Eight deliberate breakages, eight caught: the fleet eating nothing again, a
consort breathing your tank, the ownership rule dropped, a hull ordered out from
anywhere, a wreck allowed to sail, the yard's cost line removed, the quote rounded
away from the act, and the standing order back on its loose gate.

Six new checks, 959 across the suite, all green.

## 2026-07-30 — SEEDFALL: the conn was selling climbs no hull could make (#102)

Task #102 said the orbit law fights itself and wastes **1,046 tonnes against an
ideal of 4** at an asteroid. That is true, and it is measured with an unlimited
tank, and **a hull carries twenty tonnes.** Everything in this cycle followed
from taking that seriously.

**What the tank changes.** Flown on the 20 t a captain opens with, across three
sectors and every rung of every body: **every high rung at every body was
offered and not one of them was reachable** — from a 77 km moonlet to a 38,723 km
giant. The ideal cost is 25 to 264 tonnes. So the captain spent the whole tank,
arrived at 63–76% of the height they asked for, and had nothing left to leave on.
The waste is real but the tank bounds it; what was actually broken was the
**offer**. `orbits.heights_for` has asked `holdable` since the ladder was
written — are the thrusters *fine* enough — and has never once asked whether the
tank is *big* enough.

So there is a price now. `climb_dv` is `|v_circ(from) − v_circ(to)|`, the cost of
a thrust-limited spiral, taken **from the axis of the orbit the ship is on rather
than from where it happens to be** — `semi_major_km`'s own docstring records why
and I got it wrong anyway, pricing a climb at 11.36 t that the hull then made on
3.93 because its axis was already most of the way there. `pilot.climb_options` is
the one door the console reads: every rung, its price, and whether the tank can
buy it. A refused rung is shown **greyed with the price on it** rather than
hidden, because the tank is volatiles in the hold — **a high orbit is a fuel
decision**, and a captain who wants one can go and buy the mass. Measured: the
same rung refused on 20 t and flown on 36.

**Both new constants came out of the data, and both first drafts were wrong.**
`QUOTABLE` is how much authority a rung needs before its price can be believed —
the worst rung whose spend ran away had 25.7 pulses inside the eccentricity
budget and cost **nine times its quote**; the best that behaved had 100.7 and cost
1.4×. Nothing in the sample falls between, so 60 sits with a factor of two in
hand either side. I first set 25 and `test_climbs` caught it inside a minute: a
rung quoted at 2.88 t went on to eat 18.83 of a 20 t tank. `CLIMB_MARGIN` is what
a price has to allow over the ideal; one climb in twelve came out above the ideal
and it came out at **2.03×**, so 1.4 was a promise that could not be kept and 2.5
is one that can.

**Three of my own faults, all of the same kind.** `climb_options` worked the
affordability out itself instead of asking `heights_for`, so the offer and the
gate disagreed — I built a two-doors bug an hour after writing about two-doors
bugs. `holdable` briefly had the fuel folded into it, and `test_orbits` refused
that immediately: *"4 of 6 withheld heights turned out to be perfectly
flyable"* — quite right, they are flyable given mass, and a predicate about
thruster fineness must not deny them. And `HEIGHT_TOLERANCE` lived in the
autopilot while the *price* needed the same line, so `quotable` refused the
standard rung at sixteen bodies of thirty-nine — the rung a transfer arrives at,
which costs nothing. It lives in `orbits` now and one constant answers both.

**And the law itself: two mechanisms found, and nothing shipped.** Task #101's
plane change **does not exist** — `hz/|h|` is 1.000 and the plane-change Δv is
0.0 m/s at every arrival — so the previous cycle's explanation for why a spiral
fails was wrong. Tracing it instead: the demand is purely tangential, so it asks
for *zero radial velocity*, and at e=0.005 with v≈4,840 the orbit's own radial
breathing is ±25 m/s — fifty-five pulses. The entire thrust went into braking an
oscillation it could not win, and braking removes energy: the axis fell 2,427 →
2,165 km and the hull went aground. Keep the radial component and a second
mechanism appears — demanding *circular speed at the radius you are at* pumps
energy into an eccentric orbit, because the ship lingers near apoapsis where that
demand says go faster. An apsidal law (prograde at apoapsis to raise, retrograde
at periapsis to lower, each of which also rounds the orbit off) is right on both
counts and flew the asteroid for **3.1 t against the shipped law's 1,205**.

**It is not shipped.** On 20 t it reaches 69–79% of a high rung against the
shipped law's 71–81%, and at an asteroid whose arrival periapsis is already 148 km
inside the rock it goes **aground** where the shipped law survives — its energy
pumping accidentally lifts the periapsis out. Four laws written, measured, and
withdrawn, with the mechanisms recorded in `sim/autopilot.py` so the next cycle
starts from the measurement rather than the intuition.

Six deliberate breakages, six caught: the tank gate removed, the quotable gate
removed, the price taken from the range instead of the axis, the margin flattened
to one, the ladder priced but never refused, and a refused rung hidden instead of
shown.

Five new checks, 953 across the suite, all green.
