# INTERFACE.md — SEEDFALL navigation map

The top-level map of the game. Read this before opening any source file in
`seedfall/`.

## What this is

**SEEDFALL** is a native PyQt6 space exploration / trading / combat RPG built on
the GESTALT design programme in this repository — a modern Starflight with a
Civilization layer. You command a grown starship in the Verge, survey and trade,
fight or refuse to, research a fifty-eight-node tech tree, design hulls out of
grown organs and fabricated machinery, plant colonies, and deal with the Bloom.

The GESTALT documents supply one of the five technologies and all of the
physics: the grown hull classes from the Fleet Class Reference, the six-layer
hull from the Design Dossier, the phosphorus bottleneck and 9:1 ore ratio from
Metabolism, the wet/dry cyborg control stack from Nervous System, the cell types
from the Cell Atlas, and the reproduction-licence containment regime from the
Fleet Registry. The other four technologies exist so that the grown fleet has
something to be measured against.

**Combat is positional.** Ships carry a heading and a speed on a real plane.
The five range bands still exist — weapons are specified in them — but the band
is *derived* from an actual separation rather than stored, so closing is a
manoeuvre rather than a menu pick. Every mount has a firing arc (fore, broadside,
turret) and will refuse to fire outside it, which makes turning to bring a gun to
bear a real decision.

**And you can only sit in one seat.** Each turn you take one station personally —
Helm, Gunnery or Engineering — and your officers hold the other two at their own
level, which is competent and worse than you. Directed gunnery shoots markedly
better than automatic; engineering routes power, patches the outermost breach or
dumps heat; the helm decides what will bear next turn.

**The Bloom is an antagonist, not a timer.** Five named stages advanced by the
sector-wide burden: past Motile it keeps roaming instars in the field that prefer
your colonies to empty ground; past Adaptive it builds resistance (up to 55%) to
whatever weapon family you keep using, and forgets what you stop using. At
Kessel's Reach, found by surveying the origin system, is the First Instar — the
original husk with a Charter serial still on it. Containment requires the sector
clean *and* that husk dead, which takes about twenty burn passes from a
battleship.

**Diplomacy has two axes.** Your standing with each power, and how the powers
regard *each other* — a relations matrix that starts hostile in most pairs.
Tribute, intelligence and relief move the first; only brokering moves the second,
and brokering requires both parties to think well of you already. Concord needs
all four at Kin **and** all six pairs at peace, so it is a diplomatic achievement
rather than four grinds.

**Getting anywhere is a decision.** A jump drops you at the system edge, not
alongside anything. Bodies sit on real orbits that keep moving while you fly, so
the range to a target depends on when you leave. Four burn profiles trade
reaction mass against days — and *coasting is always free*, which is what stops
an empty tank from becoming a deadlock. Local work (survey, extract, dig, land)
flies the ship alongside first, so a player who never opens the helm still gets a
coherent transit; the helm is where you choose a better one.

**A hull is only opened where there is a yard to open it.** A player asked why
they could refit anywhere. They could: `apply_refit` validated the design and
the cost and *nothing else*, so the rule lived in the button rather than the
simulation and any other caller — the remote bridge included — could strip a
hull in deep space. The button's own version was wrong twice besides: it
tested "this system contains a port", which since anchorages is not the same
as being alongside one, and it accepted any quay rather than one with a yard.
`shipyard.can_refit_here` is the rule now, expressed through
`anchorage.docked_at` and `offering(game, "shipyard")`, and the screen reads
it instead of holding its own.

**Which numbers are actually held in place.** `tests/tripwire.py` changes
every module-level tuning constant in the game — zero, double, half — and
reports the ones no check notices. A survivor is dead, tautologically checked,
or genuinely unpinned, and all three are worth knowing. The clean run: **60 of
131 unprotected**, the worst being `approaches.ODDS_PER_DAY`, which retires
the entire envoy system in silence when zeroed. `tests/test_tuning.py` pins
the worst of them, always against a figure written in the check and never
against the constant under test — the mistake this whole apparatus exists to
stop.

(The tool's own first run reported sixteen and was wrong: it rewrote source
between suite runs while Python served `.pyc` files compiled from the mutated
text, so restores did not reliably take. It runs with bytecode disabled now.
A tool that audits the tests has to be audited too.)

**A screen cannot free the widget that is talking to it.** The rule has cost
three segfaults — a `Card`, a `QLineEdit` mid-keystroke, and a `QComboBox`
whose popup was still delivering the click that dismissed it. Each was fixed
at its call site with `widgets.defer`, one at a time, as players found them.

`View.refresh` closes the class instead. The outgoing widgets are parked on
the view and released on the *next* turn of the event loop, so whatever
emitted is guaranteed to outlive the event it emitted during — whether or not
the call site remembered to defer. (They still do; it is belt and braces now
rather than the only thing standing between a drop-down and a crash.)

And the suite can now catch a signal instead of dying from one.
`tests/popup_probe.py` sends **real mouse events to a popup's viewport** —
the actual path the crash lives on, which `setCurrentIndex` and
`activated.emit` never touch — and runs as its own process, so a segfault is a
failed check with an exit code rather than a dead test run. Verified: backing
the fix out makes it report `exit -11`.

**There is somebody behind the counter.** A quay was a bag of services.
`sim/memory.py` has carried a `port` mind kind since it was written and a
fresh chronicle's store was empty and stayed empty — nothing ever put a person
where you dock fifty times.

`sim/officials.py` splits them in two, deliberately. **Who they are is
derived**: name, temperament and which lever could exist against them, seeded
from the port id, stable for the chronicle, no migration — the rule
`anchorage` and `traffic` obey. **What passed between you is stored**, on the
mind that already persists: regard, memories, levers found, favours running.

The politics is in the ceiling. Trading squarely makes somebody *helpful* and
stops — `DEALING_CAP` is a wall patience cannot climb. Past it you need either
something they want or something they would rather you did not say. Leaning on
a lever works whatever they think of you, costs **more** regard than asking as
a friend (`LEAN_MULTIPLIER`), spends the lever, and drops the ceiling honest
dealing can ever reach again (`CAP_PER_LEAN`) — you can trade your way back
into being useful, never back into being liked. Five favours, each read
somewhere real: a search that does not happen, a wider and richer contract
board, goods at the office rate, a berth regardless, a word before a claim.

**The powers come to you now.** Diplomacy ran one way: six actions, all
player→faction, and the powers themselves did exactly one thing — `drift`,
pulling their grievances back toward a baseline. So the four of them were a
vending machine. You put standing in and took tariffs out, and a captain could
ignore the board for twenty years without anyone knocking.

`sim/approach.py` is the other direction, and its rule is that **every
approach has to be caused**. A power asks for silicon because its own quays
are short of silicon — read off `Market.stock` and restricted to what is in
your hold, because "somebody has looked at what you are carrying" has to be
true. It asks you to denounce the Freeholds because it is losing to the
Freeholds. It warns you off a rival because you have been carrying that
rival's cargo. It offers terms because your standing has passed 62. It levies
your holdings because they are inside its declared space. Nothing fires
because a die came up; the die only decides *when*, among reasons that already
exist. No reason, no envoy — pinned by a check that plays four hundred months
with every trigger dead.

An envoy is something you can be part-way through, so it lives on `Game` with
an `.over` flag and `window.go()` will not let you wander off. Three answers,
each costed in full before it is taken — and **letting the window lapse costs
exactly what refusing costs**, because an offer with a free deadline is a
button that waits forever rather than a decision.

**A body can be worked out.** It used to cap at 95% depleted and then pay a
token tonne a session **for ever** — measured still yielding at trip 199,
identically to trip 20. So a seam never ended, there was never a reason to go
and find another, and a method that works a body gently bought nothing at all:
the cap arrived whatever you did.

`mining.worked_out` ends it, and the four methods finally pull apart. From one
body: `bore` lifts 2.45 t a day and takes 202 t in total; `leach` lifts 1.01 a
day and takes 407. Rate against lifetime, and neither number is visible from
the other, so `mining.prospect` states both — how long the body has left under
this method, and how much is still in it this way. `WORKING_LOSS` calibrates
that forecast against what a body actually gives up, because the midpoint
estimate read 15% high for every method including the one with no mishap risk;
`test_seams` re-measures it so it cannot drift.

**The four ways to run a programme are finally four choices.** Measured,
`push` was simply the best: fastest mean time to unlock — 76 days against
`careful`'s 132 — with its 28%-a-season setback risk *already inside that
figure*, because a setback costs progress and progress is what "days to
unlock" counts. Four approaches on the screen, one answer.

The blurb had named the missing cost from the beginning — *"skip the
confirmations, build on results nobody has replicated"* — and nothing read it.
A pushed result is **provisional** now: the technology unlocks and contributes
`PROVISIONAL_WORTH` (55%) of its bonuses until somebody goes back over the
figures, which costs bench time and no evidence. That is a cost days-to-unlock
cannot see, which is exactly why the dominance was invisible.

Measured after: to two *sound* technologies, `parallel` wins on a full bench
and `copy` on a thin one, and `push` — still the fastest to raw capability —
is the slowest of the four to soundness. No approach is best at everything.

**A near miss on the ground is worth something.** `SPOILED` sat in
`sim/expedition.py` with a comment reading "what a spoiled attempt is worth,
as a share", set to `0.0`, and read by nothing — found by `tests/tripwire.py`,
which is what it is for: a constant already at its degenerate value is either
dead or a feature somebody switched off and forgot.

So every attempt on the ground was all-or-nothing. Missing the mark by one and
fumbling it by five were the same outcome, an officer's level was a cliff
rather than a slope, and the screen — which states everything else before you
commit — had nothing to say about failure but that it might spring a hazard.

A miss inside `NEAR_MISS` now brings back a tapering share: measured, 645
credits for missing by one against 351 for missing by two, and nothing at all
beyond the window. Across every reward type a botch keeps 12–36% of a clean
attempt. The odds line says so — *"17% of the time, about 30% of the prize
still comes back"* — because "it fails" and "it fails and you keep a third"
are different decisions.

**The approach is drawn, and can be flown for you.** The docking mini-game
modelled an error per axis, a drift per axis, a readout blurred by the sensors
and a precision set by the hull and the navigator — and all of it reached the
player as three integers and six buttons. The drift reached them not at all,
so a pilot correcting the worst reading three times running could watch the
other two walk out of tolerance and never be told why.

`ui/approach_plot.py` draws it: range and attitude as a position against the
collar with the tolerance box at the centre, roll as the hull's tilt (a roll
error is not a position and pretending it is would be a prettier lie than the
numbers were), and a ghost showing where the next correction lands — drift
included. `minigames.forecast` is the number behind the ghost, and every burn
button now says what it leaves and which axes it lets slip.

`minigames.autopilot` is the drive computer, gated on the same `doctrine` stat
as the battle computer. It picks the axis that costs most to leave, weighing
how far out it is against where its drift is taking it, and cannot fire harder
than the hull allows. **It is priced**: a computer-flown approach is graded as
a bare clean dock. Measured, it docks about as often as a careful hand — 68%
against 68% — at grade 1.00 against 2.39. Before that cap it matched a good
pilot exactly, which makes an approach a chore to automate rather than a skill
worth having.

**The plot shows what bears.** Everything needed to answer "can this mount
shoot right now" was modelled — `tactical` knows the arc and the bearing,
`Weapon.bears_at` knows the range band, `combat._fire` knows if the magazine
is dry — and none of it was ever shown. It reached the player *after* the turn
was spent, as a log line explaining that the shot had not happened. So a
captain choosing between *come about* and *present the broadside* chose blind
and was told afterwards which had been right.

`sim/firing.py` answers per mount, before the turn: does it bear, is the range
right, is there ammunition, and if not exactly how far the bow must come round
or how many bands to close. The plot draws one wedge per arc, lit when
something in it bears, and the enemy's arcs faintly — sitting in a forward arc
is a decision. `closing_rate` is the other half of a static picture: a range
with no sign of which way it is going. It is the *instantaneous* rate, what
happens if neither hull turns, and is documented as such rather than dressed
up as a forecast the simulation would not honour.

Building it found the game holding **three** opinions on whether a gun can
fire — `_fire` refuses above 0.6, every selector picks only 0.5, and
`assessment` called anything above 0.5 unusable. In practice the gap is empty
(`bears_at` steps 0.22 a band, so penalties are 0, 0.22, 0.44, 0.66), so this
was a landmine rather than a live defect. `CAN_FIRE` and `WORTH_FIRING` name
both, `assessment` delegates, and a check holds the gap shut so widening a
weapon's bands has to be a decision.

