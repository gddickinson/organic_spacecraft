# Innovation 6 — The Assembly (politics)

## Why

Diplomacy has two axes: the captain's standing, and a relations matrix
between the four powers. The matrix is moved only by the captain's brokering,
by drift, and by ventures. The play-test found:
- **Concord** (all four powers at Kin and all six pairs at peace) was reached
  only through exploits, never by honest play.
- The powers never meet. There is no forum where their interests collide in
  public and where a captain with standing can move the outcome.

## What the player gets

**A sector council that sits every season.**

### Sessions

- Every ~90 days (seeded jitter of ±10) the four powers sit at a rotating
  capital: the Charter, Concordat, Freehold and Dry Choir capitals in turn.
- A despatch announces each session about 30 days ahead, with the agenda.
- Each session tables 2–3 **resolutions** drawn from a table of about 16,
  weighted by the state of the sector:
  - Bloom pressure raises "Bloom Levy";
  - war raises "Ceasefire";
  - smuggling raises "Contraband Accord".

### Resolutions

Each has a text, a sponsor power and an **effect** from a closed vocabulary.
The term is 180 days.

| Resolution | Effect key | Read by |
|---|---|---|
| Bloom Levy | powers pay into containment; tariffs +5% | `exchequer` (income tithe), containment `ventures` odds, `wharfage.rate` |
| Open Quays | wharfage −50% everywhere | `wharfage.rate` |
| Licence Amnesty | unlicensed seeding legal for the term | `enforce.may_seed`, `customs` |
| Embargo on ⟨power⟩ | that power's goods can't be sold at the others' ports | `trade.sell` refusal plus reason |
| Ceasefire ⟨A, B⟩ | no fleet actions between A and B; relation floor −40 | `war`, `armada`, `ventures` |
| Research Commons | evidence from sold survey data also feeds your bench | `trade.sell_survey_data` → `inquiry.add` |
| Salvage Law | salvage from destroyed hulls is taxed 30% by the local power | `aftermath.worth_of` |
| Charter Recognition of the Choir | Dry Choir standing floor −10; Charter–Choir relation +15 | `diplomacy` |
| Convoy Escort Mandate | lawlessness −25% on capital-to-capital lanes | `piracy.lawlessness` |
| Colony Charter | founding a colony in unclaimed space is +20% cheaper | `colony` costs |
| Harbour Dues Reform | the recruit desk and repairs are 15% cheaper | `services` |
| Border Treaty ⟨A, B⟩ | annexation between A and B is frozen | `territory`, `ventures` annexation |

Add a few more of the same shape, to about 16.

### Voting

- Each power votes yes, no or abstain from its **interest**, a score from its
  creed and doctrine (`data/factions.py`), its agenda (`data/diplomacy`
  AGENDAS), the relations matrix (it votes against a rival's sponsorship), and
  its purse (`exchequer`).
- A resolution passes on 3 of 4 yes votes, or on 2 yes with 2 abstain.
- **The forecast** shows the expected vote from each power, with its reasons.
  The forecast *is* the vote if nothing changes: pinned by a check.

### Lobbying

Before the session, the captain can move a power's vote. Every act has a
preview that states the swing, the cost and the side-effects, and the act
equals the preview.
- **Petition:** spends standing with that power, scaled by the swing.
- **Pay:** credits, with a diminishing return, and it is noticed: "bought
  votes" is remembered by the other powers (`sim/memory`).
- **Leak:** needs intelligence (charts, or field notes on the rival);
  embarrasses the sponsor.
- **Attend:** be at the session capital on the day to **speak**. Comms officer
  skill and your standing give a swing on every power, plus a renown-style
  chronicle line.

### Consequences

- **The relations matrix moves.** Losing powers take −4 to −8 with the powers
  that voted them down; co-voters take +3 to +6. This is the honest road to
  Concord: consistently brokering passable compromises raises every pair.
- A passed resolution sets effect keys for its term, and **every key is read
  by the system named above** ("nothing computed that nothing consumes"). The
  key disappears at expiry.
- Despatches report the outcome, with who voted how.

## Design

- **Content:** `data/assembly.py` holds resolutions as (id, name, text, effect
  key, parameters, sponsor weights, term) and the session cadence.
- **Rules:** `sim/assembly.py` covers sessions (schedule, agenda draw with a
  per-session RNG key, not `game.rng` at view time), `forecast(game, res_id)`,
  `lobby(game, act, power, res_id)` with a preview, `sit(game)` (resolve),
  `effects(game)` (the live keys for the systems to read) and `tick`.
- **State:** `Game.assembly: object | None = None` holds a registered
  `AssemblyState`: next session day and capital, agenda, lobby record, active
  resolutions with expiry, and history.
- **Clock:** `assembly.tick(game, n, r)` in sector time.
- **Reading effects:** each consuming system reads one door,
  `assembly.effect(game, key, default)`. Keep each read to one line at the
  point of use. An efficacy check turns each effect off and shows its number
  move.

## UI

An "Assembly" tab on the Diplomacy screen (`ui/diplomacy_view.py` hosts it;
the panel lives in a new `ui/assembly_panel.py`):
- the next session, with a countdown, the capital (and a "set a course"
  button), and the agenda;
- for each resolution: the text, its effect in plain words, the sponsor, the
  forecast votes with reasons, and lobby actions with costs and swings;
- active resolutions with their expiry;
- history.

The Help/manual gets a topic.

## Balance targets

- About 40–60% of tabled resolutions pass without lobbying.
- A captain who lobbies well can pass or kill about 80%, at real cost.
- Over 5 years, a player who consistently brokers compromises raises the mean
  pair relation by about +30 or more, compared with −10 to +5 for one who
  ignores the Assembly. This is the honest Concord road.
- No lobbying loop may gain more standing than it spends.

## Tests (new suite `test_assembly`)

- Sessions come on schedule at a rotating capital, and the agenda is
  deterministic per session (opening the screen does not change it).
- The forecast equals the vote when nothing changes.
- Each lobby act equals its preview.
- Attending in person swings votes, and not attending does not.
- Each effect key moves its consumer's number (efficacy).
- Effects expire on the stated day.
- Relations move by outcome.
- A long honest-broker bot raises the mean relation measurably more than an
  idle one.
- Cross-process save mid-agenda.

## Later hooks

A "Bounty Compact" (innovation 3) and a "Deep Gate Moratorium" (innovation
1) should be added as resolutions once those merge.
