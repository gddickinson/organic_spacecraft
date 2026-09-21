"""The gunnery school: ten actions, in the order somebody would teach them.

Each one is a real situation the Verge can put a captain in, taken off the
board and run at a gun where nobody dies for getting it wrong. They are
written to be *played in order* — the range teaches the stick, the pass
teaches lead, point defence teaches priorities, and by the time a gunner is
asked to take a station apart they know which part to take first.

The records are in `data/drill_types.py`; `sim/drills.py` builds an action out
of one and judges it. Nothing here is a number the game uses elsewhere: the
guns come from `sim/foes`, the hulls from `foes.KINDS`, and what a round does
from `data/armaments.py`.
"""

from __future__ import annotations

from .drill_types import Aim, Drill, Spawn, Wave

#: The gun crews' names for the foe's fittings, by what the group carries.
#: A blister is a turret and nothing else; a station is turrets, the mast that
#: aims them, and the reactor that runs both.
STATION_PARTS = ("turret", "turret", "turret", "turret", "sensor", "reactor",
                 "dock")
BATTERY_PARTS = ("turret", "turret", "sensor", "magazine")
RIG_PARTS = ("refinery", "dock", "turret", "sensor")
DOME_PARTS = ("hab", "turret", "turret", "sensor", "reactor")
WARSHIP_PARTS = ("turret", "turret", "engine", "sensor")


