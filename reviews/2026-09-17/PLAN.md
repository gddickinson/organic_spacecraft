# Plan — implement the review, and ten innovations

This plan implements all 60 review findings in this folder and adds ten
innovations that widen the game and the universe it is set in. It runs in
four phases. Each phase ends at a **gate**: the full suite green, a scripted
play-test over several seeds, and screenshots checked by eye. Nothing moves
on until the gate passes.

## Ground rules (they bind every stream)

- Layer rule `data → world → sim → ui`. `sim/` never imports Qt. One clock
  (`Game.advance_days`). No game rule lives in `ui/`.
- **Every new saved thing is a registered dataclass *field* with a default.**
  Old saves must keep loading, and a cross-process save/load check must pass.
- Every screen that offers a commitment states its consequence. A check
  performs the act and compares it with the preview.
- Every feature that claims to move a number is measured moving it, by an
  efficacy check that switches it off.
- Every file stays under 500 lines, and `tests/test_length.ALLOWED` gets no
  new debt.
- Exit codes are read from the interpreter, never through a pipe. No test
  touches `~/.seedfall`.

## How the work is run

The work runs as parallel streams, each in its own git worktree. Every
worktree is cut from a snapshot of the integrated tree, taken with
`git stash create`, so nothing is committed without being asked. When a
stream finishes, its diff against the snapshot is applied with
`git apply --3way`. Conflicts are resolved by hand, then the gate runs.

Hot files shared between streams are:
- `core/state.py` (Game fields)
- `core/clock.py` (tick hooks)
- `data/screens.py`
- `tests/suites.py`
- `data/help.py`

Streams append to these and keep their edits small. **No stream edits
`INTERFACE.md`, `IMPROVEMENTS.md`, `README.md` or `SESSION_LOG.md`.** Each
writes a `CHANGES-<stream>.md` note instead, and Phase 3 folds the notes into
the maps.

---

## Phase 0 — foundations (done directly, first)

Everything else depends on saves that survive a restart and on a suite that
runs in minutes rather than 17.

| Items | Work |
|---|---|
| #1 | `core/state.load_game` imports every `seedfall.sim`/`world` module before decoding (`save.ensure_registry`). `encode` refuses an unregistered dataclass. |
| #2 | `core/ids.py`: one id service. Every `_uid = itertools.count()` becomes `ids.next_id(kind)`. The counters are saved on `Game.ids` and reseeded to max(saved, seen+1) on load. |
| #3 | Runtime attributes become declared fields. `save.STRICT` (set by the tests) raises on any undeclared `__dict__` key. A long played game is saved under strict mode. |
| #4 | `clock._one_step`: a step with no whole day in it spends only ship time. It carries the fraction and never draws `rng("tick")`. |
| #8 | `save.read` catches everything and moves a bad file to `.bad`. Adds a version migration table (v1 → v2), load invariants, `fsync`, and a unique temporary file. |
| #5 | `app.main` installs `sys.excepthook`: write a crash log, save to a recovery slot, show the error. Fixes the Help-search deferred-focus crash. |
| #6 | Rail buttons drop `setShortcut` and the menu owns the keys. A check sends real key events. |
| #7 | The tripwire mutates a temporary copy of the package, never the tree. |
| #36–37 | `tests/__main__`: argparse, `--list`, unknown suite exits 2, `-j N` (one subprocess per suite), a timing table, try/except per suite, flushed output. |
| — | New suite `test_persistence`: resume across a process boundary, id counters, strict fields, corrupt, old and truncated saves, migration. |

**Gate 0:** the full suite green under `-j`, `test_persistence` green, and a
scratchpad copy of the real 5 Aug save resumes in a fresh process.

---

## Phase 1 — the review, as five parallel streams

| Stream | Items | Owns (primarily) |
|---|---|---|
| **A · rules** | #9–11 exploits, #12 Bloom curve smoothing, #13 death moves into the sim, #14 envoy grace and a real "Leave it", #15 minimum starting pocket, #16–20 (licence gates, commissions, shock quotes, bench spam, text, take-command rule, RNG-free screens, one `sim/stores.py`) | `sim/threat, trade, survey, colony, contracts, freight, market, research, consorts, aftermath`, `world/galaxy`, `data/lessons*`, `data/lore` |
| **B · interface** | #21–29 (clipping and scroll, battle layout, incremental log and in-place refresh, per-beat HUD path cache, keyboard and focus, visual fixes, freeing pop-outs, rules out of `ui/`, one thrust pad), plus save slots with a chronicle picker on the title screen | `ui/*` except `battle_view`'s resolution section |
| **C · engine** | #30 bridge validation, #31 LLM off the UI thread with a breaker, #32 imports, the re-entrancy guard and `xeno.__all__`, #33 narrow `except` blocks, #34 memoising `exchequer.income` | `bridge/*`, `core/llm.py`, `sim/voice, hail`, `core/clock` guard |
| **D · tooling** | #38 bridge protocol tests restored, #39 weak checks, #40 order dependence and optional Qt, #41 pytest shim, #42 `tests/qtkit.py`, #43 pyproject, CI and ruff | `tests/*` (except new suites owned by other streams), repo-root config |
| **E · documents** | #44–53 content fixes across the 13 documents, #51 a committed `calcs/` module plus a check against the documents, #59 root `sim/` honesty and `params.py` | `docs/*.html`, `calcs/`, root `sim/`, `assets/figures` |