**The seats you leave now think.** You are one person on a bridge with three
stations: you take one each turn and the officers hold the other two. What
"hold" meant was literal — `order_id = side.helm_order or "hold"` — so an
unattended helm repeated your last order until you came back to it. Order
*close* on turn one and walk to gunnery, and the helm flew you down the
enemy's throat for the rest of the engagement while a competent navigator sat
there doing exactly what they were told. That is not a hard choice about where
to spend attention; it is a punishment for looking away.

`sim/doctrine.py` is the battle computer. It reads the plane — band, aspect,
heat, hull, what bears — and picks an order for each empty seat, and the
battle screen states which and why **before** the turn resolves.

It is neither free nor better than you. `doctrine` is a stat off the compute
fitting: 0.15 for the wet-stack core you launch with, up to 1.00 for a Cold
Ledger. Below `MINIMUM = 0.30` there is no computer and the old
repeat-forever behaviour stands, which is what every other check in the suite
was written against. Above it the shortlist widens with the rating. And a seat
run by the machine works at the *officer's* rate, not yours — measured, the
computer vents 90% of what you vent sitting there — so choosing a station
still matters. Measured effect: 12.1% of the enemy's hull removed over 24
fights with no computer, 16.9% with an excellent one.

**The Verge is not empty.** Nothing gave another hull a *position*: encounters
were rolled the instant you arrived and thrown away, consorts followed you
implicitly, and faction ventures were a number in a ledger. So the sector
looked deserted in the one view that should look busiest, and "a Concordat
patrol jumped me at Loam Span" arrived with no warning it could have given.

`sim/traffic.py` derives a handful of hulls per system — traders, patrols,
prospectors, couriers, and the occasional unmarked hull — each with a name, a
faction, an errand and a position that moves with the clock along its leg.
**Derived, not stored**, like anchorages: persistent identity with no
migration, at the price that derivation must never touch `game.rng()`, which
advances with the save and would reshuffle the sector on every reload.

The payoff is that the chart *predicts*. `roll_encounter` weighs who is
actually present, so the hull that turns onto you is one you could have
plotted first — by name — and a system with something running dark is
measurably more dangerous to arrive in (18% of arrivals contested against 6%,
same system, same day). Busyness follows the port: a capital works five hulls,
unclaimed space one, and a system the Bloom has eaten fewer than either,
because the traffic left.

**A berth is a place.** A player asked why the helm shows only the star and
the planets, and how they would ever navigate back to a shipyard. They could
not: a `Port` hung off a `System` with **no position at all** — no body, no
orbit, no coordinates. The quay you were standing on was nowhere in space, and
docking was a screen you switched to from the chart, so the one view you fly
from could not show you the one place you most need to fly back to.

`sim/anchorage.py` gives each one somewhere to be, anchored to a body — which
means it inherits a real orbit that moves with the clock, and every intercept,
burn profile and transfer quote works on it unchanged, because flying to a
quay *is* flying to the body it orbits. Anchorages are **derived, never
stored**, like `ship.stats()`: one source of truth, no migration, and no way
for a saved quay to disagree with the port it belongs to. The price of that
choice is that derivation must not depend on the clock or the RNG, which is
what `test_anchorage` pins.

The helm now draws quays (▣), capitals (◈) and your own holdings (⬡) with
labels, says in words where the hull is standing, and lists everything you can
put in at with a course and a fuel bill. `offering(game, "shipyard")` answers
the original question directly. Known *hulls* are still not plotted — nothing
in the game gives another ship a persistent position, so that is honestly a
separate piece of work rather than a marker.

**The hands get older too.** A player asked why they did not. Because
`ship.crew` was an integer — a headcount with nothing to hang an age on — so
"your crew ages on a long crossing" was true of the three named officers and
of nobody else aboard. A twenty-year chronicle retired the bridge and left the
lower decks untouched, and sleeping the hands saved something no number
recorded, which is exactly why a dormancy bug hid there for a cycle.

They are still a mass, deliberately: two numbers on the `Ship`, a mean and a
spread, aged by proper time at the lineage's rate and slowed by whatever share
of them is under. The spread is what makes ageing-out a slope — as it carries
part of the mess deck past the lineage's span they start leaving, a few a
year, rather than the hull emptying on one tick.

And they can finally be **replaced**. `ship.crew` moved in exactly one
direction before — down, through fighting, hunger, and sleeps somebody did not
come up from — with no way to sign anybody on at all. `lifespan.sign_on` takes
hands within the berths that exist, for a fee, and a young intake pulls the
average down: an old deck at 80 comes back to 49.

**And you can sleep through it.** Dilation was the only answer to a long
crossing: fly harder and pay in reaction mass — an engineering answer to a
biological problem. `sim/dormancy.py` is the other one. `trehalose` has sat in
the commodity tables since the beginning described as *"vitrified sugar with
CAHS proteins; replaces the water in a cell and holds it, unbreathing"* — the
sugar real tardigrades use — and nothing ever consumed a gram of it.

Three methods and a null: **cold sleep** (a third of the ageing, a third of
the rations, 0.6% a head per hundred days), **trehalose vitrification** (4% of
the ageing and 5% of the rations, at 2.4% a head and a real bill in sugar),
and **low-power idle**, which only a Dry Choir lineage can do because it is
not sleep at all. Measured over a 600-day crossing: a sleeper ages 0.07 years
against the watch's 1.64, and eats 13 tonnes against 61.

The design turns on three rules. **Somebody stays awake** — `MIN_WATCH`, and
the watch pays full price in years and rations. **The saving is on proper
time**, folded into `lifespan` and `upkeep` rather than special-cased, so what
the screen promises and what the clock applies cannot drift. And **it does not
stack free with dilation**: both cost the ship's own work, so doing both costs
it twice — measured, a year banks 712 research awake at rest, 154 asleep, 123
at dilation 4, and 30 doing both.

**Time is relative, and there are two clocks.** `Game.day` is the Verge's:
every deadline, market, colony, faction and hull-in-a-yard runs on it.
`Game.ship_day` is proper time — what the hull and the people in it actually
live through. They agree until you fly a crossing hard, and `advance_days(n,
dilation)` is the only place either is written.

The split is a design statement, not bookkeeping. **Sector time**: markets,
ventures, diplomacy, colonies, contracts, the Bloom. **Ship time**: research,
repair, cooling, refining, ageing, upkeep, morale, wages. So a hard burn buys
your crew their remaining years back and costs you everything you would have
got done in the years you skipped — a `data/crossings.py` choice between a
long coast, a steady transit, a hard burn and a relativistic run, at 1× to 11×
dilation and 0.45× to 5× the reaction mass.

**Who is aboard, and what time does to them.** Everyone used to be the same
thing: immortal, breathing, eating nothing — while the opening screen sold a
**Dry Choir** lineage on "no air to run out of" and the daily tick asphyxiated
your recordings on exactly the same schedule as a wet crew. A lineage
(`data/lineages.py`) is a substrate, and it decides three things:

| Lineage | Prime / span | Ages at | Eats per head per day | Breathes |
|---|---|---|---|---|
| Wet | 52 / 96 y | 1.00× | biomass (a tonne a head a year) | yes |
| Grafted | 88 / 164 y | 0.58× | biomass + magnetite | yes |
| Dry Choir | 240 / 620 y | 0.14× | silicon + magnetite, 16× the power | **no** |
| Xenoform | 380 / 900 y | 0.07× | volatiles + a trace of xenolith | no |

Upkeep is drawn from commodities the economy already trades, deliberately: a
bill payable in a currency nobody sells is a tax, not a decision. A hull is
provisioned on day one with 220 days of *its own* crew's consumption, so a
Choir captain is not punished for a choice made on the character screen.
Going short is slow — six days of grace, then it costs people or levels
depending on what ran out.

**How you look at a body decides what you find.** Surveying used to be one
button: three days, no cost, no risk, the same kind of answer for a comet as for
an ocean world — while thirteen sensor fittings and a drone technology existed
only to nudge a single `scan` float. There are now four methods, and they are
deliberately *not* a ladder:

| Method | Flies there | Sees | Blind to | Wants |
|---|---|---|---|---|
| Long-range sweep | no | resources | life, anomalies, anything buried | to be inside your sensor reach |
| Close pass | yes | resources, life, anomalies | anything buried | reaction mass for the trip |
| Probe swarm | no | resources, life, anomalies | anything buried | `dronework`, 3 t silicon + 2 t alloy |
| Deep survey | yes | everything, including buried sites | — | scan ≥ 0.55, 4 t of charges, nine days |

Each method names what it `finds`, and `world/planets.survey_body` is filtered
by that list, so a method that says it cannot see lifeforms genuinely cannot.
The panel states the whole bill before you commit — days, stores, **and the
reaction mass for getting there** — plus what the method will be blind to, which
is the part that makes choosing one a decision rather than a formality.

Sensor reach is what gates the free method, and it is the reason a **listening
post is worth planting**: three colony classes advertise sensor reach, and
`colony.effects` has tallied it per system since they were written — but nothing
ever read the tally, so a CHORUS node extended your array by exactly nothing.
`sim/survey.reach()` reads it now. It stays per-system rather than folded into
`ship_stats`, because a dish spread across one system should not help you three
jumps away.

**Two mini-games.** The **docking approach** is the control loop from the
nervous-system study — sense, compute, act, hold homeostasis — with three drifting
axes, one correction per pass, and readings blurred by how good your sensors are.
A clean approach earns standing; a botched one buys a tug. The **decoding bench**
takes a recording of something that was not speaking to you: four positions, a
hidden pattern, and feedback that tells you how many glyphs are exactly right and
how many are merely present, never which. Solving one is worth alien
understanding, and costs nothing but attempts.

**There is a game on the ground.** Landing a party opens a 7×7 zone map revealed
one tile at a time. Moving costs days of supply (known ground is cheap to
re-cross, which is what makes coming home survivable); terrain springs hazards
that officers' skills mitigate; site features offer choices resolved against a
named stat. Nothing is banked until the party is back on the lander, and running
out of supply in the field costs most of the haul. How much biomass you commit at
launch buys how long they can stay.

**Contracts are optional work with deadlines.** Six kinds, posted per port and
scaled by distance. They are checked on the clock and complete the moment their
terms are met rather than when you remember to hand them in. Nothing in the game
requires taking one — the five endings are open from turn one.

**Alien technology is a separate progression from research.** Four cultures —
the Abyssals, the Ossuary, the Weft and the Tessellate — left twelve
technologies scattered across the sector as buried sites. None can be reasoned
out. Understanding accumulates in study points from four sources: excavating a
site, taking relics apart in a laboratory, buying somebody's field notes at a
port, and seizing them off a hull you destroy. At full understanding the
technology is *incorporated* — its id is appended to `research.unlocked`, so the
shipyard and codex treat it like anything else you know, and it never appears in
the research tree because you could not have derived it.

**Thirty-five hulls and nineteen stations across five families:**

| Family | Hulls | Character |
|---|--:|---|
| Grown | 12 | Gestated from a seed. Heals; eats phosphate; takes months. |
| Fabricated | 13 | Concordat of Yards. Welded in weeks, dear, and never mends. |
| Hybrid | 4 | Freehold grafts. Both bills, both gifts. |
| Synthetic | 4 | Dry Choir. Crewless, superb instruments, no self-repair. |
| Xeno | 2 | Not ours. It mends, and nobody has explained how. |

Which parts graft to which frame is `ACCEPTS` in `data/hull_types.py`: a grown
hull refuses a fusion lance, a Yards hull refuses an intima, a hybrid takes
either, and a synthetic frame takes fabricated and Dry Choir work but nothing
alive.

## Running

```
python -m seedfall                  # title screen
python -m seedfall --new            # straight into a new chronicle
python -m seedfall --seed verge-7   # a specific sector
python -m seedfall.tests            # simulation + interface suites
python -m seedfall.tests sim        # one suite
```

Requires **PyQt6** (`pip install PyQt6`). Nothing else — no network, no server,
no browser. Saves live in `~/.seedfall/save.json`.

## Layout

