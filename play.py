#!/usr/bin/env python3
"""Start SEEDFALL from the project folder.

    python3 play.py              # the title screen
    python3 play.py --new        # straight into a new chronicle
    python3 play.py --help       # every option

The same as `python -m seedfall`, from anywhere: it finds the game beside
itself, so the terminal does not have to be in this folder. Every flag is
passed through (`seedfall/core/cli.py`).
"""

import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

from seedfall.__main__ import main  # noqa: E402

if __name__ == "__main__":
    raise SystemExit(main())
