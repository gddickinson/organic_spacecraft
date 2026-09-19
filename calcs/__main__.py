"""CLI: ``python -m calcs`` prints every value; ``--check`` compares with the docs.

    python -m calcs              # the table of computed values
    python -m calcs --check      # every data-calc number in docs/*.html vs calcs
    python -m calcs --check -v   # ... listing the passing ones too
    python -m calcs --grep navis # only keys containing 'navis'
"""

import argparse
import sys

from .docscheck import DOCS, check
from .registry import all_values


def table(pattern=""):
    for key, v in all_values().items():
        if pattern not in key:
            continue
        x = v.value
        s = f"{x:,.4g}" if 1e-3 <= abs(x) < 1e6 or x == 0 else f"{x:.3e}"
        print(f"{key:32s} {s:>12s}  {v.unit:12s} {v.note}")


def main(argv=None):
    ap = argparse.ArgumentParser(prog="python -m calcs", description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--check", action="store_true", help="compare with the documents")
    ap.add_argument("-v", "--verbose", action="store_true")
    ap.add_argument("--grep", default="", help="filter the value table by key")
    ap.add_argument("--docs", default=str(DOCS), help="documents directory")
    a = ap.parse_args(argv)
    if a.check:
        ok, _ = check(a.docs, a.verbose)
        return 0 if ok else 1
    table(a.grep)
    return 0


if __name__ == "__main__":
    sys.exit(main())
