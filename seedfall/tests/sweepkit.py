"""Finding every tuning constant in the game, and changing one on disk.

Split out of `tests/tripwire.py` when that reached five hundred lines exactly —
the point at which the next line anybody added to it would have failed the
suite. The seam is a real one and the file had two jobs: *which suites speak
for which module, and what a sweep concluded* stayed there; **how to find a
constant and how to change it** is here.

It is a leaf. It reads nothing from the sweep and knows nothing about suites,
which is why `scratchpad` tools that hunt a single constant's guard can use it
without dragging the whole apparatus along — they had been reimplementing
`rewrite` by hand, which is one transcription error away from a mutation that
does not restore.

**The two traps this module exists to remember**, both paid for once already:

* A negative literal is not an `ast.Constant`. `-60.0` parses as
  `UnaryOp(USub, Constant(60.0))`, so for as long as `constants` matched only
  `ast.Constant`, every negative constant in the codebase was invisible — 422
  swept, 14 unseen, among them whether a quay opens a hatch to you and whether
  two powers are at war.
* Rewriting by reading and writing the same path can truncate it. A probe
  killed mid-`write_text` left `data/industry.py` at zero bytes, and a
  value-based check called it clean; only `git diff` noticed.
"""

from __future__ import annotations

import ast
import os
import pathlib
import tempfile


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
    put(path, "".join(out))
    return original


def put(path: pathlib.Path, text: str) -> None:
    """Replace a file's contents in one step, or not at all.

    **`write_text` truncates and then writes**, so a process killed between
    the two leaves the file short — or empty. That is not hypothetical here:
    a probe once left `data/industry.py` at zero bytes, and while this module
    was being worked on a hard `SIGKILL` timeout caught a sweep mid-write and
    left `data/diplomacy.py` **168 lines shorter than it started**, taking the
    whole courtship curve with it.

    The sweep's own `SIGTERM` handler cannot help: it never runs. Writing to a
    sibling temp file and renaming does, because `os.replace` is atomic — the
    path either names the old contents or the new one, and never a half.
    """
    fd, tmp = tempfile.mkstemp(dir=str(path.parent), suffix=".swp")
    try:
        with os.fdopen(fd, "w") as handle:
            handle.write(text)
        os.replace(tmp, path)
    except BaseException:
        pathlib.Path(tmp).unlink(missing_ok=True)
        raise
