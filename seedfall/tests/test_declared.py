"""Nothing is declared in the tables and then read by nobody.

`test_reachable.py` asks this of functions and has earned its keep repeatedly —
most recently catching `orbits.nearest_height`, written and never wired in. This
asks it of **data**, which turns out to be the richer seam: an audit of every
field on every dataclass in `data/` found eight that nothing anywhere reads, and
several of them had docstrings *asserting* they mattered.

    starclasses.luminosity   "drives how hard the light falls on everything
                              else, which is why an M dwarf's worlds are dim
                              and an A-type's are glaring" — it drove nothing
    starclasses.halo         the corona colour, never drawn
    lineages.boredom         "what that costs in morale" — morale_tick had no
                              lineage term at all
    lineages.time_sense      "the line each one says about a long transit" — a
                              written line no player ever saw
    lessons.skip_if          a tutorial step that should skip itself, and did
                              not
    consorts.shield          1.0 screening, 0.0 flanking — never read
    mounts.axis              "losing one leaves the thrust off-axis", and it
                              did not
    commodities.cat          a category nothing grouped by

A dead field is worse than a missing one. It reads as a feature to anyone
looking at the table, it is quoted in the prose beside it, and it silently
promises behaviour the game does not have.

**Task #88 pointed it at `sim/` and `world/` as well, and the seam was richer
still.** 1,169 fields across the four packages, and the sweep turned up:

    crew.Officer.trait_id    every one of the seven traits in `TRAITS` declares
                             an effect and a magnitude — accuracy, evade, scan,
                             repair, trade, diplomacy, tactical — and not one
                             was ever applied. A Bloom veteran fought exactly
                             like anybody else, and `make_officer` charges 25 a
                             month for the privilege.
    firing.Shot.band_shift   "bands to close (negative) or open (positive) to
                             reach its envelope", on the one board whose job is
                             to say what would fix a mount
    anchorage.extras         a dict written at construction in three places and
                             read only by a test
    territory.Demand.holdings  a stored count of what was at stake, never set
                             and never read, beside a live `holdings_in()`

Two lessons about the guard itself came out of extending it:

- **A write is not a read.** The first version matched `.name` anywhere, so
  `self.x = 1` counted as reading `x`. It now walks the AST and asks for a
  `Load`, which is what "somebody consumes this" actually means.
- **A field only the suite reads is still dead.** `anchorage.extras` was read by
  `test_anchorage` and by nothing in the game, which is why the sweep looks at
  the package with the tests excluded.

The allowlist below carries a **reason per entry**. That distinction matters: an
allowlist used to dodge the work is the anti-pattern this check exists to stop,
and an allowlist with a written reason is how "known, deliberate, and not a
defect" gets said out loud.
"""

from __future__ import annotations

import ast
import pathlib

from .harness import Suite

#: Fields that are legitimately declared and legitimately unread, with why.
#: Anything not in here must be read somewhere, or wired up, or deleted.
ALLOWED: dict[str, str] = {
    "commodities.Commodity.cat":
        "A grouping for a market screen that lists goods in one flat table. "
        "Kept because the categories are the right ones and a grouped board is "
        "wanted; it is display metadata rather than a rule, and nothing in the "
        "sim should ever read it.",
    "lessons.Lesson.skip_if":
        "A watcher naming a thing already true, so a tutorial step can skip "
        "itself. Task #87: the tutorial's step machinery advances on watchers "
        "firing, and skipping needs it to evaluate one at entry instead.",
}


#: The packages swept. `core/` is in because it is where the save and the RNG
#: live and a dead field there would be the quietest of all; it has never had
#: one.
SWEPT = ("data", "sim", "world", "core")


def _fields() -> list[tuple[str, str, int]]:
    """Every field declared on a dataclass in the swept packages."""
    out = []
    for path in sorted(p for sub in SWEPT
                       for p in (pathlib.Path("seedfall") / sub).glob("*.py")):
        tree = ast.parse(path.read_text())
        for node in ast.walk(tree):
            if not isinstance(node, ast.ClassDef):
                continue
            for item in node.body:
                if not isinstance(item, ast.AnnAssign):
                    continue
                if not isinstance(item.target, ast.Name):
                    continue
                name = item.target.id
                if name.startswith("_"):
                    continue
                out.append((f"{path.stem}.{node.name}.{name}", name,
                            item.lineno))
    return out


