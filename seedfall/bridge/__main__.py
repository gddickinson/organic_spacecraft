"""Start a bridge over a game, so something outside can drive it.

    python -m seedfall.bridge                 # a fresh chronicle
    python -m seedfall.bridge --load          # the saved one
    python -m seedfall.bridge --seed verge-7 --port 8765

It prints the host, port and token as one JSON line and then serves until
interrupted. Loopback only, token required; there is no discovery and nothing
is exposed beyond this machine.
"""

from __future__ import annotations

import argparse
import json
import sys
import time

from ..core import state as state_mod
from .server import serve


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(prog="seedfall.bridge")
    parser.add_argument("--seed", default=None, help="sector seed")
    parser.add_argument("--load", action="store_true",
                        help="serve the saved chronicle instead of a new one")
    parser.add_argument("--port", type=int, default=0,
                        help="loopback port; 0 asks the OS for a free one")
    args = parser.parse_args(argv)

    game = state_mod.load_game() if args.load else None
    if game is None:
        if args.load:
            print(json.dumps({"ok": False, "why": "no save to serve"}))
            return 1
        game = state_mod.new_game(args.seed)

    bridge = serve(game, port=args.port)
    print(json.dumps({"ok": True, **bridge.address(),
                      "day": game.day, "seed": game.seed}), flush=True)
    try:
        while True:
            time.sleep(0.5)
    except KeyboardInterrupt:
        pass
    finally:
        bridge.stop()
    return 0


if __name__ == "__main__":
    sys.exit(main())
