# Session log, part 07 of 31

Archived from the root `SESSION_LOG.md`. Dated entries here span 2026-07-31 to 2026-07-31; undated entries keep their original place.

## 2026-07-31 — SEEDFALL: eighty-four fittings, and #80 closes

The last page in the catalogue that was words only: the shipyard listed every
part as a name, a tonnage and a sentence. `data/parts3d.py` draws all
eighty-four, and the interesting thing about this one is the **claim**, which is
deliberately narrower than for a hull or an organism.

A fitting is a component. At a glance a captain needs to know what kind of thing
it is, whose yard built it, and roughly how much hull it will eat — not *which*
of the eighteen defensive plates this is. Eighteen plates cannot be eighteen
pictures, and asserting they were would be the same lie as five silhouettes
across thirty-five hull classes, pointing the other way: a distinction drawn
where none exists.

So: the slot is the silhouette, the yard is the colour, the tonnage is the bulk,
and three marks carry what it does — a `wpn` gets a barrel, an `ability` an
emitter, a `civilian` fitting a housing instead of a hardpoint. Measured: seven
slots with a worst pair of compute against utility at 68%; five yards each
sharing under half its palette with any other on the same can; a 10 t Bioelectric
Net covering 1,607 px against a 210 t Foldrunner Coil at 5,428; and 18 armed
fittings carrying a barrel with nothing else doing so, checked against the field
on every one of the eighty-four.

**All five passed first time** — the first time that has happened this session,
and the reason is that the claim was honest before the code was written.

The reachability guard sharpened three commits ago caught new code within
minutes: `parts3d.mesh_for`, written by analogy with `works3d.mesh_for` and
`robots3d.mesh_for` and called by nothing, since `thumb3d` uses `build(...).mesh`
directly. Deleted rather than given an invented caller. Fourth orphan this
session.

**#80 is closed.** Every catalogue page in the game now carries pictures: 35
hull classes, 19 stations, 20 machines, 16 xenoform body plans, 84 fittings, 7
worlds, 9 stars, 5 errands of traffic and 4 berths.

Full suite green: **1,151 checks**.

## 2026-07-31 — SEEDFALL: sixteen body plans and eight biochemistries (#80)

The Life tab was the last catalogue page in the game with no picture on it, and
it is the most interesting of the four because **there is no bestiary to
illustrate.** `world/planets._make_lifeform` assembles an organism from a body
plan, a metabolism and up to two traits, so a picture has to be assembled the
same way. `data/life3d.py` is that, off the record itself — `Lifeform.name`
*is* the body plan, because the generator passes `rng.pick(FORMS)` straight
into it, so nothing had to be stored twice or parsed back out of prose.

Sixteen plans over five silhouettes — mats spread, bells drift with tentacles,
tubes anchor, fronds stand, bodies segment and grow limbs. Eight biochemistries
as eight liveries, each measured to share under half its palette with any
other: chemo in rock, thermo in vent-red, halo in brine-white, radio in gold,
crypto in glassy teal, piezo in abyssal blue. Five traits you can see, and five
you cannot.

**Two defects, and both the same one.** A magnetotactic organism's aligned
magnetite chains changed **zero pixels** — drawn inside the body, where a dome
is wider than they were, so the one thing that trait means was invisible. And
once that was fixed, every trait on a long low animal came out between three
and sixteen pixels, because the marks were scaled by `height` and an armoured
grazer is 0.30 tall: three pixels of glass on a silaffin lattice. A mark is
sized to the creature now, whichever axis its largest dimension lies along.
Faintest anywhere is 40 px.

The declared-field guard caught the tail of it: `Shape.livery` was the
metabolism echoed back and is gone, and `Shape.marks` earned its keep by
becoming the honest line on the panel — "silaffin lattice, ice-binding —
drawn" against "damage-suppressed — real, and nothing a portrait can show."
You cannot see a repaired chromosome from a lander, and a page implying the
portrait is the whole organism would be lying in the small way this project
keeps finding.

One from looking at the rendered screen: a portrait stacked down a panel takes
the whole width if allowed to, so each was a 620-pixel black band with an
80-pixel animal in the middle of it.

Full suite green: **1,146 checks**.

## 2026-07-31 — SEEDFALL: a call resolves to the module it came from (#26)

The reachability guard matched **bare names**: `defined` held `module.func` and
`called` held bare `func`, so a `mining.summary` nobody calls was masked by any
other module's `summary` being called. Its own docstring guessed that hid "one
orphan, not a class of them". It hid **thirteen**.

Getting the resolution right took four rounds, each a path a naive version gets
wrong, and each one measured before it was fixed:

