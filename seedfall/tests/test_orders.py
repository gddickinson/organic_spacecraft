"""Standing-orders checks — the index that makes fifteen systems findable.

Each cycle added a system that was perfectly discoverable to whoever had just
built it. A new captain got a sector chart, one line of log, and no indication
that commissions, consorts, colony works or the research bench existed. These
hold the orders panel to naming things that are actually true, to never going
quiet on a captain who has something worth doing, and to shutting up about
anything already dealt with.
"""

from __future__ import annotations

from ..core.rng import RNG
from ..core.state import new_game
from ..data import chassis as chassis_data
from ..data.orders import ORDERS, ORDERS_BY_ID, SHOWN
from ..data.parts import PARTS
from ..sim import colony as colony_sim
from ..sim import loading, orders
from ..sim import research as research_sim
from ..sim import ventures as venture_sim
from ..sim.orders import PREDICATES
from ..sim.ship import build_layers, make_ship
from ..ui.window import NAV
from .harness import Suite


def _seeded(game):
    """A game able to plant colonies and pay for things."""
    game.credits = 400000
    game.ship.fitted.append("seed_bay")
    game.research.unlocked.append("bioleach")
    game.recompute()
    for key in ("alloy", "ore", "biomass", "volatiles"):
        game.stores[key] = 9000
    return game


def _states():
    """A spread of games covering what a captain might be in the middle of."""
    out = {}

    out["fresh"] = new_game("orders-fresh")

    stressed = new_game("orders-stress")
    stressed.credits = 0
    stressed.ship.cargo = {}
    stressed.ship.o2 = 0.2
    for layer in stressed.ship.layers:
        layer.hp = 0
    out["stressed"] = stressed

    unhappy = new_game("orders-crew")
    unhappy.officers[0].loyalty = 20.0
    out["restless crew"] = unhappy

    settler = _seeded(new_game("orders-colony"))
    out["able to settle"] = settler

    grown = _seeded(new_game("orders-works"))
    body = next(b for b in grown.system.bodies
                if b.kind in ("asteroid", "moon", "rocky"))
    colony_sim.found(grown, grown.system, body, "radix_mine")
    grown.advance_days(200)
    out["colony online"] = grown

    fleeted = new_game("orders-fleet")
    escort = make_ship("vesper", ["mag_lance", "reaction_organ", "opsin_eyes"],
                       "Kestrel")
    build_layers(escort, fleeted.bonuses)
    fleeted.fleet.append(escort)
    out["second hull"] = fleeted

    political = new_game("orders-politics")
    political.credits = 200000
    venture_sim.start(political, RNG("v"), "charter")
    out["venture live"] = political

    starved = new_game("orders-bench")
    tech = next(t for t in research_sim.researchable(starved.research.unlocked))
    research_sim.set_project(starved.research, tech.id)
    starved.research.evidence = {}
    starved.advance_days(30)
    out["starved bench"] = starved

    heavy = new_game("orders-heavy")
    chassis = heavy.ship.chassis_def
    for slot, count in chassis.slots.items():
        options = [p for p in PARTS if p.slot == slot
                   and chassis_data.accepts_family(chassis, p.family)]
        options.sort(key=lambda p: -p.mass)
        for part in options[:count]:
            if part.id not in heavy.ship.fitted:
                heavy.ship.fitted.append(part.id)
    heavy.ship.cargo = {"ore": 200}
    heavy.recompute()
    out["overloaded"] = heavy

    # A system whose bodies have all been looked at: nothing left to survey,
    # somewhere worth landing, and a chart worth selling.
    charted = new_game("orders-charted")
    charted.credits = 200000
    for body in charted.system.bodies:
        body.surveyed = True
    out["charted system"] = charted

    return out


