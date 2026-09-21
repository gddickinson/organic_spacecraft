# IMPROVEMENTS.md — the live backlog

What could be better, honestly sized, kept current. The done column stays,
because a list that forgets what it cost is a list that re-estimates badly.
History and reasoning live in [`notes/`](notes/README.md) and
`SESSION_LOG.md`; this file is only the state of play.

## Where the done list went

Every pass that closed something is kept, unchanged, under
[`improvements/`](improvements/): the done column stays, split so no file
passes 500 lines.

- [done-01.md](improvements/done-01.md) — Done — the flight-deck campaign; Done — the third pass; Done — the fourth pass; Done — the fifth pass; Done — the sixth pass; Done — the eighth pass; Done — the ninth pass; Done — the tenth pass
- [done-02.md](improvements/done-02.md) — Done — the eleventh pass; Done — the twelfth pass; Done — the thirteenth pass; Done — the fourteenth pass; Done — the fifteenth pass; Done — the sixteenth pass; Done — the seventeenth pass
- [done-03.md](improvements/done-03.md) — Done — the nineteenth pass; Closed by the nineteenth pass — the 2026-08-05 e; Done — the eighteenth pass; Closed by the eighteenth pass — the governance s

## Closed by the 2026-09 review and its ten innovations

The whole-project review (`../reviews/2026-09-17/`, with `STATUS.md` mapping
each item to its fix) closed these from the lists below:

- **No sound** — a synthesised soundscape, about thirty cues made at first
  run behind a no-op façade (`ui/synth`, `ui/audio`, `ui/soundmap`; `audio`,
  `soundmap`).
- **Lawlessness had one moment to bite** — beside the jump exit,
  `piracy.lawlessness` is now read by the hunt board (where raiders work) and
  by every freight line's route risk, and two Assembly resolutions move it.
- **One save slot** — named slots and a chronicle picker (`core/slots.py`).
- **The header clipped the ship name** — `widgets.Elided`.
- **Forced-answer screens locked navigation** for envoys — "Leave it for
  now" sets one aside until its day (`approach.set_aside`). A power's demand
  and a legacy situation still hold the window (see below).
- **Nine length debts** — every file is under 500 lines, and
  `tests/test_length.ALLOWED` is empty.
- **Dead imports** — the tree-wide ruff sweep, and the `exports` suite, which
  catches a sweep that removes a re-export a caller reads.
- **Let the captain hide too** — `sim/running_dark.py`: fewer meetings, a
  first volley, suspicion where the law is; a shroud deepens it.

## Closed on 2026-09-19 — a contact you can see

The flight model knew everything about a collision and drew none of it:
measured, a 55 m/s arrival at a Fleet Hub cost 1,134 of a 336-point hull and
moved nothing on the screen but a line of nine-point italic type — in a
window whose main camera was not even pointing at the structure.

- **`sim/shock.py`** — the one door between the fact and the picture. It
  reads a resolved approach (or a turn of an engagement) and hands back what
  passed between the two: kind, bearing, both sides' damage, the shove, the
  fitting that was missed, the words. Qt-free; every figure is the flight's.
- **`ui/effects.py` / `effect_marks.py` / `effect_paint.py` /
  `effect_clock.py`** — the timeline, the marks, the composition, and a
  second 40 ms timer, because a collision *stops* the flight clock and the
  first frame of an explosion is not an explosion.
- Ten kinds of contact are drawn, plus the volley you take in combat; the
  conn turns to the camera that saw it (`viewport.best_view`); the outside
  view draws what the *other* side took. Two new sound cues: `impact`,
  `graze`. New suite: `shock`, twelve checks.

## Open — the Traveller programme, begun 2026-09-20

The world profile landed (`data/uwp.py`, `sim/profile.py`): eight
characteristics per world, derived from the sector, with trade
classifications, bases and a travel advisory. It is the spine the rest of
*Traveller*'s breadth hangs off, in the order that gets the most out of what
SEEDFALL already has:

