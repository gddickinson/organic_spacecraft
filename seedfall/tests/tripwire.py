"""Which tuning constants are actually protected by a check, and which are not.

Three cycles running I have written a check that reads the very constant whose
effect it claims to test — `after_cap == before_cap - CAP_PER_LEAN`,
`total - room >= round(total * MIN_WATCH)` — and then watched it pass with
that constant set to zero. Each time I caught it by hand, by trying to break
the thing on purpose. Each time I said I would watch for it.

Relying on remembering is not a method. This is: **change a constant and see
whether anything notices.**

A constant that can be doubled, halved or zeroed without a single check
failing is in one of three states, and all three are worth knowing about:

- **Dead.** Nothing reads it. The game has had several of these — a colony's
  sensor bonus that no code path consumed, a `demand` mapping that did not
  exist on the object it was read from.
- **Tautologically checked.** Something reads it, and so does the assertion,
  so they move together and the check cannot fail. My habit.
- **Genuinely unpinned.** Real, load-bearing, and nothing holds it in place —
  so the next person to tune it finds out from a player.

This is slow — a suite run per constant — so it is a tool rather than a check.
Run it directly:

    python3 -m seedfall.tests.tripwire            # everything
    python3 -m seedfall.tests.tripwire dormancy   # one module

It reports only what survives, because that is the list worth acting on.
"""

from __future__ import annotations

import ast
import os
import pathlib
import subprocess
import sys

#: Every suite except the slow ones and the ones that need a window. Derived
#: from the canonical list rather than copied: this module kept its own, it
#: went stale the moment a suite was added, and the constants that suite
#: protected looked unprotected because nothing here was running it. My own
#: `SIGNING_FEE` check was reported unprotected for exactly that reason.
#:
#: `tutorial` was in here for building a window, and that cost it its fast path:
#: `SETTLED_IN_DAYS` looked unprotected because the only suite that could speak
#: for it was excluded. It sets the offscreen platform itself and the whole
#: suite is two seconds, so needing a window was never the reason to skip it —
#: being expensive is. Zero, half and double are all caught.
SLOW = {"chronicle", "verbs", "ui", "resume", "efficacy", "balance",
        "instruments", "bridge", "manual", "voices", "play",
        "layers", "plans", "xeno", "dig", "reachable", "tuning"}


def _suites() -> list:
    from .__main__ import ALL_SUITES
    return [name for name in ALL_SUITES if name not in SLOW]


SUITES = _suites()

#: Constants that are deliberately structural rather than tuning — changing
#: them is a different kind of edit and the sweep only adds noise.
SKIP = {"MASK", "SAVE_VERSION", "KEEP", "MAX_BAND", "ARENA"}

ROOT = pathlib.Path(__file__).resolve().parent.parent.parent


def constants(only: str = "") -> list:
    """Every module-level numeric constant, as (path, name, value)."""
    out = []
    for folder in ("data", "sim", "core"):
        for path in sorted((ROOT / "seedfall" / folder).glob("*.py")):
            if only and only not in path.stem:
                continue
            tree = ast.parse(path.read_text())
            for node in tree.body:
                if not isinstance(node, ast.Assign) or len(node.targets) != 1:
                    continue
                target = node.targets[0]
                if not isinstance(target, ast.Name) or not target.id.isupper():
                    continue
                if target.id in SKIP:
                    continue
                value = node.value
                # **A negative literal is not an `ast.Constant`.** `-60.0`
                # parses as `UnaryOp(op=USub, operand=Constant(60.0))`, so for
                # as long as this matched only `ast.Constant` every negative
                # constant in the codebase was skipped in silence. Measured
                # when it was found: 422 swept, **14 invisible**, among them
                # `clearance.WELCOME_AT` (whether a quay opens a hatch to
                # you), `grudge.COLD_SHOULDER` and `allegiance.IMPLACABLE`
                # (whether a power will deal with you at all) and
                # `war.WAR_AT` (whether two powers are fighting). Task #60 is
                # titled "all 153 tuning constants measured, none
                # unprotected"; that was true only of the ones this could see.
                sign = 1
                if isinstance(value, ast.UnaryOp) and \
                        isinstance(value.op, ast.USub):
                    sign, value = -1, value.operand
                if isinstance(value, ast.Constant) and \
                        isinstance(value.value, (int, float)) and \
                        not isinstance(value.value, bool):
                    out.append((path, target.id, sign * value.value))
    return out