Every stream adds checks for what it fixes. Stream A also turns the
play-test's exploit measurements into regression checks (`test_exploits`):
- no Lineage before about day 400;
- re-sweeps pay nothing;
- counter churn does not move standing;
- an honest bot reaches at least one ending on most seeds.

**Gate 1:** all five patches integrated, the full suite green, a scripted
campaign on 5 seeds × 3 strategies × 3 years with no exceptions and no
degenerate winner, and screenshots of every screen at 1040×680 and at the
default size.

---

## Phase 2 — ten innovations

Each innovation widens a different part of the game, and together they make
the universe larger. Each one ships with:
- data tables, a `sim` module with its saved state as fields, and a clock
  hook;
- a UI tab or panel, and help/manual text;
- checks, including efficacy checks and a cross-process save.

### Wave A (independent of each other)

**1. The Far Reaches — universe.** Three regions beyond the Verge, each
reached through a dormant **deep anchor** of the Weave that has to be
relit. Relighting takes a survey of the anchor, a project with a material
bill, and a new *Deep Weave* technology.
- **The Shoals:** an emission nebula. Sensors reach half as far, it is rich
  in volatiles and a new *nebular condensate*, Freehold havens sit inside,
  and raiders are heavy.
- **The Hollow:** a void. Lanes are long, rogue planets carry no light, and
  a fifth dead culture's relics lie there as unique fittings.
