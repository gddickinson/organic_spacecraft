"""No file grows past five hundred lines, and the ones that already have shrink.

The five-hundred-line rule has been this project's standing instruction from
the start, and **nothing enforced it**. That is the whole reason task #138
exists: files drifted over one commit at a time, nobody noticed until somebody
counted, and then it was fifteen of them at once — each needing a real seam
found and cut, which is a cycle's work apiece.

A hand-kept list of what is too long goes stale the moment anything is edited.
This is the ratchet instead:

- A file **not** on `ALLOWED` must be at or under `LIMIT`. That is every file
  in the project except the debts below, and it is what stops the list growing.
- A file **on** `ALLOWED` must not exceed the length recorded there. The debt
  can be paid off; it cannot be added to.
- When a file comes under the limit its row is deleted, and the check itself
  insists on that — a row that no longer needs to be there is a lie about how
  much is left.

The counts are measured, not estimated: they are what `wc -l` says today.
"""

from __future__ import annotations

import pathlib

from .harness import Suite

#: The rule, from the project's own standing instructions.
LIMIT = 500

ROOT = pathlib.Path(__file__).resolve().parent.parent

#: Files over the limit when the ratchet went in, and how far over.
#:
#: Each is a real seam waiting to be found, not a licence. `sim/conn.py` is
#: **not** here: it was 612 and the tick integrator came out into
#: `sim/conn_step.py`, leaving 484. That is the shape of paying one off.
ALLOWED = {
    "data/works3d.py": 635,
    "sim/robots.py": 616,
    "sim/control.py": 602,
    "sim/flight.py": 512,
    "sim/exchequer.py": 506,
    "ui/viewport.py": 533,
    "ui/map_view.py": 526,
    "ui/widgets.py": 517,
    "tests/test_robots.py": 624,
    "tests/test_orbits.py": 567,
    "tests/test_control.py": 560,
    "tests/test_conn.py": 523,
    "tests/test_industry.py": 520,
    "tests/chronicle.py": 517,
}


def _sources() -> dict:
    """Every Python file in the package, by path relative to it."""
    out = {}
    for path in sorted(ROOT.rglob("*.py")):
        if "__pycache__" in path.parts:
            continue
        rel = str(path.relative_to(ROOT))
        out[rel] = len(path.read_text().splitlines())
    return out


def run(suite: Suite) -> None:
    check = suite.check

    @check("nothing new is over five hundred lines")
    def _():
        # The list cannot grow. A file that is not already a recorded debt has
        # to come in under the rule, whoever wrote it and however good the
        # reason felt at the time.
        found = _sources()
        over = {rel: n for rel, n in found.items()
                if n > LIMIT and rel not in ALLOWED}
        assert not over, (
            "over five hundred lines and not a recorded debt: "
            + ", ".join(f"{rel} ({n})" for rel, n in sorted(over.items())))
        return (f"{len(found)} files, {len(found) - len(ALLOWED)} of them "
                f"under {LIMIT}")

    @check("the files that are too long are not getting longer")
    def _():
        # A debt can be paid off in pieces. It cannot be added to — which is
        # what happened for fifteen files running while nothing was watching.
        found = _sources()
        grown = {rel: (found[rel], was) for rel, was in ALLOWED.items()
                 if rel in found and found[rel] > was}
        assert not grown, (
            "already too long and grown since: "
            + ", ".join(f"{rel} {was} → {now}"
                        for rel, (now, was) in sorted(grown.items())))
        total = sum(found[rel] - LIMIT for rel in ALLOWED if rel in found)
        return (f"{len(ALLOWED)} files over the line, {total} lines of debt "
                f"between them")

    @check("a debt that has been paid is struck off the list")
    def _():
        # **The row is the lie, not the file.** A file split down to size and
        # left on the list makes the debt look bigger than it is, and the next
        # person to read the list plans work that is already done. It also
        # catches a rename: a row naming a file that no longer exists.
        found = _sources()
        gone = sorted(rel for rel in ALLOWED if rel not in found)
        assert not gone, f"recorded debts for files that do not exist: {gone}"
        paid = sorted(rel for rel in ALLOWED if found[rel] <= LIMIT)
        assert not paid, (
            "under the limit now and still listed as a debt — strike them "
            f"off: {paid}")
        worst = max(ALLOWED.items(), key=lambda kv: kv[1])
        return f"no stale rows; the longest left is {worst[0]} at {worst[1]}"