def variants(value):
    """Degenerate values worth trying, most disruptive first."""
    tries = []
    if value != 0:
        tries.append(0 if isinstance(value, int) else 0.0)
    tries.append(value * 2 if value else 1)
    if value:
        tries.append(value / 2 if isinstance(value, float) else max(1, value // 2))
    return tries


def rewrite(path: pathlib.Path, name: str, new) -> str:
    """Set a constant, returning the original text for restoring."""
    original = path.read_text()
    out, done = [], False
    for line in original.splitlines(keepends=True):
        stripped = line.lstrip()
        if not done and stripped.startswith(f"{name} ") and "=" in line:
            indent = line[:len(line) - len(stripped)]
            out.append(f"{indent}{name} = {new!r}\n")
            done = True
        else:
            out.append(line)
    if not done:
        return ""
    path.write_text("".join(out))
    return original


#: A clean run of the subset takes about ten seconds. Sixty is generous, and
#: bounded: a mutated constant can send the sim into a very slow path — an
#: unreachable loop bound, a zero step — and a generous timeout turns one bad
#: value into a quarter of an hour of nothing.
LIMIT = 60


#: Suites named after a module, so a constant is tried against its own
#: neighbourhood first. Two stages, because the broad set costs thirty-six
#: seconds and most constants are caught by their own suite in two: run the
#: cheap one, and only pay for the wide one on the survivors. A single-stage
#: sweep of everything is three hours and finds the same answer.
#: One entry per module, and **exactly** one: six modules had two, and in a
#: dict literal the later wins silently. `stations` was the costly one — its
#: broad entry (routing, orderplan, seatwork) sat above a second entry reading
#: just `("gunnery",)`, so every constant the three seats own had been swept
#: against one suite that does not name them. `mounts` lost `lopsided` and
#: `rumours` lost `missions` the same way. `tests/test_harness_guard.py` now
#: refuses a duplicate, because this is not the sort of thing anyone sees by
#: reading a hundred-line table.
KIN = {
    "dormancy": ("dormancy",), "lineages": ("time",), "crossings": ("time",),
    "officials": ("counter", "officials"),
    "approaches": ("envoy", "approach"), "approach": ("envoy", "approach"),
    "surveys": ("surveys",), "survey": ("charting", "surveys"),
    "anchorage": ("anchorage",),
    "doctrine": ("doctrine",), "firing": ("firing", "gunnery"),
    "tactical": ("gunnery", "combat"), "combat": ("seatwork", "combat", "gunnery"),
    "abilities": ("abilities", "combat"),
    "encounters": ("magazine", "readiness"),
    "impulse": ("impulse", "conn"),
    "knock": ("knock",),
    "moorings": ("moorings", "conn"),
    "clearance": ("clearance", "berthing"),
    "freeflight": ("freeflight", "conn"),
    "berths3d": ("standoff", "silhouettes"),
    "works3d": ("works3d",),
    "robots": ("robots",),
    "robots3d": ("robots3d",),
    "bays": ("bay", "berthing"),
    "control": ("control", "berthing"),
    "forcing": ("forcing", "control", "berthing"),
    "landing": ("setdown", "landing"),
    "interdiction": ("interdiction",),
    "relics3d": ("relics3d",),
    "fleets": ("fleets", "control"),
    "armada": ("armada", "fleets"),
    "war": ("war", "armada"),
    "piracy": ("piracy", "traffic", "fence"),
    "life3d": ("life3d",),
    "parts3d": ("parts3d",),
    "readiness": ("readiness",),
    "parley": ("parley", "combat"),
    "stations": ("routing", "orderplan", "seatwork", "turnplan", "gunnery"),
    "damage": ("thermal_doors", "combat"), "contraband": ("customs",),
    "customs": ("customs", "fence"), "diplomacy": ("politics",),
    "grudge": ("grudges",), "colonies": ("works", "founding"),
    "works": ("works",), "mining": ("mining",), "research": ("bench",),
    "inquiry": ("evidence", "bench"), "flight": ("helm", "flight", "burns"),
    "contracts": ("postings", "missions", "cargo"),
    "chains": ("missions",),
    "expedition": ("landing", "ground", "wayhome"), "weather": ("ground",),
    "territory": ("territory", "levy"), "allegiance": ("allegiance",),
    "charts": ("charting", "charts"), "notes": ("notes",),
    "freight": ("freight",),
    "market": ("trade",), "economy": ("trade",), "commodities": ("trade",),
    "loyalty": ("conviction", "crew"), "convictions": ("conviction", "crew"),
    "crew": ("conviction", "crew"),
    "lifespan": ("time",), "upkeep": ("time",), "clock": ("time", "ticks"),
    "bloom": ("bloom",),
    "threat": ("bloom",), "ventures": ("politics",),
    "intel": ("explore",), "transit": ("transit",), "shipyard": ("design",),

    # Modules that had no entry at all and so paid the wide run for every
    # constant they own — twenty-one of them, including `ship`, which holds
    # the thermal rule the whole game reads.
    "aftermath": ("aftermath",), "assessment": ("assessment",),
    "colony": ("grants", "founding", "swarm"),
    "minigames": ("approaching", "approach"),
    "plans": ("picture",), "ship": ("thermal_doors", "thermal", "feedstock"),
    "shocks": ("trade",), "tech": ("evidence", "bench"),
    "trade": ("counter", "trade"), "orders": ("orders",),
    "legacy": ("legacy",), "beginning": ("beginnings",),
    "watches": ("transit",),
    "services": ("trade",),

    # The conn and the plotting board. Both own a lot of tuning — thruster
    # impulses, the orbit band, the horizon — and all of it is answered by
    # the one suite, so neither should ever pay for the wide run.
    "conn": ("conn",), "autopilot": ("conn",), "track": ("conn",),
    "viewport": ("cameras",), "berthing": ("berthing", "conn"),
    "orbits": ("orbits", "conn", "berthing", "climbs"),
    "outcome": ("orbits", "conn", "berthing"), "targets": ("conn", "berthing"),
    "thrusters": ("thrusters",), "attitude": ("thrusters", "conn"),
    "weave": ("weave",), "gates": ("weave",),
    "instruments": ("conn",), "models3d": ("cameras",),
    "render3d": ("cameras",), "gunfire": ("gunfire",),
    "sky": ("cameras", "worlds"), "worlds3d": ("worlds",),
    "starclasses": ("worlds", "orbits"),
    "programmes": ("programmes",),
    "declared": ("declared",),
    "consorts": ("combat", "screening", "company"),
    "mounts": ("thrusters", "lopsided"),
    "pilot": ("pilot", "conn", "climbs"),
    "gunnery": ("volley", "gunboard", "gunnery"),
    "battle3d": ("gunfire",),
    "burnplan": ("thrusters", "helm"),
    "exchequer": ("exchequer", "politics"),
    "industry": ("industry", "exchequer"),
    "rumours": ("provenance", "explore", "missions"),
    "memory": ("provenance", "grudges"),
    "options": ("options",),
    "traffic": ("traffic", "mesh"),
    "lifeforms": ("biology", "surveys"),
    "biology": ("biology",),
    "settlements": ("settlement", "exchequer"),
    "settlement": ("settlement",),
    "tutorial": ("tutorial",),
    "wharfage": ("wharfage", "counter", "accord"),
    "accord": ("accord", "wharfage"),
    "turnplan": ("turnplan", "orderplan"),
    "surfaces": ("surfaces", "worlds", "lighting"),
    "hulls3d": ("hullshapes", "combat"),
    "stars3d": ("starlight", "cameras"),
    "ships3d": ("silhouettes",),          # berths3d is above, with "standoff"
}


def _run(suites) -> bool:
    """Run these suites in a child that never writes or reads stale bytecode.

    Without `PYTHONDONTWRITEBYTECODE` this tool silently poisons itself. It
    rewrites a constant, Python compiles a `.pyc` from the mutated source, the
    constant is restored — and the next process is still served the cached
    bytecode, because the restore does not always move the mtime far enough to
    invalidate it. I found this the way it deserved to be found: a check
    crashed with `PER_LOSS` reading 0.0 at runtime and 9.0 on disk.

    Every result from a sweep without this is worthless in both directions —
    a mutation that outlived its restore, or a restore that never took.
    """
    env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1")
    done = subprocess.run(
        [sys.executable, "-B", "-m", "seedfall.tests", *suites],
        capture_output=True, text=True, cwd=ROOT, timeout=LIMIT, env=env)
    return done.returncode == 0


_CLEAN: dict = {}


def completes(suites) -> bool:
    """Does this set finish inside `LIMIT` with **nothing** mutated?

    **A hang only means something if the same run does not hang anyway**, and
    for the broad set it does. Measured: `SUITES` is 155 suites and takes about
    25 minutes since `core/clock.MAX_STEP` became 1 — the note on `KIN` saying
    "the broad set costs thirty-six seconds" was written before that. So the
    second stage has been timing out on every constant, mutated or not, since
    #116 landed.

    That would be merely useless if a timeout were treated as no information.
    It was treated as *proof*: "a hang is a very loud notice". So every
    constant its own suite failed to catch has been reported protected on the
    strength of a stopwatch. Calibrated once per set and cached, because the
    answer cannot change inside a run.
    """
    key = tuple(suites)
    if key not in _CLEAN:
        try:
            _run(suites)
            _CLEAN[key] = True
        except subprocess.TimeoutExpired:
            _CLEAN[key] = False
    return _CLEAN[key]


def noticed(suites) -> bool:
    """Did any of these object to what is on disk right now?

    **The one door for that question**, and there were two: `suite_passes` and
    the `try_value` closure inside `main` each had their own `try/except`
    around `_run`, and only one of them could be reached by a check. A
    mutation restoring the old "a hang is a very loud notice" in the other
    left every check green.
    """
    try:
        return not _run(suites)
    except subprocess.TimeoutExpired:
        return completes(suites)


def suite_passes(module: str = "") -> bool:
    """True if nothing noticed.

    A hang counts as noticed only where `completes` says the set finishes when
    unmutated — otherwise the stopwatch is measuring the suite, not the
    constant, and a stage that cannot finish clean does not get a vote.
    """
    near = KIN.get(module)
    if near and noticed(near):
        return False
    if not completes(SUITES):
        return True                     # the broad stage abstains
    return not noticed(SUITES)


def main(argv: list) -> int:
    """Sweep, restoring the tree whatever happens.

    A killed sweep used to leave the constant it was holding mutated — I
    stopped one mid-trial and left `QUIET_DAYS = 0` sitting in the working
    tree. A tool that edits source has to put it back on the way out, not
    only on the happy path.
    """
    only = argv[0] if argv else ""
    found = constants(only)
    # Any bytecode left over from an earlier run may have been compiled from
    # a mutated source. Start clean.
    for cache in ROOT.rglob("__pycache__"):
        for stale in cache.glob("*.pyc"):
            stale.unlink(missing_ok=True)

    print(f"sweeping {len(found)} constants "
          f"({'module ' + only if only else 'every module'})\n", flush=True)

    import atexit
    import signal
    holding: dict = {}

    def restore(*_args):
        for where, text in list(holding.items()):
            pathlib.Path(where).write_text(text)
        holding.clear()

    atexit.register(restore)
    for sig in (signal.SIGINT, signal.SIGTERM):
        signal.signal(sig, lambda *_a: (restore(), sys.exit(130)))

    survived, distant = [], []
    for index, (path, name, value) in enumerate(found, 1):
        print(f".. [{index:3d}/{len(found)}] {path.stem}.{name}", flush=True)
        noticed = False

        def try_value(candidate, suites) -> bool:
            """Set the constant, run those suites, always put it back."""
            original = rewrite(path, name, candidate)
            if not original:
                return False
            holding[str(path)] = original
            try:
                # Through `noticed`, the one door for "did anything object".
                # This carried its own copy of the try/except, and no check
                # could reach it — so a mutation restoring "a hang is a very
                # loud notice" here left the whole suite green.
                return noticed(suites)
            finally:
                path.write_text(original)
                holding.pop(str(path), None)

        # Stage one: every variant against the constant's own neighbourhood.
        # Two seconds a go, and it catches most of them.
        near = KIN.get(path.stem)
        caught_by = ""
        if near:
            for candidate in variants(value):
                if try_value(candidate, near):
                    noticed, caught_by = True, ", ".join(near)
                    break

        # Stage two, only for survivors: the wide set, and only the single
        # most disruptive value. Thirty-six seconds is worth paying once to
        # confirm a finding; it is not worth paying three times to reconfirm.
        if not noticed:
            noticed = try_value(variants(value)[0], SUITES)
            if noticed:
                caught_by = "the wide set only"

        flag = "  " if noticed else "??"
        print(f"{flag} [{index:3d}/{len(found)}] {path.stem}.{name} = {value!r}"
              + (f"   — {caught_by}" if noticed else "   — nothing noticed"),
              flush=True)
        if not noticed:
            survived.append((path.stem, name, value))
        elif not near or caught_by == "the wide set only":
            # Protected, but by nothing that names its subject. Worth knowing:
            # it is held up by a suite that happened to walk past, which is a
            # thinner thread than a check written for it.
            distant.append((path.stem, name, value))

    print(f"\n{len(survived)} of {len(found)} constants are unprotected:")
    for module, name, value in survived:
        print(f"    {module}.{name} = {value!r}")
    if distant:
        print(f"\n{len(distant)} are protected only by a suite that does not "
              "name their subject:")
        for module, name, value in distant:
            print(f"    {module}.{name} = {value!r}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