- **A call where the function lives.** `BERTHS = {"quay": quay(), ...}` inside
  `berths3d.py` is a use. Missing it alone reported **220** false orphans.
- **An aliased import.** `from .life_panel import build as life_catalogue`
  means a call to `life_catalogue()` is `life_panel.build`, not
  `life_panel.life_catalogue` — the obvious version credits the alias.
- **A re-export.** `chassis_data.accepts_family` is
  `hull_types.accepts_family`, reached through a module that imported it.
- **A reference that is not a call.** A callback or a dispatch-table entry is
  consumed without ever being written `f()`.

And a decorated function is consumed by whatever registers it: `@verb` builds
the bridge's vocabulary in `protocol.VERBS`, `@register` the save codec. Nobody
decorates a function for nothing. Anything still unplaceable — a call on a
parameter like `ops.enemy_turn`, a `getattr`, a string key — stays in a loose
bucket crediting every module, so the check under-reports rather than crying
wolf. 1,267 of 1,278 now resolve exactly.

**Two of the thirteen were harm, not dead weight.** `conn.impact_damage` was a
thin wrapper around `outcome.impact_damage` that nothing called — a *second
door* onto collision damage, after `sim/impulse.collide` became the one door
and made a collision two-sided. Deleting it exposed that
`outcome.impact_damage` was itself dead, superseded by that model. Both gone,
and the impact figures are unchanged: 8 m/s → 24, 20 → 150, 45 → 759.

The other eleven are readouts with no reader — six `summary()` aggregators
written "for the panel" that no panel opens, plus `sky.note`,
`berthing.preview`, `bays.line`, `contracts.summary` and `transit.summary`.
Recorded in `ALLOWED` with a reason each rather than decided in a hurry: every
one needs a judgement about whether the screen that would show it deserves to
exist, and that is a piece of work on its own. The check can see them now,
which it never could.

Full suite green: **1,140 checks**.

## 2026-07-31 — SEEDFALL: structures you fly into (#108, third slice)

The last named piece of the docking-clearance request — *"stations large enough
that a ship can fly inside of them, and then be docked internally"* — and it
began by finding that **seven of the nineteen holdings could not be docked with
at all.**

Not a speculative feature. `data/works3d.py` gave every colony class its own
structure with its own berths, and `radius_km` was quietly doing two jobs: how
big a thing *is* (what the window draws, what the card says) and what a ship can
*hit*. Furniture — rings, masts, gantries, arms — is exactly what you berth
against, so a berth inside the bounding sphere is normal. Flown rather than
computed, a conn driven at an ARCA Habitat reported

    ARCA Deepcut at 12 m/s — 3,995 m from mast 3. The frames took it.

And the same question was asked in **two** places, both reading `radius_km`:
`sim/conn`'s swept-path test and `sim/outcome`'s arrival test. `bays.hull_km`
is the one door now. A world keeps its own radius — a planet has no furniture,
so its radius is its ground.

**The rule is derived per structure rather than chosen once.** A berth is a
fitting on the outside, so the hull stops just short of the nearest one. The
first draft did apply a single share — 0.55 — to everything, which made the
seven reachable and also halved the solid radius of a quay, a hub and a Weave
gate whose berths sit at 0.91 to 1.11 and never needed it. Three checks caught
it at once: a hull driven into a station at 45 m/s came away **adrift**, because
the thing it was aimed at had shrunk out from under it. Ramming a hub is a real
act with real consequences for both hulls, and a constant chosen for one problem
broke it.

**And then the bays.** A drum a million people live inside and a gestation shell
that hands out finished hulls have their berths in the middle *on purpose*, so
those two stay solid and you go in through the aperture. Flown: a hull passes a
**383 m mouth** and makes fast at a cradle **120 m from the middle** of a GRAVID
Nursery — *"Station held on Deepcut: 120 m, 0.4 m/s relative. Lines across."*
ARCA opens **2,050 m** across a 2.75 km drum, with the berths on the inner wall.
Fly down the middle and you get inside; keep going and you hit the far end,
which is right — you must stop and cross to the wall.

One modelling error the flying caught: the first bore was *wider than the solid
part*, a 3.2 km opening through a 2.7 km middle, so every off-axis approach
simply flew past and there was no rim to miss. The check holds the two apart for
every bay now.

`bays.clearance_km` was written and called by nothing, and deleted rather than
given an invented caller. That is the third time this cycle.

## 2026-07-31 — SEEDFALL: a hull the machines are holding (#110, fifth slice)