```
seedfall/
├── __main__.py         entry point: python -m seedfall
├── core/               engine primitives — no game rules, no Qt
│   ├── rng.py          seeded mulberry32 + pick/weighted/gauss/shuffle helpers
│   ├── util.py         formatting (credits, mass, stardate, duration) and clamp
│   ├── save.py         generic dataclass ⇄ JSON codec, @register, atomic write
│   ├── solid.py        a tiny 3D kit: primitives, projection, key/fill/rim
│   │                   lighting, specular and a depth term
│   ├── llm.py          optional language model, off by default, hard timeout
│   └── state.py        the Game object, advance_days(), new_game(), load_game()
├── data/               static content tables — pure data, no logic
│   ├── commodities.py  14 tradeable goods
│   ├── beginnings.py   stocks, origins and postings — who you are before day one
│   ├── personas.py     voices: register, tics, and offline sentence frames
│   ├── screens.py      the rail and the key for each screen — read by both layers
│   ├── help.py         the manual: prose, and which facts each topic generates
│   ├── lessons.py      the tutorial's eight steps, and what each one watches for
│   ├── epochs.py       what the Verge becomes after each of the ten endings
│   ├── scenarios.py    40 situations an epoch puts in front of you
│   ├── chassis.py      the hull registry — assembles and re-exports the rest
│   ├── hull_types.py   layer stacks, the Chassis record, family rules (ACCEPTS)
│   ├── hulls_grown.py  the 12 GESTALT classes
│   ├── hulls_built.py  13 fabricated · 4 hybrid · 4 synthetic · 2 xeno
│   ├── part_types.py   Part / Weapon / Ability shapes, slots, range bands
│   ├── modules.py      drives, power, sensors, compute, utility organs
│   ├── armaments.py    weapons and defences
│   ├── parts.py        merged registry over modules + armaments
│   ├── tech.py         61-node research tree, 10 branches, 5 tiers
│   ├── colonies.py     19 colony and station classes, and `EFFECT_TEXT`:
│   │                   what each grant means, in words
│   ├── factions.py     6 powers + reputation bands
│   ├── lifeforms.py    xenobiology generation tables + anomalies
│   ├── strata.py       the four layers of a dig, 3 methods, finds and spoils
│   ├── contraband.py   who outlaws what, how hard they look, what they say
│   ├── territory.py    what a power says when its claim lands on your ground
│   ├── charts.py       what each power pays for a survey, and what for
│   ├── surveys.py      the four ways of looking, and what each cannot see
│   ├── approaches.py   the powers coming to you: what each wants, and why
│   ├── officials.py    harbourmasters: tempers, levers and favours
│   ├── dormancy.py     ways of sleeping a crossing, and what each risks
│   ├── lineages.py     what a crew member is made of: span, upkeep, ageing
│   ├── crossings.py    how hard to fly a jump, and which clock pays for it
│   ├── fieldnotes.py   the eight things the ground can tell you
│   └── lore.py         intro, victories, endings, name pools, glossary
├── world/              generated content
│   ├── galaxy.py       sector generation, lane relaxation, distance/transit
│   ├── planets.py      bodies, biomes, resource grades, survey resolution
│   └── economy.py      per-port supply/demand, prices, market drift
├── sim/                game rules — never import Qt
│   ├── ship.py         Ship model, stats(), layer stack, cargo, repair
│   ├── shipyard.py     design validation, costing, build queue, refit
│   ├── combat.py       turn resolution, firing, damage, endings;
│   │                   `_run_seats` runs helm and engineering either way;
│   │                   `cook()` holds heat under `HEAT_CEILING`
│   ├── battle_state.py the Side and Battle shapes, shared by resolver/AI/UI
│   ├── tactical.py     the plane: positions, headings, firing arcs, bands
│   ├── stations.py     helm / gunnery / engineering orders
│   ├── enemy_ai.py     how the other side fights — same geometry, no cheating
│   ├── abilities.py    defensive abilities, returning their own log lines
│   ├── colony.py       founding, daily yields, aggregate colony effects
│   ├── research.py     project selection and point accrual
│   ├── crew.py         officers, recruitment, experience, morale
│   ├── encounters.py   NPC generation and transit events
│   ├── threat.py       Bloom growth and spread, cleansing, victory checks
│   ├── xeno.py         study points, incorporation, alien passive bonuses
│   ├── bloom.py        stages, roaming instars, resistance, the First Instar
│   ├── contracts.py    generation, acceptance, progress, expiry
│   ├── diplomacy.py    standing, the relations matrix, treaties, brokering;
│   │                   every gift priced through `allegiance`
│   ├── expedition.py   the ground game: zone map, movement, attempts, hauls
│   ├── reach.py        what you can get to at all, and what a drive would open
│   ├── plans.py        the ship as solids: hull, fittings, hold, berths;
│   │                   `scar()` marks the blight a hurt hull shows
│   ├── beginning.py    turning an opening choice into a chronicle
│   ├── legacy.py       life after an ending: epochs, pressure, situations
│   ├── telemetry.py    what the instrument windows read, band by band
│   ├── memory.py       minds: what everyone remembers about you
│   ├── grudge.py       what a power's memory costs you, and why
│   ├── voice.py        speech, written by the game or by a model
│   ├── manual.py       resolves the manual's facts from the tables themselves
│   ├── options.py      player settings, every one of which does something
│   ├── tutorial.py     watches the game until the thing has actually been done
│   ├── fieldwork.py    everything done off the ship — digs, analysis, landings
│   ├── assessment.py   reading an engagement: who wins, why, what to do
│   ├── chains.py       commissions: work that escalates and closes doors
│   ├── inquiry.py      evidence, approaches, setbacks and breakthroughs
│   ├── intel.py        how well a system is known, and what a chart is worth
│   ├── loading.py      fitted mass against what the hull is rated to shift
│   ├── orders.py       which standing orders apply — the discoverability index
│   ├── parley.py       breaking off and talking your way out
│   ├── transit.py      standing the watches of a crossing
│   ├── dig.py          working a site stratum by stratum, banking as you go
│   ├── customs.py      the contraband run: the unposted price and the search
│   ├── allegiance.py   what serving a power costs you with its enemies
│   ├── territory.py    claims against holdings: trespass, levy, defiance
│   ├── charts.py       pricing a survey by what is actually in the system
│   ├── aftermath.py    what an engagement leaves behind: salvage and standing
│   ├── notes.py        field notes: filed, looked up again, and worth something
│   ├── trade.py        buying and selling over a counter, and survey data
│   ├── services.py     repairs, a paid word, and a fortnight of bench time
│   ├── freight.py      the freight desk: what is worth loading, and where
│   ├── responses.py    provocation, the Bloom's answers, and studying a mass
│   ├── market.py       supply shocks, and the prices you wrote down
│   ├── ventures.py     what the powers do on their own account
│   ├── weather.py      the front overhead during a landing
│   ├── mining.py       seams, depth, and how hard you work a body
│   ├── rumours.py      leads that point somewhere before you have been
│   ├── consorts.py     escorts: standing orders, screening, who draws fire
│   ├── loyalty.py      what the bridge thinks of how you run the ship
│   ├── works.py        colony development: what a settlement becomes
│   ├── flight.py       the helm: orbits, intercepts, routing, transfer burns
│   ├── survey.py       what a way of looking costs, finds, and is blind to
│   ├── approach.py     a power's envoy: caused, costed, and answerable;
│   │                   a treaty signed here costs what one you propose costs
│   ├── officials.py    who runs the quay, what they think, what you know
│   ├── anchorage.py    quays, hubs and holdings — places you can put in
│   ├── traffic.py      other hulls: where they are and what they are doing
│   ├── doctrine.py     the battle computer: what unattended seats decide
│   ├── firing.py       which mounts bear, and what would fix the rest
│   ├── damage.py       a hit: which layer takes it, what breaches, the words
│   ├── dormancy.py     who is under, what it saves, and who wakes up
│   ├── lifespan.py     ageing, decline, and the end of a career
│   ├── upkeep.py       what each lineage eats, and what going short costs
│   ├── minigames.py    the docking control loop and the decoding bench
│   └── actions.py      player actions spanning modules (jump/survey/mine/dive)
├── ui/                 PyQt6 presentation — never mutates state directly
│   ├── theme.py        palette, fonts, the global stylesheet
│   ├── widgets.py      Panel, Card, Bar, Pill, TabBar and the View base class
│   ├── window.py       MainWindow: hud, nav rail, view stack, log, dialogs
│   ├── title.py        title screen and the opening briefing
│   ├── app.py          QApplication bootstrap
│   ├── map_view.py     custom-painted sector chart and jump control
│   ├── system_view.py  bodies, survey, extraction, diving, colonising
│   ├── survey_panel.py the four methods as cards, each stating its blind spot
│   ├── crossing_panel.py  the four ways to fly it, costed on both clocks
│   ├── anchorage_panel.py where you can put in, and how to get back to it
│   ├── traffic_panel.py   who else is out here, and which of them runs dark
│   ├── doctrine_panel.py  what the seats you are not in intend this turn
│   ├── firing_panel.py    mount by mount: ready, or exactly what is stopping it
│   ├── approach_plot.py   the docking approach, drawn instead of counted
│   ├── envoy_view.py      a power's proposition, with all three answers costed
│   ├── official_panel.py  the desk: who is there, and both ways of asking
│   ├── dormancy_panel.py  the long sleep, costed in years, tonnes and lives
│   ├── tactical_plot.py   the engagement from above, arcs included
│   ├── port_view.py    market, services, recruitment
│   ├── board_panel.py  the contract board, split out of port_view
│   ├── ship_view.py    layer stack, fittings, crew, hold
│   ├── plans_panel.py  the ship drawn: materials, rim light, blight
│   ├── yard_view.py    hull designer, build queue, fleet management
│   ├── tech_view.py    research tree
│   ├── empire_view.py  colonies, depot, victory progress, waiting
│   ├── codex_view.py   class reference, powers, glossary, about
│   ├── xeno_view.py    the xenology desk (hosted as a Research tab)
│   ├── expedition_view.py  the landing zone: fogged map, party, field log
│   ├── diplomacy_view.py   relations matrix and the overture desk
│   ├── helm_view.py    orbit chart and burn planner
│   ├── minigame_view.py    docking approach and decoding bench
│   ├── dig_view.py     the trench: the stratum you are on and how to take it
│   ├── blackmarket_panel.py  the quiet word on the quay, and the tip-off
│   ├── freight_panel.py  what is worth loading here, and what it clears
│   ├── demand_view.py  answering a power that has annexed ground you hold
│   └── battle_view.py  combat screen and post-engagement resolution
└── tests/              python -m seedfall.tests
    ├── harness.py      a tiny check runner (no pytest dependency)
    ├── test_sim.py     27 simulation checks
    ├── test_xeno.py    5 alien-technology checks
    ├── test_play.py    14 playability checks — can the game be won and lost
    ├── test_combat.py  5 tactical checks — arcs, stations, consorts
    ├── captain_ai.py   a competent test pilot: steers until its arcs bear
    ├── test_empire.py  6 colony checks — works, effects, costs, persistence
    ├── test_crew.py    7 crew checks — convictions, loyalty, consequences
    ├── test_missions.py 7 commission checks — escalation, blocking, lapsing
    ├── test_explore.py 8 exploration checks — the intel ladder, rumours
    ├── test_mining.py  7 mining checks — seams, methods, wear, exhaustion
    ├── test_research.py 8 research checks — evidence, approaches, setbacks
    ├── test_trade.py   8 trade checks — shocks, the register, staleness
    ├── test_ground.py  7 ground checks — weather, sight, being pinned
    ├── test_politics.py 8 politics checks — ventures, sides, the Concord
    ├── test_design.py  6 design checks — loading, overloading, stranding
    ├── test_orders.py  8 orders checks — reachability, urgency, unread state
    ├── test_assessment.py 6 read checks — honesty, arcs, robustness
    ├── test_balance.py 8 balance checks — measured by playing the fights
    ├── test_bloom_arc.py 7 Bloom checks — provocation, answers, study
    ├── test_transit.py 6 crossing checks — watches, aborting, tension
    ├── test_customs.py 9 contraband checks — the premium, the search, heat
    ├── test_allegiance.py 8 checks — taking sides, and brokering out of it
    ├── test_territory.py 8 checks — annexation, levy, defiance, seizure
    ├── test_charts.py  9 chart checks — contents, buyers, staleness, rate
    ├── test_aftermath.py 7 checks — salvage, standing, and who is glad
    ├── test_notes.py   8 field-note checks — filed, counted, kept, reachable
    ├── test_layers.py  5 layer checks — no Qt below, no ledger above
    ├── test_cargo.py   6 cargo-contract checks — the board offers no traps
    ├── test_freight.py 7 freight checks — the desk, its floor, and a career
    ├── test_workings.py 7 mining checks — the rig stops when the hold is full
    ├── test_burns.py   7 burn checks — heat, cooking, and a real profile choice
    ├── test_bench.py   5 bench checks — the draw matches what the screen says
    ├── test_works.py   5 works checks — nothing gated behind a phantom tech
    ├── test_overtures.py 5 checks — the preview is what the overture does
    ├── test_seats.py   6 seat checks — what taking a station is worth
    ├── test_founding.py 5 checks — the seed dialog says what will grow
    ├── test_attempts.py 6 checks — the odds shown are the odds rolled
    ├── test_reach.py   6 reach checks — the chart's wall is a real wall
    ├── test_plans.py   8 plan checks — the model is the ship, and it is solid
    ├── test_picture.py 8 checks — the picture shows the ship's condition
    ├── test_courting.py 8 checks — a gift is seen by the recipient's enemies
    ├── test_thermal.py 12 checks — guns and helm both bounded
    ├── test_helm.py    5 checks — every number on the burn board is accounted
    ├── test_grants.py  5 checks — every colony grant is read, and explained
    ├── test_postings.py 5 checks — the board only offers work you can reach
    ├── test_counter.py 5 checks — the board's price is the counter's price
    ├── test_landing.py 6 checks — walking home beats stranding
    ├── test_charting.py 5 checks — a chart is dated, and goes off
    ├── test_conviction.py 6 checks — every event an officer cares about fires
    ├── test_bench_kinds.py 5 checks — evidence names are real, tech is reachable
    ├── test_envoy.py   7 checks — the preview is the answer, both doors alike
    ├── test_seatwork.py 5 checks — the crew hold their seats either way
    ├── test_thermal_doors.py 5 checks — every heat door goes through one gate
    ├── test_ventures.py 6 checks — both sides of a venture are costed
    ├── test_orderplan.py 6 checks — every order says what it will do
    ├── ground_ai.py    a party leader good enough to measure the ground with
    ├── suites.py       the suite table `__main__` dispatches from
    ├── test_beginnings.py 9 checks — the commission you pick is the one you get
    ├── test_legacy.py  7 aftermath checks — an ending is a turn, not a stop
    ├── test_instruments.py 5 checks — a gauge agrees with the ship and itself
    ├── test_voices.py  8 checks — the game speaks with no model reachable
    ├── test_grudges.py 9 checks — memory reaches the price and the board
    ├── test_gunnery.py 5 checks — what a weapon delivers is what the bridge said
    ├── test_controls.py 4 checks — every control that is not a button
    ├── interact.py     plays by pressing what is on the screen, not by calling sim
    ├── test_bridge.py  6 checks — the protocol answers, always, and stays local
    ├── test_manual.py  13 checks — the manual cannot go stale, options cannot lie
    ├── test_tutorial.py 8 checks — it will not take your word for it
    ├── chronicle.py    one captain, one save, a decade of doing everything
    ├── test_chronicle.py 3 checks — that decade, through every screen
    ├── capture.py      renders every screen offscreen, for the README
    ├── captain_bot.py  the long-game captain the playability checks fly
    ├── probes.py       the newer efficacy probes, split out of levers.py
    ├── test_dig.py     7 dig checks — strata, methods, banking, backfilling
    ├── test_resume.py  5 resume checks — anything half-done survives a save
    ├── efficacy.py     the harness: neutralise a feature, measure the world
    ├── levers.py       one entry per claim the game makes about a number
    ├── test_efficacy.py 31 checks — every feature has to move something
    ├── test_reachable.py 4 reachability checks — nothing written and uncalled
    ├── test_verbs.py   10 verb checks — every control in the game, clicked
    ├── test_flight.py  5 helm checks — determinism, intercepts, routing
    └── test_ui.py      24 interface checks, rendered on Qt's offscreen platform
```

