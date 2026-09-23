"""A world's surface, drawn: terrain, what is on it, and where to set down.

The screen for `sim/worldmap.py` and `sim/worldsites.py`. It owns no rules —
the map is derived in the sim and this paints it — and it is deliberately
the same picture the landing zone is drawn as (`ui/zone_canvas.ZoneMap`):
tinted tiles, a letter in a ring for anything on one, and a legend under it,
because ten kinds of place share six colours and three of those are green.

Picking a cell says what is there. A cell with a place on it names the
place; an empty one names the ground and what it costs to cross
(`data/expedition.TERRAIN`), which is the number that decides a route once
a party is down there.
"""

from __future__ import annotations

from PyQt6.QtCore import QRectF, Qt, pyqtSignal
from PyQt6.QtGui import QColor, QFont, QPainter, QPen
from PyQt6.QtWidgets import QSizePolicy, QWidget

from ..data.expedition import TERRAIN
from ..sim import descent as descent_sim
from ..sim import worldmap, worldsites
from ..world.planets import BODY_KINDS
from . import painting, theme
from .widgets import Panel, View, button, label, mono_label, note

#: How big a cell is drawn. A world is 24 × 14, so this fits the minimum
#: window with the panel beside it.
CELL = 30


class WorldCanvas(QWidget):
    """The map: one tile a cell, a mark for anything standing on one."""

    picked = pyqtSignal(int, int)

    def __init__(self, view):
        super().__init__()
        self.view = view
        self.setFixedSize(CELL * worldmap.WIDE + 2, CELL * worldmap.HIGH + 2)
        self.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

    def mousePressEvent(self, ev):                      # noqa: N802
        x = int(ev.position().x() // CELL)
        y = int(ev.position().y() // CELL)
        if 0 <= x < worldmap.WIDE and 0 <= y < worldmap.HIGH:
            self.picked.emit(x, y)

    @painting.safe_paint
    def paintEvent(self, _ev):                          # noqa: N802
        body = self.view.body()
        if body is None:
            return
        game = self.view.game
        world = worldmap.of(game, body)
        here = {(s.x, s.y): s for s in worldsites.of(game, body)}
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        for cell in world.cells:
            box = QRectF(cell.x * CELL + 1, cell.y * CELL + 1,
                         CELL - 1, CELL - 1)
            tint = QColor(theme.tint(TERRAIN[cell.terrain].tint))
            # Height as shade, so a map reads as ground rather than as a
            # chart: the same terrain is darker in a trench than on a rise.
            shade = 0.55 + 0.45 * cell.height
            tint = QColor(int(tint.red() * shade), int(tint.green() * shade),
                          int(tint.blue() * shade))
            if cell.water:
                tint = tint.darker(150)
            p.fillRect(box, tint)
            if (cell.x, cell.y) == self.view.cell:
                p.setPen(QPen(QColor(theme.tint("lumen")), 2))
                p.drawRect(box)
        for (x, y), site in here.items():
            box = QRectF(x * CELL + 1, y * CELL + 1, CELL - 1, CELL - 1)
            colour = QColor(theme.tint(site.what.tint))
            p.setPen(QPen(colour, 2))
            p.drawEllipse(box.adjusted(3, 3, -3, -3))
            p.setFont(QFont(theme.mono_family(), 12, QFont.Weight.Bold))
            p.drawText(box, Qt.AlignmentFlag.AlignCenter, site.what.mark)
        p.end()


class WorldMapView(View):
    """The surface of the world the ship is in orbit of."""

    title = "The surface"

    def __init__(self, win):
        super().__init__(win)
        #: The cell the captain has a finger on.
        self.cell: tuple = (-1, -1)
        self.canvas = None

    def body(self):
        """The world being looked at: the one she is in orbit of."""
        return descent_sim.in_orbit(self.game)

    def build(self) -> None:
        game = self.game
        body = self.body()
        if body is None or not BODY_KINDS[body.kind][2]:
            self.head("The surface", descent_sim.says(game))
            self.buttons(button("Back to the system",
                                lambda: self.win.go("system")))
            self.col.addStretch(1)
            return
        world = worldmap.of(game, body)
        self.head(f"{body.name} — the surface",
                  worldmap.says(game, body))
        self.canvas = WorldCanvas(self)
        self.canvas.picked.connect(self._pick)
        self.row(self.canvas, self._beside(game, body, world))
        self.col.addStretch(1)

    def _beside(self, game, body, world) -> Panel:
        p = Panel("What is down there")
        p.add(note(worldsites.says(game, body)))
        p.add(mono_label("The ground"))
        counts = sorted(((world.count(t), t) for t in TERRAIN), reverse=True)
        for many, tid in counts:
            if not many:
                continue
            p.add_row(TERRAIN[tid].name,
                      f"{many} cell{'' if many == 1 else 's'} · "
                      f"{TERRAIN[tid].cost}d to cross")
        here = [s for s in worldsites.of(game, body)]
        if here:
            p.add(mono_label("What is on it"))
            for site in here:
                p.add_row(f"{site.what.mark}  {site.name}",
                          site.what.name + (f" · {site.heads:,}"
                                            if site.heads else ""),
                          site.what.tint)
        x, y = self.cell
        if 0 <= x < worldmap.WIDE and 0 <= y < worldmap.HIGH:
            cell = world.at(x, y)
            p.add(mono_label("Where your finger is"))
            standing = worldsites.at(game, body, x, y)
            p.add_row(f"{cell.lat:+.0f}°, {cell.lon:+.0f}°",
                      standing.name if standing is not None
                      else TERRAIN[cell.terrain].name)
            p.add(label(standing.what.blurb if standing is not None
                        else TERRAIN[cell.terrain].blurb, "", wrap=True))
        p.add(note("A landing party goes down from orbit in the lander. "
                   "What this map shows is the ground they will be "
                   "walking: pick a cell and set down on it."))
        ok, why = self._may_land(game, body)
        fly = button("Fly her down yourself", self._fly, kind="primary",
                     enabled=ok, why=why)
        fly.setObjectName("surface_fly")
        down = button("Send the party down", self._land, enabled=ok, why=why)
        down.setObjectName("surface_land")
        p.add_buttons(fly, down)
        p.add(note("Flying her down puts you in the cockpit for the "
                   "descent, and the minutes are the flight's. Sending "
                   "them is an order to an officer, and costs three days."))
        return p

    def _may_land(self, game, body) -> tuple:
        """May a party go down on the cell in hand? `(ok, why)`."""
        x, y = self.cell
        if not (0 <= x < worldmap.WIDE and 0 <= y < worldmap.HIGH):
            return False, "Pick somewhere on the map first."
        if worldmap.of(game, body).at(x, y).water:
            return False, "That is under water. A lander wants ground."
        if game.expedition is not None and not game.expedition.over:
            return False, "A party is already on the ground."
        if not body.surveyed:
            return False, "Survey it from orbit first."
        craft = descent_sim.best(game, body)
        if craft is None:
            return False, descent_sim.why_none(game, body)
        return True, ""

    def _ask_load(self):
        """How much goes down with them, or None if they stay aboard."""
        from ..data.expedition import SUPPLY_LOADS
        return self.win.dialog(
            "How long down there?",
            [label("The lander's hold carries the supplies, the vehicle and "
                   "the camp. What will not fit stays aboard.", "",
                   wrap=True)],
            [(row[0], n) for n, row in enumerate(SUPPLY_LOADS)]
            + [("Stay aboard", None)])

    def _party(self, game, craft) -> list:
        """Who rides down: as many as her seats leave room for."""
        from ..sim import descent as descent_sim
        room = descent_sim.party_room(craft)
        return [o.id for o in game.officers][:room]

    def _fly(self) -> None:
        """Take her down yourself (`sim/descent_flight`)."""
        from ..sim import descent as descent_sim
        from ..sim import descent_flight
        game = self.game
        body = self.body()
        ok, why = self._may_land(game, body)
        if not ok:
            self.win.toast(why, "warn")
            return
        craft = descent_sim.best(game, body)
        picked = self._ask_load()
        if picked is None:
            return
        got = descent_flight.begin(
            game, craft, game.system.bodies.index(body), cell=self.cell,
            load=int(picked), officer_ids=self._party(game, craft))
        if not got.get("ok"):
            self.win.toast(got.get("why", "She stays on the cradle."), "warn")
            return
        self.win.refresh()
        from .craft_window import open_cockpit
        open_cockpit(self.win)

    def _land(self) -> None:
        """Put a party down on the cell in hand (`sim/fieldwork`)."""
        from ..sim import descent as descent_sim
        from ..sim import fieldwork as fieldwork_sim
        game = self.game
        body = self.body()
        ok, why = self._may_land(game, body)
        if not ok:
            self.win.toast(why, "warn")
            return
        picked = self._ask_load()
        if picked is None:
            return
        index = game.system.bodies.index(body)
        got = fieldwork_sim.launch_expedition(
            game, index, self._party(game, descent_sim.best(game, body)),
            load=int(picked), at=self.cell)
        if not got.get("ok"):
            self.win.toast(got.get("why", "She stays on the cradle."), "warn")
            return
        self.win.refresh()
        self.win.go("ground")

    def _pick(self, x: int, y: int) -> None:
        self.cell = (x, y)
        self.refresh()
