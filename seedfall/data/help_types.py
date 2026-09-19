"""The shape of a manual topic — shared by `data/help.py` and `data/help_more.py`."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Topic:
    id: str
    title: str
    screen: str              # which view this is about, "" for general
    body: tuple              # paragraphs
    #: Generated lines, by id, resolved in `sim/manual.py`.
    facts: tuple = ()
    see: tuple = ()          # other topic ids