1. **Speculative trade** — the classifications moving prices, with a Broker
   check on the lot. *Built and backed out once already*: multiplying the
   counter's quotes re-balances the whole economy, breaking the freight
   desk's load clamp and the careful captain's five-year ending. It needs a
   balance pass of its own — re-pin `renown`, `chronicle`, `freight`,
   `freightlines` and `wharfage` against the new curve, and probably a
   smaller shift than the table's first draft.
2. ~~**A 2d6 grammar**~~ — landed as `sim/checks.py`: six characteristics, a
   seven-rung difficulty ladder, −3 untrained, and the Effect. **What is left
   is the bringing-across**: every act that still resolves on an ad-hoc curve
   (survey, dig, repair, haggling, the docking approach) could be re-stated
   in the grammar, one at a time, each with its own re-pinning.
3. ~~**Life-path beginnings**~~ — landed as `data/careers.py` and
   `sim/lifepath.py`, derived per officer. **What is left is the captain**:
   `ui/beginning_view.py` still asks who you are with three choices, where
   Traveller would have you play the terms out and take what they give you.
4. **Patrons and tickets** — work that comes from a person, with a chance the
   job is not what it was said to be. The contract board is the shape; what
   is missing is the person and the lie.
5. **The monthly bill** — a hull's mortgage, maintenance and life support.
   Traveller's whole economy is driven by a payment falling due; SEEDFALL's
   purse has no such pressure.
6. **Law level bites** — the profile has the digit; wire it to what the port
   will find in the hold (`sim/customs`, `sim/contraband`).

### Left over from the crew screen (2026-09-20)

- **A station cannot be reassigned.** An officer holds the station they were
  hired into for life. Traveller's answer is that the person is the skills
  and the post is a chair; SEEDFALL's bonuses are keyed to `officer.role`,
  so moving somebody is a balance change, not a button.
- **Hiring is still the quay's.** The berth board stays on the Port screen
  because who is looking for work is a fact about the port. The Crew screen
  has a door to it, which is right, but a captain planning a hire has to read
  the hole on one screen and fill it on another.
- **`lifespan.age_of` invents and stores an age on the first ask.** Fixed
  where it bit (`sim/lifepath.of` resolves the age itself now), but the shape
  is still there: a *read* that writes. Anything else deriving from
  `officer.age` has the same order-dependence waiting for it.

### Left over from the concourse (2026-09-21, mostly closed)

Closed the same day: a hull is a place (`data/venues_aboard.py`), anagathics
bill by the month (`sim/clinic.tick`), and hiring halls hire
(`crew.pool_here`). What is left:

- **The derived-silhouette renderer is out of vocabulary.** Three habitat
  classes were refused by `test_works3d` because everything with a crowd in
  it comes out a ring, and a ring dominates the outline. Adding a fifth
  ring-shaped class will hit the same wall. The fix is either more parts or
  a ring whose radius varies with what it carries.
- **The new careers never come up as a *first* career** for a bridge
  station whose `BY_STATION` list does not name them, which is most of
  them. That is correct for a navigator and wrong for a purser the game
  does not have.
- **A face is only ever drawn still.** The portraits carry mood, years and
  fitted hardware and nothing about what somebody is *doing*: a watch
  ashore, a surgery under way, a course running. The concourse scene has the
  crowd; the people on the crew screen are passport photographs.
- **A ship that is a clinic never needs a port**, which is now true and not
  yet balanced. A LAZARET with a vat deck can graft at sea; nothing charges
  it more for doing so than a hospital ashore would.

### Left over from the substrates (2026-09-21)

- **Robots are still two systems.** `sim/robots.py` has machines with hull
  numbers that work a holding, and `data/lineages.frame` is a machine that
  stands a watch, and neither knows the other exists. A Verger that earned
  its way onto a bridge would be the obvious story and is not wired.
- **A mind has no second body.** The fiction says it wears whatever body
  the watch needs; mechanically it is an officer like any other. Instancing
  one into two stations, or losing the body and not the person, is the
  thing that would make the substrate mean something.
