"""`--coverage`: what each suite touches, and what nothing does.

Not a suite. The runner already gives every suite a process of its own, so
each one can be wrapped in `coverage run` with a data file of its own — and
that is the only way to answer the question a combined figure cannot: *which
suites would notice if this module broke?* A module no suite executes is a
module whose constants `tripwire` can mutate to its heart's content.

Written to one directory:

- `.coverage.<suite>` — each suite's own data, kept;
- `.coverage` — all of them combined (`coverage html --data-file=...` works);
- `coverage-map.json` — module → the suites that execute any line of it,
  plus the modules none does.

`coverage` is optional: a machine without it is told so and the run refused
(exit 2), rather than run without the measurement that was asked for.
"""

from __future__ import annotations

import importlib.util
import io
import json
import sys
import tempfile
from pathlib import Path

PACKAGE = Path(__file__).resolve().parent.parent
#: The checks measure the game, not themselves.
OMIT = str(PACKAGE / "tests" / "*")


class Recorder:
    def __init__(self, where: Path):
        self.where = where

    @classmethod
    def start(cls, folder: str = "") -> "Recorder | None":
        if importlib.util.find_spec("coverage") is None:
            print("--coverage needs the `coverage` package: "
                  "pip install coverage (or the [dev] extra)", file=sys.stderr)
            return None
        where = Path(folder) if folder else Path(
            tempfile.mkdtemp(prefix="seedfall-coverage-"))
        where.mkdir(parents=True, exist_ok=True)
        for stale in where.glob(".coverage*"):
            stale.unlink()
        return cls(where)

    def data_file(self, key: str) -> Path:
        return self.where / f".coverage.{key}"

    def wrap(self, key: str) -> tuple:
        """The `python -m coverage run ...` prefix for one suite's child."""
        return ("-m", "coverage", "run", f"--data-file={self.data_file(key)}",
                f"--source={PACKAGE}", f"--omit={OMIT}")

    def finish(self, keys: list) -> dict:
        """Combine, map and report. Returns the map it wrote."""
        from coverage import Coverage, CoverageData

        touched: dict[str, list] = {}
        files = []
        for key in keys:
            path = self.data_file(key)
            if not path.exists():
                continue            # a suite that crashed, or never started
            files.append(str(path))
            data = CoverageData(basename=str(path))
            data.read()
            for measured in data.measured_files():
                rel = _rel(measured)
                touched.setdefault(rel, [])
                if data.lines(measured):
                    touched[rel].append(key)
        combined = self.where / ".coverage"
        cov = Coverage(data_file=str(combined), source=[str(PACKAGE)],
                       omit=[OMIT])
        cov.combine(files, keep=True)
        cov.save()
        total = cov.report(file=io.StringIO())
        packages = _by_package(cov)
        untouched = sorted(m for m, who in touched.items() if not who)
        out = {"total_percent": round(total, 1), "suites": sorted(keys),
               "packages": packages, "untouched": untouched,
               "modules": {m: sorted(who) for m, who in sorted(touched.items())}}
        (self.where / "coverage-map.json").write_text(json.dumps(out, indent=1))
        print(f"  coverage {total:.1f}% over {len(files)} suites — "
              + " · ".join(f"{p} {v['percent']:.0f}%"
                           for p, v in sorted(packages.items())))
        print(f"  {len(untouched)} modules no suite here executes; map and "
              f"data in {self.where}", flush=True)
        return out


def _rel(path: str) -> str:
    try:
        return str(Path(path).resolve().relative_to(PACKAGE))
    except ValueError:
        return path


def _by_package(cov) -> dict:
    """Statements and misses per top-level subpackage (`sim`, `ui`, ...)."""
    sums: dict[str, list] = {}
    for measured in cov.get_data().measured_files():
        rel = _rel(measured)
        top = rel.split("/")[0] if "/" in rel else "(root)"
        try:
            _name, statements, _excluded, missing, _text = cov.analysis2(measured)
        except Exception:                             # noqa: BLE001
            continue            # a file that has gone since it was measured
        row = sums.setdefault(top, [0, 0])
        row[0] += len(statements)
        row[1] += len(missing)
    return {top: {"statements": n, "missed": m,
                  "percent": round(100.0 * (n - m) / n, 1) if n else 100.0}
            for top, (n, m) in sums.items()}