Robotic ships, and the fix was one condition written twice. Both places that
ask whether a hull is deserted — the air running out in `core/clock` and the
stores running out in `sim/upkeep` — asked only whether any *person* was left:

    if game.ship.crew <= 0 and not lifespan.active(game.officers):
        game.die("Nobody left aboard to hold the watch.")

Measured with three machines standing engineering, science and comms, and
`state.recompute` already reading regen 1.71 and research 1.38 off them: both
lines fired. A hull the Dry Choir would call fully crewed was reported as
abandoned — the opposite of what `hullforms` has said about the synthetic
family since it was written, "crewless Dry Choir work".

`robots.watchkeepers` is the one door both consult now. Driven through the
game: a breach kills the last two hands, and two machines carry the hull two
hundred days further — **mending the very breach that killed the crew, 10% to
100% of whole.** Starve it instead and the other path does the same. Take the
machines away and both end the chronicle exactly as before; break them, or
crate them in the hold, and it ends again.

**`awake_share` was right by accident.** With a complement of zero it returned
1.0 through a `total <= 0` guard rather than because anything counted machines.
Now they count, and the consequence that was missing appears: 37 aboard with 30
under reads 19% alone and 23% with two machines, and the bench goes 31% to 36%.
Machines keep the workshop turning while the crew sleeps, which is a thing a
captain would obviously expect and the game did not do.

One bug of my own making: the second `from ..sim import robots as robots_sim`
inside `advance_days` made the name local to the whole function, so the
module-level import was unbound at the *earlier* use and the crewless path
crashed on its first run.

Six mutations, six caught — but three of them only after the checks were
strengthened. The starvation path was never exercised, a broken frame was never
tested as a non-watch, and the sleep check asserted something true either way.
A fourth came out of the sweep itself: the condition is *aboard **and**
working*, not *not broken*, and a machine crated in the hold was holding the
ship.

Full suite green: **1,135 checks**.

## 2026-07-31 — SEEDFALL: what a machine looks like, from what it is for (#110, fourth slice)

The Machines tab was the last catalogue page in the game that was a wall of
text. `data/robots3d.py` gives each of the twenty classes a body, built out of
its own entry the way `works3d` builds a holding — so a new class gets a body
without anybody drawing one, and there is a check that proves it: an invented
E4, level-five, eleven-tonne mining-and-survey frame comes out as `trunk, rig,
dish, thrusters, hands, head`.

The vocabulary is the one real robotics uses — what it stands on, what it works
with, what it senses with. Cargo gives it a slung hold, mining gives it cutting
heads, repair and works give it manipulators, survey a dish, ground a ventral
pack. **Autonomy is drawn**: at E3 and above a machine carries a sensor head,
because deciding for itself is what it is for and the thing that decides needs
something to decide with; below that it carries a relay mast, because somebody
else is flying it. A class with no watch that goes to the body has thrusters
and no feet. A Loader Exoframe is a harness with a person-shaped hole; an
Anchorite is a rack and nothing else.

**Three defects, all the same defect.** The silhouette check found a gun mount
drawn exactly where a hybrid's graft band already sat — a Wet-wired Gunner
rendering **100%** the same as a Graft-Pilot; then bulk reaching only the trunk,
so a 2 t Hullwright and a 4 t Myrmidon shared **95%**; then level drawn nowhere
at all, so a Precentor rated four looked like a Coral Tender rated two at
**89%**. Each time the difference was in the data and could not be seen. The
fixes were bulk through the limbs and stance, and a second pair of manipulators
for a senior machine.

The bar is 88%, and higher than `test_silhouettes`' 72% on purpose: that one is
for gates against couriers, long spindly things whose outlines barely meet.
These are compact frames that all stand on legs and carry arms, and the honest
worst pair is a Precentor against a Coral Tender at 86%. Every defect the check
caught sat at 89% or above, so the margin is real rather than a rubber stamp.

The reachability guard caught one more: `robots3d.is_robot`, written by analogy
with `works3d.is_work` and needed by nothing, since `mesh_for` already returns
None for a class that has no body. Deleted rather than given an invented caller.

## 2026-07-31 — SEEDFALL: hands that are not people (#110)

Asked for robots — robotic ships, robots on stations, robot crew, cyborgs,
organic robots, and different kinds for different technologies — and asked
whether `genesis-world` helps.

