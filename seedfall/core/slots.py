"""Named chronicles kept beside the one in play, and what each is at a glance.

There was one save. "Begin again" said so — "there is one save and this
overwrites it" — so a captain who wanted to try the other answer to an envoy,
or to keep a twenty-year chronicle while starting a second, had to lose one to
have the other. A slot is a copy of a chronicle under a name, written by the
same `save.write` as the real thing; loading one makes it the chronicle in
play, and the save in play goes on being the only file the game writes to by
itself.

**Every path here is derived from `save.save_path()`**, the one door, so a
redirected save (`SEEDFALL_SAVE`, every test process, every headless probe)
redirects its slots with it. A constant would have put the suite's slots in
the player's `~/.seedfall`, which is the defect `save_path` exists to end.

**A listing never decodes a chronicle.** Each save carries a `summary` block at
its head (`summary_of`, written by `save.write`), and `read_summary` reads the
first four kilobytes for it. Measured on a 185 KB chronicle: `load_game` costs
224 ms cold in a fresh process (the registry's imports) and about 10 ms warm;
the head read costs 0.1 ms. The cost is the lesser reason, though. Decoding
is what `save.read` does, and a file it cannot decode is moved aside as
`.bad` — a title screen that decoded to *list* would quarantine a damaged
slot just by drawing it. A save written before there were summaries is still
listed: its JSON is parsed (not decoded) and summarised the same way.
"""

from __future__ import annotations

import json
import re
import shutil
import time
from pathlib import Path

from . import save as save_mod

#: The folder of slots beside the player's own `save.json`.
SLOT_DIR = "slots"

#: The key `save.write` puts the summary under, second in the payload so it
#: sits inside the first few hundred bytes of the file.
SUMMARY_KEY = "summary"

#: How much of a file `read_summary` looks at. A summary is about 300 bytes;
#: the head of the payload before it is `{"version": 2, `.
HEAD_BYTES = 4096

#: Slot names become file names, so they keep to what every filesystem the
#: game runs on accepts and nothing that walks out of the folder: letters,
#: digits, space, `-`, `_` and `.` — never a leading dot, never `/`.
_UNSAFE = re.compile(r"[^\w .\-]+", re.ASCII)
MAX_NAME = 48


def slot_dir() -> Path:
    """Where the named chronicles live.

    Beside the player's `save.json` it is `slots/`. A redirected save is a
    file named for its process in a *shared* directory — a temp folder that
    every concurrent test run also writes to — so `slots/` there would be one
    folder for all of them, the race `save_path` was written to end. Any save
    not called `save.json` keeps its slots in a folder named after itself.
    """
    here = save_mod.save_path()
    if here.name == save_mod.SAVE_NAME:
        return here.parent / SLOT_DIR
    return here.with_name(here.stem + ".slots")


def recovery_path() -> Path:
    """The copy `ui/crash.py` writes when the game hits an error — beside the
    save, never over it. Pinned to `crash.paths` by `test_slots`."""
    return save_mod.save_path().parent / "recovery.json"


def backup_path() -> Path:
    """The previous save, which `save.write` keeps on every write."""
    here = save_mod.save_path()
    return here.with_name(here.name + ".bak")


def clean_name(name: str) -> str:
    """A slot name as a file will carry it, or "" if nothing usable is left."""
    text = _UNSAFE.sub("", name or "")
    text = re.sub(r"\.{2,}", ".", text).strip().lstrip(".")
    return text[:MAX_NAME].strip()


def slot_path(name: str) -> Path | None:
    """The file a slot of this name is kept in, or None for an unusable name."""
    safe = clean_name(name)
    return slot_dir() / f"{safe}.json" if safe else None


def summary_of(state) -> dict | None:
    """What a chronicle is, read from its **encoded** form.

    Encoded rather than live, so one function serves both doors: `save.write`
    hands it the dict it is about to write, and an older save with no summary
    is parsed as plain JSON and handed the same dict — no registry, no decode,
    nothing that can quarantine a file just for being looked at.

    The chronicle has no captain's name — `Choices.name` names the hull — so
    the calling (`origin`) stands for who is in command.
    """
    game = state.get("game") if isinstance(state, dict) else None
    if not isinstance(game, dict):
        return None
    try:
        ship = game.get("ship") or {}
        systems = (game.get("galaxy") or {}).get("systems") or []
        at = game.get("location_id", 0)
        place = (systems[at].get("name", "")
                 if isinstance(at, int) and 0 <= at < len(systems) else "")
        start = game.get("beginning")
        ending = (game.get("ending") or game.get("victory")
                  or ("lost" if game.get("dead") else ""))
        return {"seed": str(game.get("seed", "")),
                "day": int(game.get("day", 0) or 0),
                "credits": round(float(game.get("credits", 0) or 0)),
                "ship": str(ship.get("name", "")),
                "chassis": str(ship.get("chassis", "")),
                "system": str(place),
                "origin": str(start.get("origin", ""))
                if isinstance(start, dict) else "",
                "ending": str(ending or ""),
                "saved": round(time.time())}
    except (AttributeError, TypeError, ValueError, IndexError):
        # A summary is a convenience for the title screen. It is never a
        # reason for the save it rides on to fail.
        return None


