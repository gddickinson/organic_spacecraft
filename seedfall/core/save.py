"""Saving and loading.

Game state is built from plain mutable dataclasses, so it serialises
generically: every dataclass instance is written with a ``__t__`` tag naming its
class, and rebuilt from a registry on the way back in. Content tables (hulls,
parts, technologies) are never stored — state refers to them by id — so a save
stays valid when the tables gain new entries.
"""

from __future__ import annotations

import json
import os
from dataclasses import fields, is_dataclass
from pathlib import Path

SAVE_DIR = Path.home() / ".seedfall"
SAVE_NAME = "save.json"
SAVE_VERSION = 1

#: Environment variable that moves the chronicle somewhere else.
#:
#: The test harness sets it, per process. Named rather than hard-coded in two
#: places because `tests/__init__.py` is the only thing that writes it and this
#: is the only thing that reads it.
SAVE_ENV = "SEEDFALL_SAVE"


def save_path() -> Path:
    """Where the chronicle is kept. **One door, asked afresh every time.**

    It used to be a module constant, `SAVE_PATH`, spent as a *default
    argument* on `write`, `read`, `exists` and `clear`. A default binds when
    the function is defined, so the path could not be redirected by anything —
    not by a test, not by a second process, not by assigning to the constant
    afterwards.

    Two things followed, and both were measured rather than supposed:

    - **The suite wrote over the player's own saved game.** Fourteen check
      files call `save_mod.write({"game": game})` with no path. After a run,
      `~/.seedfall/save.json` held 192,514 bytes of a game seeded `lab8` — a
      fixture invented for the orrery checks — at day 0 with 18,000 credits.
      Whatever chronicle the player had was gone.
    - **Two runs at once corrupted each other.** `write` stages through
      `save.tmp` and renames, which is atomic for one writer and a race for
      two. It produced five phantom failures in one session — `anchorage`,
      `traffic`, `tutorial`, `grudges`, `territory` — none of which was a real
      defect. The full suite now takes about 25 minutes against a cron that
      fires every 10, so overlapping runs are the normal case and not the
      unlucky one.
    """
    override = os.environ.get(SAVE_ENV)
    return Path(override) if override else SAVE_DIR / SAVE_NAME

_REGISTRY: dict[str, type] = {}


def register(cls):
    """Class decorator: make a dataclass restorable from a save file."""
    _REGISTRY[cls.__name__] = cls
    return cls


def encode(obj):
    if is_dataclass(obj) and not isinstance(obj, type):
        # Fields marked transient are derived values (ship stats, research
        # bonuses, colony effects). They are recomputed on load, and some of
        # them hold references to the content tables, which must never be
        # written into a save.
        out = {f.name: encode(getattr(obj, f.name)) for f in fields(obj)
               if not f.metadata.get("transient")}
        out["__t__"] = type(obj).__name__
        return out
    if isinstance(obj, dict):
        return {k: encode(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [encode(v) for v in obj]
    if isinstance(obj, set):
        return sorted(obj)
    return obj


def decode(obj):
    if isinstance(obj, dict):
        tag = obj.get("__t__")
        payload = {k: decode(v) for k, v in obj.items() if k != "__t__"}
        if tag:
            cls = _REGISTRY.get(tag)
            if cls is None:
                raise ValueError(f"save refers to unknown type {tag!r}")
            known = {f.name for f in fields(cls)}
            # Tolerate a save written by an older or newer build.
            return cls(**{k: v for k, v in payload.items() if k in known})
        return payload
    if isinstance(obj, list):
        return [decode(v) for v in obj]
    return obj


def write(state_dict: dict, path: Path | None = None) -> bool:
    path = Path(path) if path is not None else save_path()
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        payload = {"version": SAVE_VERSION, "state": encode(state_dict)}
        tmp = path.with_suffix(".tmp")
        tmp.write_text(json.dumps(payload), encoding="utf-8")
        tmp.replace(path)          # atomic: a crash mid-write cannot corrupt it
        return True
    except OSError as err:
        print(f"[seedfall] save failed: {err}")
        return False


def read(path: Path | None = None):
    path = Path(path) if path is not None else save_path()
    try:
        if not path.is_file():
            return None
        payload = json.loads(path.read_text(encoding="utf-8"))
        if payload.get("version") != SAVE_VERSION:
            return None
        return decode(payload["state"])
    except (OSError, ValueError, KeyError) as err:
        print(f"[seedfall] save could not be read: {err}")
        return None


def exists(path: Path | None = None) -> bool:
    path = Path(path) if path is not None else save_path()
    return path.is_file()


def clear(path: Path | None = None) -> None:
    path = Path(path) if path is not None else save_path()
    try:
        path.unlink(missing_ok=True)
    except OSError:
        pass
