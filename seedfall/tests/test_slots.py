"""Named chronicles: kept, listed, loaded and deleted without touching the rest.

There was one save, and "Begin again" said it would be written over. Slots
(`core/slots.py`) keep a chronicle under a name beside the one in play; the
title screen lists them (`ui/chronicle_picker.py`) from a summary at the head
of each file. What these pin:

- **Where.** Every slot is under the redirected save, so a run can never put
  one in the player's `~/.seedfall` — the defect `save_path` exists to end.
- **What.** A slot loads back as the chronicle that was kept, and the summary
  at the head of every save says what the chronicle is.
- **Without decoding.** A listing reads the summary only: a slot whose body
  is damaged still lists, and is not quarantined for having been looked at.
- **Old saves.** A save from before summaries still loads and still lists.
- **Deleting one thing.** Delete removes that slot and nothing else, and no
  name reaches outside the folder.
- **The screens.** The title offers every chronicle with its buttons and they
  do what they say; the menu's "Save as…" keeps the live chronicle, and a
  dismissed question keeps nothing.

Every check runs against a temporary directory named as the player's is
(`save.json`, so the slots take the player's `slots/` shape), restored after.
"""

from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path

from ..core import save as save_mod
from ..core import slots
from ..core.state import load_game, new_game
from .harness import Suite


def _plain(game, path: Path) -> None:
    """Write `game` the way a build before summaries did."""
    path.write_text(json.dumps({"version": save_mod.SAVE_VERSION,
                                "state": save_mod.encode(game.to_save())}))


def run(suite: Suite) -> bool:
    # True: the suite is marked as needing Qt, and the runner reads a falsy
    # return from one of those as "skipped".
    before = os.environ.get(save_mod.SAVE_ENV)
    with tempfile.TemporaryDirectory(prefix="seedfall-slots-") as tmp:
        os.environ[save_mod.SAVE_ENV] = str(Path(tmp) / save_mod.SAVE_NAME)
        try:
            _checks(suite, Path(tmp))
        finally:
            if before is None:
                os.environ.pop(save_mod.SAVE_ENV, None)
            else:
                os.environ[save_mod.SAVE_ENV] = before
    return True


