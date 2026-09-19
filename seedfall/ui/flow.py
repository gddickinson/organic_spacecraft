"""Buttons that wrap onto as many lines as the width needs.

A line of buttons in a `QHBoxLayout` asks for the sum of their widths and
never wraps: four "Fly at <name>" buttons demanded 660 px of a 430 px column
on the Pilot screen, and the battle's twenty orders, laid out that way, set a
minimum wider than the screen at every size below 1,560 px.

`TabBar` wraps by chunking into rows of a fixed count, and says why it does
not use a height-for-width layout: inside a scroll area that negotiates badly
and collapses the column above it. This keeps plain rows and an honest
minimum height, and only changes *which widgets share a line* — on each
resize, from the width it was actually given — so the scroll area's usual
measure of `minimumSize` stays true.
"""

from __future__ import annotations

from PyQt6.QtCore import QSize
from PyQt6.QtWidgets import QHBoxLayout, QVBoxLayout, QWidget


class Flow(QWidget):
    """Widgets left to right, as many to a line as fit, each line packed on
    its own (a long button does not widen the column under it)."""

    def __init__(self, widgets=(), spacing: int = 6, line: int = 4):
        super().__init__()
        self._down = QVBoxLayout(self)
        self._down.setContentsMargins(0, 2, 0, 2)
        self._down.setSpacing(line)
        self._gap = spacing
        self._kids = [w for w in widgets if w is not None]
        self._lines: list[int] = []
        self._place([len(self._kids)] if self._kids else [])

    def per_line(self) -> list:
        """How many sit on each line at the width it has now."""
        return list(self._lines)

    def _widths(self) -> list:
        return [max(w.sizeHint().width(), w.minimumWidth()) for w in self._kids]

    def _fits(self, width: int) -> list:
        """Greedy: fill each line until the next one would not fit."""
        lines, used, count = [], 0, 0
        for w in self._widths():
            wanted = w if count == 0 else used + self._gap + w
            if count and wanted > width:
                lines.append(count)
                used, count = w, 1
            else:
                used, count = wanted, count + 1
        if count:
            lines.append(count)
        return lines

    def _place(self, lines: list) -> None:
        # The widgets stay parented to this one throughout; only the line
        # layouts holding them are taken down and made again.
        while self._down.count():
            item = self._down.takeAt(0)
            if item.layout() is not None:
                while item.layout().count():
                    item.layout().takeAt(0)
                item.layout().deleteLater()
        start = 0
        for count in lines:
            across = QHBoxLayout()
            across.setSpacing(self._gap)
            for w in self._kids[start:start + count]:
                across.addWidget(w)
            across.addStretch(1)
            self._down.addLayout(across)
            start += count
        self._lines = list(lines)

    def minimumSizeHint(self) -> QSize:  # noqa: N802
        base = super().minimumSizeHint()
        widths = self._widths()
        return QSize(max(widths) if widths else 0, base.height())

    def sizeHint(self) -> QSize:  # noqa: N802
        widths = self._widths()
        base = super().sizeHint()
        return QSize(sum(widths) + self._gap * max(0, len(widths) - 1),
                     base.height())

    def resizeEvent(self, ev):  # noqa: N802
        super().resizeEvent(ev)
        lines = self._fits(ev.size().width())
        if lines != self._lines:
            self._place(lines)
            self.updateGeometry()