## How the layers connect

The dependency rule is one-directional and worth preserving:

```
data/  ──►  world/  ──►  sim/  ──►  ui/  ──►  __main__
                    core/ is available to everything
```

- **`core/state.Game` owns time.** `advance_days(n)` is the only clock: it ticks
  research, colonies, build slips, hull regrowth, every market, payroll, air,
  morale and the Bloom, then checks for victory. Nothing else advances a day.
- **`sim/` never imports Qt.** It takes a `game` and returns plain data. That is
  why the simulation suite can run headless and why the whole rules layer is
  testable without a display.
- **`ui/` never mutates state directly** — a view calls a `sim/` function, then
  `win.refresh()`, which recomputes derived values and redraws.
- **`ship.stats()` is the single source of derived numbers.** Chassis base +
  fitted parts + research bonuses + officer skills, with a power-brownout
  multiplier. Anything asking "how far can this ship jump" asks `stats()`.
- **Views subclass `ui.widgets.View`** and implement `build()`; the base class
  clears and rebuilds the column on every refresh. Simple and fast enough — a
  full screen is a few hundred widgets.

## The parts that will bite you

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

  **Put heat in with `ship.add_heat`, which clamps on the way in.** This used
  to say "call `cook()` wherever heat is added; there are exactly two such
  places" — and there were six. A crossing watch, a flight incident, an
  action's own effects and taking a hit in combat all added heat raw, so a
  fault alone took a hull sitting at the ceiling to 2.36x its cap. Asking
  callers to remember is what four of six did not do.
  `tests/test_thermal_doors.py` fails on any `\.heat +=` outside `ship.py`.
  (`sim/customs.py` has its own unrelated `add_heat` — scrutiny from the
  revenue, not thermal load.)
- **Heat is bounded by `HEAT_CEILING`, and that is load-bearing.** It used to
  be unbounded, and because the overheat penalty scales with how far over the
  cap you are, it compounded: a Bastion firing the five heavy mounts it has
  slots for went 68 → 132 → 187 → 243 → 279 and routed itself on turn five at
  93% hull. `cook()` is called from `_fire`, which is the only thing in the
  game that adds heat, so one clamp at the source covers every hull. An
  end-of-turn clamp was tried too and measured to change nothing at all, so it
  was removed rather than left in looking useful.
- **Every tuning constant is pinned, and that is measured rather than
  assumed.** All 153 module-level numeric constants across `data/`, `sim/` and
  `core/` were swept: doubled, halved and zeroed, and every one is noticed by
  a check. The sweep also reports *where* the protection comes from — a
  constant caught only by the wide set is held up by a suite that happened to
  walk past, which is a thinner thread than a check written for it.
  `consorts.WITHDRAW_AT` was the only one in that state and now has its own.
  Re-run with `python3 -m seedfall.tests.tripwire`; about seventy minutes, and
  never alongside the suite, because it rewrites source while it works.
- **A forecast has to clamp what the hull clamps.** `order_preview` quotes
  what the heat *becomes*, not the raw sum: a salvo worth 74 on a hull at 30
  with a 50 cap stops at the ceiling, so the line reads "heat 30 → 100 of 50 —
  pinned at the ceiling" and not "→ 104". My first draft quoted the sum, which
  is the same defect the function exists to fix, one layer up.
- **A screen with two buttons has to price both of them.** The ventures panel
  showed the odds as they stood, priced *backing*, and left "Work against it"
  bare — no standing cost, and no hint that either button moves the odds by
  `SWAY`: measured, a 51% venture becomes 81% backed and 21% opposed. It never
  mentioned that being right afterwards pays again either. `RIGHT_BACKED` and
  `RIGHT_OPPOSED` were bare numbers inside `_resolve`; they are in
  `data/ventures.py` now and `ventures.preview` reads the same ones.
- **`tripwire.KIN` is hand-written, and a stale entry fails silently.** The
  tool runs a constant against its own neighbourhood first and only pays for
  the wide sweep if that passes. An entry naming a suite that no longer
  exists makes `python -m seedfall.tests <name>` run nothing and exit zero, so
  the fast stage "passes" every time and every constant quietly costs the full
  run — measured, `ship` swept in 17s with a fast path and 240s without. An
  entry naming a `SLOW` suite is worse: the verdict then depends on whether a
  module has an entry at all. `test_harness_guard` holds both, and requires
  every module with constants either to have a fast path or to be named as
  having no suite that covers it.
- **Every action that spends a turn must run the seats.** `take_turn` takes
  two shapes: `{"type": "station", "order": ...}`, which runs the crew-station
  system, and the older `{"type": "fire", "weapon_id": ...}` family, which the
  battle screen still uses for the firing picture's per-mount buttons and the
  ability buttons. The older shape never called `_run_stations`, so picking a
  mount meant nobody flew the ship and nobody stood in engineering that turn —
  measured, heat 30 ended at 24.0 through the old door and 19.44 through the
  new, with `helm_order` still `None`. Only `move` had ever been migrated.
  `_run_seats` is now called from both. Note the helm runs *before* the guns
  on both paths, so a mount that bears when you press the button may not bear
  when the shot goes.
- **`TREATY_WEIGHT` is read by both doors into signing one.**
  `diplomacy.perform` charges the signatory's enemies through
  `sim/allegiance.py`; `approach.answer` did not, so the same instrument with
  the same signatory cost −6 with each of three powers when you proposed it
  and **nothing** when you accepted their offer. Waiting to be asked was how
  you signed a treaty for free. Both read the one constant now, and
  `preview` states the price.
- **`preview["credits"]` is money moving; `preview["offer"]` is the price on
  the table.** They were one field, and the envoy screen rendered a haggle as
  "Treasury: +794" — a captain reading that row believed they had been paid
  for asking. Nothing is paid until the offer is accepted.
- **A fixture that names something the game does not know is invisible.**
  `inquiry.add` returns 0.0 for an unrecognised kind — silently, which is
  right for a sim that must survive an old save. `test_provisional` typed six
  evidence kinds by hand; three (`field`, `relic`, `trade`) do not exist and
  one that does (`reading`) was missing. Six of the ten branch mixes want
  `reading`, cognition 35% of it, so the suite that decides whether any
  research approach dominates measured those branches 20–30% slow. Derive
  from `EVIDENCE`, as `test_bench` always did. `tests/test_bench_kinds.py`
  checks the call sites **and** any hand-written `*KINDS` list, because the
  call site passed a variable and no search of call sites could have seen it.
- **A returned value nobody reads is a feature nobody gets.** `crew.grant_xp`
  hands back the officers it has just promoted — that is what the return is
  *for* — and all eight call sites dropped it, so `promoted` (+5 to everyone
  aboard, it is in `UNIVERSAL`) never once fired and a promotion was not even
  logged. Pass `game=` and it reports itself: the ship feels the event, the
  officer gets `PROMOTION_OWN` on top, and it goes in the log.
- **An event whose name is composed cannot be found by searching for it.**
  `loyalty.served` builds `f"{conviction.id}_served"`, so the audit in
  `tests/test_conviction.py` keeps an explicit `COMPOSED` allowance and proves
  those separately by behaviour. Anything else must appear literally in
  `sim/`, `core/`, `ui/`, `world/` or `bridge/`.
- **Two doors into the same event will drift, and the drivers use the working
  one.** Surveying a body can be reached through `actions.survey` — which the
  remote bridge and every test driver call — and through `survey.perform`,
  which the screen calls. Only the first dated the finished chart, so
  `charts.freshness` returned 1.0 for every chart a player ever made:
  `FRESH_DAYS` and `STALE_FLOOR` decided nothing, and the survey office's
  "Age of the survey" row sat behind `if fresh < 0.95` and could not fire.
  Nothing caught it because every driver in the suite went through the door
  that worked. `tests/test_charting.py` asserts both doors leave the same
  state.
- **Order the penalties after the limits, not instead of them.**
  `haul_kept` applied the carrying limit on the way home and skipped it
  entirely when the party stranded, so stranding returned 40% of an *uncapped*
  pile: 500 t collected came home as 200 t stranded against 60 t returned. The
  penalty was a reward by a factor of twenty-three, and the way to play the
  ground was to strand the party deliberately. Cap first, charge second.
- **`tests/ground_ai.py` is to the ground what `captain_ai` is to combat.**
  Walking a party at random and grabbing whatever is underfoot measures
  nothing, because it never returns to the lander, so every policy strands and
  scores the same. `margin` — supply held back for the walk home — is the one
  decision the ground poses, and sweeping it should show a peak in the middle:
  measured 29 t at margin 0, 35 t at 4, 23 t at 14.
