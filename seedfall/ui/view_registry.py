"""Which class draws which screen, and the one place that builds them all.

Split out of `ui/window.py` at the seam that was already there: the window
does navigation, the clock, the log and the rail, and this is the *table* of
what it navigates between. The window had grown past five hundred lines with
the import block and the table taking up a fifth of it, and the table is the
part that changes every time a screen is added.

The imports are inside the function on purpose. Twenty-six screens pulled in
at module scope is twenty-six import chains before a window can exist, and
several of them reach into `sim/` — which is fine at build time and not fine
at import time.
"""

from __future__ import annotations


def classes() -> dict:
    """Every screen id against the class that draws it.

    The ids here and the ids in `data/screens.py` are not the same set and
    are not meant to be: the rail names the screens a player can *open*, and
    this names every screen the window can *show*, including the ones another
    screen pushes you into — a battle, a docking, a crossing, an envoy.
    """
    from .battle_view import BattleView
    from .codex_view import CodexView
    from .concourse_view import ConcourseView
    from .crew_view import CrewView
    from .demand_view import DemandView
    from .despatch_view import DespatchView
    from .dig_view import DigView
    from .diplomacy_view import DiplomacyView
    from .empire_view import EmpireView
    from .envoy_view import EnvoyView
    from .expedition_view import ExpeditionView
    from .gunnery_view import GunneryView
    from .helm_view import HelmView
    from .help_view import HelpView
    from .law_view import LawView
    from .legacy_view import LegacyView
    from .map_view import MapView
    from .minigame_view import DecodingView, DockingView
    from .pilot_view import PilotView
    from .port_view import PortView
    from .ship_view import ShipView
    from .system_view import SystemView
    from .tech_view import TechView
    from .transit_view import TransitView
    from .yard_view import YardView

    return {
        "map": MapView, "system": SystemView, "port": PortView,
        "ship": ShipView, "yard": YardView, "tech": TechView,
        "empire": EmpireView, "codex": CodexView, "battle": BattleView,
        "ground": ExpeditionView, "helm": HelmView,
        "gunnery": GunneryView,
        "crew": CrewView,
        "concourse": ConcourseView,
        "pilot": PilotView,
        "diplomacy": DiplomacyView, "law": LawView,
        "despatches": DespatchView,
        "docking": DockingView, "decoding": DecodingView,
        "transit": TransitView, "dig": DigView, "legacy": LegacyView,
        "help": HelpView,
        "demand": DemandView,
        "envoy": EnvoyView,
    }


def build(win) -> None:
    """Make one of each, hide it, and put it on the window's stack."""
    for vid, cls in classes().items():
        view = cls(win)
        view.hide()
        win.stack_layout.addWidget(view)
        win.views[vid] = view