**It does not, and it is worth saying why.** Genesis World is a GPU
multi-physics platform for training embodied-AI policies: rigid/FEM/MPM/SPH/PBD
solvers sharing one scene, URDF and MJCF asset parsing, ray-traced rendering,
kernels compiled to CUDA and Metal. It simulates contact-rich manipulation at
kilohertz. SEEDFALL simulates orbital mechanics on a sixty-second tick, renders
through a 219-line software rasteriser, keeps every file under five hundred
lines, and rests its entire test harness on being deterministic and headless.
Taking it as a dependency would trade all of that for physics the game does not
have a question for. What *is* useful from the research is the **ECSS autonomy
ladder** — E1 real-time teleoperation, E2 preplanned, E3 adaptive, E4
goal-directed — and the light-lag figures behind it: 20 ms in low orbit, 3–5 s
to the Moon, 8–40 minutes to Mars, which is why nobody drives a rover with a
joystick.

That ladder is the design. **A robot is worth what its autonomy can carry
across the gap to whoever is telling it what to do**, and SEEDFALL measures
that gap everywhere already. So `sim/robots.grip` is two terms: what a machine
does on its own account, plus the share that needed you, decaying with the
round trip. Measured across the rungs:

    alongside    E1 1.000  E2 1.000  E3 1.000  E4 1.000
    the Moon     E1 0.597  E2 0.998  E3 1.000  E4 1.000
    1 AU         E1 0.004  E2 0.569  E3 0.967  E4 1.000
    40 AU        E1 0.000  E2 0.078  E3 0.513  E4 0.999
    4.2 ly       E1 0.000  E2 0.050  E3 0.250  E4 0.643

Which turns "which robot" into "where will it be working". Measured in play: a
Spar Rigger is **level four** and teleoperated, and posted to a holding 2.1 AU
away — a 36-minute round trip — it works at **0.007**. A Verger is level three
and adaptive, at the same holding, and works at **2.80**. The catalogue never
has to say which is better.

Twenty classes across the five families the hulls and holdings already use:
Yards frames that are cheap and obedient, Dry Choir recordings that are superb
and autonomous and never mend, grown Myrmidons and Scarabs that eat biomass and
heal overnight, hybrid graft-pilots and wet-wired gunners who are a person and
a machine and pay both bills, and two xeno things nobody has explained. Every
one is gated on a technology that already existed in the tree — `aicore`,
`dronework`, `synthmind`, `consensus`, `mea`, `neuromorphic`, `xenoalloy` — and
none of them is a bonus with a name: a machine either stands a bridge watch the
game already reads, or holds a duty a holding already needs doing.

**The model was wrong before the constant was.** The first draft had grip decay
to zero, so an Anchorite — a mind racked in a holding and *bought to be left
behind* — kept a thousandth of itself the moment the ship sailed. The ECSS
ladder does not describe how well a robot obeys; it describes how much mission
it executes on its own. `STANDING` is that: E1 nothing, E4 sixty per cent. What
the distance costs is the part that was you.

A machine carries no loyalty field on purpose, so it works at exactly its level
— neither the 1.2 a devoted officer gives nor the 0.45 a mutinous one does.

Ten mutations, ten caught — but the tenth only after the check was fixed. The
panel check exercised `where_line` and `lag_line` and never built the widget,
so printing the *rating* instead of the *reading* passed. It reads the pills
now: a statue at a holding says `LVL 0.01/4`, not `lvl 4`.

The tripwire sweep found two more: `ALONGSIDE_AU` was declared and never read
— it is the clamp that stops a machine on the body the hull is holding over
paying grip for a few hundred kilometres of orbit — and `MEND_PER_DAY` and
`BROKEN_AT` were held only by the wide set, so the grown-against-built trade
was not named by any suite that knew what it meant. Sixty days of work now
puts a welded Hullwright under at 0.23 and leaves a grown Myrmidon at 1.00,
and forty days stowed mends one and not the other. 0 of 6 unprotected.

**And then the hole that mattered most.** The cycle above shipped a roster, a
law, a panel and a codex tab — and nothing in the game called `build`, `post`
or `scrap`. Twenty classes a player could read about and never own. The
reachability guard does not catch that, because a call from a check counts as
a call. `ui/machineshop.py` is the door: build cards per yard, a posting
control, and scrap.

The posting control is the part worth having. It quotes what a machine would
be worth **at the place you are about to send it**, before you send it — the
same Myrmidon reads "Aboard — standing a watch — lvl 2.00" and "Post to
Deepcut — lvl 0.33" in one list. Driven through the real widgets: three Build
presses built three machines, the combo posted one to Deepcut, and the
effective level came out at 0.3267 against the quoted 0.33.

Two defects from looking at the rendered screen: cards with no binomial printed
the first sentence of the blurb as a sub-label and then the blurb under it, so
every fabricated card said the same thing twice; and there was no check that
the door existed at all, which there now is — it clicks the real buttons.

