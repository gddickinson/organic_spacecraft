"""What the deck canvas writes and draws besides the ground itself.

Split out of `ui/afoot_canvas.py` at the five-hundred-line ceiling: the
shape each kind of thing is drawn as, the line under the pointer, the
letters each person wears, and where a room's name is lettered. Pure
painting and reading — nothing here moves anything.
"""

from __future__ import annotations

from PyQt6.QtCore import QPointF, QRectF, Qt
from PyQt6.QtGui import QColor, QPen

from ..data.afoot_things import THING_BY_ID
from ..sim import afoot_fight, afoot_map
from ..sim.afoot_state import actor_at
from . import theme


def draw_thing(p, t, rect: QRectF, colour: QColor, tile: float) -> None:
    """One thing, as a small shape of its own."""
    p.setPen(QPen(colour, max(1.0, tile * 0.08)))
    p.setBrush(Qt.BrushStyle.NoBrush)
    k = t.kind
    inner = rect.adjusted(tile * 0.18, tile * 0.18, -tile * 0.18, -tile * 0.18)
    if k in ("door", "hatch"):
        if t.state in ("open", "broken"):
            p.drawLine(rect.topLeft(), rect.bottomLeft())
            p.drawLine(rect.topRight(), rect.bottomRight())
        else:
            fill = QColor(colour)
            fill.setAlpha(150 if t.state != "locked" else 230)
            p.fillRect(inner, fill)
            if t.state == "locked":
                p.setPen(QPen(QColor(theme.tint("warn")), 1.5))
                p.drawRect(inner)
    elif k in ("lift", "airlock", "gangway"):
        p.drawEllipse(inner)
        p.drawEllipse(inner.adjusted(tile * 0.14, tile * 0.14,
                                     -tile * 0.14, -tile * 0.14))
    elif k in ("counter", "desk", "table", "bench", "rack"):
        fill = QColor(colour)
        fill.setAlpha(90)
        p.fillRect(rect.adjusted(1, tile * 0.25, -1, -tile * 0.25), fill)
    elif k in ("locker", "crate", "strongbox"):
        fill = QColor(colour)
        fill.setAlpha(60 if t.state == "searched" else 140)
        p.fillRect(inner, fill)
        p.drawRect(inner)
    elif k in ("cargo", "machinery", "pillar"):
        fill = QColor(colour)
        fill.setAlpha(120)
        p.fillRect(rect.adjusted(1, 1, -1, -1), fill)
    elif k in ("console",):
        p.fillRect(inner, QColor(colour.red(), colour.green(), colour.blue(),
                                 110))
        p.drawLine(inner.topLeft(), inner.topRight())
    elif k in ("bed", "medbed"):
        p.drawRoundedRect(rect.adjusted(2, tile * 0.2, -2, -tile * 0.2), 3, 3)
    elif k in ("relic",):
        c = rect.center()
        r = tile * 0.36
        p.drawPolygon([QPointF(c.x(), c.y() - r), QPointF(c.x() + r, c.y()),
                       QPointF(c.x(), c.y() + r), QPointF(c.x() - r, c.y())])
    elif k in ("spore_node", "fault"):
        fill = QColor(colour)
        fill.setAlpha(80 if t.state == "done" else 200)
        p.setBrush(fill)
        p.drawEllipse(inner)
    elif k in ("spores", "breach"):
        dots = QColor(colour)
        dots.setAlpha(120)
        for fx, fy in ((0.3, 0.3), (0.7, 0.4), (0.45, 0.7)):
            p.fillRect(QRectF(rect.x() + rect.width() * fx,
                              rect.y() + rect.height() * fy, 2, 2), dots)
    elif k == "plant":
        p.drawEllipse(inner)
    else:
        p.drawRect(inner)


def hover_text(game, walk, square, now) -> str:
    """What is under the pointer, in one line — asked, never done."""
    if square is None:
        if walk.decks[walk.viewing].wrap:
            return (f"Round {walk.round} · {walk.mode} · a ring, no ends · "
                    "left-click to walk or act · right-click to go up to it")
        return (f"Round {walk.round} · {walk.mode} · "
                "left-click to walk or act · right-click to go up to it")
    x, y = square
    deck = walk.decks[walk.viewing]
    if not deck.was_seen(x, y) and square not in now:
        return "Nobody has looked there yet."
    bits = []
    room = next((r for r in walk.rooms if r.holds(walk.viewing, x, y)
                 and r.known), None)
    if room is not None:
        bits.append(room.name)
    who = actor_at(walk, walk.viewing, x, y)
    me = next((a for a in walk.actors if a.id == walk.selected), None)
    if who is not None and (who.side == "party" or square in now):
        bits.append(f"{who.name} ({who.mood if who.side == 'npc' else 'yours'}"
                    f", {who.status})")
        if who.side == "npc" and me is not None and who.standing:
            got = afoot_fight.terms(game, walk, me, who)
            if got["ok"]:
                lo, hi = afoot_fight.damage_range(me, who)
                bits.append(f"{got['odds']:.0%} to hit, {lo}–{hi}")
            else:
                bits.append(got["why"])
    for t in walk.things:
        if t.deck == walk.viewing and (t.x, t.y) == square:
            kind = THING_BY_ID.get(t.kind)
            bits.append(f"{kind.name.lower()}{' (' + t.state + ')' if t.state else ''}")
    if me is not None and me.deck == walk.viewing and who is None:
        route = afoot_map.path(walk, me, x, y)
        if route:
            cost = afoot_map.price(walk, me.deck, route, me)
            bits.append(f"{cost} to walk" + (
                f" ({me.mp} this round)" if walk.mode == "action" else ""))
    return " · ".join(bits) or "Deck."


def tokens(walk) -> dict:
    """The letters each person wears on the deck. The party wear their
    initials, two letters, so none of them is ever mistaken for the one-letter
    constable beside them — and two of the party with the same initials wear
    a letter and their place in the party instead."""
    out, seen = {}, {}
    mates = [a for a in walk.actors if a.side == "party"]
    for n, a in enumerate(mates):
        words = [w for w in a.name.split() if w[:1].isalpha()] or ["?"]
        mark = (words[0][:1] + (words[-1][:1] if len(words) > 1 else
                                words[0][1:2])).upper()
        seen.setdefault(mark, []).append((n, a))
    for mark, who in seen.items():
        for n, a in who:
            out[a.id] = mark if len(who) == 1 else f"{mark[0]}{n + 1}"
    for a in walk.actors:
        if a.side != "party":
            out[a.id] = (a.name[:1] or "?").upper()
    return out


def label_spot(room) -> tuple:
    """(x, y, run): where a room's name is lettered — the longest run of its
    floor on the first row that has any."""
    rows = room.mask or ["1" * room.w] * room.h
    for j, row in enumerate(rows):
        best, start, run = (0, 0), None, 0
        for i, c in enumerate(row + "0"):
            if c == "1":
                start = i if start is None else start
                run += 1
            elif start is not None:
                best = max(best, (run, start))
                start, run = None, 0
        if best[0]:
            return room.x + best[1], room.y + j, best[0]
    return room.x, room.y, room.w