def _reads() -> tuple[set, set]:
    """Names the package *loads*, and names it uses as an accessor key.

    Two sets rather than one blob of text, because the first version of this
    matched `.name` with a regex and so counted `self.x = 1` as reading `x`. A
    write is not a read: a field that is only ever assigned is exactly as dead
    as one nobody mentions, and three of the findings were of that shape.

    Accessor keys are the narrow escape hatch, and **it was cut too wide the
    first time.** Prose strings never counted — allowing any literal would let
    the word "defiant" in a log line excuse `Colony.defiant` — but crediting any
    dict subscript or `.get("literal")` was nearly as bad, and it hid a real
    dead field for a whole cycle: `diplomacy.DiplomaticState.favours` is read
    nowhere at all, and was excused because `sim/officials.py` keeps a *different*
    per-official favours dict and reaches it as `store["favours"]`. A field
    excused by an unrelated dict that happens to share its name is a guard doing
    nothing.

    So what counts now is a **named accessor reaching a field by string**:
    `getattr`, `hasattr` and `setattr`, and a two-argument `get`/`set_to` whose
    subject comes first and key second — which is exactly the shape of
    `options.get(game, "hints")`, whose body is `getattr(held(game), name)`. A
    bare subscript reaches a dict, not a field, and no longer counts.
    """
    loaded: set = set()
    keyed: set = set()
    for path in sorted(pathlib.Path("seedfall").rglob("*.py")):
        if "tests" in path.parts:
            continue
        tree = ast.parse(path.read_text())
        for node in ast.walk(tree):
            if isinstance(node, ast.Attribute):
                if isinstance(node.ctx, ast.Load):
                    loaded.add(node.attr)
            elif (isinstance(node, ast.Call)
                  and isinstance(node.func, ast.Name)
                  and node.func.id in ("getattr", "hasattr", "setattr")
                  and len(node.args) >= 2
                  and isinstance(node.args[1], ast.Constant)
                  and isinstance(node.args[1].value, str)):
                keyed.add(node.args[1].value)
            elif (isinstance(node, ast.Call)
                  and isinstance(node.func, ast.Attribute)
                  and node.func.attr in ("get", "set_to")
                  and len(node.args) == 2
                  and isinstance(node.args[1], ast.Constant)
                  and isinstance(node.args[1].value, str)):
                keyed.add(node.args[1].value)
    return loaded, keyed


def run(suite: Suite) -> None:
    check = suite.check

    @check("nothing is declared in the tables and read by nobody")
    def _():
        # Loaded anywhere in the package outside the tests, or reached by name
        # as an accessor key. Still deliberately generous — a field sharing a
        # name with an unrelated attribute counts as read, so this under-reports
        # rather than crying wolf.
        #
        # It used to be a regex for `.name`, which counted `self.x = 1` as
        # reading `x`. That is not a read, and three of the findings when this
        # was pointed at `sim/` were of exactly that shape: written once, at
        # construction or on an answer, and consulted by nobody ever after.
        loaded, keyed = _reads()
        fields = _fields()
        assert len(fields) > 1000, len(fields)

        dead = [(full, line) for full, name, line in fields
                if name not in loaded and name not in keyed]

        unexplained = [(f, ln) for f, ln in dead if f not in ALLOWED]
        assert not unexplained, (
            f"{len(unexplained)} field(s) declared in the tables and read by "
            "nothing. Wire each one up, delete it, or add it to ALLOWED with "
            f"a reason: {[f for f, _ln in unexplained]}")

        # And the allowlist has to stay honest in the other direction: an
        # entry for a field that *is* now read is a stale excuse, and an entry
        # for a field that no longer exists is a lie about the tables.
        names = {full for full, _name, _ln in fields}
        stale = [f for f in ALLOWED if f not in names]
        assert not stale, (
            f"ALLOWED names fields that no longer exist: {stale}")
        revived = [f for f in ALLOWED if f not in {d for d, _ln in dead}]
        assert not revived, (
            f"ALLOWED still excuses fields that are now read — delete the "
            f"entry: {revived}")
        for full, why in ALLOWED.items():
            assert len(why) > 60, (
                f"{full} is excused with {len(why)} characters. An allowlist "
                "entry without a real reason is how this check gets defeated.")
        return (f"{len(fields)} fields declared, {len(dead)} unread and every "
                f"one of them explained ({len(ALLOWED)} entries)")

    @check("the check can still see a dead field when there is one")
    def _():
        # The mutation-proofing, in the check itself: a guard that cannot fail
        # is worse than no guard, and this one walks source that could quietly
        # stop matching anything at all.
        loaded, keyed = _reads()
        fields = _fields()
        # A name nothing could possibly read.
        invented = "quinquireme_of_nineveh"
        assert invented not in loaded and invented not in keyed
        # And the machinery finds real fields, with real readers.
        by_name = {name for _full, name, _ln in fields}
        for known in ("radius_km", "cost", "blurb"):
            assert known in by_name, known
            assert known in loaded, known

        # A write is not a read, which is the distinction the AST pass exists
        # for. `heat` is stored all over the sim and also consulted, so a guard
        # counting stores would call anything write-only alive.
        assert "heat" in loaded

        # **And the accessor hatch has to stay narrow.** It was cut wide enough
        # to credit any dict subscript, which excused
        # `diplomacy.DiplomaticState.favours` for a whole cycle: that field was
        # read nowhere, and `sim/officials.py` keeps an unrelated per-official
        # favours dict it reaches as `store["favours"]`. A field excused by a
        # dict that happens to share its name is a guard doing nothing.
        #
        # `hold` and `cargo` are subscripted all over the sim and are also
        # genuine attributes, so they cannot show the difference; a name that is
        # *only* ever a dict key can. `stores` is keyed by commodity id, so
        # "phosphate" is a key and nothing's field.
        assert "phosphate" not in keyed, (
            "a bare dict key is being credited as reading a field; that is how "
            "`DiplomaticState.favours` stayed hidden")
        # What the hatch is *for*: `options.get(game, "hints")` reaches a field
        # by string through a named accessor whose body is a `getattr`.
        for setting in ("hints", "autosave_days", "instrument_ms"):
            assert setting in keyed, (
                f"{setting} is reached only through `options.get` and is no "
                "longer credited — the hatch has been cut too narrow")
        return (f"{len(by_name)} distinct field names; an invented one reads "
                f"as unread, three known ones as read, {len(keyed)} names "
                "reached by accessor key")
