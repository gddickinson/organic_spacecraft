# Tests — what each suite holds and why (1 of 2)

Moved out of `seedfall/INTERFACE.md`, which is now only the map. Text unchanged.


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
- **`test_parley.py`** checks a *probabilistic* forecast the only honest way:
  state the chance the panel shows, then hail four hundred times and count. 22%
  said / 19% run, 45/45, 60/64 — inside three sigma at each standing. The odds
  were nowhere before this: "Hail them" was a hidden one-shot whose losing side
  is the enemy taking a free turn, on the same panel where
  `stations.order_preview` prints a line per helm order. **And the hail never
  asked what the power remembered** — `b.rep` is the standing on the books,
  `grudge.feeling` is the memory behind it, which the game already spends on
  prices, favours and whether work is posted. A Charter that remembers a
  destroyed hull sits at -88, which takes a hail from 22% to 4%; one that
  remembers a rescue lifts it to 28%. `parley.odds`/`escape_odds` are the one
  door and return the named terms, so the panel reads "42% they stand down —
  your standing with them +17 · you have the upper hand +13 · what they remember
  of you -7. Refused, they fire anyway."
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
  locked out on day one. Its newest check buys what the desk quotes:
  `voyage` sized a load by hold and purse and never by the stock on the quay, so
  **12 of 15 recommended runs forecast more tonnage than the port held, the worst
  by 2.7×** — a 287-tonne voyage out of a berth holding 59. That was wrong twice,
  because `worth_flying` ranks by `net` and `net` scales with tonnage, so the
  ordering was decided by cargo that did not exist.
- **`test_wharfage.py`** trades at nine quays and checks both sides of every
  deal: what leaves the captain's account arrives in the holder's purse to the
  credit. The rate it charges is read *off the rendered board* and applied to a
  real purchase, because reading `wharfage.rate` would only prove the module
  agrees with itself. It measures what the charge is worth in play — over the
  runs the desk actually recommends the two quays take **11% of what a run
  clears**, 10% loading at an outpost against 12% at a station — and what
  standing is worth: **a factor of four between Kin and Hunted**. A decade of one
  chronicle: 272 deals, 799,533 across the counter, 18,359 in dues, and **41% of
  what the Charter holds by the end came off the captain**.
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
- **`test_showflying.py`** holds all of it, mostly off the widgets rather than
  the sim behind them: the record is the burn and is cleared by a coast; both
  consoles light exactly the axis that fired; the toggle is shared and turns
  off two ways; *Ahead* lights the aft cluster; the diagram's new light lands
  **on the mount that fired**, measured in pixels against where
  `data/mounts.py` puts it; and the predicted course equals the flying to the
  digit. Its framing check needed three goes — a bounding box cannot tell
  "centred on the pair" from "centred on the target", and neither can the 2D
  midpoint, because perspective throws it 20–31 px out even when correct. What
  is crisp is which *side* of the centre each object falls on, asked at three
  camera angles. Fourteen mutations, fourteen caught.

- **`test_clearance.py`** holds the protocol: what a willing structure sends
  (and that none of it is trivial — a turning hub must say it turns); four
  distinct refusals with four distinct reasons, and the standing one proved to
  be a *gate* by putting the captain back in favour; a ship clearing you for
  its collar; the approach flying the berth the port assigned rather than the
  one it fancied; and the clearance agreeing with the geometry to the metre.
  Nine mutations, nine caught.

- **`test_freeflight.py`** holds flying for its own sake: the pad is live
  with nothing to approach; nothing ends the flight but the pilot, including
  at zero range where every arrival test is true at once; what was flown is
  where the ship has got to, to within a kilometre in four thousand; the mass
  and the hours are charged and the ledger says what it was; a hand-over keeps
  the way on; a refused hand-over moves nothing; and the window offers it with
  a button that says which act it will do. Ten mutations, ten caught — the
  tenth only after the refusal check was made to use a *clearance* refusal:
  the first one it tried was turned away by `can_conn` before the ship had
  been moved at all, so it could never have exercised the restore it claimed
  to cover.

