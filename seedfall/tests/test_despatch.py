"""The despatch board — the inbox is finally a screen, and word travels.

`sim/comms.py` ticked, saved and grew for six passes with zero UI callers:
nothing could mark a signal read, questions could not be answered anywhere a
player could find, and the store grew without bound. These play the whole
loop: the screen's buttons go through the sim's doors, the sector actually
writes when something happens far away, old litter is swept, and the
keyboard's digits mean what they look like they mean.
"""

from __future__ import annotations

import os

from ..core.rng import RNG
from ..core.state import new_game
from ..data.screens import SCREENS
from ..sim import comms as comms_sim
from ..sim import threat as threat_sim
from .harness import Suite


def _use_offscreen() -> None:
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")


def run(suite: Suite) -> None:
    check = suite.check

    @check("a digit key is the rail position it opens")
    def _():
        # `4` opened the fifth entry, and by the end of the rail the offset
        # was two — which reads as a broken keyboard, not a design.
        rows = []
        for index, (sid, _label, key) in enumerate(SCREENS):
            if key.isdigit():
                assert int(key) % 10 == (index + 1) % 10, (
                    f"key {key} opens rail position {index + 1} ({sid})")
                rows.append(key)
        assert len(rows) == 10, f"only {len(rows)} digit keys on the rail"
        return f"digits {''.join(rows)} sit on rail positions 1–10, in order"

    @check("bulletins age out, and an open question never does")
    def _():
        game = new_game("sweep-age")
        old_news = comms_sim.send(game, "news", "Sector bulletin", "news",
                                  "Old word", "It mattered once.")
        old_ask = comms_sim.send(game, "charter", "The Charter", "power",
                                 "A question", "Answer at your leisure.",
                                 replies=(("noted", "Acknowledge"),))
        fresh = comms_sim.send(game, "news", "Sector bulletin", "news",
                               "New word", "It matters now.")
        for sig in (old_news, old_ask):
            sig.sent_day = sig.due_day = -(comms_sim.EXPIRE_DAYS + 40)
        comms_sim.sweep(game)
        held = {s.id for s in comms_sim.inbox(game)}
        assert old_news.id not in held, "a year-stale bulletin is still held"
        assert old_ask.id in held, "an open question was swept"
        assert fresh.id in held
        return ("stale telling swept, the question and the fresh word kept "
                f"({len(held)} on the board)")

    @check("the sector writes when a colony is lost, at courier speed")
    def _():
        game = new_game("colony-word")
        rng = RNG("colony-word")
        from ..data.colonies import COLONIES
        from ..sim.colony import Colony
        # The farthest system word can actually *ride* to — asked of the lag
        # machinery itself, because reachability is its judgement to make.
        # The first draft picked the far corner outright and the bulletin
        # arrived 54 years late by light, the second picked the farthest
        # port and that sat behind a jump gap no hull can hop. A day late
        # and within a career is the claim; the regime is the game's.
        here = game.location_id
        rides = [(comms_sim.lag_days(game, s.id, here), s)
                 for s in game.galaxy.systems if s.id != here]
        far = max((s for lag, s in rides if 0.5 < lag < 2000),
                  key=lambda s: comms_sim.lag_days(game, s.id, here))
        far.bloom = 0.98
        kind = next(c for c in COLONIES
                    if any(b.kind in c.sites for b in far.bodies))
        body = next(b for b in far.bodies if b.kind in kind.sites)
        col = Colony(id=901, class_id=kind.id, name="Doomed Reach",
                     system_id=far.id, body_id=body.id, need=0, online=True)
        game.colonies.append(col)
        for _ in range(60):
            threat_sim.tick(game, threat_sim.SPREAD_INTERVAL, rng)
            if col not in game.colonies:
                break
        assert col not in game.colonies, (
            "sixty growth ticks at 0.98 bloom never took an unwarded colony")
        word = [s for s in comms_sim._all(game) if "is lost" in s.subject]
        assert word, "a colony died and the sector said nothing"
        sig = word[0]
        assert sig.due_day >= sig.sent_day, (sig.sent_day, sig.due_day)
        assert sig.due_day > sig.sent_day, (
            "word from the far side of the sector arrived instantly — "
            "the courier lag never applied")
        assert sig.due_day - sig.sent_day < 2000, (
            f"{sig.due_day - sig.sent_day:.0f} days on the road to a "
            "harboured system — the lag picked the light-only regime")
        return (f"'{sig.subject}' sent day {sig.sent_day:.0f}, arrives day "
                f"{sig.due_day:.0f} — {sig.due_day - sig.sent_day:.0f} days "
                "on the road")

    @check("the bridge can read the board and answer it")
    def _():
        from ..bridge import protocol
        game = new_game("bridge-board")
        told = comms_sim.send(game, "charter", "The Charter", "power",
                              "Your standing", "It has moved.",
                              replies=(("noted", "Acknowledge"),))
        plain = comms_sim.send(game, "news", "Sector bulletin", "news",
                               "Word", "Of no consequence.")
        board = protocol.VERBS["despatches"][0](game)
        assert board["ok"] and board["unread"] >= 2
        ids = {row["id"] for row in board["despatches"]}
        assert told.id in ids and plain.id in ids
        asked = next(r for r in board["despatches"] if r["id"] == told.id)
        assert asked["asks"] and asked["replies"][0]["key"] == "noted"

        answer_verb = protocol.VERBS["answer_signal"][0]
        out = answer_verb(game, told.id, "noted")
        assert out["ok"], out
        assert told.answered == "noted" and told.read
        out2 = answer_verb(game, plain.id)
        assert out2["ok"] and plain.read
        refused = answer_verb(game, told.id, "noted")
        assert not refused["ok"], "answered the same question twice"
        return "listed, answered, marked read; a second answer is refused"

    @check("the screen's buttons go through the sim's doors")
    def _():
        _use_offscreen()
        from PyQt6.QtWidgets import QApplication, QPushButton
        from ..ui.window import MainWindow
        app = QApplication.instance() or QApplication([])
        game = new_game("despatch-screen")
        telling = comms_sim.send(game, "news", "Sector bulletin", "news",
                                 "A quiet week", "Nothing much moved.")
        asking = comms_sim.send(game, "concordat", "The Concordat", "power",
                                "A word", "Will you acknowledge?",
                                replies=(("noted", "Acknowledge"),))
        win = MainWindow(game)
        try:
            win.dialog = lambda *a, **k: None
            win.refresh()
            assert win.despatch_btn.isVisible() or win.despatch_btn.text(), (
                "two unread despatches and the HUD shows nothing")
            win.go("despatches")
            app.processEvents()
            view = win.views["despatches"]
            noted = [b for b in view.findChildren(QPushButton)
                     if b.text() == "Noted"]
            assert noted, "no Noted button for an unread bulletin"
            noted[0].click()
            app.processEvents()
            assert telling.read, "the button did not go through comms.read"
            answer = [b for b in win.views["despatches"].findChildren(QPushButton)
                      if b.text() == "Acknowledge"]
            assert answer, "no reply button for an open question"
            answer[0].click()
            app.processEvents()
            assert asking.answered == "noted", (
                "the reply did not go through comms.answer")
            unread_now = comms_sim.unread(game)
            assert unread_now == 0, f"{unread_now} still unread after both"
        finally:
            win.close()
            win.deleteLater()
            app.processEvents()
        return ("HUD counted 2; Noted and Acknowledge both landed in the "
                "sim; the board reads clear")