- **Establishing state by hand can make a check unreachable.**
  `test_officials` proved the office rate worked by writing it into the dated
  `favours` dict directly. It does not get there that way: a quiet price is
  granted "this once", carries `lasts=0`, and `ask()` recorded favours under
  `if favour.lasts:` — so a zero-day favour fell straight through and the
  price code could never fire in a real game. The check exercised a state the
  game could not produce and read as coverage. Grant through the same call the
  player uses.
- **One helper for the price, and nothing applied at the till.** The office
  rate was applied inside `trade.buy`/`trade.sell`, so the board showed 36/t
  while the counter charged 31.68. `market.quote_buy`/`quote_sell` are the
  price — office rate, grudge bias and all — and `tests/test_counter.py`
  sweeps the two against each other.
- **A posting has to name somewhere the hull can get to.** `_pick_target` was
  documented as choosing a system "reachable in principle" and tested only
  `bloom < 0.4`; reachability is transitive and nothing checked it, so **65%
  of targeted postings named a system outside the reachable component** (15 of
  42 systems fly at the opening drive). Ask `reach.component`, which is the
  same answer the chart gives. `reach.route_to` costs the flight, and the card
  states it.
- **A coverage check pinned to one seed is a check you are getting away with.**
  `test_chronicle`'s "does everything it claims" ran on a fixed seed by
  design, but only **1 seed in 24** ever planted a colony — so it was pinned
  to the one that worked and any change anywhere would break it. The cause was
  a driver bug, not luck: `chronicle._refit_here` still tested "the system has
  a port" after `shipyard.can_refit_here` tightened to "alongside a yard", so
  `apply_refit` returned "you are not alongside a yard" and the driver dropped
  it. Putting in at a yard first took planting to 6 seeds in 48.
- **A vocabulary whitelist is not coverage.** Two suites listed
  `megastructure` in a `KNOWN_EFFECTS` set, which asserts only that nobody
  declares an *unknown* key — never that a declared one is consumed. It read
  like coverage for a flag no line of the game consulted: the ARCA Habitat
  cost 400,000 credits, 2,600 tonnes of ore and 900 days, and its one
  distinguishing property did nothing. `test_grants.py` asks the general
  question instead — *is every declared effect read by something* — and found
  a second dead key (`drydock`) on its first run.
