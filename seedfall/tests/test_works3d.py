"""Nineteen station classes, and whether any of them is its own structure.

Measured before `data/works3d.py` existed. Plant one of every colony class,
ask the game what is in the sky, and look up the mesh each one gets:

    colony anchorages: 19
    distinct meshes: 1

An ARCA Habitat holding a million people, a TARDIGRADE Vault, a VESPER Picket
and a Fabricator Yard were all four tanks in a frame — in the sky, on the
approach, and at the berth you make fast to. The codex tab that lists them had
no picture on it at all.

The claims:

- **Nineteen classes are nineteen structures**, measured as rendered
  silhouettes rather than as different tuples — two meshes can differ in every
  vertex and read as the same blob.
- **The picture is the specification.** A class that digs has roots, one that
  distils has a bell, one that builds hulls has a cradle, one that holds a town
  has a ring — every one of them read off the entry the card prints in words.
- **The berth is a fitting you can see**, and a work with nowhere to make fast
  holds you off on a boom instead of inventing one.
- **One size, not two.** The sky drew an anchorage at 0.6 km while the approach
  handed the conn 0.4 km for the same object. They come from one door now, and
  ARCA — the one habitat whose true size the documents state — comes out at the
  2.5 km the documents state.
- **The catalogue shows them**, at a size that fits the card.
- **The sky and the berth agree**: a planted holding reaches the window as its
  own class and is drawn as the structure it is.
"""

from __future__ import annotations

import math

from ..core.state import new_game
from ..data import berths3d, models3d, works3d
from ..data.colonies import COLONIES, COLONIES_BY_ID
from ..sim import anchorage as anchorage_sim
from ..sim import colony as colony_sim
from ..sim import sky as sky_sim
from ..sim import targets as targets_sim
from ..sim import track as track_sim
from .harness import Suite

SIZE = 150

#: What the GESTALT habitat document states, and the one figure the scale in
#: `works3d` is pinned to: ARCA is a 2.5 km drum holding a million people.
ARCA_KM = 2.5


def _app():
    from .test_ui import _use_offscreen
    _use_offscreen()
    from PyQt6.QtWidgets import QApplication
    app = QApplication.instance() or QApplication([])
    assert app is not None
    return app


def _mask(look: str) -> set:
    """The pixels one class of structure covers, at the attitude it is held."""
    from PyQt6.QtGui import QColor, QImage, QPainter
    from ..ui import render3d, thumb3d

    _app()
    image = QImage(SIZE, SIZE, QImage.Format.Format_RGB32)
    sky = QColor("#000000")
    image.fill(sky)
    painter = QPainter(image)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
    camera = render3d.Camera(at=(0, 0, 0), forward=(0, 0, 1), up=(0, 1, 0),
                             width=SIZE, height=SIZE,
                             half_fov=thumb3d.HALF_FOV)
    thumb3d.paint(painter, camera, "work", look)
    painter.end()
    return {(x, y) for y in range(SIZE) for x in range(SIZE)
            if image.pixel(x, y) != sky.rgb()}


def _overlap(a: set, b: set) -> float:
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


def _settled(seed="works3d"):
    """A game with one of every class planted and running."""
    game = new_game(seed)
    body = game.system.bodies[1]
    for index, c in enumerate(COLONIES):
        game.colonies.append(colony_sim.Colony(
            id=index + 1, class_id=c.id, name=c.name,
            system_id=game.system.id, body_id=body.id, need=0, online=True))
    return game