- **Nobody refuses to serve.** The gates have views about the crew; the
  *crew* has a view only through the purist conviction. An officer who will
  not sign to a hull carrying a frame would close the loop.
- **The vatborn have no story.** They are a lifespan and a price. The
  specification somebody paid for, and who paid it, is a life-path career
  waiting to be written.

## Open — the 2026-08-04 review: the systems layers

A four-agent review (combat, economy, strategic layer, player experience)
plus a live play-through over the bridge, looking everywhere the flight-deck
campaigns did not. The verdict: the flight deck holds and the systems layers
do not — not one item below was on this list before, and every number was
measured by driving the sim, not by reading it. In rough value order.
(The worst of it — the session-brick, the data loss, the same-counter
arbitrage, the contract exploits, the dead board, the unreachable Bloom,
the flash organ, the diplomacy exploits — was fixed the same day; see the
tenth pass above.)

*(Most of this list was closed by the nineteenth pass above — the scrap
exploit, the raw prices, the contraband market, the promotion arithmetic,
the robots, SOL-FORGE, the Cartel ledger, threat scaling, surrender/prize,
`nonlethal`, the brace button, the Charter's warships, the comms UI and the
keyboard sweep. What follows is only what remains open.)*

- **Mining is the worst-paid thing in the game** at 129 cr/day median, and
  it is the one with hull wear and mishap risk. Now that colonies have a
  ceiling (eleventh pass) the comparison is fairer, but a rig should still
  beat sitting still.
- No window geometry persistence; flat buttons' border contrast is not yet
  measured against WCAG's 3:1 (it was 2.02:1 before the theme change);
  `chloro`/`osteo` luminance-identical for a deuteranope; 8–9 px type with
  no scale setting; the Bloom absent from the HUD (a burden chip off
  `threat.harbours_left`); the yard's "After refit" numbers at the default
  window size, unchecked since the `fit` work; a power's demand and a legacy
  situation still lock navigation, where an envoy can now be set aside.
- `comms.tick` itself still watches one fact (the standing band). The board
  is no longer quiet — the Assembly's sittings, the sky's forecasts and the
  nova, rivals, the Kith, officer arcs, colony losses and epoch turns all
  write to it from their own sites — but wars, port closures and harbour
  losses are still only log lines (`sim/threat.py`).

## Open — from the final play-test (2026-09-18)

An independent play-test (first hour over the bridge, three strategies for
two years each) found eleven things. Nine were fixed that day, with part of
the tenth: envoy money through the purses, the tests' save tidy-up, the
sky-data quote, the berth lesson, the chart and Helm layouts, the Academy,
the Hollow's reach wording, signing on crew, raw `**` in Help, "A The
Tessellate site", and raw floats in the Port. Still open:

- **Where can you trade from?** The Port prices and buys for any hull in the
  system — survey data sold at Fleet Hub from 7 AU — while the shipyard
  wants you alongside and the berth lesson says the Port opens once you are.
  "Let the harbourmaster bring you in" opens the Port and docks nothing.
  One rule, chosen and applied at every counter; it moves the economy, so it
  is a design pass with the bots re-measured, not a patch.
- **The Assembly's listed reasons do not sum to the vote** shown (+0.3 of
  reasons against −0.2); one function should produce both.
- **"Payroll missed" repeats** on about one broke day in three. It draws on
  the day's luck, so quieting it changes every seed; do it with a pinned
  state-hash update.
- **Small words:** "On station: Charter 2 Well kept"; the log calls
  volatiles "Ice" and survey data "Data"; "Fly free — no destination" clips
  in its dialog, and "Magnetosome Biomineralisatio" at 1040 px; the tutorial
  says a close pass costs reaction mass (it cost 0); the Register says you
  have been nowhere that trades a good while you stand in such a port.
