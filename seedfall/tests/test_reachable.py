"""Nothing computed that nothing consumes.

Three times running a feature shipped a number the game never read. A levy
venture incremented a counter nothing consulted. `death_reason` was recorded on
every death and never shown. The Bloom's growth multiplier was derived from its
responses and used by nobody, so it would have "answered" a provoked captain by
printing a line and changing nothing at all.

Two of those were caught by the `Game`-fields check in `test_orders.py`, which
walks persistent state. This is the other half: a function that returns a value
and is called from nowhere is a feature that does not exist, however carefully
it is written.

Finding it also turned up two genuine holes rather than dead code — treaties
that bought no trade advantage despite the function promising one, and instars
that could never be killed because nothing called `kill_instar`.

**Calls resolve to the module they were defined in.** They did not: names were
matched bare, so a `mining.summary` nobody calls was masked by any other
module's `summary` being called — and across the package that hid **eleven**
functions, not the one the earlier note guessed at. Six of them are aggregation
readouts written "for the panel" that no panel ever opened.

Resolving properly means following four paths a naive version gets wrong, each
of which cost a round of false alarms before it was handled:

- **A call where the function lives.** `BERTHS = {"quay": quay(), ...}` inside
  `berths3d.py` is a use. Missing this alone reported 220 false orphans.
- **An aliased import.** `from .life_panel import build as life_catalogue`
  means a call to `life_catalogue()` is `life_panel.build`, not
  `life_panel.life_catalogue`.
- **A re-export.** `chassis_data.accepts_family` is `hull_types.accepts_family`,
  reached through a module that imported it.
- **A reference that is not a call.** A function passed as a callback or put in
  a dispatch table is consumed without ever being written `f()`.

And a **decorated** function is consumed by whatever its decorator registers it
with: `@verb` puts the bridge's vocabulary in `protocol.VERBS`, `@register`
puts a dataclass in the save codec. Nobody decorates a function for nothing.

Anything the resolver cannot place — a call on a parameter, `ops.enemy_turn`;
a name reached through `getattr`; a string in a table — stays in a loose bucket
that credits every module. The check under-reports rather than crying wolf.

**Except a file's own locals, and that gap had a live example.**
`control.provoked` was written the day the approach ladder landed and read by
nobody at all, and this file passed on it for weeks — because `sim/threat.py`
holds a local variable spelled `provoked`, and a bare name credited every
module with a function of that name. Reading a local is not a reference to
somebody else's function; it is a different word that happens to be spelled
the same.

The exclusion is **per file** and not across the tree, which matters: dropping
a name everywhere it is bound anywhere would lose genuine bare-name references,
because a function passed as a callback in one module is often a loop variable
in another. Measured when it was added, the loose bucket fell from 23,628 names
to 20,894 and **not one function changed verdict** — it cost nothing and closed
the hole. `_scan` is split out so the regression check can drive the same
analysis over synthetic sources, and it is pinned in both directions: loosen it
and a local credits again, tighten it further and a dispatch table stops
counting.

A function called only from a readout still passes: it is consumed, even if the
readout is never opened.
"""

from __future__ import annotations

import ast
import pathlib

from .harness import Suite

ROOT = pathlib.Path(__file__).resolve().parents[1]

#: Entry points the package offers rather than consumes. A `main`, a save-codec
#: hook or a suite runner is called from outside the tree or by the framework.
EXPORTED = {"main", "run", "encode", "decode", "read", "write", "exists",
            "clear_save", "report", "check", "build_app"}

#: Deliberately kept, with the reason. Anything added here needs one.
#:
#: These are what precise resolution found on the day it was written —
#: every one a readout with no reader, invisible to bare-name matching because
#: some *other* module's `summary`, `line`, `note` or `preview` is called.
#: They are recorded rather than quietly allowed: each needs a decision about
#: whether the screen that wants it should exist, and that is a piece of work
#: on its own rather than a row of snap judgements at the end of a long day.
#:
#: One has since gone: `bays.line` said what a structure you fly into tells an
#: approaching hull, and that belonged inside `clearance.line` — the one door a
#: structure already speaks through — rather than beside it.
ALLOWED: dict[str, str] = {
    "berthing.preview": "what committing would cost, in `commit`'s own terms; "
                        "the conn shows its own figures instead",
    "chains.summary": "counts of chains live, done and failed — no screen asks",
    "contracts.summary": "one contract as a line; the board formats its own",
    "diplomacy.summary": "treaties and the whole relations matrix, unread",
    "grudge.summary": "every power, what it feels and why — unread",
    "mining.summary": "seams reachable and out of reach; the panel walks them "
                      "itself",
    "programmes.summary": "what the bench has been for — unread",
    "sky.note": "one line naming what is in the sky — unread",
    "transit.summary": "a transit's spend against its plan — unread",
    "ventures.summary": "ventures live, resolved, backed and opposed — unread",
}


