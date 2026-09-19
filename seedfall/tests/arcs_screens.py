"""Officer arcs on disk and on the screens — run by `test_arcs`.

Split out of `test_arcs.py` at the length rule. A story saved mid-beat is
answered in a fresh process exactly as it is in this one; an officer from a
save written before stories existed is dealt theirs, the same every time;
and the Crew tab, the Despatches board and the Codex show them — pressed,
not merely built, and looking at them changes nothing.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

from ..core import save as save_mod
from ..data.arcs import ARCS, ARCS_BY_ID, SIGNATURES
from ..sim import arcs as arcs_sim
from . import arc_captain as cap

ROOT = Path(__file__).resolve().parents[2]


def report(game) -> dict:
    """What a fresh process reports back about the stories, and this one."""
    return {"credits": round(game.credits, 6), "day": game.day,
            "officers": [[o.id, o.arc, o.arc_beat, o.signature,
                          round(o.loyalty, 6), o.arc_state.get("chose"),
                          o.arc_state.get("place"),
                          bool(o.arc_state.get("sig"))]
                         for o in game.officers]}


def _saved_mid_story():
    """One officer's beat open and asking; another's armed and waiting."""
    game = cap.chronicle("arcs-save")
    first, second = game.officers[0], game.officers[1]
    cap.at_beat(game, first, "old_debts", 1)
    sig = cap.opened(game, first)
    cap.deal(game, second, "gambler")
    second.arc_beat = 1
    second.arc_state = {"chose": ["pay"], "next": int(game.day) + 1}
    game.advance_days(2)
    assert second.arc_state.get("armed") is not None
    return game, sig


def _texts(widget) -> list:
    from PyQt6.QtWidgets import QLabel
    return [w.text() for w in widget.findChildren(QLabel)]


def run(suite) -> None:
    check = suite.check

    @check("a chronicle saved mid-story is answered the same in a fresh "
           "process")
    def _():
        game, sig = _saved_mid_story()
        path = Path(tempfile.mkdtemp(prefix="seedfall-arcs-")) / "arcs.json"
        assert save_mod.write({"game": game}, path)
        code = ("import json\nfrom seedfall.core.state import load_game\n"
                "from seedfall.bridge import protocol\n"
                "from seedfall.tests.arcs_screens import report\n"
                f"g = load_game({str(path)!r})\n"
                f"said = protocol.VERBS['answer_signal'][0](g, {sig.id!r}, "
                "'pay')\n"
                "g.advance_days(30)\n"
                "print(json.dumps({'said': said, **report(g)}))\n")
        env = dict(os.environ, SEEDFALL_SAVE=str(path),
                   QT_QPA_PLATFORM="offscreen")
        proc = subprocess.run([sys.executable, "-c", code], env=env,
                              cwd=str(ROOT), capture_output=True, text=True,
                              timeout=300)
        lines = [l for l in proc.stdout.splitlines() if l.startswith("{")]
        assert lines, proc.stderr[-800:]
        there = json.loads(lines[-1])
        from ..bridge import protocol
        said = protocol.VERBS["answer_signal"][0](game, sig.id, "pay")
        game.advance_days(30)
        here = json.loads(json.dumps({"said": said, **report(game)}))
        assert there == here, (there, here)
        assert there["said"]["ok"] and there["officers"][0][2] == 2
        return (f"answered in a fresh process: beat {there['officers'][0][2]}"
                f" of 3, ₡{there['credits']:,.0f}, every officer's story equal")

    @check("an officer from a save before stories is dealt one, the same "
           "every time")
    def _():
        game = cap.chronicle("arcs-old-save")
        game.advance_days(200)
        dealt = [o.arc for o in game.officers]
        raw = save_mod.encode({"game": game})
        for officer in raw["game"]["officers"]:
            for field in ("arc", "arc_beat", "arc_state", "signature"):
                officer.pop(field, None)
        again = []
        for _ in range(2):
            old = save_mod.decode(json.loads(json.dumps(raw)))["game"]
            old.recompute()
            assert all(o.arc is None and o.arc_state == {}
                       for o in old.officers)
            ahead = arcs_sim.planned(old)
            old.advance_days(1)
            again.append([(o.arc, o.arc_state["next"]) for o in old.officers])
            assert [o.arc for o in old.officers] == list(ahead.values())
        assert again[0] == again[1], again
        assert [a for a, _next in again[0]] == dealt, (again[0], dealt)
        return f"dealt {', '.join(dealt)} — as on the first day, twice"

    from .qtkit import use_offscreen
    use_offscreen()

    @check("the Crew tab shows every officer's story at both sizes, and "
           "opening it changes nothing")
    def _():
        from . import qtkit
        from ..ui import theme
        qtkit.app().setStyleSheet(theme.stylesheet())
        seen = []
        for size in ((1040, 680), (1360, 880)):
            game, _sig = _saved_mid_story()
            third = game.officers[2]
            third.arc, third.arc_beat = "widow", 3
            third.signature = "remembered"
            win = qtkit.main_window(game, size)
            win.show()
            win.go("ship")
            # After the window is up: building one fills in the options and
            # the like, which is the window's business, not the tab's.
            frozen = (game.rng_seed, save_mod.encode({"game": game}))
            view = win.views["ship"]
            view.tab = "crew"
            view.refresh()
            texts = " ".join(_texts(view))
            for officer in game.officers:
                arc = ARCS_BY_ID[officer.arc]
                assert arc.title in texts, (arc.title, size)
            # A pill shouts its word (`widgets.Pill`), so ask in lower case.
            assert "remembered" in texts.lower() and "Lapses in" in texts
            assert (game.rng_seed, save_mod.encode({"game": game})) == \
                frozen, "opening the crew tab changed the chronicle"
            seen.append(f"{size[0]}×{size[1]}")
            win.close()
        return f"three stories and a signature at {', '.join(seen)}"

    @check("the Despatches board shows each beat with every answer costed, "
           "and pressing one answers it")
    def _():
        from PyQt6.QtWidgets import QPushButton
        from . import qtkit
        pressed = 0
        game = cap.chronicle("arcs-board")
        win = qtkit.main_window(game)
        officer = game.officers[0]
        for arc in ARCS:
            for index, beat in enumerate(arc.beats):
                cap.at_beat(game, officer, arc.id, index)
                sig = cap.opened(game, officer)
                win.go("despatches")
                view = win.views["despatches"]
                view.refresh()
                texts = " ".join(_texts(view))
                assert sig.subject in texts, sig.subject
                assert arcs_sim.preview(game, sig, beat.choices[0].key)[
                    "line"] in texts, "an answer's cost is not on the board"
                words = dict(sig.replies)[beat.choices[0].key]
                button = next(b for b in view.findChildren(QPushButton)
                              if b.text() == words)
                assert button.isEnabled(), words
                button.click()
                assert sig.answered == beat.choices[0].key, sig.answered
                assert officer.arc_beat == index + 1
                officer.signature = None
                pressed += 1
        assert pressed == 36, pressed
        return "36 beats on the board, each answered by its own button"

    @check("an answer the ship cannot pay for is greyed, and says why")
    def _():
        from PyQt6.QtWidgets import QPushButton
        from . import qtkit
        game = cap.chronicle("arcs-grey")
        officer = game.officers[0]
        cap.at_beat(game, officer, "old_debts", 1)
        sig = cap.opened(game, officer)
        game.credits = 100
        win = qtkit.main_window(game)
        win.go("despatches")
        view = win.views["despatches"]
        view.refresh()
        words = dict(sig.replies)["pay"]
        button = next(b for b in view.findChildren(QPushButton)
                      if b.text() == words)
        assert not button.isEnabled() and "treasury" in button.toolTip()
        others = [b for b in view.findChildren(QPushButton)
                  if b.text() in dict(sig.replies).values() and b.isEnabled()]
        assert len(others) == 2, [b.text() for b in others]
        return f"“{words}” greyed: {button.toolTip()}"

    @check("the Codex's crew page lists the stories told and every signature")
    def _():
        from . import qtkit
        game = cap.chronicle("arcs-codex")
        officer = game.officers[1]
        cap.deal(game, officer, "heir")
        cap.see_through(game, officer)
        win = qtkit.main_window(game)
        win.go("codex")
        view = win.views["codex"]
        view.tab = "crew"
        view.refresh()
        texts = " ".join(_texts(view))
        assert officer.name in texts and "Landed" in texts
        assert all(spec.name in texts for spec in SIGNATURES.values())
        assert len(arcs_sim.record(game)) >= 1 and len(ARCS) == 12
        return f"{officer.name}'s story told, and all twelve signatures"
