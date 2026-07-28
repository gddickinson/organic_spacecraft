"""The options page: one panel, shown either in a window or inside Help.

Deliberately one implementation. An options page that exists twice is a place
for two different sets of bounds to appear, and this project has spent enough
cycles on screens that disagreed with the thing they were describing.

`OptionsPanel` is the whole page. `OptionsDialog` is that panel in a window,
which is what the menu bar opens; the Help screen embeds the same widget.
Nothing here decides anything — `sim/options.py` holds the settings and their
bounds, and `core/llm.py` holds the speech state.
"""

from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (QComboBox, QDialog, QHBoxLayout, QLineEdit,
                             QScrollArea, QVBoxLayout, QWidget)

from ..core import llm
from ..sim import options as options_sim
from . import theme
from .widgets import Card, Panel, button, defer, label, note, spacer


class OptionsPanel(QWidget):
    """Every setting, and what each one does."""

    def __init__(self, win):
        super().__init__()
        self.win = win
        self.column = QVBoxLayout(self)
        self.column.setContentsMargins(0, 0, 0, 0)
        self.column.setSpacing(8)
        self._probed = None            # what `offer()` last said, if asked
        self.rebuild()

    # ── frame ──────────────────────────────────────────────────────────────

    def rebuild(self) -> None:
        while self.column.count():
            item = self.column.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        self.column.addWidget(note(
            "Everything here does something. There is no density slider that "
            "adjusts nothing and no difficulty label that multiplies by one — "
            "a check reads the package and fails if a setting stops being "
            "read."))

        play = Panel("Play")
        speech = Panel("Speech")
        for entry in options_sim.summary(self.win.game):
            target = speech if entry["name"].startswith(("llm_", "voices")) \
                else play
            target.add(self._setting(entry))
        self.column.addWidget(play)
        speech.add(spacer(4))
        speech.add(self._state())
        self.column.addWidget(speech)
        self.column.addStretch(1)

    def _set(self, name: str, value) -> None:
        result = options_sim.set_to(self.win.game, name, value)
        if not result.get("ok"):
            self.win.toast(result.get("why", "No."), "warn")
            return
        self.win.apply_options()
        self.win.save()
        self.rebuild()

    # ── one setting ────────────────────────────────────────────────────────

    def _setting(self, entry) -> Card:
        card = Card(selectable=False)
        card.add(label(entry["label"], "h3"))
        card.add(note(entry["doc"]))
        card.add({"bool": self._toggle, "choice": self._choice,
                  "text": self._text}.get(entry["kind"], self._number)(entry))
        return card

    def _toggle(self, entry) -> QWidget:
        return button("On" if entry["value"] else "Off",
                      lambda n=entry["name"], v=entry["value"]:
                      self._set(n, not v),
                      kind="primary" if entry["value"] else "")

    def _number(self, entry) -> QWidget:
        low, high = entry["bounds"]
        unit = "days" if entry["kind"] == "days" else "ms"
        step = max(1, (high - low) // 10)
        row = QWidget()
        line = QHBoxLayout(row)
        line.setContentsMargins(0, 0, 0, 0)
        line.addWidget(button("−", lambda n=entry["name"], v=entry["value"]:
                              self._set(n, v - step)))
        line.addWidget(label(f"{entry['value']} {unit}", "label"))
        line.addWidget(button("+", lambda n=entry["name"], v=entry["value"]:
                              self._set(n, v + step)))
        line.addWidget(label(f"({low}–{high})", "dim"))
        line.addStretch(1)
        return row

    def _choice(self, entry) -> QWidget:
        box = QComboBox()
        box.addItem("Whichever answers first", "")
        for candidate in llm.candidates():
            box.addItem(candidate.name, candidate.id)
        wanted = entry["value"] or ""
        index = box.findData(wanted)
        box.setCurrentIndex(index if index >= 0 else 0)
        # Deferred: `_set` rebuilds this panel, which frees the box that is
        # still emitting. Same hazard as the search field, same fix.
        box.currentIndexChanged.connect(
            lambda _i, b=box, n=entry["name"]:
            defer(lambda: self._set(n, b.currentData())))
        box.setFixedWidth(320)
        return box

    def _text(self, entry) -> QWidget:
        row = QWidget()
        line = QHBoxLayout(row)
        line.setContentsMargins(0, 0, 0, 0)
        box = QLineEdit(entry["value"])
        box.setPlaceholderText("blank — each provider's own default")
        box.setFixedWidth(320)
        box.editingFinished.connect(
            lambda b=box, n=entry["name"]:
            defer(lambda: self._set(n, b.text())))
        line.addWidget(box)
        line.addStretch(1)
        return row

    # ── what speech is actually doing ──────────────────────────────────────

    def _state(self) -> Panel:
        game = self.win.game
        p = Panel("What is answering")
        p.add(note(
            "The game writes every voice itself unless a model is both asked "
            "for and answering. Nothing is lost when there is none: the "
            "written path is the default and is what the whole suite "
            "measures."))
        p.add_row("Status", llm.describe())
        live = options_sim.voices_live(game)
        p.add_row("In use now",
                  "a model" if live else "the game's own writing",
                  tint="lumen" if live else None)

        if self._probed is None:
            p.add(note("Nothing has been asked yet — probing reaches out to "
                       "this machine, so it happens when you ask and not "
                       "before."))
        else:
            for found in self._probed:
                detail = f"{found['model']}"
                if found["needs"]:
                    detail += f" · needs {found['needs']}"
                p.add_row(f"{found['name']} — {detail}",
                          "answering" if found["answering"] else "no reply",
                          tint="chloro" if found["answering"] else "warn")
            if not self._probed:
                p.add(label("Nothing is configured on this machine. Run "
                            "Ollama, or export ANTHROPIC_API_KEY or "
                            "OPENAI_API_KEY, then look again.", "", "warn",
                            wrap=True))
        p.add(spacer(4))
        p.add_buttons(button("Look for models", self._look, kind="primary"),
                      button("Say something", self._sample))
        return p

    def _look(self) -> None:
        llm.reset()
        self._probed = llm.offer()
        self.rebuild()

    def _sample(self) -> None:
        """Hear a line, so 'a model is answering' is something you can check."""
        from ..sim import voice as voice_sim
        said = voice_sim.speak(self.win.game, "ship:self", persona="ship",
                               name=self.win.game.ship.name, kind="ship",
                               situation="greet",
                               fact="Reaction mass at sixty per cent")
        self.win.dialog(
            f"{said['speaker']} — {said['source']}",
            [label(said["line"], "", "chloro", wrap=True),
             note("Written by the game itself." if said["source"] == "written"
                  else f"Written by {llm.describe()}")])


class OptionsDialog(QDialog):
    """The options page in a window, which is what the menu bar opens."""

    def __init__(self, win):
        super().__init__(win)
        self.setWindowTitle("Options — SEEDFALL")
        self.setStyleSheet(theme.stylesheet())
        self.setMinimumSize(800, 640)
        column = QVBoxLayout(self)
        column.setContentsMargins(20, 18, 20, 16)
        column.setSpacing(8)
        column.addWidget(label("Options", "h1"))

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.Shape.NoFrame)
        scroll.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setWidget(OptionsPanel(win))
        column.addWidget(scroll, 1)
        column.addWidget(button("Done", self.accept, kind="primary"))
