"""Saving and loading.

Game state is built from plain mutable dataclasses, so it serialises
generically: every dataclass instance is written with a ``__t__`` tag naming its
class, and rebuilt from a registry on the way back in. Content tables (hulls,
parts, technologies) are never stored — state refers to them by id — so a save
stays valid when the tables gain new entries.
"""

from __future__ import annotations

import importlib
import json
import os
import pkgutil
import shutil
import tempfile
import time
from dataclasses import fields, is_dataclass
from pathlib import Path

SAVE_DIR = Path.home() / ".seedfall"
SAVE_NAME = "save.json"
#: 2 — the id counters travel with the chronicle (`Game.ids`). Version 1
#: saves read unchanged: every field added since has a default.
SAVE_VERSION = 2

#: Set by the test harness. A dataclass carrying an attribute that is not
#: one of its fields is an error rather than a silent loss — see `encode`.
STRICT = False

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
    if override:
        return Path(override)
    # **A process with no screen is never the player.** An offscreen window
    # built by a probe autosaves like any other, and on 2026-09-17 one built
    # without `SEEDFALL_SAVE` wrote over the player's own chronicle (the
    # `.bak` this module keeps is what got it back). So headless runs get a
    # scratch file of their own unless they name a path explicitly.
    if os.environ.get("QT_QPA_PLATFORM", "").lower() in HEADLESS:
        return Path(tempfile.gettempdir()) / f"seedfall-headless-{os.getpid()}.json"
    return SAVE_DIR / SAVE_NAME


#: Qt platforms with no display: nobody is playing in one.
HEADLESS = ("offscreen", "minimal")

_REGISTRY: dict[str, type] = {}

#: The packages whose modules declare saved types. **Filled by import, so
#: imported before anything is read.** The registry used to fill only as a
#: side effect of whatever the process happened to have imported: a fresh
#: `python -m seedfall` held 28 of 56 types, and every save it was asked to
#: resume failed on `Choices` or `Envoy` — while every check passed, because
#: every check loaded its save in the process that wrote it.
SAVED_PACKAGES = ("seedfall.core", "seedfall.world", "seedfall.sim")

#: Undeclared attributes met while writing (class.attribute), outside strict
#: mode. Read by the suite; kept so a lenient write still says what it lost.
UNDECLARED: set[str] = set()

_last_error: str | None = None


def register(cls):
    """Class decorator: make a dataclass restorable from a save file."""
    _REGISTRY[cls.__name__] = cls
    return cls


def ensure_registry() -> int:
    """Import every module that can declare a saved type. Returns the count
    of registered types, so a caller can say how many it found."""
    for name in SAVED_PACKAGES:
        package = importlib.import_module(name)
        for info in pkgutil.iter_modules(package.__path__, name + "."):
            importlib.import_module(info.name)
    return len(_REGISTRY)


def last_error() -> str | None:
    """Why the last `read` returned nothing, in words — or None."""
    return _last_error


def encode(obj):
    if is_dataclass(obj) and not isinstance(obj, type):
        cls = type(obj)
        if _REGISTRY.get(cls.__name__) is not cls:
            # Written, it could never be read back. Refuse at the write,
            # where the stack says which object it was.
            raise TypeError(f"{cls.__name__} is saved but not @register'd")
        names = [f.name for f in fields(obj)]
        # A name the class itself defines (a method a check has stubbed on
        # the instance) is not state; everything else in `__dict__` is.
        extra = {a for a in getattr(obj, "__dict__", {})
                 if a not in names and not hasattr(cls, a)}
        if extra:
            # **An attribute set at runtime is not saved.** Hunger debt, the
            # envoy's quiet period and a tutorial counter were all dropped by
            # every reload this way, and the chronicle diverged within a month.
            lost = {f"{cls.__name__}.{a}" for a in extra}
            if STRICT:
                raise TypeError(f"undeclared attributes would be lost: "
                                f"{sorted(lost)}")
            UNDECLARED.update(lost)
        # Fields marked transient are derived values (ship stats, research
        # bonuses, colony effects). They are recomputed on load, and some of
        # them hold references to the content tables, which must never be
        # written into a save.
        out = {f.name: encode(getattr(obj, f.name)) for f in fields(obj)
               if not f.metadata.get("transient")}
        out["__t__"] = cls.__name__
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


def _migrate(state, version):
    """Bring an older save's state up to `SAVE_VERSION`, one step at a time.

    Each entry takes the raw decoded-JSON state of version n and returns
    version n+1. Version 1 → 2 changes nothing on disk: the id counters are
    rebuilt from what the save holds (`core.ids.restore`).
    """
    if not isinstance(version, int) or version < 1:
        raise ValueError(f"save has no usable version ({version!r})")
    if version > SAVE_VERSION:
        raise ValueError(f"save was written by a newer build (v{version})")
    while version < SAVE_VERSION:
        state = MIGRATIONS[version](state)
        version += 1
    return state


#: version → function(state) -> state of version + 1.
MIGRATIONS = {1: lambda state: state}


def write(state_dict: dict, path: Path | None = None) -> bool:
    """Write the chronicle. Staged to a file of its own, flushed to disk,
    then renamed over the save; the previous save is kept as ``.bak``."""
    path = Path(path) if path is not None else save_path()
    tmp = path.with_name(f"{path.name}.{os.getpid()}.tmp")
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        state = encode(state_dict)
        # Second, so the title screen finds it in the file's first few
        # hundred bytes without decoding the chronicle — see `core/slots.py`.
        from .slots import summary_of
        text = json.dumps({"version": SAVE_VERSION,
                           "summary": summary_of(state),
                           "state": state}, allow_nan=False)
        with open(tmp, "w", encoding="utf-8") as fh:
            fh.write(text)
            fh.flush()
            os.fsync(fh.fileno())
        if path.is_file():
            shutil.copy2(path, path.with_name(path.name + ".bak"))
        tmp.replace(path)          # atomic: a crash mid-write cannot corrupt it
        return True
    except (OSError, TypeError, ValueError) as err:
        if STRICT and isinstance(err, TypeError):
            raise
        print(f"[seedfall] save failed: {err}")
        try:
            tmp.unlink(missing_ok=True)
        except OSError:
            pass
        return False


def read(path: Path | None = None):
    """The saved state, or None. **Never raises, and never destroys.** A file
    that cannot be read is moved aside as ``.bad`` (not deleted), so the
    title screen's New cannot clear the only copy of it."""
    global _last_error
    _last_error = None
    path = Path(path) if path is not None else save_path()
    if not path.is_file():
        return None
    try:
        ensure_registry()
        payload = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(payload, dict) or "state" not in payload:
            raise ValueError("not a SEEDFALL save")
        state = _migrate(payload["state"], payload.get("version"))
        out = decode(state)
        if not isinstance(out, dict):
            raise ValueError("save holds no chronicle")
        return out
    except Exception as err:                                   # noqa: BLE001
        _last_error = f"{type(err).__name__}: {err}"
        print(f"[seedfall] save could not be read: {_last_error}")
        if "newer build" not in str(err):
            quarantine(path)
        return None


def quarantine(path: Path) -> Path | None:
    """Move an unreadable save aside, stamped, and return where it went."""
    dest = path.with_name(f"{path.stem}.{time.strftime('%Y%m%d-%H%M%S')}.bad")
    try:
        path.replace(dest)
        return dest
    except OSError:
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
