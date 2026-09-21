"""The package maps: one `INTERFACE.md` per package, written from the code.

    python -m seedfall.tests.maps --write    # regenerate every package map
    python -m seedfall.tests.maps            # say which maps are out of date

`seedfall/INTERFACE.md` grew to 6,383 lines by being written by hand; a map
that has to be remembered goes stale the day a module is added, and one that
large stops being read. So each package's map is *generated*: one row per
module, the row being the first sentence of that module's own docstring, in
groups named below. The top-level `seedfall/INTERFACE.md` stays hand-written
and short, and says why the pieces are shaped as they are; the `maps` suite
fails when a package map is missing a module or names one that is gone.
"""

from __future__ import annotations

import ast
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]

PACKAGES = {
    "core": "Engine primitives: the save, ids, the clock and its phases. No rules, no Qt.",
    "data": "Static content tables. Pure data: no logic, no Qt.",
    "world": "Generated content: the sector, the Reaches, planets, markets.",
    "sim": "Game rules. Never imports Qt.",
    "ui": "PyQt6 presentation. Holds no rules; sim acts log themselves.",
    "bridge": "Driving a game from outside the window: protocol, server, client.",
    "tests": "The suites (`python -m seedfall.tests`) and the kits they share.",
}

#: Groups for the two big packages, in reading order. A module not named here
#: lands in "Everything else", so a new module is never missing, only filed.
GROUPS = {
    "sim": [
        ("The ship and its fittings", "ship stats plans loading thrusters shipyard stores services "
         "abilities damage adaptation readiness"),
        ("Flying: the conn and the flight deck", "conn conn_open conn_step flightdeck freeflight autopilot "
         "attitude pilot preview instruments outcome collision detection track "
         "targets bays moorings moorings_steer knock impulse tug control clearance telemetry "
         "sheer forcing berthing anchorage orbits orbit_heights elements shock"),
        ("Getting anywhere", "actions flight heliocentric burnplan burn_incidents path reach "
         "transit dormancy passage wayhome gates weave gatetraffic regions relight"),
        ("Fighting", "combat battle_state tactical stations turnplan enemy_ai doctrine gunnery "
         "firing gunfire shooting assessment parley prize aftermath engage consorts "
         "turret gunsight foes skirmish drills manning"),
        ("Rivals and the hunt", "nemeses rivals rival_ends hunts running_dark hostiles"),
        ("Trade, freight and money", "trade market profile shore freight freightlines linetrips lineroute "
         "lineforecast lineledger haulers masters wharfage customs exchequer "
         "exchequer_ledger exchequer_payback industry commitments contracts chains"),
        ("Surveying, mining and the ground", "survey mining charts intel rumours notes fieldwork "
         "expedition expedition_gen landing weather biology dig xeno programmes"),
        ("Research", "research inquiry"),
        ("Holdings", "colony works settlement robots telepresence territory interdiction"),
        ("The powers, the law and the Assembly", "diplomacy diplomacy_acts accord allegiance approach "
         "ventures war armada fleets grudge officials law governance dockets "
         "tribunal debts warrants enforce clemency piracy assembly "
         "assembly_session assembly_vote assembly_lobby"),
        ("The crew and their stories", "crew roster loyalty lifespan upkeep arcs "
         "arc_beats arc_places lifepath checks person"),
        ("The Bloom and the endings", "threat bloom responses legacy"),
        ("The Kith and the sky", "kith kith_acts kith_world phenomena phenomena_tick "
         "phenomena_forecast phenomena_bodies phenomena_shelter phenomena_nova "
         "phenomena_science sky"),
        ("Voices, news and memory", "comms hail voice memory traffic encounters"),
        ("Renown, counsel and the memoir", "renown renown_facts renown_perks counsel "
         "counsel_sources counsel_doors counsel_kit memoir"),
        ("Starting, teaching and settings", "beginning tutorial tutorial_watch manual options "
         "orders minigames"),
    ],
    "ui": [
        ("The window", "app window window_dialogs menubar hud log_panel crash popout monitors "
         "title chronicle_picker seed_dialog beginning_view tutorial_bar focus flow "
         "view_base widgets theme painting layer_row endings"),
        ("The chart and the system", "map_view star_chart reaches_chart sky_chart system_view "
         "survey_panel crossing_panel anchorage_panel traffic_panel life_panel "
         "mesh_panel orbit_chart reaches_panel sky_strip weave_panel spheres surface"),
        ("Flying", "helm_view pilot_view pilot_panels pilot_acts conn_window "
         "conn_controls conn_panel "
         "conn_moves conn_targets flight_window flight_clock flying_keys autopilot_bar "
         "approach_window approach_plot viewport viewport_hud viewport_mark "
         "viewport_math viewport_target sights mount_sight thrust_pad gauges plot_canvas "
         "plot3d_window render3d stars3d thumb3d "
         "effects effect_paint effect_marks effect_clock"),
        ("Fighting", "battle_view battle_orders battle_text battle3d tactical_plot tactical_board "
         "tactical_window gunner_window fire_panel firing_panel doctrine_panel "
         "assessment_panel hunts_panel hunt_marks "
         "gunnery_view turret_window turret_view turret_scene turret_hud "
         "turret_panels turret_controls"),
        ("Port, trade and the yard", "port_view market_grid board_panel commissions_panel "
         "freight_panel register_panel blackmarket_panel berths_panel official_panel "
         "rumours_panel yard_view shipdiagram machineshop robots_panel "
         "concourse_panel"),
        ("The ship", "ship_view plans_panel body_panel arc_panel dormancy_panel mining_panel"),
        ("The crew", "crew_view crew_roster crew_sheet crew_ops"),
        ("Holdings, the house and the Voyage", "empire_view works_panel industry_panel "
         "exchequer_panel house_panel house_dialog voyage_panel counsel_card "
         "renown_chip programmes_panel ventures_panel"),
        ("The powers and the law", "diplomacy_view assembly_panel envoy_view demand_view law_view"),
        ("Research, the ground and the Kith", "tech_view tech_tree inquiry_panel xeno_view "
         "expedition_view dig_view minigame_view kith_panel kith_codex"),
        ("News, help and the rest", "despatch_view comms_window codex_view help_view "
         "academy_panel legacy_view memoir_panel orders_panel transit_view options_view"),
        ("Sound", "audio synth soundmap"),
    ],
}


