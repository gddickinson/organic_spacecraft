"""The command line: what `python -m seedfall` (and `play.py`) accepts.

Parsed before Qt is imported, so `--help` answers on a machine without PyQt6
and never opens a window. The flags were read by hand in `ui/app.py` until
2026-09: an unknown one was silently ignored, `--help` launched the game, and
`--new` said nothing about the chronicle it was replacing.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

USAGE_EPILOG = """\
examples:
  python -m seedfall                  the title screen: resume, slots, the Hall
  python -m seedfall --new            straight into a new chronicle
  python -m seedfall --seed verge-7   a new chronicle in a sector you can share
  python3 play.py --new               the same, from the project folder

The save is ~/.seedfall/save.json (or the file SEEDFALL_SAVE names), with
named slots beside it in slots/. Starting a new chronicle never destroys the
one in play: it is kept as a slot called "Set aside <date>", which the title
screen lists.
"""


def _prog() -> str:
    """How it was started, for the usage line."""
    name = Path(sys.argv[0]).name if sys.argv and sys.argv[0] else ""
    return "python3 play.py" if name == "play.py" else "python -m seedfall"


def parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(
        prog=_prog(),
        description="SEEDFALL — command a grown hull in the Verge: survey, "
                    "trade, fight or\nrefuse to, research, and plant "
                    "colonies.",
        epilog=USAGE_EPILOG,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--new", action="store_true",
                    help="skip the title screen and start a new chronicle "
                         "(the one in play is kept as a named slot)")
    ap.add_argument("--seed", metavar="NAME",
                    help="start a new chronicle in the sector this seed "
                         "grows; the same seed is the same sky (implies --new)")
    ap.add_argument("--bridge", action="store_true",
                    help="also serve the window over a loopback control "
                         "socket, and print its address as one BRIDGE line")
    ap.add_argument("--port", type=int, default=0, metavar="N",
                    help="the bridge's port (default: any free one)")
    return ap


def parse(argv: list[str]) -> argparse.Namespace:
    """The options, or exit: 0 after `--help`, 2 after a flag it does not
    know (with the reason on stderr)."""
    options = parser().parse_args(argv)
    options.new = options.new or bool(options.seed)
    return options