- **`test_standoff.py`** holds the berth that comes out to you: the berth is
  off the hull rather than on it; holding still runs the boom out and drifting
  runs it back in; near and slow is not moored until it has you; the clearance
  says a different act in different words at a tighter rate; and the arm is
  *drawn* as far out as it has come. That last check was the interesting one —
  it first counted lit pixels in the whole frame, which rose with the boom and
  looked convincing, but a mutation drawing the arm permanently at full stretch
  passed it 44 against 43, because the count was mostly reading the change of
  tint and pen at capture rather than length. It now walks the arm's own path
  through the same camera the window builds and finds the furthest lit point:
  commanded against drawn, 25%→32%, 50%→56%, 75%→82%, 100%→100%. Thirteen
  mutations, twelve caught, the thirteenth a no-op recorded as one in
  `viewport._boom`.

- **`test_moorings.py`** holds the berths: every sort has them and they scale
  with the structure; the far side is not a berth at four sorts and four
  scales; the berth is chosen on final and held; and the computer still
  berths, asked *where it ended up*. Eight mutations, eight caught.
- **`test_byhand.py`** puts hands on the flight controls and looks at where
  the ship stops: three chronicles berthed on the mast in 2–6 presses from the
  corridor. It reads the pad's own labels rather than the sim behind them —
  the guidance arrows were lost from the buttons once and nothing noticed,
  because every other check called `moorings.steer` directly, and a mutation
  that doubled the figure printed on a button passed until the check read the
  button. Six mutations, six caught.

- **`test_knock.py`** holds the consequences: a struck quay off station where
  the whole game reads it, measured against the *same day* unstruck because a
  body sweeps tens of millions of km in a fortnight and the first version of
  that measurement reported a 648 km shove as 42 million; a manned berth
  recovering and a derelict not; the drift being the shove and nothing else;
  a hub rammed at 30 m/s, flown; and a knock surviving a reload. Its own
  sweep found two faults in itself — an **unbounded loop that hung the suite**
  when the recovery was mutated away, and `KEEPING_DAYS` unpinned because
  ordering assertions survive a rescale. Both fixed; eight of eight caught.

- **`test_impulse.py`** holds the momentum: conservation measured across four
  decades of mass rather than asserted from the formula that produced it; the
  player charged exactly what the one-sided formula charged at all four
  written speeds; the mass ratio deciding who suffers, symmetric under
  swapping the roles; a burn against a mooring moving the pair (0.68 m/s on a
  hub, 11.6 on a courier, 0.11 on a gate, from 12 m/s of ship); and a hub
  rammed at 30 m/s reaching the chronicle from both sides. Eight mutations,
  eight caught.

- **`test_reticle.py`** is three pixel-read claims about the target bracket:
  it appears on one feed of six and it is the one the quay is in; it follows
  the geometry rather than the name of a camera (nose 90° round and it leaves
  the bow); and it sits on the target rather than in the middle of the frame,
  measured 30° off the bore where those two differ by 69 px.

- **`test_readiness.py`** holds the tactical station to seven claims, all
  seven mutation-tested. The rehearsal is the fight's own arithmetic; a
  hundred reports cost no heat, no cargo, no hull and no luck; the window
  shows the fight it is titled with; standing by it lists every hull and
  admits its plot is a rehearsal; the ranges move when the ship does; and the
  rehearsal holds still between repaints — that last one asked of the
  *pixels*, because handing `initial_layout` an rng moves the picture and not
  one figure in the report.

- **`test_position.py`** is the one door for where the ship is, held to five
  claims: a new captain is moored at the quay their opening log names and the
  conn opens on it (six chronicles); every consumer reads the *same function*,
  proved by moving the hull from the innermost orbit to the outermost — 8.13 AU
  — and watching `berthing.reach_to` follow from 359 to 1,405 million km; a
  moored ship rides its orbit, 0.59 AU over 120 days and still alongside; a
  jump stands off at exactly `ARRIVAL_RADIUS` and a *placed* stand-off holds
  the place it was given; and a save written before `ship_xy` existed opens
  where it always thought it was.