def _checks(suite: Suite, tmp: Path) -> None:
    check = suite.check
    game = new_game("slots-test-seed")
    game.wait_days(20)
    game.credits = 31_415
    game.save()

    @check("slots live beside the redirected save, never in the player's")
    def _():
        here = slots.slot_dir()
        assert here == tmp / slots.SLOT_DIR, here
        theirs = save_mod.SAVE_DIR.resolve()
        for path in (here, slots.recovery_path(), slots.backup_path()):
            assert theirs not in path.resolve().parents, (
                f"{path} is inside the player's {theirs}")
        # A save not named `save.json` is a per-process file in a shared
        # temp folder, and its slots get a folder of their own name.
        os.environ[save_mod.SAVE_ENV] = str(tmp / "seedfall-test-123.json")
        try:
            own = slots.slot_dir()
        finally:
            os.environ[save_mod.SAVE_ENV] = str(tmp / save_mod.SAVE_NAME)
        assert own == tmp / "seedfall-test-123.slots", own
        return f"{here.name}/ beside save.json; {own.name}/ beside a pid save"

    @check("the recovery copy listed is the one the crash hook writes")
    def _():
        try:
            from ..ui import crash
        except ImportError as err:        # no PyQt: crash.py is ui-side
            return f"skipped: {err}"
        assert crash.paths()[1] == slots.recovery_path(), (
            crash.paths()[1], slots.recovery_path())
        return str(slots.recovery_path().name)

    @check("a chronicle kept as a slot loads back as the same chronicle")
    def _():
        res = slots.save_as("Before the envoy", game)
        assert res["ok"], res["why"]
        back = load_game(res["path"])
        assert back is not None, "the slot did not load"
        got = (back.seed, back.day, round(back.credits), back.ship.name,
               back.location_id, len(back.log))
        want = (game.seed, game.day, round(game.credits), game.ship.name,
                game.location_id, len(game.log))
        assert got == want, f"{got} != {want}"
        return f"day {back.day}, {round(back.credits):,} credits, round trip"

    @check("every save carries a summary at its head, and it is the game's")
    def _():
        head = save_mod.save_path().read_text(encoding="utf-8")[:600]
        assert head.startswith('{"version": '), head[:40]
        got = slots.read_summary(save_mod.save_path())
        assert got is not None, "no summary read"
        want = {"seed": game.seed, "day": game.day,
                "credits": round(game.credits), "ship": game.ship.name,
                "chassis": game.ship.chassis, "system": game.system.name}
        wrong = {k: (got.get(k), v) for k, v in want.items() if got.get(k) != v}
        assert not wrong, f"summary disagrees with the game: {wrong}"
        at = head.find('"summary": ')
        assert 0 <= at < 64, f"the summary is at byte {at}, not the head"
        return f"at byte {at}: {got['system']}, day {got['day']}"

    @check("a listing reads the summary and never decodes a chronicle")
    def _():
        # A slot whose chronicle is ruined past its summary: a listing that
        # decoded would fail on it — and `save.read` would move it aside as
        # `.bad`, so merely drawing the title screen would hide the file.
        good = slots.slot_path("Before the envoy").read_text(encoding="utf-8")
        ruined = slots.slot_path("Ruined")
        ruined.write_text(good[:good.index('"state": ') + 20] + "#garbage")
        real_decode = save_mod.decode
        calls = []
        save_mod.decode = lambda obj: calls.append(1) or real_decode(obj)
        try:
            listed = {e["name"]: e for e in slots.listing()}
        finally:
            save_mod.decode = real_decode
        assert not calls, f"listing decoded {len(calls)} time(s)"
        assert "Ruined" in listed and listed["Ruined"]["summary"], (
            "a slot with a damaged body did not list by its summary")
        assert ruined.is_file(), "listing moved the damaged slot aside"
        kinds = sorted({e["kind"] for e in listed.values()})
        ruined.unlink()
        return f"{len(listed)} listed ({', '.join(kinds)}), 0 decodes"

    @check("a save written before summaries still loads and still lists")
    def _():
        old = slots.slot_path("From an older build")
        _plain(game, old)
        assert '"summary"' not in old.read_text(encoding="utf-8")[:200]
        seen = slots.read_summary(old)
        assert seen and seen["day"] == game.day and seen["seed"] == game.seed, (
            f"an old save summarised as {seen}")
        back = load_game(old)
        assert back is not None and back.day == game.day, "it did not load"
        old.unlink()
        return f"summarised from its body: day {seen['day']}"

    @check("deleting a slot removes that slot and nothing else")
    def _():
        slots.save_as("Second", game)
        save_mod.write(game.to_save(), slots.recovery_path())
        game.save()                                  # so a .bak exists
        others = [save_mod.save_path(), slots.backup_path(),
                  slots.recovery_path(), slots.slot_path("Before the envoy")]
        assert all(p.is_file() for p in others), [str(p) for p in others]
        res = slots.delete("Second")
        assert res["ok"], res["why"]
        assert not slots.slot_path("Second").exists()
        assert all(p.is_file() for p in others), "delete took something else"
        # No name walks out of the folder, and none reaches the save in play.
        for name in ("../save", "../../save.json", "", "Second"):
            assert not slots.delete(name)["ok"], f"deleted {name!r}"
        assert save_mod.save_path().is_file()
        return "one slot gone; the save in play, .bak, recovery and the rest kept"

    _screens(suite, tmp, game)


