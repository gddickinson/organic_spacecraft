# SESSION_LOG.md — GESTALT project

Running progress log. Newest first.


## 2026-09-20 — People with lives, and somewhere to spend money

Everybody aboard is now somebody: twelve homeworlds, ten upbringings, twelve
ambitions, sixteen kinds of relationship, the berths they held before yours
and why each ended — dealt out of the career that made them, and derived, so
nothing is saved. A hundred and one things to own in twelve categories, each
with a tech level and a law level that hook straight into the world profile:
what is on the shelf is where you are standing, and what the customs desk
takes off you is the same list read the other way.

And a concourse to spend it on — a new Port tab with chandlers, banking,
eating houses and entertainments, twenty-two venues gated on the starport
class and the population, so where you put in decides what there is to do. A
night ashore buys morale, loyalty, standing and sometimes a rumour. The bank
mints nothing and the chandler keeps its spread.

241 suites, 1,817 checks, 0 failed.


## 2026-09-20 — Two dice, and a life lived before the berth

Traveller's resolution grammar (`sim/checks.py`): six characteristics, a
seven-rung difficulty ladder, −3 for untrained, and `2d6 + skill +
characteristic DM + difficulty DM ≥ 8`, with the Effect — a check answers *by
how much*. `chance` is an exact count over thirty-six outcomes and the same
arithmetic the roll uses, so a screen can quote odds it will honour.

And the life behind every officer (`data/careers.py`, `sim/lifepath.py`):
eight careers of the Verge, four-year terms, survival and advancement throws,
skills that deepen, mishaps that end a career, ageing after thirty-four, and
what they mustered out with. Derived from what the chronicle already knows,
so nothing is saved and an officer from an old save has a history at once. It
reads on the Ship screen's Crew tab.

240 suites, 1,809 checks, 0 failed.


## 2026-09-20 — A world in eight characters

*Traveller*'s Universal World Profile, laid over the Verge. Every world now
reads as eight characteristics — starport, size, atmosphere, hydrographics,
population, government, law level, tech level — with the trade
classifications they earn, the bases and a travel advisory, on the System
screen under the body's own facts. It is **derived, never stored**: the
sector already knew all of it in eight different places.

The obvious next step, Traveller's speculative trade, was built and backed
out in the same pass: multiplying the counter's quotes by a world's
classifications re-balances an economy a dozen checks are tuned against. It
needs a measured balance pass, and `seedfall/IMPROVEMENTS.md` now carries the
Traveller programme in the order it should land.

239 suites, 1,801 checks, 0 failed.


## 2026-09-20 — A gun with hands on it

SEEDFALL has had guns since the first engagement and never a gunner. There
is now a real-time turret layer at the other grain from `sim/combat`: you sit
behind one of the ship's mountings, look down the bore, traverse it by hand,
lead a crossing target and fire. The HUD's vocabulary is FreeSpace 2's —
reticle and separate lead pip, target monitor with the target's subsystems,
contact ball, a directive list that ticks itself off — and the ten training
drills are the situations the game can actually put a captain in: attacking
ships, a station, shore batteries, mining and planetary works, point defence,
a defensive action, and a fleet action with friends in your arc.

Contacts have **places that can be shot off them**: silence a hub by taking
its turrets, blind it by taking its mast, cripple a corvette by taking its
drive. A gun manned during a real engagement banks what it does back into
that battle. New `Gunnery` screen on the rail (`g`).

238 suites, 1,794 checks, 0 failed.


## 2026-09-20 — The nightly, made green

The push workflow runs the fast suites and was green; the nightly runs every
suite and had **never** passed, failing the same two checks on all three
Pythons since the day it was written. Neither was the game.

The bridge did not fit its own window and never had — it cleared the check
here by 19 px of a straddled row, and on a runner, whose only font package is
`fonts-dejavu-core`, the taller serif put two controls under the fold and cut
the trigger short. The camera now gives up whatever the controls need
(`ui/pilot_panels.fit_feed`, through a new `Pane.fit` hook), "Fly at …" moved
to the column this file's own rule puts flying in, and the check is both
stricter and run twice — on this machine's fonts and on the runner's.

And `Bridge.stop` closed its socket while the serving thread was inside
`accept`, which on Linux leaves the port listening; it now waits for the
thread, so when `stop` returns the port is gone on either kernel.

237 suites, 1,782 checks, 0 failed.


## 2026-09-19 — What a contact looks like

SEEDFALL modelled collisions in detail and showed almost none of it.
Photographed first: a hull flown into a Fleet Hub at 55 m/s — 1,134 points
off a hull that has 336 — changed nothing on the screen but one line of
nine-point italic type, and the structure was not even in the camera the
player was looking at.