- **A quoted burn's risk is the profile plus three surcharges** — distance,
  the star at either end of the leg, and the heat already in the hull — and
  `path_note` must account for all of them. Two were silent, and the third was
  found only because a check asked the *general* question ("does anything cost
  more than its profile without the screen saying why") rather than testing
  the two known cases. That check verifies each component separately: an
  earlier version asked only whether *some* note existed, and a surviving note
  masked a deleted one.
- **Never `git checkout <path>` to undo a scratch mutation.** Mutation testing
  wants the file back exactly as it was, and `git checkout` restores it from
  the *index* — which silently throws away the uncommitted work the cycle is
  about. It cost this file its whole change once. Read the bytes into memory
  first and write them back in a `finally:`; `tests/` mutation harnesses do.
- **Driving a fight with one repeated order measures nothing.** Combat is
  positional: a hull whose mounts are all on the beam never fires while it
  steers straight at the enemy, so a test that only ever says "salvo" reports
  zero damage and looks like a balance problem. Use `tests/captain_ai.py`,
  which picks the helm order that suits the arcs the ship actually carries.
- **A consort is a `Side`.** `sim/consorts.py` subclasses it, so `_fire`,
  `_apply_to_layers` and the arc checks work on one without changes. What that
  buys is also the constraint: anything that assumes a battle has exactly two
  sides — `_who()` did — has to learn otherwise.
- **Save identity**: `game.ship` must be the same object as its entry in
  `game.fleet`. `load_game()` re-links them after decoding; damage would
  otherwise apply to a copy.
- **Transient fields**: anything on a dataclass marked
  `metadata={"transient": True}` is skipped by the save codec. `Game.ship_stats`
  holds references to the content tables and must never be written to a save.
- **Qt mnemonics**: an `&` in a button label becomes an accelerator underscore.
  Write "and".
- **Never derive anything persistent from `hash()`.** Python randomises string
  hashing per process, so a value derived from it changes on every launch.
  Orbital phases did exactly this, and a saved game reloaded with every planet
  somewhere new. Use `core.rng.hash_seed`.
- **`View._sync_scroll()` is why screens paint correctly on the first frame.**
  Rebuilding a view's column does not tell its `QScrollArea` that the contents
  changed size, and the layout's true minimum is not known until the new
  widgets are polished — so it measures once immediately and once more after
  the event loop settles. Qt recovered on its own by the second turn, which
  made the fault invisible in play and very visible in a screenshot.
- **Adding a hull family** means touching six places: `LAYER_SETS`, `ACCEPTS`,
  `FAMILY_LABEL`/`FAMILY_TINT`/`FAMILY_NOTE`, `BASE_POWER`, `BUILD_NEED`, and
  `NO_REGEN` if it cannot heal — all of them in `data/hull_types.py`. The test
  suite checks every family for all six, and that its layer weights sum to one.
- **Xenotech ids live in `research.unlocked` alongside real technologies.**
  Anything walking that list must tolerate ids that are not in `TECH_BY_ID` —
  `tech.bonuses()` already skips them, and the gate check in `test_sim.py`
  accepts either vocabulary. Alien passive bonuses are folded in separately by
  `Game.recompute()`.
- **Study banked past a prerequisite is kept, not lost.** You can dig up the
  Phase Loom before you understand the Null Seam; `xeno.settle()` runs on the
  clock and incorporates anything whose moment has arrived.
- **A colony's numbers come from `sim/works.py`, not its class.** `yields_of`,
  `upkeep_of`, `effects_of` and `pop_ceiling` combine the class definition with
  whatever the settlement has since built. Read `col.definition.yields`
  directly and you will report what the colony produced the day it was planted.
- **Anything a work grants that needs an action, not just a number, has to be
  triggered where the work completes.** Opening a harbour was read only at
  maturation, so a colony that built one afterwards had the `port` effect and
  no market.
- **A conviction that reacts to an event nothing raises is dead flavour.**
  `data/convictions.py` names events; something in `sim/` or `ui/` has to call
  `loyalty.record()` with that exact string or the belief never fires. A check
  in `test_crew.py` greps the tree and fails on any event that is never raised
  — it caught ten of them on the day the system was written, including every
  belief the xenologist held.
- **Loyalty bands and loyalty mechanics share their edges.** `BANDS` in
  `data/convictions.py` turns on `WALKOUT` and `RESTLESS`, the same constants
  `effective_level()` uses, so the pill on the roster is a statement about what
  the officer will actually do. Move one and move the other.
- **A commission stage is an ordinary contract.** `sim/chains.py` builds one
  through `contracts.shape()`, the same function the board uses, so deadlines,
  cargo, bounties and expeditions all work untouched. What makes it a chain is
  `Contract.chain` and what happens in `chains.on_contract_done()`.
- **`contracts.active()` is board work only.** Commission stages are excluded
  from it and from the `MAX_ACTIVE` cap, because they are not work you chose to
  juggle. Use `contracts.all_open()` when you genuinely mean everything live.
- **`shape()` takes its scale before it writes the title.** A stage that asked
  for half the usual tonnage used to be titled with the full figure and
  complete at the halved one — a posting nobody could plan a hold around.
- **`rumours.circulating()` must stay pure.** It runs every time the port desk
  is drawn. Deciding truth used to plant what the story claimed, which seeded
  bloom and buried relics across the sector merely because somebody looked at a
  noticeboard. Truth is now a dice roll at circulation; `plant()` runs in
  `take()`, when you have actually committed to the lead.
- **Intel levels are derived, never stored.** `intel.level()` reads
  `body.surveyed`, `system.visited` and the bought-chart list, so nothing has
  to be kept in step. Add a way to learn about a system and it belongs in that
  function.
- **Volatiles are never buried below an open cut, and neither is whatever a
  body is advertised as.** `mining._depth_of()` enforces both. Fuel at depth
  two strands a captain with no bore and no reaction mass — the same deadlock
  the mining root's `drink` was added to prevent — and a rock listed as
  ore-bearing that needs a shaft is a survey that lied.
- **Seams are derived from `body.resources`, never stored.** Depth comes from
  `hash_seed` of the body and resource, so every existing save has seams
  without a migration and the same rock always hides the same thing in the same
  place. Never use `hash()` here; see the note above about orbits.
- **`STARVED_FLOOR` is why a new captain is not stuck.** A programme runs at
  that fraction with nothing on the bench; evidence buys the rest. Set it to
  zero and a captain who picks a project on turn one and flies makes no
  progress at all, which reads as a broken game rather than a hungry one.
- **A programme's evidence mix comes from its branch**, in
  `data/inquiry.BRANCH_MIX`, not from each of the sixty-one technologies. A new
  technology needs no work there; a new *branch* does, and `test_research.py`
  fails if one is missing.
- **An evidence kind nothing grants is an empty locker.** The same greping
  check as the convictions: every kind in `EVIDENCE` must appear as a literal
  in a `sim/` or `ui/` call to `inquiry.add`.
- **`Stock.shock` is kept apart from `Stock.supply` on purpose.** The daily
  drift pulls supply toward equilibrium; if a blight were folded into supply
  the drift would quietly erase it, and expiring it could never restore the
  original price. `market.apply_to_markets()` recomputes every row from the
  live shocks wholesale rather than adjusting, so an expired shock lifts
  cleanly and two overlapping ones cannot drift out of step.
- **The register is memory, not observation.** `market.note_prices()` writes
  down what a port pays only while you are standing in it, and
  `market.confidence()` decays what you wrote. Nothing should ever read a
  distant market directly — that is the whole mechanic.
- **A weather condition gated on a biome that does not exist is unreachable.**
  `data/weather.py` gates whiteouts and downpours on biome ids, and those must
  be real ones from `world/planets` — the first draft invented "ice" and
  "ocean" and silently lost two of its seven conditions. `test_ground.py`
  checks every gate against a real galaxy.
- **Anything that stops the party moving must leave something it can do.**
  A katabatic gale refuses movement, so `expedition.shelter()` is always
  available and always costs a day of supply. Without it a pinned party can
  neither progress nor die and the expedition simply stops.
- **`diplomacy.drift()` is what stops the sector ratcheting shut.** Every
  blockade and censure is a debit; with nothing pulling the other way a decade
  of background politics drove every pair far below `CONCORD_RELATION` and left
  an ending unreachable through no fault of the player. Grievances fade toward
  `INITIAL_RELATIONS`. Any new faction behaviour that moves relations needs to
  be weighed against it.
- **Ventures never annex a system you hold a colony in.** `_claimable()`
  excludes them. Losing a settlement to a registry filing would be good drama
  and would also silently break the colony that is still pointing at it.
- **Never size anything against `chassis.mass_t`.** Structural mass runs from a
  sixty-tonne SPORE to a twelve-billion-tonne LEVIATHAN, so any threshold built
  on it is meaningless for most of the range. `sim/loading.py` sizes capacity
  from slot count and hold rating, which are on the same scale as the parts and
  cargo that fill them.
- **Loading affects jump range at 45% strength, deliberately.** A full hold
  costing speed is a trade; a full hold leaving a captain unable to reach the
  nearest system is the stranding deadlock this project has hit twice.
  `test_design.py` checks the laden jump against the nearest neighbour.
- **A new system is not finished until `data/orders.py` can point at it.**
  Fifteen cycles each added something perfectly discoverable to whoever had
  just built it; a new captain saw a chart, one log line, and no sign any of it
  existed. Every entry there needs a predicate of the same id in
  `sim/orders.py`, and `test_orders.py` fails on either half being missing.
- **Anything persistent on `Game` needs a reader.** `test_orders.py` walks the
  dataclass fields and fails on any that nothing loads — it caught a levy
  counter that incremented and changed nothing, and a death reason the game
  recorded and never showed.
- **Never compare combatants by raw hull and raw damage.** Enemy hull is a
  chassis lottery that does not track difficulty at all — `make_enemy` picks
  from a faction pool and scales hull only 10% per difficulty point — while
  armament and armour both track it cleanly. `assessment.weight()` compares
  turns-to-break after armour, and its thresholds are calibrated against 320
  measured fights rather than guessed.
- **Most fights end when somebody's nerve goes, not their hull.** Any model of
  who is winning that ignores resolve reads far bleaker than the game plays,
  which is why the thresholds sit where they do rather than at the obvious 1.0.
- **Build a fresh hull for every fight in a balance measurement.** Reusing one
  ship across a run silently starts every fight after the first with a wreck.
  It reads as "encounters are brutally hard" and sent an entire afternoon's
  tuning the wrong way before the artefact was spotted.
- **Nerve is driven by the fight, not the clock.** `_end_of_turn` once drained
  resolve purely on the turn counter, and the enemy lost it twice as fast as
  the player, so an unarmed hull drove off a battleship three times in four by
  waiting. It now turns on damage taken, being behind on damage, and futility —
  that last term is what keeps endurance a real strategy for a hull built to be
  hit.
- **Every low-tier weapon in the game is grown-family.** A fabricated hull at
  tier one can mount none of them, which is why faction warships used to arrive
  unarmed. `encounters._weapon_pool` raises the tier until something fits.
- **Qt swallows exceptions raised inside a slot.** It prints a traceback to
  stderr and carries on, so `button.click()` returns perfectly happily and a
  test that only clicks sees nothing wrong. This is why fleeing and hailing
  could be broken for a whole cycle while `test_ui.py` rendered every screen
  and passed. `test_verbs.py` installs a `sys.excepthook` to catch them; if
  that trap ever stops working every verb check goes quietly green, so there is
  a check for the trap itself.
- **Rendering a screen does not press its buttons.** `test_ui.py` proves the
  screens draw; `test_verbs.py` proves the verbs run. They are different
  claims and a refactor can break the second without touching the first.
- **`responses.growth_multiplier()` is read in `threat.tick`, and that is the
  only thing making provocation matter.** It was computed and read by nothing
  at all on the first pass — the same shape as the levy counter that
  incremented and changed nothing. If a new Bloom response adds an effect, find
  the place that consumes it before believing it works.
- **Studying a mass and burning it are exclusive on the same mass.** Study
  yields xenolith and readings scaled by how much growth is present and feeds
  it a little; burning removes the thing you would have studied. That conflict
  is the setting's central tension and `STUDY_FLOOR` is what keeps a burnt-out
  system from paying twice.
- **A public function nobody calls is a feature that does not exist.**
  `test_reachable.py` walks the tree and fails on any public module-level
  function called from nowhere at all. Be clear about its limit: it will not
  catch one that is called only from a readout or only by the suite. The
  Bloom's growth multiplier was consumed by `summary()` from the day it was
  written while contributing nothing to the simulation, and this check would
  have passed on it. Reachability is a floor, not a guarantee.
- **`return None` is not a result.** Counting it made the analysis flag every
  early-exit function; the self-check caught that on its first run, which is
  the argument for the self-check existing.
- **A feature is not finished until a lever in `tests/levers.py` proves it
  moves the world.** Reachability only shows a function is called;
  `test_efficacy.py` switches each claimed effect off and demands the same
  seeded scenario come out different. Disconnect the Bloom growth multiplier
  and reachability still reports "every one reachable" while efficacy fails.
- **Levers patch a module attribute, not an imported name.** The codebase calls
  across modules as `module.function(...)`, so the lookup happens at call time
  and every caller sees the substitution. A lever aimed at something imported
  by name would silently do nothing, so the suite checks each substitution
  actually changes its measurement before trusting the comparison.
- **Watch for a probe that saturates or starts already satisfied.** The first
  Bloom lever ran long enough for every system to pin at its 1.0 ceiling, so a
  Bloom growing half again as fast reached exactly the same total; the first
  research lever stocked the bench full in *both* runs. Both read as inert
  features when the features were fine.
- **A crossing charges as it goes, not up front.** `transit.begin()` takes
  nothing; each watch spends its share. That is what makes cutting the burn a
  real decision — you keep what you have not yet spent and lose what you have.
- **The price register holds price quotes and nothing else.** Chart completion
  dates used to be stashed in `game.register` beside them, and
  `market.best_markets` walks every value in it and reads `.sell` — so charting
  anything and then opening a port raised `AttributeError` inside a Qt slot,
  where Qt swallows it and the panel simply fails to draw. Chart dates live in
  `game.charts_made` now, with a migration for old saves. Found by rendering
  the screens for the README, which is a kind of play the suite was not doing.
- **A ground option states its odds, its prize and its risk.** The screen
  listed "(science, difficulty 3)" and nothing else. Resolution is
  `1d6 + officer level >= difficulty + 2`, so that same string is a
  one-in-three with a green officer and five-in-six with a level-three one; the
  reward was unpacked into a discarded variable; and a failure springs a hazard
  40% of the time, unstated. `expedition.odds_for()` gives all four, and the
  ground game is nothing but a sequence of these choices.
- **The seed dialog says what will grow.** It showed each class's cost and
  gestation and never its yield — the one thing that separates them. Measured
  on one rocky body: fourteen classes from 2.6 t of ore a day (RADIX Mine,
  12,000) to 260 credits a day (Free Port, 74,000) to 4.2 research a day
  (Reactivated Array, 96,000), and three that yield nothing and buy effects
  instead. `colony.forecast()` gives yield, upkeep, effects and a rough
  payback, and the card shows them.
- **A colony forecast prices at a flat table, not at a market.** A payback that
  swings with whichever port you are standing in is not something a player can
  compare classes with.
- **A seat says what taking it is worth, not just who is holding it.** The
  orders panel printed each station's officer level and never the consequence.
  Measured from the sim: gunnery is +0.22 to hit with a green officer and +0.10
  with a veteran; an unattended helm repeats its last order at 0.7 + 0.06 a nav
  level of the turn rate; an unattended engineering section sheds a fraction of
  its vent and can do nothing else. `stations.seat_value()` states each, so who
  you have decides where you should be sitting.
- **An overture says what it buys, not only what it costs.** The diplomacy
  screen listed a name, a blurb and a price and never a benefit: tribute at
  12,000 credits for +9 standing read the same as relief at 40 t of biomass
  for +11, which is about six times better per credit. `dip.preview()` is a
  pure function returning what will move — the target, third parties, and the
  relations matrix — and the screen draws it.
- **A treaty's cost with the signatory's enemies is now stated.** It charges
  standing through `allegiance` and said so nowhere: you signed, and two other
  powers thought less of you for a reason the game never mentioned. In a sector
  at war that is six points with each of the other three.
- **Nothing is gated behind a technology that does not exist.** "Build a
  xenology annex" — 100 days, 11,000 credits, +0.5 research a day and +0.04
  diplomacy — was gated on `tech="xenolinguistics"`, which is in neither the
  research tree nor the xenotechnologies. It was buildable by 0 of 19 colony
  classes with everything in the game unlocked. One entry in the whole content
  set was wrong; `test_works.py` now checks all 131 gated entries across works,
  colonies, parts and chassis, plus every tech prerequisite.
- **A test fixture was part of why it hid.** `test_verbs` appended the phantom
  id to `research.unlocked`, so the sweep that clicks every control saw a work
  no real chronicle could reach. A fixture that invents content is a fixture
  that stops the suite noticing content is missing.
- **What the bench says a programme will eat is what it eats.** `needs()` is
  documented as the end-to-end total and the screen prints it as "26 wanted";
  `draw()` then spent `total / 60` a day while a careful programme runs about
  128 days, so the bench ate 2.1x the advertised figure on every track. The
  sixty was a duration nobody had checked. The draw is paced over
  `span_of()` — the programme's real expected length at the current rate — so
  the two agree.
- **A quote is priced for the approach in hand.** Running parallel tracks costs
  "three benches' worth of material" by its own blurb, and the readout quoted
  the careful number. `needs()` takes the `Research` and applies the approach's
  draw, so the shelves are read against what this programme will actually take.
- **The four burn profiles are a decision because a hard burn arrives hot.**
  Measured: a system flown end to end took 55 days coasting and 10 on hard
  burns, and the hard burn cost about three hundred credits of reaction mass
  and 1.2% of a hull that heals itself. Nobody would ever have coasted — and
  its own blurb promised the radiators would complain. A burn now leaves heat
  in the hull (62% of cap on a hard burn), a hot hull is riskier to burn again
  in, and over the cap the radiators stop keeping up and the hull cooks. One
  hard burn from cold is free; a habit of them costs 11% of the hull.
- **Heat is no longer a one-way ratchet.** Nothing outside combat added it and
  nothing shed it, so a ship sat at thirty for twelve hundred days with vents
  rated at twenty-four a turn. `ship.cool()` runs on the clock. `REST_VENT` is
  not a physical ratio — it is the rate that makes heat a state you fly in
  rather than one that has gone by the time you arrive.
- **A rig stops when the hold is full.** `extract()` used to compute the whole
  spell's haul, take `min(raised, cargo_free)` and deplete the body for the
  full duration anyway. Measured: sixty days with an empty hold took 106.2 t
  and worked the body out by 0.384; with the hold 97% full it took 10.2 t and
  worked it out by the *identical* 0.384. Ninety-six tonnes raised and thrown
  away, a third of the body spent, and nothing said so. The working now ends
  when there is nowhere to put what it raises, and time and depletion both
  follow what was actually lifted.
- **A full hold must not be a stranding.** Refusing to work a body with
  nowhere to put the ore is right, and on its own it deadlocks: no room to mine
  ice for reaction mass, no mass to jump on, and the only way to dump anything
  was the contraband panel, which appears solely when carrying contraband at a
  hostile port. `trade.jettison()` is general now and the hold has a vent
  control. The project already holds that an empty tank must not be a deadlock;
  this is the same rule from the other side.
- **Everything that can refuse a working is checked before the ship flies out
  to it.** `flight.ensure_at()` came first, so a refusal cost twelve days of
  flying and gave nothing back. The regression check caught that, not me.
- **The panel forecasts the spell.** It quoted tonnes a day and offered "Work
  it — 30 days" with no notion of what that came to; now it says "25 t in 14
  days — the hold fills first".
- **The freight desk is an information tool with a floor under it.** Within a
  starting jump only 5% of lane/goods pairs show a positive spread, and the
  runs that do exist are invisible — finding one means visiting every
  neighbour first. The desk draws on two honest sources: your own register
  (real prices, going stale) and the harbourmaster, who names his own power's
  ports and what they are short of but will not quote their board.
- **A spread thinner than the drift is not a trade.** `tick_market` moves
  supply about 1.8% a day plus a random walk, so a thin margin is gone by the
  time the hull arrives. Flown and banded by spread, every band below a fifth
  loses money on average, so `MIN_SPREAD` is 0.20 and the desk will not
  recommend anything under it. Measured over two-year careers: 981 credits on
  your own notes, 33,069 following the desk.
- **What a run clears is the voyage, not the spread.** Ranking by margin per
  tonne is how a captain flies a four-credit spread nine light-years and pays
  for the reaction mass themselves.
- **Short-range legal arbitrage is thin by design and that is fine.** Ports of
  one power want the same things, so trading means crossing into somebody
  else's space. The contract board is the early game — every one of twelve
  openings has affordable work — and the desk comes into its own with range and
  a register.
- **A cargo contract is priced against what its cargo costs.** The reward was
  `amount * (base * 0.55 + rate * 0.4)`, and `base * 0.55` is the *floor* — what
  a market holding none of a good pays for it. Nobody sells at the floor, so the
  board priced its own work against a number that does not exist: 44% of cargo
  contracts paid less than sourcing their cargo, worst case fifty thousand
  credits down. `cargo_cost()` prices it properly and the board shows the
  arithmetic, because a fee on its own made a trap look like a living.
- **Distance pays haulage on cargo, not a share of the goods.** The old
  multiplicative premium turned an eighty-tonne silicon run into 130,000 clear.
  Freight is priced by mass and distance — a tonne is a tonne in the hold.
- **A quote prices for the captain reading it; generation prices neutrally.** A
  contract's fee cannot depend on the standing of whoever happens to see the
  board, but what *you* will be charged does. Getting that backwards made the
  quote wrong by two per cent, which the check caught.
- **A field note is kept, not printed once.** Recovered lore lived in
  `expedition.lore`, was shown in the report dialog, and went out with the
  expedition object — never on the `Game`, never in the codex, and worth
  nothing, since `REWARD_SCALE["lore"]` was (0, 0). Three feature options
  existed to display a sentence and take it away. Notes now have identity
  (`data/fieldnotes.py`), are filed with the body, system and day they came
  from, and are evidence on an inquiry track, so going down and reading the
  room is worth doing.
- **A note is not cargo.** Stranding costs 60% of the haul; it does not cost
  what somebody already read and remembered. `test_notes.py` pins that.
- **No screen writes the ledger.** Seventeen sites across four view modules
  spent credits and moved standing directly — buying, selling, hiring, paying a
  bonus, repairing, buying a lead, commissioning bench time, scrapping a hull,
  tying up at a quay, and moving contraband off the books. Every one was a rule
  only a mouse could perform. They live in `sim/trade.py`, `sim/services.py`,
  `sim/crew.py`, `sim/shipyard.py`, `sim/customs.py` and `sim/minigames.py` now.
- **`test_layers.py` enforces the one-directional rule instead of stating it.**
  It matches ledger writes structurally — assignment to `.credits`, augmented
  assignment, `game.rep[…] = …`, any call to `adjust_rep` — and carries a
  self-check that plants all three shapes and fails if the matcher misses any,
  because a structural matcher that silently matches nothing would have passed
  on the day the defect was at its worst.
- **What a fight leaves behind belongs to the rules, not the screen.** Salvage,
  loot, cargo off the wreck, bounty progress, seized xenology, instar kills,
  consorts lost, loyalty and every standing change used to live in
  `ui/battle_view.py._finish()`; `sim/combat.py` held a loot dict and nothing
  else. Nothing headless could resolve an engagement, so every balance run that
  fought a battle collected no loot, no standing and no bounty credit. It is
  `sim/aftermath.resolve()` now, and the view reads what it returns.
- **`Battle.settled` makes the payout idempotent.** Both the screen and a
  headless driver can reach the end of a fight; neither may collect the salvage
  twice.
- **A kill is noted by everyone who dislikes the victim.** Destroying a hull
  moved its owner and nobody else, in a sector whose whole politics is a
  relations matrix. It now pays the owner's rivals a share scaled by the same
  severity ramp `sim/allegiance.py` uses, so a cordial sector gloats not at all
  and one at war gloats loudly. A Bloom kill pleases all four powers rather
  than the Charter alone, which is what it did — hardcoded, in a screen.
- **A chart is priced on what it says, not on how many bodies it has.**
  `survey_value()` was `460 + 210 * len(bodies)`, so a system with a buried
  Abyssal site and ore worth crossing the sector for fetched what five bare
  rocks fetched. Measured: charting the home system took 53 days and paid
  1,510 — 28 credits a day, against roughly 1,600 for smuggling. The whole
  42-system sector came to 55,014, about one contraband run.
- **The price list is scaled against the rest of the economy, not chosen.** The
  best contract in the game pays about 27,000 and the dearest hull 900,000. A
  first pass put a remarkable system's chart at 92,000 — over three times the
  best contract — which fixed exploration being worthless by making it the
  best-paying thing in the sector. The numbers in `data/charts.py` land a
  median chart near 26,000 and charting near 750 credits a day.
- **Who buys is a decision, because the powers want different things.** The Dry
  Choir pays over the odds for life and anomalies, the Yards for ore and sites,
  the Charter for anything alive or old or growing. Best and worst buyer differ
  by 1.6x on average and the best buyer varies by system, so a chart is
  something you carry to the right quay.
- **Charts go stale.** A survey is dated when it is finished and decays to 45%
  over two years, which makes a survey circuit a living rather than a one-off
  sweep of the sector.
- **Claims and holdings have to be able to collide.** `ventures._claimable()`
  used to exclude any system the player held a colony in, and `can_found()`
  never looked at `system.faction` — so the powers declined to contest your
  ground and you could squat on theirs, and territory was never once disputed.
  Both directions are live now, through `sim/territory.py`.
- **A demand is something you are in the middle of**, so `Demand` is a field on
  the `Game` with an `.over` flag and `window.go()` diverts to it. `test_resume`
  picked it up as the sixth guarded activity with no prompting — which is the
  whole point of writing that check as a rule rather than a list.
- **Every answer to a demand costs something different.** Paying the levy keeps
  the holding and gives up 30% of what it makes; ceding loses it and reads
  best with them; refusing keeps it, costs standing, and means somebody comes
  for it — measured at 12 of 12 defiant holdings seized within eight years. A
  claim that lapses cancels the standoff rather than leaving it hanging.
- **Work for a power is a position, not an errand.** Completing a contract
  charges you standing with everyone that power is at odds with, scaled by how
  bad the rift is (`sim/allegiance.py`). `contracts.py` did not import
  `diplomacy` at all, so you could be the Charter's courier, the Concordat's
  bounty hunter and the Freeholds' prospector in the same week while all three
  were at war, and every one of them thought better of you for it.
- **The penalty is not the point; the escape is.** Severity ramps from zero at
  −15 to full at −70, so brokering a rift *part* of the way down is worth doing.
  Measured: the same 28 jobs return 108 total standing in a hostile sector and
  170 in a brokered one. That is what finally gives the relations matrix a job
  in ordinary play rather than only at the Concord ending.
- **Contraband needs both halves or it is not a trade.** A good that is
  outlawed somewhere has no posted price there and therefore a much better
  unposted one (`customs.premium`), and the same power opens your hold at the
  dock (`customs.inspect`). Shipping only the search would be a tax nobody
  would choose to pay; shipping only the premium is what the game already had,
  and measurement said it beat honest trade outright.
- **Scrutiny is the brake.** Selling into a black market and being cleared both
  raise a per-faction heat that thins what they will pay, thickens the search,
  and decays on the clock. Without it one dock is an unlimited money printer.
  `COOLING` was tuned by playing careers, not chosen: at the first value a run
  put on more heat than a month shed, so every career ended down.
- **Mitigations multiply, they do not subtract.** Standing, a clean approach and
  a concealed hold each take a share off the odds. Subtracting them let a
  fitted-out hull with good standing drive the risk under the floor and stop
  being a smuggler at all.
- **A part that is kit for a trade is marked `civilian`** and NPC loadouts skip
  it. Adding two smuggling parts put them straight into the enemy outfit pool
  and broke the combat-assessment check — a feature about trade silently
  re-tuning every encounter in the game.
- **A dig banks per layer, not at the end.** `dig.work()` credits understanding
  as each stratum comes out, so a trench abandoned after the casing is worth the
  casing. That is the whole reason backfilling is a choice rather than a way of
  throwing the dig away, and it is what `test_dig.py` pins: restoring
  bank-at-the-end passes every other dig check and fails that one alone.
- **Anything you can be in the middle of belongs on the `Game`.** The window
  exposes `transit`, `docking`, `decoding`, `dig` and `decoding_tech` as properties
  over game fields; holding them on the window loses them over a save, which
  docking and decoding did unnoticed for many cycles. `test_resume.py` reads
  the guard in `window.go()`, takes every activity with an `.over` flag, and
  fails on any that is not a field on the `Game`.
- **A `Battle` stays on the window on purpose**, recorded in `battle_state` and
  in `TRANSIENT` in `test_resume.py`: combat resolves in one sitting and no
  clock runs during it. Anything else added to that allowlist needs its reason
  written down beside it.
- **Colony effects are a closed vocabulary.** `test_sim.py` asserts that every
  key in a `ColonyClass.effects` is one the game actually reads, so a typo in a
  station definition fails the suite instead of silently doing nothing.

## Tests

`python -m seedfall.tests` — no dependencies beyond PyQt6 itself.

- **`test_sim.py`** drives the rules headlessly: sector generation and
  determinism, every chassis and part, tech-tree reachability, trade, colonies,
  building, combat outcome distributions, Bloom pacing, save round-trip.
- **`test_combat.py`** covers arcs and crew stations, and holds the consorts to
  the bargain their orders describe: screening must measurably pull fire off
  the flag, and flankers must shoot markedly more than screens do.
- **`test_empire.py`** plants a colony, matures it and develops it: that a
  finished work changes production, that its effects reach ward, build sites
  and sensors, that material is charged up front, and that works survive a
  save.
- **`test_crew.py`** checks that the same act pulls a bridge apart rather than
  together, that loyalty is felt at the crew stations and not only on a roster,
  and that a year of missed payroll actually costs you officers.
- **`test_missions.py`** runs a commission to its end, and checks the three
  things that make one different from a posting: that stages escalate, that
  taking one is refused at its rival's own port, and that a missed deadline
  withdraws it permanently.
- **`test_explore.py`** climbs the intel ladder rung by rung, checks a chart
  cannot be bought twice or a survey sold twice, and — the important one —
  proves that thirty passes over the rumour desk leave the galaxy byte for byte
  unchanged.
- **`test_mining.py`** measures the four methods against each other over
  twenty runs apiece and asserts they are actually different bargains — a bore
  must out-yield an open cut by a third and cost more hull and more of the body
  doing it — then works a body out and checks it stops paying.
- **`test_research.py`** measures a captain who surveys against one who does
  not — the second must reach the first technology in well under three quarters
  the time, or the evidence model is decoration — and checks that a captain who
  picks a project on turn one and does nothing else still gets there.
- **`test_trade.py`** puts a shock on a market, checks the price moves, then
  expires it and checks the price comes back — the failure mode being a sector
  that accumulates permanent distortions over a long game. It also formats
  every shock's text to catch an unfilled field, which would otherwise crash a
  port screen months into somebody's game.
- **`test_ground.py`** pins a party under a gale and shelters until the
  expedition ends, which is the check that a stuck state cannot exist. It also
  measures tiles crossed with and without weather, so a condition that costs
  nothing fails.
- **`test_politics.py`** checks that a determined broker can still reach the
  Concord against twenty-five years of background churn, and — because the
  emergent numbers plateau against the -100 floor either way and make a weak
  signal — tests the fading mechanism directly by pushing a relation down and
  watching it come back.
- **`test_design.py`** builds every chassis at a sensible fit and fails if any
  is penalised for it, then maxes one out and fails if it is not. It also
  checks that a fully laden starting hull can still reach its nearest
  neighbour.
- **`test_orders.py`** builds ten game states and demands every standing order
  fire in at least one of them, calls every predicate unguarded so a broken one
  cannot hide behind the panel's exception guard, and checks that acting on an
  order makes it go quiet.
- **`test_assessment.py`** plays out forty fights across two hulls and four
  difficulties and fails if a worse-sounding verdict wins more often than a
  better-sounding one — the read is worth nothing if it is not honest. It fails
  against the raw-hull comparison the first draft used.
- **`test_balance.py`** plays out every assertion it makes. It checks no
  faction fields an unarmed warship, that heavier threats arrive in heavier
  hulls, that the win rate falls with difficulty and rises with a better ship,
  that waiting is not a way to beat a battleship, and that fleeing and hailing
  both actually run — the last because splitting them into `parley.py` left
  them calling names that no longer existed and nothing drove either path.
- **`test_verbs.py`** clicks every enabled control in the game — 210 of them
  across the standing screens, an engagement, an expedition, all four port
  tabs and both mini-games — each on a fresh game, and again with a wrecked
  hull that has no money, no crew and no air. It fails against last cycle's
  parley regression, which is what it was written for.
- **`test_bloom_arc.py`** provokes the Bloom until every response has fired,
  checks they fire in order and never twice, and — the one that matters —
  measures actual spread with and without them, because a multiplier nothing
  reads looks exactly like one that works.
- **`test_reachable.py`** found the three things this cycle fixed: treaties
  that bought no trade advantage, instars that could not be killed, and
  officers whose convictions never felt your standing move. It carries a
  self-check, because an analysis that cannot fail is worse than none.
- **`test_efficacy.py`** carries two checks on itself: that a deliberately
  decorative feature fails, and that every lever's substitution bites. A
  harness that cannot fail is worse than none.
- **`test_transit.py`** flies the same crossings under a hurried policy and a
  careful one and fails unless hurrying genuinely saves days and genuinely
  costs hull. An option that is best on every axis is not a decision.
- **`test_notes.py`** drives a party into a wreck, works it for notes, brings
  them home, and fails unless the shelf, the provenance and the evidence all
  survive — including across a save. It also checks every note is reachable and
  that the draw prefers ones you lack, so no written discovery is unfindable.
- **`test_attempts.py`** rolls each option six hundred times and fails unless
  the empirical success rate matches the quoted chance — the resolution lives
  in `attempt` and the quote in `odds_for`, and the point is that they cannot
  drift. Dropping the `+2` from the quote makes it report "said 67% rolled
  32%".
- **`test_tutorial.py`** exists because the failure mode of a tutorial is
  silent: a step that advances when Next is pressed teaches nobody anything and
  will march a confused player through eight screens of congratulation. Every
  lesson names a watcher, every watcher is a function of game state compared
  against a mark taken when the lesson opened, and the checks walk the whole
  thing by *doing* each action — then separately prove that three hundred days
  of doing nothing leaves it on lesson one. Replacing the watcher with "trust
  the player" fails three of them.
- **`test_manual.py`** enforces two things that screens usually escape. A
  manual that says "thirty-five hulls" is wrong the day somebody adds one and
  nothing would notice, so every countable claim is generated from the table it
  describes and a check fails if a topic names a fact nothing can resolve. And
  an option that changes nothing is a lie: every setting the screen offers must
  appear somewhere in the package outside `options.py`, so a setting that stops
  being read fails here rather than sitting on screen doing nothing. It also
  found the key collision below.
- **`test_bridge.py`** drives the whole protocol in-process, because verbs are
  plain functions over a `Game` and a socket is a detail. One check does open a
  real loopback connection, because the thing that broke only breaks over one:
  `survey` returns a `Lifeform` among its results, the reply was merged into
  the envelope, and `json.dumps` raised *inside the connection thread* — the
  socket died silently and the caller was left reading an empty line. A
  boundary has to be total; a caller on a pipe can catch neither a traceback
  nor a hang-up.
- **`test_gunnery.py`** exists because combat had one outcome. `_fire` floors
  damage at `max(dmg * 0.15, dmg - armour)` so that something always gets
  through, and `_apply_to_layers` then discarded anything at or below half a
  point — which swallowed the floor whole for the only weapon a new captain
  owns. Measured: 360 engagements, 100% driven-off, both hulls at 100%. The
  read panel had been reporting the correct 0.45 a turn the whole time, which
  is how one rule with two implementations hides.
- **`test_reach.py`'s "a pocket is a long project and not a trap"** is the
  check carrying a design decision. Generation was *not* changed to close the
  gaps, because playing a two-system pocket showed evidence still accumulates,
  both its markets sell magnetite, and it earned 71,000 of the 78,000 credits
  in under seven years. The wall is a gate, not a lock — so the fix was making
  the gate legible rather than removing it. If a future change makes a pocket
  genuinely unsupplyable, that check fails and the decision gets revisited.
- **`test_grudges.py`** holds memory to *changing behaviour* rather than
  colouring speech: a quay prices you by what it remembers, a power that holds
  enough against you stops posting work, and feeling travels between powers
  close on the relations matrix. The rule underneath is that `because()` must
  name the memories responsible for whatever `feeling()` returns — nothing in
  this game may dislike you for a reason it cannot state. Making the price bias
  and the cold shoulder inert fails two checks here and one efficacy lever.
- **`test_voices.py`** exists to prove the language model is optional in the
  way it claims to be. `llm.complete` is replaced with something that raises,
  so a check that reaches for a model fails loudly, and what is measured is the
  written fallback: eight personas across seven moods, all distinct, none
  leaking a frame slot. The suite stays hermetic and the game stays whole with
  nothing installed.
- **`test_legacy.py`** covers the ten endings and the epoch each one opens.
  Its sharpest check performs all 120 answers across the forty situations and
  compares each against the effect its card printed — the card and
  `legacy.apply` read the same dict, and this is what keeps them one dict. It
  caught the Cartel ending being unreachable by construction: the threshold
  asked for prices from 25 systems and a sector has only 17 to 24 markets.
- **`test_beginnings.py`** pins the invariant the whole suite rests on: a
  `new_game()` with no choices must be *exactly* the game as it shipped, because
  three hundred and eighty checks are written against that opening and a default
  that quietly differed would leave all of them passing while measuring a
  different game. It also found a live soft-lock — see below.
- **`test_plans.py`** holds the ship model to being built out of the actual
  ship, and holds the renderer to the one thing a software rasteriser gets
  wrong silently. A face wound the wrong way is culled when it should be drawn,
  and the symptom is not a crash or a blank screen: the ship renders as a
  handsome x-ray of its own far wall with the cargo floating in front of the
  hull, and roughly half the faces cull either way so the count says nothing.
  Two checks cover it — one on the normals of every primitive, one that puts a
  box inside a sphere and insists the sphere occludes it.
- **`test_courting.py`** holds diplomacy to being a choice. Measured before
  anything was touched, a captain with money sat at 92/100/100/100 with all
  four powers *while two of them were at −67 with each other*: the three gift
  overtures added standing with their target and cost nothing anywhere else,
  so the relations matrix was scenery and `broker` — the one action that moves
  it — bought nothing you could not get by ignoring it. Gifts run through
  `sim/allegiance.py` now, which contracts, treaties and territory already
  used. Measured after: courting one side of an implacable feud reaches 100
  and −100; courting both reaches 69 and 63, neither at Kin. Brokering the
  rift first drops what courting costs elsewhere from 7.8 to 1.0, which is the
  purpose `broker` never had.

  Playing it then found the trap it created. Below −60 standing every overture
  was refused and the only move left was `denounce`, which makes it worse — a
  captain at −100 with unlimited credits courted a power for 120 sessions and
  moved them **not one point**. `tribute` reaches to −100 now, so there is
  always a door and it is the expensive, undignified one: 555 days of steady
  tribute to climb back from the floor.

- **`test_picture.py`** holds the picture of the ship to showing the ship. A
  hull at 25% used to render pixel-for-pixel identically to one fresh out of
  the yard: every reading of the damage was a percentage in a side panel,
  while the model — the one thing always on the screen — said nothing. Damage
  is drawn now as blight spreading over the hull, following the *outermost*
  layer, because that is the one damage lands on first and the one you could
  actually see. The checks measure it end to end rather than by field: two
  renders that differ by pixel count, the same ship twice that does not, and
  neighbour agreement to hold the blight to contiguous patches — the first
  version asked whether a marked face had a marked neighbour, which with half
  the hull marked is true by chance, and scored per-face static at 99%.
  `speckle()` scatters from a stable hash rather than `game.rng()`, because
  drawing happens many times a second and must never advance the save; one
  check exists solely to keep it that way.

- **`test_reach.py`** walks the reachable component with `jump_quote` rather
  than re-deriving it, so the chart and the Set course button cannot drift, and
  fits each drive the chart offers before believing what it claims to open.
- **`test_chronicle.py`** is the one suite that does not build a fresh, narrow
  game. `chronicle.py` flies a single captain for ten years — surveying whole
  systems, refitting, hiring, trading off the freight desk, mining, digging,
  landing parties, planting colonies, running works and moving the relations
  matrix — and the suite repaints every screen and every tab against that save
  as it accumulates, with `sys.excepthook` armed because Qt swallows what a
  slot raises. It exists because the README screenshots found a shipped crash
  in minutes that forty-three suites had missed: the crash needed a *charted*
  sector and a *port screen* in the same save, and nothing put accumulated
  state in front of the screens that read it. The driver carries its own
  history in comments — each measured failure that made it cover less than it
  claimed — and the third check fails if any of those counters reads zero
  again. Tabs are read off the live `TabBar` rather than a hardcoded list, and
  clicked rather than assigned, so a tab added tomorrow is covered tomorrow and
  the refresh runs where the exception would really be swallowed.
- **`test_founding.py`** plants all fourteen classes a body will take, matures
  each, and fails unless the yield, upkeep, effects and gestation are what the
  dialog forecast. Its fixture stocks every commodity rather than a guessed
  list — the first version missed spidroin and died on a class it was not
  testing.
- **`test_seats.py`** drives the claims through `run_helm` and
  `run_engineering` rather than re-deriving their formulas, so changing one and
  not the quoted figure is caught. Its fixture creates a tactical officer
  before setting one's level: the opening crew is a scientist, a navigator and
  an engineer, so promoting "the tactical officer" silently did nothing and the
  check compared a green bridge with itself.
- **`test_overtures.py`** performs every overture and fails unless the standing
  and the matrix move exactly as previewed, and unless previewing moves nothing
  at all. Hiding the treaty's rivals again makes it report "said {charter:
  14}, did {charter: 14, concordat: -1, freeholds: -2.2}".