- **Balance:** a neutral trader who neither hails nor flees can be taken
  apart by a Concordat HAMMERFALL at standing −7 (14 turns); hail-then-flee
  escapes at 77% hull. Honest trading income varies wildly by seed (−₡940
  to +₡7,900 a month for the same bot).

## Open — defects and debts, in rough value order

1. **Tuning constants without a guard.** The tripwire's last clean sweep
   read 60 of 131 unprotected (`notes/design-01.md`, "Which numbers are
   actually held in place"); a few have been pinned since, and new constants
   (`path.py`, `engage.REACH_KM`, `freeflight.RUN_MARGIN`) joined the pool.
   Each pin is its own small piece of work: drive the sim to the bar,
   bracket with absolute values. Re-run the sweep before choosing targets.
2. **Other ships are not plotted on the helm chart.** Nothing gives a known
   hull a persistent position a chart could draw — honestly a design piece
   (where does a sighting live, how stale may it go), not a marker to add.
3. **The engine light lives one beat.** `fired_*` is truthfully "the burn
   that happened this tick", so at 250 ms the light flickers under an
   autopilot that corrects intermittently. A short UI-side latch (or a
   "last burn" row) would read better without lying about the record.
4. **The docking mini-game and the conn share a gate by accident.**
   `berthing.can_conn` refuses while `game.docking` (the mini-game) runs —
   two systems both named "approach" meeting in one check. Works, but the
   naming invites the next bug; worth a rename or a comment at the gate.
5. **The descent order is only on the conn console.** The flight window —
   the panel you'd actually fly a descent from — doesn't carry it.
6. **Run bill on the button as well as the board.** The ship board quotes
   it every beat; the `Run for X` button label could carry it too (stale
   between rebuilds — needs the label refreshed in `sync`).

## Ideas — not defects; would make it more fun or easier to pick up

(The first five ideas — dock-for-me, keyboard flying, the conn tutorial
lesson, time compression, brake-to-zero — shipped in the third pass.)

- **More for the effects layer, now it exists** (`ui/effects`): a dust plume
  when she is put down on a world rather than the same bloom a quay gets;
  the fractures carried onto the Ship screen's layer stack while the damage
  lasts; a scrape drawn as a streak along the skin rather than as a small
  bloom; and the engagement's own picture could use the rim arc for a shot
  that came from outside the frame, which it does not yet.
- **More HUD, now the layer exists** (`viewport_hud`): a ladder of tick
  marks on the predicted path (time-to labels), the corridor hold point
  drawn as a gate rather than a chevron, closing-rate colour on the mark,
  weapon-arc cones in the tactical plot's first-person view.
- **Throttle on the digit keys** beside the six axis keys.
- **A combat HUD in the battle screen's own viewport** — the band ring and
  arcs are on the tactical plot; the first-person cameras go dark in a
  fight today.
- **An orbit you fly is still flat.** `autopilot.across` shapes an orbit in
  the conn's *local* x/y plane and returns a tangent with `z` zero — a
  deliberate simplification, and untouched by this pass because the conn's
  frame is not the system's. Now that a heliocentric orbit has a tilt, the
  obvious next question is a polar or inclined orbit round a world, which is
  a real thing to want and would need the tangent, the rungs and the orbit
  test to agree about which plane is being held.
- **Sightings that age.** `Conn.sky` is a snapshot taken when the approach
  opens, so a dark raider can only be somewhere you did not look — it cannot
  *close* on you during a flight. This is the same missing piece as "other
  ships are not plotted on the helm chart" (defect 2): a sighting needs a
  home, a position and a staleness before either can be built. (The Sector
  Chart now draws a rival's last sighting as a ring that widens as it ages,
  `ui/hunt_marks` — the model for this, one level up.)
- **The height picker's refusal could say which gate refused it.** A rung
  can be unsold because the tank is too small *or* because `orbits.quotable`
  says the price cannot be believed on these thrusters; the tooltip blames
  the tank either way, and `flightdeck.can_arm` has to point at the picker
  rather than repeat the gate. One reason string, asked of `orbits`, would
  let both screens say the true one.
