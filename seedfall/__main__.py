"""Run SEEDFALL: ``python -m seedfall``.

Options::

    python -m seedfall                 # title screen
    python -m seedfall --new           # skip straight into a new chronicle
    python -m seedfall --seed verge-7  # a specific sector
    python -m seedfall --bridge        # also open a control socket on loopback
    python -m seedfall --help          # every option, and where the save is

`--bridge` prints one line — ``BRIDGE {"host": ..., "port": ..., "token": ...}``
— and then serves the running window over that socket, so a caller elsewhere on
this machine can drive the game you are watching. See `bridge/attached.py`.
"""

from __future__ import annotations

import sys


def main(argv=None) -> int:
    # Before Qt: `--help` and a mistyped flag are answered on any machine,
    # and neither opens a window (`core/cli`).
    from .core import cli
    options = cli.parse(list(sys.argv[1:] if argv is None else argv))
    try:
        from .ui.app import main as run
    except ImportError as err:                       # pragma: no cover
        print("SEEDFALL needs PyQt6.\n\n    pip install PyQt6\n", file=sys.stderr)
        print(f"(import failed: {err})", file=sys.stderr)
        return 1
    return run(options)


if __name__ == "__main__":
    raise SystemExit(main())