DRILLS: tuple = (
    # ── 1. the stick ───────────────────────────────────────────────────────
    Drill(
        "range", "The range",
        "Where the gun points, and how fast it gets there.",
        "Six buoys, none of them shooting back. Find them with the stick, "
        "put the director on one and watch the mounting take it. Nothing "
        "here can hurt you and nothing here is in a hurry.",
        seat="pdc", setting="deep", rung=1, about="the stick and the director",
        waves=(Wave(0.0, "Six buoys, laid out for you.", (
            Spawn("buoy", "Buoy", 6, "fixed", at_km=6.0, spread=150.0,
                  rise=40.0),)),),
        aims=(Aim("all", "Shoot every buoy", "clear"),
              Aim("quick", "Inside ninety seconds", "under", seconds=90.0,
                  primary=False),)),

    # ── 2. lead ────────────────────────────────────────────────────────────
    Drill(
        "pass", "The pass",
        "Leading a target that will not hold still.",
        "Two drones making runs on the hull. A drone crossing at three "
        "hundred metres a second is most of a kilometre from where the sight "
        "says it is — put the pip on it, not the bracket.",
        seat="slug_battery", setting="deep", rung=2, about="lead",
        waves=(Wave(0.0, "Two drones, inbound.", (
            Spawn("drone", "Drone", 2, "run", at_km=11.0, stand_km=9.0,
                  pace=0.42, guns=("LIGHT",)),)),
               Wave(35.0, "Two more, and these ones cross.", (
                   Spawn("drone", "Drone", 2, "strafe", at_km=9.0,
                         stand_km=7.0, pace=0.38, guns=("LIGHT",)),)),),
        aims=(Aim("all", "Clear the sky", "clear"),
              Aim("hull", "Keep the hull above half", "survive", share=0.5,
                  primary=False),
              Aim("shoot", "Land a third of what you fire", "accuracy",
                  share=0.33, primary=False),)),

    # ── 3. point defence ───────────────────────────────────────────────────
    Drill(
        "screen", "The screen",
        "Seekers, and the seconds you have to take them off the plot.",
        "A corvette standing off at twenty kilometres with a full rack. It "
        "cannot hurt you and what it launches can. Take the missiles first; "
        "the ship that fired them will keep.",
        seat="pdc", setting="deep", rung=3, about="point defence",
        waves=(Wave(0.0, "One corvette, standing off, racks loaded.", (
            Spawn("corvette", "Raider", 1, "stand", at_km=20.0,
                  stand_km=19.0, pace=0.12, guns=("RACK",),
                  parts=WARSHIP_PARTS),)),
               Wave(30.0, "A second rack joins it.", (
                   Spawn("corvette", "Raider", 1, "stand", at_km=21.0,
                         stand_km=18.0, pace=0.12, guns=("RACK",),
                         parts=WARSHIP_PARTS),)),),
        seconds=120.0,
        aims=(Aim("stop", "Let nothing through", "stop"),
              Aim("hold", "Two minutes on the gun", "survive", seconds=120.0),
              Aim("kill", "And take the racks off them", "clear",
                  of="corvette", primary=False),)),

    # ── 4. multiple attacking ships ────────────────────────────────────────
    Drill(
        "pack", "The pack",
        "More hostiles than you have arc, and choosing between them.",
        "Four corvettes in two pairs, and they do not arrive together. One "
        "gun cannot cover the whole sky: decide which half of it matters and "
        "let the other half come to you.",
        seat="slug_battery", setting="deep", rung=4,
        about="a running fight against several hulls",
        waves=(Wave(0.0, "Two corvettes, fine on the bow.", (
            Spawn("corvette", "Corvette", 2, "run", at_km=16.0, stand_km=10.0,
                  pace=0.30, guns=("MEDIUM", "LIGHT"), parts=WARSHIP_PARTS,
                  spread=40.0),)),
               Wave(40.0, "Two more, astern of you.", (
                   Spawn("corvette", "Corvette", 2, "strafe", at_km=14.0,
                         stand_km=8.0, pace=0.34, guns=("MEDIUM",),
                         parts=WARSHIP_PARTS, spread=60.0, rise=-25.0),)),),
        hull=420.0,
        aims=(Aim("all", "Clear the sky", "clear"),
              Aim("hull", "Keep the hull above a third", "survive", share=0.33),
              Aim("drives", "Cripple one before you kill it", "cripple",
                  primary=False),)),

    # ── 5. attacking a space station ───────────────────────────────────────
    Drill(
        "quay", "The quay",
        "Taking a structure apart, in the order that keeps you alive.",
        "A hostile hub, four blisters, a sensor mast and a reactor. Shooting "
        "the hub is slow and shooting the *turrets* is the job: silence it "
        "first, blind it second, and then take as long as you like.",
        seat="railgun", setting="station", rung=5,
        about="a strike on a station",
        waves=(Wave(0.0, "The hub, and it has seen you.", (
            Spawn("station", "Hostile hub", 1, "fixed", at_km=13.0,
                  guns=("MEDIUM", "MEDIUM", "RACK"), parts=STATION_PARTS,
                  spread=0.0, rise=6.0),)),
               Wave(50.0, "Two blisters have cut loose and are coming out.", (
                   Spawn("drone", "Defence drone", 3, "run", at_km=10.0,
                         stand_km=8.0, pace=0.40, guns=("LIGHT",)),)),),
        hull=480.0, evade=0.15,
        aims=(Aim("quiet", "Silence the hub", "silence", of="Hostile hub"),
              Aim("blind", "Take its sensor mast", "wreck", of="sensor"),
              Aim("core", "And then its reactor", "wreck", of="reactor",
                  primary=False),
              Aim("drones", "Clear the drones", "clear", of="drone",
                  primary=False),)),

    # ── 6. attacking planet defences ───────────────────────────────────────
    Drill(
        "batteries", "The shore batteries",
        "Guns that do not move, hit hard, and see you coming.",
        "Three ground batteries on the limb, dug in and out of reach of "
        "anything but a long gun. They fire slowly and they do not miss "
        "twice. Kill the masts and they will.",
        seat="mass_driver", setting="world", rung=6,
        about="a run against planetary defences",
        waves=(Wave(0.0, "Three batteries, ranging on you.", (
            Spawn("battery", "Shore battery", 3, "fixed", at_km=18.0,
                  guns=("SIEGE",), parts=BATTERY_PARTS, spread=70.0,
                  rise=-30.0),)),),
        hull=520.0, evade=0.10, seconds=180.0,
        aims=(Aim("all", "Silence all three", "clear", of="battery"),
              Aim("masts", "Blind one before it fires twice", "wreck",
                  of="sensor", primary=False),
              Aim("hull", "Keep the hull above half", "survive", share=0.5,
                  primary=False),)),

    # ── 7. attacking mining operations ─────────────────────────────────────
    Drill(
        "workings", "The workings",
        "A soft target with hard escorts, and a reason not to shoot it all.",
        "An unlicensed rig and two guard boats. The rig's refinery is what "
        "you came for; the habitat ring is not, and the Charter will ask. "
        "Take the workings and leave the people.",
        seat="lixiviant", setting="world", rung=7,
        about="a raid on a mining operation",
        waves=(Wave(0.0, "The rig, and two boats coming round it.", (
            Spawn("rig", "Unlicensed rig", 1, "fixed", at_km=9.0,
                  guns=("LIGHT",), parts=RIG_PARTS, spread=0.0, rise=-8.0),
            Spawn("corvette", "Guard boat", 2, "strafe", at_km=12.0,
                  stand_km=7.0, pace=0.32, guns=("MEDIUM",),
                  parts=WARSHIP_PARTS, spread=90.0))),),
        hull=400.0,
        aims=(Aim("works", "Wreck the refinery", "wreck", of="refinery"),
              Aim("guards", "Clear the guard boats", "clear", of="corvette"),
              Aim("people", "Leave the habitat ring alone", "spare",
                  of="hab"),)),

    # ── 8. attacking planetary operations ──────────────────────────────────
    Drill(
        "ground", "The ground works",
        "Shooting at something with people in it, from a long way up.",
        "A dome and its two batteries, on a world you are not welcome over. "
        "The batteries first, always — a dome cannot shoot and a battery "
        "can, and the order you do this in is the whole of the lesson.",
        seat="particle_beam", setting="world", rung=8,
        about="a strike on a planetary installation",
        waves=(Wave(0.0, "The dome, with its guns up.", (
            Spawn("dome", "Ground works", 1, "fixed", at_km=15.0,
                  guns=("LANCE",), parts=DOME_PARTS, spread=0.0, rise=-34.0),
            Spawn("battery", "Shore battery", 2, "fixed", at_km=16.0,
                  guns=("SIEGE",), parts=BATTERY_PARTS, spread=50.0,
                  rise=-30.0))),
               Wave(45.0, "They have put up interceptors.", (
                   Spawn("drone", "Interceptor", 4, "run", at_km=12.0,
                         stand_km=9.0, pace=0.44, guns=("LIGHT",)),)),),
        hull=520.0, evade=0.12,
        aims=(Aim("guns", "Silence the batteries", "clear", of="battery"),
              Aim("dome", "Take the dome's reactor", "wreck", of="reactor"),
              Aim("air", "Clear the interceptors", "clear", of="drone",
                  primary=False),
              Aim("people", "Leave the habitat ring alone", "spare",
                  of="hab", primary=False),)),

    # ── 9. the defensive action ────────────────────────────────────────────
    Drill(
        "siege", "Boarded",
        "Everything at once, and nowhere to go.",
        "A wave, then another, then another, and the hull does not get any "
        "thicker. This one is not won; it is survived. Two minutes.",
        seat="pdc", setting="deep", rung=9, about="a defensive action",
        waves=(Wave(0.0, "First wave.", (
            Spawn("drone", "Raider drone", 3, "run", at_km=10.0, stand_km=8.0,
                  pace=0.44, guns=("LIGHT",)),)),
               Wave(30.0, "Second wave, with racks.", (
                   Spawn("corvette", "Raider", 2, "stand", at_km=17.0,
                         stand_km=15.0, pace=0.18, guns=("RACK", "LIGHT"),
                         parts=WARSHIP_PARTS),)),
               Wave(65.0, "Torpedoes. Take them first.", (
                   Spawn("corvette", "Lance boat", 1, "stand", at_km=20.0,
                         stand_km=19.0, pace=0.14, guns=("TUBES",),
                         parts=WARSHIP_PARTS),
                   Spawn("drone", "Raider drone", 3, "strafe", at_km=9.0,
                         stand_km=6.0, pace=0.40, guns=("LIGHT",)))),),
        hull=460.0, seconds=140.0,
        aims=(Aim("hold", "Two minutes and twenty on the gun", "survive",
                  seconds=140.0),
              Aim("stop", "Let no torpedo through", "stop", of="torpedo"),
              Aim("hull", "Keep the hull above a quarter", "survive",
                  share=0.25, primary=False),)),

    # ── 10. the fleet ──────────────────────────────────────────────────────
    Drill(
        "line", "In the line",
        "A gun in a fleet action, with friends in your arc.",
        "Two consorts on your beam and a hostile squadron across the way. "
        "Everything the director offers you is a *contact*, and two of them "
        "are yours. The bracket tells you which; the trigger does not.",
        seat="railgun", setting="deep", rung=10,
        about="a fleet action",
        waves=(Wave(0.0, "Consorts on station. The squadron is closing.", (
            Spawn("consort", "Steadfast Increment", 1, "escort", at_km=4.0,
                  stand_km=3.5, pace=0.16, guns=(), hostile=False,
                  spread=40.0, rise=10.0),
            Spawn("consort", "Long Patience", 1, "escort", at_km=4.5,
                  stand_km=4.0, pace=0.16, guns=(), hostile=False,
                  spread=-40.0, rise=-10.0),
            Spawn("hull", "Squadron hull", 3, "strafe", at_km=18.0,
                  stand_km=11.0, pace=0.26, guns=("MEDIUM", "RACK"),
                  parts=WARSHIP_PARTS, spread=70.0))),),
        hull=520.0, seconds=200.0,
        aims=(Aim("all", "Break the squadron", "clear", of="hull"),
              Aim("friends", "Both consorts still flying", "protect",
                  of="consort"),
              Aim("clean", "Do not hit a friend", "spare", of="consort"),)),
)

DRILL_BY_ID = {d.id: d for d in DRILLS}


def in_order() -> tuple:
    """Every drill, in the order a gunnery school teaches them."""
    return tuple(sorted(DRILLS, key=lambda d: d.rung))


def after(drill_id: str):
    """The next drill up, or None at the top of the school."""
    rungs = in_order()
    here = next((i for i, d in enumerate(rungs) if d.id == drill_id), None)
    if here is None or here + 1 >= len(rungs):
        return None
    return rungs[here + 1]