def _hands_back_a_value(node: ast.FunctionDef) -> bool:
    """Whether this function returns anything worth consuming.

    `return None` is a control-flow return, not a result — counting it was the
    first thing the self-check caught, which is the entire argument for having
    written the self-check.
    """
    for sub in ast.walk(node):
        if not isinstance(sub, ast.Return) or sub.value is None:
            continue
        if isinstance(sub.value, ast.Constant) and sub.value.value is None:
            continue
        return True
    return False


def _public_functions() -> dict[tuple, str]:
    """Every public module-level function, keyed by where it was defined.

    Restricting this to value-returning functions missed `kill_instar`, which
    mutates and returns nothing — and which nothing called, so a roaming Bloom
    mass could never be destroyed. A function nobody calls is a feature that
    does not exist regardless of its return type.

    A **decorated** function is skipped: whatever the decorator registers it
    with is the consumer. `@verb` is the bridge's vocabulary and `@register`
    the save codec, and both dispatch by name from a table.
    """
    found: dict[tuple, str] = {}
    for path in sorted(ROOT.rglob("*.py")):
        if path.parent.name == "tests":
            continue
        tree = ast.parse(path.read_text())
        for node in tree.body:
            if not isinstance(node, ast.FunctionDef):
                continue
            if node.name.startswith("_") or node.name in EXPORTED:
                continue
            if node.decorator_list:
                continue
            found[(path.stem, node.name)] = f"{path.stem}.{node.name}"
    return found


def _imports(tree) -> tuple[dict, dict]:
    """What the names in one file refer to.

    Returns (module aliases, name imports). `from ..sim import robots as r`
    puts `r` in the first; `from .life_panel import build as shown` puts
    `shown -> (life_panel, build)` in the second — **the original name**, which
    is the one a naive version gets wrong.
    """
    mods: dict[str, str] = {}
    names: dict[str, tuple] = {}
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            base = (node.module or "").split(".")[-1]
            for alias in node.names:
                mods[alias.asname or alias.name] = alias.name
                if base:
                    names[alias.asname or alias.name] = (base, alias.name)
        elif isinstance(node, ast.Import):
            for alias in node.names:
                stem = alias.name.split(".")[-1]
                mods[alias.asname or stem] = stem
    return mods, names


def _reexports() -> dict:
    """Where a re-exported name really lives.

    `chassis.py` does `from .hull_types import accepts_family`, so a call to
    `chassis_data.accepts_family` is a use of `hull_types.accepts_family`.
    """
    out: dict = {}
    for path in sorted(ROOT.rglob("*.py")):
        if path.parent.name == "tests":
            continue
        for node in ast.walk(ast.parse(path.read_text())):
            if isinstance(node, ast.ImportFrom) and node.module:
                base = node.module.split(".")[-1]
                for alias in node.names:
                    if alias.asname is None:
                        out[(path.stem, alias.name)] = (base, alias.name)
    return out


def _bound(tree) -> set:
    """Every name this file binds for itself: locals, parameters, loop vars.

    **The hole this closes had a live example.** `control.provoked` was written
    the day the approach ladder landed and read by nobody at all, and this
    check passed on it for weeks — because `sim/threat.py` contains a local
    variable that happens to be spelled `provoked`, and a bare name credited
    *every* module with a function of that name. Reading a local is not a
    reference to somebody else's function; it is a different thing wearing the
    same word.

    Per file rather than across the tree, which matters: excluding a name
    everywhere it is bound *anywhere* would drop genuine bare-name references —
    a function passed as a callback in one module while another module happens
    to use that word for a loop variable. The question is only ever "is this
    particular name, in this particular file, a local?".
    """
    out = {n.id for n in ast.walk(tree)
           if isinstance(n, ast.Name) and isinstance(n.ctx, (ast.Store, ast.Del))}
    out |= {a.arg for a in ast.walk(tree) if isinstance(a, ast.arg)}
    return out