**Six duties advertised, one consumed.** A Scarab Crawler said "Mining" on its
card and cut no rock; a Stevedore said "Cargo" and stowed nothing. That is the
defect `tests/test_declared` guards one layer down, committed one layer up.

The fix needed no new plumbing, because every duty already had a number that
meant it on `Stats` — the door the whole game reads. `repair` lifts `regen`,
which `repair_tick` reads; `mine` lifts `mine`, which `mining.rig_of` walks;
`cargo` lifts the hold; `survey` lifts `scan`; `ground` lifts `crew_guard`,
which `sim/damage` reads when a boarding costs people. Measured: regen
1.35→1.58, mine 3.2→3.71, cargo 340→372 t, scan 0.72→1.00, crew_guard 0→0.15,
and a holding's ore 2.6→2.7. One derived magnitude behind all of them — a
level-three machine lifts its stat by about fifteen per cent of a starting
hull's, the same share a Verger lifts a holding by.

The check is the general guard rather than six specific ones: it walks
`DUTIES`, finds a class advertising each, puts it aboard or at a holding, and
demands the number move — and refuses any effect wired for a duty no card
offers. A seventh duty added tomorrow fails until it does something.

Full suite green: **1,128 checks**.

## 2026-07-31 — SEEDFALL: nineteen stations, one mesh (#80)

Asked for a real catalogue of the things in the universe, so I went and
measured what is drawn rather than what is listed. Plant one of each colony
class, ask the game what is in the sky:

    colony anchorages: 19
    distinct meshes: 1

Every holding a captain can build — an ARCA Habitat with a million people
aboard, a TARDIGRADE Vault, a VESPER Picket, a Fabricator Yard — was
`berths3d.holding()`, four tanks in a frame. In the sky, on the approach, and
at the berth you tie up to. And the codex tab that lists all nineteen carried
no picture at all: a page of specifications sitting on top of a renderer the
rest of the game had been using for cycles.

`data/works3d.py` builds one structure per class **out of the class's own
entry**, the way `hulls3d.proportions` reads a chassis. Ore or phosphate gives
it roots down into the body; volatiles a condenser bell; alloy a set of stacks;
biomass fronds; research a dish; a sensor or a survey yield gives it masts.
`gestation` is a womb and `drydock` a slipway cradle, because a nursery grows a
hull inside a placenta and the Yards weld one on a slip — the fiction had that
distinction and the picture was not using it. `megastructure` is a drum people
live *inside*, `vault` an anchored armoured drum, `ward` turrets, `port` a quay
arm with a light on the end, `drift` the vanes of something that is not
station-keeping. Nothing is hand-drawn, so a new class in `colonies.py` gets a
structure without anybody drawing one — and the portrait cannot disagree with
the card, because they are the same document.

The Jaccard check earned its keep three times, each time on **a difference
that was drawn and invisible**: masts at 0.24 sat inside the mouth of a dish,
so a Relay Choir rendered 93% the same as a CHORUS Node; stacks at 0.30 sat
inside a cradle cage, so a Fabricator Yard was 90% a GRAVID Nursery; a
habitation ring at 0.66 hid in the same cage. Two of the three fixes were
better models rather than bigger numbers. Worst pair now 69%, and it is the two
things that genuinely are both slipways.

A structure has a right way up and a ship does not. `ATTITUDE["berth"]`'s 0.42
is right for rings and arms and wrong for anything built along its own axis:
all nineteen came out as the same lumpy egg with fittings stuck on. The sign
mattered too — a positive tilt sends model +z *down* the screen, which is
nothing to a ship shown broadside and turns every dish in the sector upside
down into a skirt.

**And a size was two sizes.** `sim/sky` drew every anchorage at 0.6 km while
`sim/targets` handed the approach 0.4 km for the same object, so the thing you
picked out at forty kilometres was half again the size of the thing you came
alongside. `berths3d.radius_km` is one door now, and the scale is pinned to the
one habitat whose true size the GESTALT documents state: ARCA comes out at
2.5 km, the picket at 0.29, and every structure in between falls where its
build time and its crowd put it.

The traffic joined the codex while I was there — five errands the sky has drawn
since `ships3d` was written and no page ever showed, so a captain could not
learn what an unmarked hull looks like except by meeting one.

Nine mutations run. Eight caught; the ninth (moving `GANTRY_R`) is a genuine
no-op, because the builder and the berths read the same constant and the
fitting travels with the berth — which is the one door working. Offsetting the
berths alone, which is the disagreement the check exists for, is caught. Full
suite green: **1,116 checks**.
