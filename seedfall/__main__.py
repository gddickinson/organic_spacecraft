"""Run SEEDFALL: ``python -m seedfall``.

Options::

    python -m seedfall                 # title screen
    python -m seedfall --new           # skip straight into a new chronicle
    python -m seedfall --seed verge-7  # a specific sector
"""

from __future__ import annotations

import sys


def main() -> int:
    try:
        from .ui.app import main as run
    except ImportError as err:                       # pragma: no cover
        print("SEEDFALL needs PyQt6.\n\n    pip install PyQt6\n", file=sys.stderr)
        print(f"(import failed: {err})", file=sys.stderr)
        return 1
    return run()


if __name__ == "__main__":
    raise SystemExit(main())