def run(suite: Suite) -> None:
    check = suite.check

    @check("nineteen classes, nineteen structures in the sky")
    def _():
        # The defect itself, through the game's own doors: plant them, ask the
        # sky, count the meshes that come back.
        game = _settled()
        places = [p for p in anchorage_sim.in_system(game)
                  if p.id.startswith("colony-")]
        assert len(places) == len(COLONIES), (
            f"{len(places)} of {len(COLONIES)} planted classes reached the sky")
        meshes = {id(models3d.for_sight("anchorage", p.look)) for p in places}
        assert len(meshes) == len(COLONIES), (
            f"{len(places)} holdings share {len(meshes)} meshes")
        return f"{len(places)} holdings, {len(meshes)} distinct meshes"

    @check("they are different pictures, not different tuples")
    def _():
        # Two meshes can differ in every vertex and render as the same blob.
        # This compares what lands on the screen.
        masks = {c.id: _mask(c.id) for c in COLONIES}
        for look, mask in masks.items():
            assert len(mask) > 400, f"{look} covers only {len(mask)} pixels"
        ids = sorted(masks)
        worst, pair = 0.0, None
        for i, one in enumerate(ids):
            for other in ids[i + 1:]:
                share = _overlap(masks[one], masks[other])
                if share > worst:
                    worst, pair = share, (one, other)
        # The bar, and the margin, both measured. As shipped the closest pair
        # is the Fabricator Yard against the Orbital Drydock — two cradles,
        # which is what they both are — and they share 63%. Before this file
        # every pair shared 100%, because every pair was the same mesh.
        assert worst < 0.72, f"{pair} share {worst:.0%} of their outline"
        return (f"{len(ids)} structures, worst pair {pair[0]}/{pair[1]} at "
                f"{worst:.0%}")

    @check("the picture is the specification")
    def _():
        # Not "it has some furniture" — the specific features the card's own
        # words demand, on the classes that print those words.
        want = {
            "radix_mine": "roots",          # yields ore
            "medusa_still": "bell",         # yields volatiles
            "lichen_dome": "dome",          # grown, solid ground, a town
            "pomona_grove": "fronds",       # yields biomass
            "gravid_nursery": "womb",       # gestates hulls, not welds them
            "orbital_dock": "cradle",       # a drydock, so a slipway
            "vesper_picket": "masts",       # a sensor picket
            "chorus_node": "dish",          # yields research
            "tardigrade_vault": "vault",
            "solforge": "mirror",           # the only class sited at a star
            "arca_drum": "drum",            # a million people, living inside
            "coral_reef": "ring",           # a town of two thousand
            "chorus_node": "vanes",         # it holds no station
            "monitor_station": "guns",      # wards the system
            "skimmer": "scoop",             # gas giants and nothing else
            "free_port": "arm",             # a port, so somewhere to tie up
            "xeno_array": "shards",
            "refinery": "stacks",           # yields alloy
        }
        for look, trait in want.items():
            traits = works3d.WORKS[look].traits
            assert trait in traits, f"{look} has no {trait}: {traits}"
        # And no two classes are the same list of features.
        sets = {}
        for c in COLONIES:
            sets.setdefault(works3d.WORKS[c.id].traits, []).append(c.id)
        same = {t: ids for t, ids in sets.items() if len(ids) > 1}
        assert not same, f"classes built from the same features: {same}"
        return (f"{len(want)} classes carry the feature their entry demands; "
                f"{len(sets)} distinct builds across {len(COLONIES)}")

    @check("a berth is a fitting the structure actually has")
    def _():
        # The lesson `sim/moorings` was fixed for: a berth computed from one
        # set of numbers and drawn from another is a picture that lies about
        # where you can tie up. Every fitting must sit on a face of the mesh.
        #
        # Swept, and worth writing down: moving `GANTRY_R` does *not* fail this
        # — the builder and the berths read the same constant, so the fitting
        # travels with the berth. That is the one door doing its job rather
        # than a hole in the check; offsetting the berths in `_berths` alone,
        # which is the disagreement this guards against, is CAUGHT.
        strays = []
        for c in COLONIES:
            work = works3d.WORKS[c.id]
            for name, at in work.points:
                near = min(math.dist(at, v) for v in work.mesh[0])
                # A fitting is drawn as a small box *around* its berth, so the
                # nearest vertex is a half-diagonal away rather than on it.
                # The largest of them is the cradle head at half-extent 0.08,
                # which is 0.08·√3 = 0.139 — the bar is just above that, and a
                # berth floating anywhere else is off by whole tenths.
                if near > 0.15:
                    strays.append((c.id, name, round(near, 3)))
        assert not strays, f"berths with no fitting under them: {strays}"
        # And the sort follows: nothing to make fast to means held off.
        held = [c.id for c in COLONIES
                if works3d.WORKS[c.id].sort == "standoff"]
        alongside = [c.id for c in COLONIES
                     if works3d.WORKS[c.id].sort == "fitting"]
        assert held and alongside, (held, alongside)
        for look in held:
            assert berths3d.berth_sort(look) == "standoff", look
            # The boom's reach is allowed for, so the hull waits off the end
            # of the gantry rather than inside the frame.
            out = max(math.dist(at, (0, 0, 0))
                      for _n, at in berths3d.berth_points(look))
            stub = max(math.dist(at, (0, 0, 0))
                       for _n, at in berths3d.hinge_points(look))
            assert out > stub * 2, f"{look}: berth {out:.2f} off a {stub:.2f} stub"
        return (f"{sum(len(works3d.WORKS[c.id].points) for c in COLONIES)} "
                f"berths, every one on a fitting · {len(alongside)} alongside, "
                f"{len(held)} on a boom")

    @check("one size, and it is the size the documents state")
    def _():
        # It was two: `sim/sky` drew an anchorage at 0.6 km and `sim/targets`
        # handed the approach 0.4 km for the same structure.
        game = _settled()
        seen = {s.name: s for s in sky_sim.build(game, None)
                if s.kind == "anchorage"}
        assert seen, "no anchorage in the sky"
        for contact in track_sim.contacts(game):
            if contact.kind != "anchorage":
                continue
            drawn = seen[contact.name].radius_km
            flown = targets_sim.target_from_contact(game, contact).radius_km
            assert abs(drawn - flown) < 1e-9, (
                f"{contact.name}: sky draws {drawn:.2f} km, the approach flies "
                f"to {flown:.2f} km")
        arca = works3d.size_km("arca_drum")
        assert abs(arca - ARCA_KM) < 0.01, (
            f"ARCA comes out at {arca:.2f} km against the documents' {ARCA_KM}")
        # A spread worth having: the biggest structure is not the smallest.
        sizes = [works3d.size_km(c.id) for c in COLONIES]
        assert max(sizes) / min(sizes) > 5.0, (min(sizes), max(sizes))
        return (f"sky and approach agree on {len(seen)} structures · ARCA "
                f"{arca:.2f} km · {min(sizes):.2f} to {max(sizes):.2f} km")

    @check("the catalogue shows them, and they fit on the card")
    def _():
        from ..ui import thumb3d
        # Framed from the models rather than by eye: nothing may reach the
        # edge of its own card.
        _rate, tilt = models3d.ATTITUDE["work"]
        half = thumb3d.WORK_AT * math.tan(thumb3d.HALF_FOV)
        tallest, who = 0.0, ""
        for c in COLONIES:
            for v in works3d.WORKS[c.id].mesh[0]:
                _x, y, _z = models3d.place(v, spin=0.6, tilt=tilt)
                if abs(y) > tallest:
                    tallest, who = abs(y), c.id
        assert tallest < half, (
            f"{who} runs {tallest:.2f} off the axis against a {half:.2f} frame")
        # And the card really carries a picture, through the real widget.
        keep = _app()
        assert keep is not None
        from ..ui.window import MainWindow
        window = MainWindow(new_game("codex-works"))
        window.toast = lambda *a, **k: None
        window.go("codex")
        view = window.views["codex"]
        view.tab = "colonies"
        view.refresh()
        works = [t for t in view.findChildren(thumb3d.Thumb)
                 if t.kind == "work"]
        window.close()
        assert len(works) == len(COLONIES), (
            f"{len(works)} portraits on {len(COLONIES)} colony cards")
        return (f"{len(works)} portraits on the colonies tab · tallest {who} "
                f"fills {tallest / half:.0%} of the frame")

    @check("a holding you planted is drawn as what you planted")
    def _():
        # End to end: the class id survives the anchorage, the plot and the
        # sky, and the window draws that class's structure at that class's
        # size — which is the whole chain the one mesh used to short out.
        game = _settled()
        for contact in track_sim.contacts(game):
            if contact.kind != "anchorage" or contact.berth not in COLONIES_BY_ID:
                continue
            look = contact.berth
            assert models3d.for_sight("anchorage", look) is \
                works3d.WORKS[look].mesh, f"{look} drawn as something else"
            target = targets_sim.target_from_contact(game, contact)
            assert target.berth == look
            assert abs(target.radius_km - works3d.size_km(look)) < 1e-9
        planted = [c.berth for c in track_sim.contacts(game)
                   if c.kind == "anchorage" and c.berth in COLONIES_BY_ID]
        assert len(planted) == len(COLONIES), planted
        return (f"{len(planted)} planted holdings, each drawn and flown to as "
                "its own class")