- **The Cradle:** a young, hot cluster with new O- and B-class stars. It is
  heavy with radiation and rare minerals, and it is home to the Kith (#2).

Implementation:
- `System.region` is a new field. Coordinates are per region, and distance
  across regions is infinite except through a deep gate.
- A region is generated deterministically from the seed the first time its
  anchor is lit, so old saves can open regions too and a new game pays
  nothing until then.
- The chart gains region tabs.
- The Bloom can cross a lit anchor, which makes opening one a decision.

It is about 36 new systems, taking the universe from 42 to about 78.

**3. Nemeses and the hunt — combat.** Named rival captains who persist:
- **Who they are:** pirates, bounty hunters, a Concordat ace, a Freehold
  duellist, and a Bloom-ridden husk.
- **What they carry:** a hull scaled to yours, traits, a grudge, a history
  with you, and a **sighting that ages**.
- **How they behave:** they roam the lanes, turn up through
  `encounters.draw_threat`, break off when beaten and come back refitted,
  and taunt you through despatches.
- **Bounties:** ports post bounties with a last-known system. *Search the
  system* spends days against their stealth.
- **Running dark:** the player can go dark (transponder off, drive banked,
  a shroud fitting). It lowers encounter odds and allows ambushes, but
  customs grows suspicious.
- **Rewards:** a bounty, standing, a prize hull and a trophy fitting.

This is the combat career the game lacked.

**4. The living hull — ship progression.** Grown, hybrid and xeno hulls
record stress channels:
- layer damage;
- heat cooked;
- light-years crossed;
- days in darkness;
- tonnes mined;
- surveys;
- dives;
- radiation dose.

At a threshold one of about 16 adaptations emerges, each grounded in the
GESTALT biology, with a benefit and a cost (for example a melanised rind:
−20% dose, +3% mass). The captain *encourages* it, so it sets in over days,
or has it *pruned* at a Fleet Hub. A hull-class "genome budget" caps how
many a hull keeps. Fabricated hulls do not adapt, which is the point of
them.

**5. Freight lines — economy.** Charter a trading house, put haulers in the
fleet, hire a master for each, and set a **line**: a route, a buying rule, a
selling rule and a cadence.
- Lines trade through the real markets, so they saturate them.
- They pay wharfage and face piracy and Bloom risk on the systems they
  cross. Hulls wear, and masters' skill and loyalty move margins.
- A per-line forecast has to match what the line actually earns.
- The house gives a mid-game money engine with honest risk, and keeps the
  Cartel's price register fresh.

It is a tab under Holdings.

**6. The Assembly — politics.** Every ~90 days the four powers sit at a
rotating capital and table two or three resolutions from a table of about
16:
- a Bloom levy;
- open quays;
- a licence amnesty;
- an embargo;
- a deep-gate moratorium;
- a bounty compact;
- a research commons;
- and others.

Each power votes by its creed and the relations matrix. The captain lobbies
beforehand (standing, credits, intelligence, with vote odds shown) or
speaks in person on the day. A passed resolution sets effect keys for a
term, from a closed vocabulary that the systems it names actually read. The
results move the relations matrix, which gives Concord an honest road. It
is an Assembly tab on Diplomacy.

**10. Soundscape — presentation.** `ui/audio.py` is a façade over
`QSoundEffect` that does nothing offscreen or without QtMultimedia. Every
sound is synthesised at first run with the standard library, so the repo
carries no binary assets.

Cues:
- clicks and screen changes;
- a good/bad/warning chime for each log kind;
- a jump;
- a loop while a burn is held;
- the proximity tone from the collision guard;
- a chime when a berth is secured;
- fire, hit and breach alarms in combat;
- a survey ping;
- a despatch arriving;
- a Bloom drone that scales with the burden;
- an ambience for each region.

Volume, effects and ambience are options, and every one of them does
something.

### Wave B (needs wave A)

**2. The Kith — a living alien people.** A spacefaring, communal species
native to the Cradle that speaks in modulated light. They are neither dead
like the four cultures nor unreachable like the Abyssals.
- **A lexicon:** 24 signs in 4 domains, learned through encounters,
  observation and the decoding bench. Understanding gates what you can
  ask.
- **A gift economy:** there are no posted prices. You offer, they
  reciprocate by preferences you uncover, and a wrong gift offends.
- **Their own standing,** kept outside the Concord set.
- **Unique goods:** *songglass*, and Kith-grafted organs that read the
  living hull's adaptations.
- **Hulls:** one or two new xeno hulls.

**7. Stellar phenomena — a living sky.** Timed events on systems:
- **flares:** a radiation dose unless you shelter behind a body; sensors
  up; comms down;
- **comets:** a mining window that rises and passes, and a volatile glut;
- **ion storms:** a lane closed for days;
- **a nova** building over months in the Cradle;
- **rogue-planet flybys.**

Each event is forecast honestly on the despatch board with lead time.
*Observing* a live phenomenon is a survey act that yields a new
*phenomena* evidence kind, and the Charter and the Choir buy the data.

**8. Officer arcs — characters.** Each officer draws one of 12 personal
arcs, three beats long:
- a sibling's last signal from a Bloom system;
- a Freehold debt;
- a Choir defector;
- a disgraced Charter scientist;
- and others.

A beat arrives as a despatch with costed choices. It is triggered by
places, which may lie in the Reaches, and by dates, loyalty and events. The
last beat grants a **signature trait**. A neglected beat costs loyalty, and
the officer may leave.

**9. Renown and the Voyage — progression and onboarding.**
- **Ranks.** A career renown score from milestones in every activity, with
  ranks (Master → Captain → Commodore → Admiral → Legend) that carry real
  perks.
- **Milestones.** Each of the ten endings gains three milestones with
  concrete rewards, tuned so an honest captain reaches at least one ending
  in about five years on most seeds (measured by bot).
- **Counsel.** The first officer gives three concrete next moves drawn from
  orders, freight and contracts, each with a "take me there" button.
- **Memoir.** At an ending or a death, a career **memoir** is written into
  a persistent *Hall of Captains* shared across chronicles.

This replaces the victory panel on Holdings with a Voyage view.

**Gate 2 (after each wave):** the integrated suite green, the scripted
campaign with the new systems on (regions opened, a nemesis hunted, a line
run, a session voted, an arc finished), screenshots of the new tabs, and
performance no worse than 2× today's per-day cost with every region open.

---

## Phase 3 — the maps, the length budget, the finish

| Items | Work |
|---|---|
| #35 plus new growth | Split every file at 500 lines or more along the seams named in the review. `tests/test_length.ALLOWED` shrinks and the limit becomes *under* 500. |
| #32 | pyflakes cleanup across the tree (unused imports and locals, duplicate keys, undefined names), done mechanically once the tree stops moving. |
| #54 | `seedfall/INTERFACE.md` becomes a map under 400 lines; its design history moves to `seedfall/notes/`. `IMPROVEMENTS.md` splits into `open.md` and `done-*.md`. |
| #55 | The root session log is archived by month under `logs/`, leaving a short index at the root. |
| #56 | `git gc`. |
| #57 | The README and INTERFACE files carry true counts, generated rather than typed. The screenshots are regenerated with `seedfall.tests.capture`. `deepen-roadmap.md` is archived. |
| #58, #60 | Viewer fixes, `.gitignore`, and the log's grammar. |
| — | The `CHANGES-*` notes are folded into the maps. A new `IMPROVEMENTS` entry. `SESSION_LOG` is updated. |

**Final gate:**
- a clean full suite;
- a fresh-process resume of a long save;
- an independent play-test of the finished game, covering its first hour,
  three strategies and the new systems, reported the same way as the
  review;
- every review item marked done in this folder with a pointer to where it
  was fixed.