def summary(path: pathlib.Path) -> str:
    """The first sentence of a module's docstring, on one line."""
    try:
        doc = ast.get_docstring(ast.parse(path.read_text())) or ""
    except SyntaxError:
        return "(does not parse)"
    text = " ".join(doc.split("\n\n", 1)[0].split())
    cut = text.find(". ")
    if 0 < cut < 170:
        return text[:cut + 1]
    return text[:170] + ("…" if len(text) > 170 else "")


def modules(package: str) -> list:
    return sorted(p for p in (ROOT / package).glob("*.py") if p.name != "__init__.py")


def render(package: str) -> str:
    here = modules(package)
    by_name = {p.stem: p for p in here}
    lines = [f"# `seedfall/{package}/` — map", "",
             PACKAGES[package], "",
             "Generated by `python -m seedfall.tests.maps --write` from each "
             "module's own docstring (the first sentence of it); the `maps` "
             "suite fails when a module is missing here. Why the pieces are "
             "shaped as they are is in [`../INTERFACE.md`](../INTERFACE.md) and "
             "[`../notes/`](../notes/README.md).", "",
             f"{len(here)} modules.", ""]
    placed = set()
    for title, names in GROUPS.get(package, []):
        rows = [n for n in names.split() if n in by_name and n not in placed]
        if not rows:
            continue
        lines += [f"## {title}", ""]
        for n in rows:
            lines.append(f"- `{n}.py` — {summary(by_name[n])}")
            placed.add(n)
        lines.append("")
    rest = [p for p in here if p.stem not in placed]
    if rest:
        if GROUPS.get(package):
            lines += ["## Everything else", ""]
        for p in rest:
            lines.append(f"- `{p.name}` — {summary(p)}")
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def init_docstring(package: str) -> str:
    """The package's `__init__.py` docstring: its own opening paragraph, then
    the contents, grouped as the map groups them. The project's standing rule
    is that an `__init__` lists what its package holds; generated here so it
    cannot drift from the files."""
    import textwrap
    path = ROOT / package / "__init__.py"
    doc = ast.get_docstring(ast.parse(path.read_text())) or PACKAGES[package]
    opening = doc.split("\n\nContents")[0].strip()
    names = [p.stem for p in modules(package)]
    groups, placed = [], set()
    for title, members in GROUPS.get(package, []):
        rows = [n for n in members.split() if n in names and n not in placed]
        if rows:
            groups.append((title, rows))
            placed.update(rows)
    rest = [n for n in names if n not in placed]
    if rest:
        groups.append(("Everything else" if groups else "Modules", rest))
    out = [opening, "", f"Contents ({len(names)} modules; one line each in "
           "`INTERFACE.md`):", ""]
    for title, rows in groups:
        out += textwrap.wrap(f"{title}: " + ", ".join(rows) + ".", 76,
                             subsequent_indent="    ")
    return "\n".join(out)


def write_init(package: str) -> None:
    """Replace the leading docstring of the package's `__init__.py`."""
    path = ROOT / package / "__init__.py"
    src = path.read_text()
    tree = ast.parse(src)
    first = tree.body[0] if tree.body else None
    lines = src.split("\n")
    new = ['"""' + init_docstring(package) + '"""']
    if (first is not None and isinstance(first, ast.Expr)
            and isinstance(first.value, ast.Constant)
            and isinstance(first.value.value, str)):
        lines[first.lineno - 1:first.end_lineno] = new
    else:
        lines = new + [""] + lines
    path.write_text("\n".join(lines))


def stale() -> dict:
    """package -> what is wrong with its map ("" when it is current)."""
    out = {}
    for package in PACKAGES:
        path = ROOT / package / "INTERFACE.md"
        if not path.exists():
            out[package] = "no map"
            continue
        text = path.read_text()
        names = {p.name for p in modules(package)}
        listed = {line.split("`")[1] for line in text.splitlines()
                  if line.startswith("- `") and line.count("`") >= 2}
        missing = sorted(names - listed)
        gone = sorted(listed - names)
        if missing or gone:
            out[package] = f"missing {missing[:4]}; gone {gone[:4]}"
    return out


def main(argv: list) -> int:
    if "--write" in argv:
        for package in PACKAGES:
            (ROOT / package / "INTERFACE.md").write_text(render(package))
            if package != "tests":        # its docstring is its safety note
                write_init(package)
        print(f"wrote {len(PACKAGES)} package maps and their __init__ docstrings")
        return 0
    bad = stale()
    for package, why in bad.items():
        print(f"{package}: {why}")
    return 1 if bad else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