There is now an effects layer between the fact and the picture:
`sim/shock.py` reads a resolved flight and says what passed between the two
hulls; `ui/effects.py` keeps the timeline; `ui/effect_marks.py` and
`ui/effect_paint.py` draw it; `ui/effect_clock.py` runs the animation on a
timer of its own, because a collision stops the flight clock. Crashes,
scrapes, groundings, berthings, orbits, a boom taking the ship, a cut, point
defence and a volley you take in combat are all drawn now, off figures the
sim already had. The conn turns to the camera that saw it. The game's own
account is in [`seedfall/SESSION_LOG.md`](seedfall/SESSION_LOG.md).

237 suites, 1,782 checks, 0 failed.


## 2026-09-19 — A launcher, `--help`, and a new game that keeps the old one

- **`play.py`** in the project folder starts the game from any directory
  (`python3 play.py`, or `./play.py`) and passes every flag through.
- **`--help`**: the flags now live in `seedfall/core/cli.py` (argparse),
  parsed before Qt loads. `--help` prints every option and where the save
  is, and a mistyped flag exits 2 with the flag named. Before this, `--help`
  started the game and unknown flags were silently ignored.
- **Found while writing the help:** `--new`, and the title screen's "New
  chronicle", deleted the chronicle in play (`.bak` too) with no question.
  Both now go through `core/loading.begin_new`, which first keeps it as a
  slot called "Set aside <date>" that the title screen lists, and says so in
  the new chronicle's log.
- The new `cli` suite: 236 suites, 1,769 checks, 0 failed.


## 2026-09-18 — The review implemented, and ten new systems

Every one of the 60 findings was fixed, and ten innovations were designed
and built into SEEDFALL. [`reviews/2026-09-17/STATUS.md`](reviews/2026-09-17/STATUS.md)
maps each item to its fix and the suite that pins it; `PLAN.md`,
`innovations/` and `changes/` beside it hold the plan, the designs and each
work stream's merge notes. The game's own account is in
[`seedfall/SESSION_LOG.md`](seedfall/SESSION_LOG.md).

- **Saves:** any save now resumes in a fresh process, including a copy of the
  real 5 August save. A headless probe overwrote that save during the work;
  it was restored byte-for-byte from its `.bak`, and headless processes now
  save elsewhere.
- **The game:**
  - ten new systems: the Far Reaches, the Kith, stellar phenomena, nemeses,
    the living hull, freight lines, the Assembly, officer arcs, renown, and
    sound;
  - the exploits are closed, every screen fits 1040×680, and every file is
    under 500 lines.
- **Tooling:**
  - a parallel test runner (17 min → about 200 s);
  - `pyproject.toml`;
  - a CI workflow, green on Python 3.10–3.12 from its third run (the first
    two found a missing scipy, lint errors and two checks tied to this
    machine);
  - ruff;
  - generated package maps, and the `exports` and `maps` suites.
- **Documents:** all 13 corrected. `calcs/` recomputes 291 tagged numbers,
  and `viewer/links.py` audits every link. **All 13 need republishing.**
- **Final play-test:** an independent agent played the first hour and
  three two-year strategies. It found eleven defects, and nine were fixed
  with checks, including envoy deals that minted money and a test import
  that deleted a caller's save. `STATUS.md` has the table.
- **Final gate:** 235 suites, 1,763 checks, 0 failed. The viewer, calcs,
  `sim` and `models3d` checks pass.
- **Nothing was committed.**


## 2026-09-17 — Whole-project review

A read-only review of every part of the repo: engine, UI, tests and tooling,
gameplay (scripted play over the bridge), the 13 GESTALT documents, viewer,
`sim/`, `models3d/` and repo upkeep. There are 60 findings, ranked P0–P2, in
[`reviews/2026-09-17/`](reviews/2026-09-17/README.md). The suite was green at
the start: 199 suites, 1,482 checks, 17 min 10 s.

Headline: **Resume fails in a fresh process for every save.** The save
registry is filled only by import side effects, so `python -m seedfall` can't
read `Choices` or `Envoy`. This was confirmed against a copy of the real
`~/.seedfall/save.json`. No test crosses a process boundary, which is why a
green suite missed it. The next largest: per-process id counters (the
flagship can vanish after a reload), sub-day clock steps running the daily
tick, all 15 screen keys dead (ambiguous shortcut), a Lineage ending on day
21, and the tripwire suite rewriting source files (it left four at mode 600;
restored). No code was changed.


## Earlier

Everything before 2026-09 is archived, unchanged and in order, under
[`logs/`](logs/README.md). The game's own chronicle of passes is
[`seedfall/SESSION_LOG.md`](seedfall/SESSION_LOG.md).