def _scan(stem: str, tree, mine: set) -> tuple[set, set]:
    """One file's uses, as (resolved to a module, unplaceable bare names)."""
    mods, names = _imports(tree)
    local = _bound(tree) - mine - set(names)
    exact: set = set()
    loose: set = set()
    for node in ast.walk(tree):
        # A *reference* is a use: a callback or a dispatch-table entry is
        # consumed without ever being written `f()`.
        if isinstance(node, ast.Attribute) and isinstance(node.value, ast.Name):
            owner = mods.get(node.value.id)
            (exact.add((owner, node.attr)) if owner
             else loose.add(node.attr))
        elif isinstance(node, ast.Attribute):
            loose.add(node.attr)
        elif isinstance(node, ast.Name):
            if node.id in mine:
                exact.add((stem, node.id))   # used where it lives
            elif node.id in names:
                exact.add(names[node.id])
            elif node.id not in local:
                loose.add(node.id)
        # `__all__` entries, getattr("name") and dispatch keys count.
        elif isinstance(node, ast.Constant) and isinstance(node.value, str):
            loose.add(node.value)
    return exact, loose


def _used(defined: dict) -> tuple[set, set]:
    """What is used, as (resolved to a module, unplaceable bare names).

    Tests count as consumers: a function driven only by the suite is at least
    being exercised deliberately, which is a different mistake from one nobody
    calls at all.

    Anything that cannot be placed — a call on a parameter, a name reached
    through `getattr`, a string in a dispatch table — goes in the loose set and
    credits **every** module with that name. The check under-reports rather
    than crying wolf.

    What it no longer counts is a file's own locals: see `_bound`. Measured
    when that was added, the loose set fell from 23,628 names to 20,894 and
    **not one function changed verdict** — so it cost nothing and closed the
    gap that had hidden `control.provoked`.
    """
    here: dict[str, set] = {}
    for module, name in defined:
        here.setdefault(module, set()).add(name)

    exact: set = set()
    loose: set = set()
    for path in ROOT.rglob("*.py"):
        one, two = _scan(path.stem, ast.parse(path.read_text()),
                         here.get(path.stem, set()))
        exact |= one
        loose |= two

    via = _reexports()
    for _ in range(4):                       # chains of re-exports are short
        grown = {via[key] for key in list(exact) if key in via}
        if grown <= exact:
            break
        exact |= grown
    return exact, loose