def run(suite: Suite) -> None:
    check = suite.check

    @check("every order has a predicate, and every predicate an order")
    def _():
        listed = {o.id for o in ORDERS}
        coded = set(PREDICATES)
        assert listed == coded, (
            f"orders without a predicate: {sorted(listed - coded)}; "
            f"predicates without an order: {sorted(coded - listed)}")
        destinations = {vid for vid, *_ in NAV}
        bad = [o.id for o in ORDERS if o.goes_to not in destinations]
        assert not bad, f"orders pointing at screens that do not exist: {bad}"
        for order in ORDERS:
            assert order.title and order.text, f"{order.id} says nothing"
            assert order.weight > 0, f"{order.id} can never sort"
        return f"{len(ORDERS)} orders, all wired and all pointing somewhere real"

    @check("every order can actually fire")
    def _():
        # An order nobody can ever trigger is a line of prose in a table.
        fired = set()
        for game in _states().values():
            fired |= set(orders.summary(game)["ids"])
        # A few need a specific moment; construct those directly.
        port = new_game("orders-port")
        port.credits = 400000
        fired |= set(orders.summary(port)["ids"])
        traded = new_game("orders-trade")
        traded.ship.cargo = {}
        fired |= set(orders.summary(traded)["ids"])

        never = [o.id for o in ORDERS if o.id not in fired]
        assert not never, f"orders that never fire in any state tried: {never}"
        return f"all {len(ORDERS)} fired across {len(_states()) + 2} states"

    @check("no predicate raises, whatever state it is handed")
    def _():
        # sim.orders swallows exceptions so a broken predicate cannot take a
        # screen down with it. That means the suite is the only thing that will
        # ever see one, so call them unguarded.
        for label, game in _states().items():
            for order_id, predicate in PREDICATES.items():
                try:
                    predicate(game)
                except Exception as err:      # noqa: BLE001 - reporting it
                    raise AssertionError(
                        f"{order_id} raised {type(err).__name__} on the "
                        f"{label!r} state: {err}") from err
        return f"{len(PREDICATES)} predicates × {len(_states())} states, all clean"

    @check("a brand-new captain is told something useful")
    def _():
        game = new_game("orders-firstrun")
        standing = orders.standing(game)
        assert standing, "a new captain is told nothing at all"
        assert len(standing) <= SHOWN, f"{len(standing)} orders is not advice"
        ids = {o.id for o in standing}
        # The things a first turn should point at: work on offer, and the
        # research and survey loops nobody would otherwise open a screen for.
        assert ids & {"commission", "contracts", "rumour"}, (
            f"nothing about the work available: {ids}")
        assert "research" in ids, "nobody tells a new captain to set a project"
        return ", ".join(o.id for o in standing)

    @check("what is urgent outranks what is merely worth doing")
    def _():
        game = new_game("orders-urgent")
        game.credits = 0
        game.ship.cargo = {}
        game.ship.o2 = 0.2
        standing = orders.standing(game)
        assert standing, "a ship in trouble is told nothing"
        weights = [o.weight for o in standing]
        assert weights == sorted(weights, reverse=True), (
            f"orders are not sorted by urgency: {weights}")
        assert standing[0].weight >= 90, (
            f"the most pressing thing shown is {standing[0].id!r}, with air "
            "running out and no fuel aboard")
        return f"most pressing first: {standing[0].id} ({standing[0].weight})"

    @check("an order goes quiet once it is dealt with")
    def _():
        # Advice that never stops being given is noise.
        game = new_game("orders-quiet")
        assert orders.applies(game, "research"), "no project set, yet no advice"
        tech = next(t for t in research_sim.researchable(game.research.unlocked))
        research_sim.set_project(game.research, tech.id)
        assert not orders.applies(game, "research"), (
            "still being told to set a project after setting one")

        fuelled = new_game("orders-quiet2")
        fuelled.ship.cargo = {"volatiles": 0}
        assert orders.applies(fuelled, "fuel"), "no fuel, yet no warning"
        fuelled.ship.cargo = {"volatiles": 60}
        assert not orders.applies(fuelled, "fuel"), "still warned with a full tank"

        settler = _seeded(new_game("orders-quiet3"))
        assert orders.applies(settler, "colony"), "able to settle, yet no advice"
        body = next(b for b in settler.system.bodies
                    if b.kind in ("asteroid", "moon", "rocky"))
        colony_sim.found(settler, settler.system, body, "radix_mine")
        assert not orders.applies(settler, "colony"), (
            "still told to settle a system already settled")
        return "research, fuel and settling all fall silent once handled"

    @check("nothing on the Game is written and never read")
    def _():
        # A levy used to increment a counter that nothing anywhere consulted:
        # the venture succeeded, the save grew a number, and the sector was
        # exactly as it had been. Any persistent field wants a reader.
        import ast
        import pathlib as pl
        from ..core.state import Game

        root = pl.Path(__file__).resolve().parents[1]
        sources = [f for f in root.rglob("*.py") if f.parent.name != "tests"]
        blob = "\n".join(f.read_text() for f in sources)

        fields = [f.name for f in Game.__dataclass_fields__.values()
                  if not f.name.startswith("_")]
        unread = []
        for name in fields:
            reads = 0
            for source in sources:
                tree = ast.parse(source.read_text())
                for node in ast.walk(tree):
                    # An attribute access that is not the target of an assignment.
                    if isinstance(node, ast.Attribute) and node.attr == name:
                        if isinstance(node.ctx, ast.Load):
                            reads += 1
                    if isinstance(node, ast.Constant) and node.value == name:
                        reads += 1        # getattr(game, "name", ...)
            if reads == 0:
                unread.append(name)
        assert not unread, (
            "fields on Game that nothing ever reads: " + ", ".join(unread))
        return f"{len(fields)} fields on Game, all read somewhere"

    @check("the panel never floods the screen")
    def _():
        worst = 0
        for label, game in _states().items():
            shown = orders.standing(game)
            worst = max(worst, len(shown))
            assert len(shown) <= SHOWN, (
                f"{len(shown)} orders shown on the {label!r} state")
        return f"at most {worst} shown of {SHOWN} allowed"