- **`test_works.py`** builds every work on every colony class that will take
  it and fails unless each changes what its table says it changes, unless every
  work is buildable by somebody, and unless every gate names a real technology.
- **`test_bench.py`** runs programmes to completion on every approach and
  fails unless what was quoted is what came off the shelves. Restoring the
  hardcoded sixty makes it report "the bench takes 2.06x what it advertises".
- **`test_burns.py`** flies a whole system on each profile and fails unless
  burning hard is both faster and materially worse for the hull, and unless a
  single burn from cold costs nothing. It also pins what the helm quotes
  against what the hull actually arrives at.
- **`test_workings.py`** works the same body with an empty hold and a full one
  and fails unless the second costs proportionally less ground. Its
  proportionality check measures the room to leave from the haul the spell
  would actually raise: the first version picked a fill fraction blind and
  passed on a seed where no capping happened at all, which is the vacuous-check
  failure this project has shipped before.
- **`test_freight.py`** flies eight two-year careers with the desk and eight
  without, and fails unless the desk wins and unless the desk-following career
  is profitable at all. It also pins the threshold that made the desk honest
  and the one that nearly made it useless: `COLD` was -8, the floor of Neutral,
  and the Dry Choir *starts* at -10, so a new captain on a Dry Choir quay was
  locked out on day one.