def run(suite: Suite) -> None:
    check = suite.check

    @check("nothing in the package is written and never called")
    def _():
        # What this does and does not catch, stated plainly: it finds a public
        # function nobody calls *at all*. It will not catch one that is called
        # only from a readout or only by this suite — the Bloom's growth
        # multiplier was consumed by `summary()` from the day it was written
        # while contributing nothing to the simulation, and this check would
        # have passed on it. Being reachable is a floor, not a guarantee.
        defined = _public_functions()
        exact, loose = _used(defined)
        orphans = sorted(
            label for key, label in defined.items()
            if key not in exact and key[1] not in loose and label not in ALLOWED)
        assert not orphans, (
            f"{len(orphans)} public function(s) nothing ever calls. Either "
            "wire it into the game or delete it:\n      "
            + "\n      ".join(orphans))
        placed = sum(1 for key in defined if key in exact)
        return (f"{len(defined)} public functions, every one reachable · "
                f"{placed} resolved to the module they were defined in, "
                f"{len(ALLOWED)} readouts recorded as having no reader")

    @check("the check can still see an orphan when there is one")
    def _():
        # A check that cannot fail is worse than no check. Run the same
        # analysis over a synthetic module rather than over the real tree —
        # any literal name used here would otherwise be found *in this file*
        # by the very scan it is testing.
        source = (
            "def gives_nothing():\n    return None\n\n"
            "def gives_something():\n    return 42\n\n"
            "def _private():\n    return 1\n"
        )
        tree = ast.parse(source)
        returning = {n.name for n in tree.body
                     if isinstance(n, ast.FunctionDef)
                     and not n.name.startswith("_")
                     and _hands_back_a_value(n)}
        assert returning == {"gives_something"}, (
            f"the analysis picked out {returning} rather than the one function "
            "that returns a value")
        return "picks out a value-returning public function and ignores the rest"

    @check("a local variable of the same name no longer hides an orphan")
    def _():
        # **This is a regression check with a live example behind it.**
        # `control.provoked` was written the day the approach ladder landed
        # and read by nobody at all, and this file passed on it for weeks —
        # because `sim/threat.py` holds a local variable spelled `provoked`,
        # and a bare name credited every module with a function of that name.
        #
        # Synthetic, like the self-check above: any literal name written here
        # would otherwise be found *in this file* by the very scan being
        # tested.
        owner = ast.parse("def widens_nothing(game):\n    return 1\n")
        mine = {"widens_nothing"}
        # A completely unrelated module that happens to use the word as a
        # local. It calls nothing of anybody's.
        stranger = ast.parse(
            "def elsewhere(game):\n"
            "    widens_nothing = game.count * 2\n"
            "    return widens_nothing + 1\n")

        _own_exact, own_loose = _scan("owner", owner, mine)
        far_exact, far_loose = _scan("stranger", stranger, set())
        assert ("owner", "widens_nothing") not in far_exact
        assert "widens_nothing" not in far_loose, (
            "a local variable still credits a function it has nothing to do "
            "with — the gap that hid control.provoked is open again")
        # And the guard is not simply blind: a genuine bare-name reference,
        # which is what a callback or a dispatch-table entry looks like, is
        # still counted.
        user = ast.parse("TABLE = {'a': widens_nothing}\n")
        _e, real_loose = _scan("user", user, set())
        assert "widens_nothing" in real_loose, (
            "tightening went too far and a callback stopped counting")
        return ("a local read credits nothing; a callback still does — "
                f"{len(own_loose)} names from the owner itself")

    @check("treaties are worth something at a quay")
    def _():
        # Found by the check above: `treaty_bonus` promised that signing made
        # everyone easier to trade with, and was called by nothing, so a treaty
        # bought standing and a label and no trade advantage whatever.
        from ..core.state import new_game
        from ..sim import diplomacy as dip

        game = new_game("treaty-worth")
        game.credits = 500000
        for power in dip.POWERS:
            game.rep[power] = 80
        before = game.ship_stats.trade
        for power in dip.POWERS:
            dip.perform(game, "treaty", power)
        game.recompute()
        assert len(dip.ensure(game).treaties) == len(dip.POWERS), "no treaties signed"
        assert game.ship_stats.trade > before, (
            f"four signed treaties left the trade bonus at {game.ship_stats.trade}")
        return f"trade bonus {before:.2f} → {game.ship_stats.trade:.2f} on four treaties"

    @check("a roaming instar can be fought and killed")
    def _():
        # Also found by the check: `kill_instar` was called from nowhere, so
        # instars seeded systems and ate colonies with no counterplay at all —
        # and the provocation table paid seventy for a kill nobody could make.
        from ..core.rng import RNG
        from ..core.state import new_game
        from ..sim import bloom as bloom_sim
        from ..sim import responses as response_sim

        game = new_game("instar-kill")
        state = bloom_sim.ensure(game)
        state.stage = 3
        for system in game.galaxy.systems[:5]:
            system.bloom = 0.7
        instar = bloom_sim._spawn_instar(game, RNG("k"))
        assert instar is not None, "nothing to detach a mass from"
        state.instars.append(instar)
        instar.system_id = game.location_id

        assert bloom_sim.instar_at(game, game.location_id) is not None, (
            "a mass in your own system is invisible")
        encounter = bloom_sim.engage_instar(game, instar)
        assert encounter["enemy"], "no hull to fight"
        assert encounter["no_parley"], "the mass can be talked to"

        before = response_sim.level(game)
        bloom_sim.kill_instar(game, instar)
        assert instar not in state.instars, "killing it left it on the board"
        assert response_sim.level(game) > before, (
            "killing a mass provoked nothing, though the table pays for it")
        return f"engaged, killed, and worth {response_sim.level(game) - before:.0f} provocation"