def read_summary(path) -> dict | None:
    """The summary of the save at `path`, without decoding the chronicle.

    Read from the head of the file first: `save.write` puts it straight after
    the version, so a slot whose chronicle is damaged still lists. A save from
    before summaries existed is parsed whole — as JSON only — and summarised.
    """
    path = Path(path)
    try:
        with open(path, encoding="utf-8") as fh:
            head = fh.read(HEAD_BYTES)
    except (OSError, UnicodeDecodeError):
        return None
    key = f'"{SUMMARY_KEY}": '
    at = head.find(key)
    # Only at the head of the payload — the same words deeper in could be any
    # field of any object in the chronicle.
    if 0 <= at < 64:
        try:
            got, _end = json.JSONDecoder().raw_decode(head, at + len(key))
            if isinstance(got, dict):
                return got
        except ValueError:
            pass
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError, UnicodeDecodeError):
        return None
    return summary_of(payload.get("state")) if isinstance(payload, dict) \
        else None


def listing() -> list[dict]:
    """Every chronicle the title screen can offer, in the order it offers them.

    The one in play, then the named slots newest first, then the two that
    exist because something went wrong: the copy the crash hook kept and the
    previous save. Each is `{kind, name, path, summary}`; a summary is None
    when the file cannot be read at all, and the row says so.
    """
    out = []
    here = save_mod.save_path()
    if here.is_file():
        out.append(_entry("play", "The chronicle in play", here))
    folder = slot_dir()
    if folder.is_dir():
        kept = [_entry("slot", p.stem, p) for p in folder.glob("*.json")]
        kept.sort(key=lambda e: -(e["summary"] or {}).get("saved", 0))
        out.extend(kept)
    for kind, name, path in (("recovery", "Kept when the game hit an error",
                              recovery_path()),
                             ("backup", "The save before last", backup_path())):
        if path.is_file():
            out.append(_entry(kind, name, path))
    return out


def _entry(kind: str, name: str, path: Path) -> dict:
    return {"kind": kind, "name": name, "path": path,
            "summary": read_summary(path)}


def save_as(name: str, game=None) -> dict:
    """Keep a chronicle under a name. `{ok, why, text, path}`.

    With a live `game` that game is written; without one, the save in play is
    copied as it stands on disk — which is what the title screen has before
    anything is loaded. A name already taken is overwritten; the screen asks
    first, because this cannot tell a slip from an intention.
    """
    path = slot_path(name)
    if path is None:
        return {"ok": False, "why": "A slot needs a name with a letter or a "
                "digit in it.", "text": "", "path": None}
    if game is not None:
        wrote = save_mod.write(game.to_save(), path)
    else:
        source = save_mod.save_path()
        if not source.is_file():
            return {"ok": False, "why": "There is no chronicle in play to keep.",
                    "text": "", "path": None}
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, path)
            wrote = True
        except OSError:
            wrote = False
    if not wrote:
        return {"ok": False, "why": f"«{path.stem}» could not be written.",
                "text": "", "path": None}
    return {"ok": True, "why": "", "path": path,
            "text": f"Kept as «{path.stem}». The chronicle in play carries on."}


def delete(name: str) -> dict:
    """Remove one named slot, and nothing else. `{ok, why, text}`.

    Only a slot: the save in play, the crash copy and the `.bak` are not
    names in the folder, so no name can reach them.
    """
    path = slot_path(name)
    if path is None or not path.is_file():
        return {"ok": False, "why": f"There is no slot called «{name}».",
                "text": ""}
    try:
        path.unlink()
        path.with_name(path.name + ".bak").unlink(missing_ok=True)
    except OSError as err:
        return {"ok": False, "why": f"«{path.stem}» could not be deleted: {err}",
                "text": ""}
    return {"ok": True, "why": "", "text": f"«{path.stem}» is gone."}