- **`test_cargo.py`** buys the cargo, flies the delivery and banks the fee,
  and fails unless what the board quoted is what the treasury did. Its haulage
  check measures *net*, not a ratio to cargo value: the first version asserted
  reward/cost < 4 and failed at 11.7x on ore hauled a long way, which is not a
  fault — freight is priced by mass and distance, so the ratio to a cheap
  good's value says nothing.
- **`test_layers.py`** holds both halves of the layer rule: that no module
  under `sim/`, `data/`, `world/` or `core/` imports Qt, and that no module
  under `ui/` writes the ledger. Neither breach the project actually suffered
  was an import going the wrong way — both were rules written upward, which is
  why the Qt check alone was never enough.
- **`test_aftermath.py`** plays
  the same engagement twice — once through `sim/aftermath.resolve()` and once
  through the view's `_finish()` — and fails unless credits, standing and
  research come out identical, so the extraction has to stay faithful and not
  merely tidy. Paying a 250-credit bonus from the screen fails it by name.
- **`test_charts.py`** pins the number that made the cycle worth doing: it
  measures charting in credits per day across six sectors and fails both if it
  drops back toward the 28 it was and if it climbs past 1,500, which would make
  surveying the best-paying thing in the game rather than a living. Restoring
  the flat rate fails four of its eight checks, the last one reporting "35
  credits a day".
- **`test_territory.py`** fails unless the powers will actually annex ground
  you hold, unless all three answers diverge, and unless a levy takes the share
  it says it does. Its helper asserts the holding is still *in* `game.colonies`
  and not merely `online`: a colony can mature and be overgrown inside the same
  `advance_days` call, which handed the first version of these checks a holding
  that had already been eaten.
- **`test_allegiance.py`** holds the order of play in place: serving one power
  exclusively must make you its partisan and nobody else's friend, and a broker
  who makes peace first must still be able to work all four to Kin. It also
  pins the card to the ledger — what the board quotes a job will cost and what
  standing actually moves have to be the same number.
- **`test_customs.py`** flies whole smuggling careers and fails unless the run
  pays, unless committing to it (a concealed hold, standing, a clean approach)
  pays markedly better than a bare hull, and unless hammering one dock stops
  paying. It also pins the shape of the risk: every mitigation stacked must
  still leave you catchable.
- **`test_dig.py`** works sites to the bottom under all three methods and fails
  unless the choice is genuine: care must yield most in total, cutting must be
  fastest and cost hull, and working briskly must beat care *per day* — an
  option nobody would ever pick is not an option. It also names the floor it
  found: `test_reachable.py` matches bare names, so `dig.summary` — written this
  cycle and called by nothing — was masked by other modules' `summary`.
- **`test_resume.py`** saves mid-approach, mid-exchange and mid-crossing and
  demands all three come back identical — including the decoding secret, since
  a code regenerated on load would let a player save, guess, reload and guess
  again.
- **`test_flight.py`** holds the helm to its promises: that a seed grows one
  fixed set of orbits *in every process*, that a transfer aims where a body
  will be rather than where it is, that the intercept solve converges, and that
  no course is plotted through a star.
- **`test_ui.py`** builds the real `MainWindow` on Qt's `offscreen` platform and
  paints every screen and every tab, including a live engagement. It stubs
  `win.dialog` because `QDialog.exec()` would block. One check builds its own
  window: grabbing a widget forces a layout pass, so a check for first-frame
  layout cannot reuse one every earlier check has already painted.
