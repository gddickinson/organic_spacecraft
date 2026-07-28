"""Driving SEEDFALL from outside the window.

`protocol.py` is the whole vocabulary — verbs over a `Game`, no Qt, no socket —
so it can be exercised in-process by the suite. `server.py` is a thin loopback
transport over it, and `client.py` is enough to drive one.

Three things this is for, all asked for:

- driving a game headlessly, for testing and for scripted play;
- letting an agent hold a character or a rival captain, so the Verge acts
  rather than only reacts;
- a second captain joining, with an autonomous seat taking over when they are
  not there.
"""

from .protocol import VERBS, describe, dispatch, snapshot   # noqa: F401
