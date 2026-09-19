"""What a broad `except` must do when it catches something it was not for.

Eleven `except Exception` blocks in `sim/` guarded a paint or a readout
against one expected failure — a contact whose body has gone, a battle built
without a chronicle behind it, an officer that cannot take an attribute. None
of them fired in six instrumented years of scripted play (review 2026-09-17,
#33), which means that all any of them could still catch was a *new* bug,
and hide it: a sky that silently drew nothing, an order that silently did
not apply.

So each now catches what it was written for by name, and hands anything
else to `swallowed`:

- **in play**, one line on stderr the first time a given site fires, and
  the game carries on as it always did — a painter is not worth a crash;
- **under test** (the harness imports `seedfall.tests`, which nothing in the
  game does), it re-raises, so the check that walked into it goes red and
  says where.
"""

from __future__ import annotations

import sys

#: Sites that have already said so this session. One line each, not one per
#: frame: a painter that fails fails sixty times a second.
_SEEN: set = set()


def swallowed(where: str, err: BaseException) -> None:
    """Report an unexpected exception from a broad `except`, once per site.

    Call it from inside the `except` block. Under test it re-raises `err`
    with its own traceback; in play it prints one line and returns.
    """
    if "seedfall.tests" in sys.modules:
        raise err
    if where in _SEEN:
        return
    _SEEN.add(where)
    print(f"seedfall: {where} swallowed {type(err).__name__}: {err}",
          file=sys.stderr)