def _screens(suite: Suite, tmp: Path, game) -> None:
    """The title's picker and the menu's "Save as…", pressed."""
    check = suite.check
    try:
        from .test_ui import _use_offscreen
        _use_offscreen()
        from PyQt6.QtGui import QAction
        from PyQt6.QtWidgets import QApplication, QLineEdit, QPushButton
    except ImportError as err:
        print(f"  (slot screens skipped: PyQt6 not available — {err})")
        return
    from ..ui import theme
    from ..ui.title import TitleDialog

    app = QApplication.instance() or QApplication([])
    app.setStyleSheet(theme.stylesheet())

    def settle():
        for _ in range(3):
            app.processEvents()

    def pressed(dlg, text):
        return [b for b in dlg.findChildren(QPushButton)
                if b.text() == text and b.isVisibleTo(dlg)]

    @check("the title offers every chronicle on disk, with its buttons")
    def _():
        dlg = TitleDialog()
        dlg.dialog = lambda *a, **k: True
        entries = slots.listing()
        kinds = [e["kind"] for e in entries]
        assert len(pressed(dlg, "Resume")) == kinds.count("play") == 1
        assert len(pressed(dlg, "Delete")) == kinds.count("slot")
        assert len(pressed(dlg, "Load")) == len(entries) - 1
        # Delete, confirmed, removes the slot and the row after the click.
        pressed(dlg, "Delete")[0].click()
        settle()
        assert len(pressed(dlg, "Delete")) == kinds.count("slot") - 1
        assert len(slots.listing()) == len(entries) - 1
        dlg.deleteLater()
        return f"{len(entries)} chronicles offered: {', '.join(kinds)}"

    @check("loading a slot from the title hands back that chronicle")
    def _():
        slots.save_as("Loadable", game)
        dlg = TitleDialog()
        refused = []
        dlg.dialog = lambda *a, **k: refused.append(a[0]) or False
        row = next(b for b in pressed(dlg, "Load")
                   if "Loadable" in _row_text(b))
        row.click()
        assert dlg.game is None and refused, "loaded without saying so"
        dlg.dialog = lambda *a, **k: True
        row.click()
        assert dlg.game is not None and dlg.game.day == game.day
        dlg.deleteLater()
        return f"refused first ({refused[0]!r}), then loaded day {game.day}"

    @check("Save as keeps the live chronicle; a dismissed question keeps none")
    def _():
        from ..ui.window import MainWindow
        win = MainWindow(game)
        win.confirm = lambda *a, **k: True
        act = next(a for a in win.findChildren(QAction)
                   if a.text() == "Save as…")
        win.dialog = lambda *a, **k: None
        before = sorted(p.name for p in slots.slot_dir().glob("*.json"))
        act.trigger()
        after = sorted(p.name for p in slots.slot_dir().glob("*.json"))
        assert before == after, f"a dismissed Save as wrote {after}"

        def named(heading, widgets, buttons=(), **_k):
            box = next(w for w in widgets if isinstance(w, QLineEdit))
            box.setText("From the menu")
            return True
        win.dialog = named
        act.trigger()
        kept = slots.slot_path("From the menu")
        assert kept.is_file(), "Save as wrote nothing"
        assert slots.read_summary(kept)["day"] == game.day
        win.close()
        return f"{kept.name}, day {game.day}; dismissed: nothing written"

    @check("a chronicle opened from the title is saved at once")
    def _():
        # `refresh` autosaves when the calendar passes the day last saved,
        # and that mark belonged to the *old* chronicle: a new one at day 0
        # stayed unsaved until it caught up with the old one's calendar.
        from ..ui import title
        from ..ui.window import MainWindow
        win = MainWindow(game)
        win.dialog = lambda *a, **k: None
        win.save()
        fresh = new_game("slots-fresh-seed")
        real = title.ask_for_game
        title.ask_for_game = lambda *a, **k: fresh
        try:
            title.start_new_chronicle(win)
        finally:
            title.ask_for_game = real
        on_disk = slots.read_summary(save_mod.save_path())
        win.close()
        assert on_disk["seed"] == fresh.seed, (
            f"the save in play is still {on_disk['seed']}")
        return f"save in play is {on_disk['seed']} at day {on_disk['day']}"


def _row_text(button) -> str:
    """Every label on the row a picker button sits in."""
    from PyQt6.QtWidgets import QLabel
    row = button.parentWidget()
    return " ".join(lb.text() for lb in row.findChildren(QLabel))
