"""Resolving the manual's facts from the tables they are about.

A help page that says "thirty-five hulls" is wrong the day somebody adds one,
and nothing in the suite would ever notice. So every countable claim is counted
here, at read time, from the table it concerns — and `test_manual` fails if a
topic names a fact this module cannot resolve.

Prose lives in `data/help.py`. Numbers live where the game keeps them. Nothing
is restated in two places.
"""

from __future__ import annotations

from ..data.help import TOPICS, TOPICS_BY_ID

FACTS = {}


def fact(name: str):
    def keep(fn):
        FACTS[name] = fn
        return fn
    return keep


@fact("endings")
def _endings(game) -> list:
    from ..data.epochs import EPOCHS_BY_ID
    from ..data.lore import VICTORIES
    lines = [f"{len(VICTORIES)} endings, none locked behind another:"]
    for vid, name, _tint, how, _text in VICTORIES:
        after = EPOCHS_BY_ID.get(vid)
        lines.append(f"  {name} — {how}."
                     + (f" Then: {after.name}." if after else ""))
    return lines


@fact("starting_kit")
def _starting_kit(game) -> list:
    from ..data.chassis import CHASSIS_BY_ID
    chassis = CHASSIS_BY_ID[game.ship.chassis]
    return [f"You are flying a {chassis.name}: {chassis.cargo} t of hold, "
            f"{chassis.crew} berths, {len(game.ship.fitted)} fittings, "
            f"{round(game.credits):,} credits, "
            f"{len(game.officers)} officers aboard."]


@fact("burns")
def _burns(game) -> list:
    from .flight import BURNS, burn_heat
    stats = game.ship_stats
    lines = ["Burn profiles, and what each does to this hull:"]
    for burn in BURNS:
        lines.append(f"  {burn.name} — {burn.blurb} "
                     f"(arrives +{burn_heat(burn, stats):.0f} heat)")
    return lines


@fact("reach")
def _reach(game) -> list:
    from . import reach as reach_sim
    return [reach_sim.note(game)]


@fact("survey_pay")
def _survey_pay(game) -> list:
    from ..data.charts import APPETITES
    lines = [f"{len(APPETITES)} powers buy charts, and they want "
             "different things:"]
    for appetite in APPETITES:
        lines.append(f"  {appetite.faction} — {appetite.line}")
    return lines


@fact("goods")
def _goods(game) -> list:
    from ..data.commodities import COMMODITIES
    from ..data.contraband import REGIMES
    lines = [f"{len(COMMODITIES)} goods trade in the Verge, and "
             f"{len(REGIMES)} powers outlaw something:"]
    for regime in REGIMES:
        lines.append(f"  {regime.faction} — {regime.writ}: "
                     + ", ".join(regime.outlaws))
    return lines


@fact("contract_kinds")
def _contract_kinds(game) -> list:
    from ..data.contracts import KINDS
    lines = [f"{len(KINDS)} kinds of contract are posted:"]
    for kind in KINDS.values():
        lines.append(f"  {kind.name} — {kind.blurb}")
    return lines


@fact("tech_tree")
def _tech_tree(game) -> list:
    from ..data.tech import TECH
    branches = sorted({t.branch for t in TECH})
    return [f"{len(TECH)} technologies across {len(branches)} branches: "
            + ", ".join(branches) + ".",
            f"You hold {len(game.research.unlocked)} of them."]


@fact("xenotech")
def _xenotech(game) -> list:
    from ..data.xenotech import XENOTECH
    from . import xeno as xeno_sim
    cultures = sorted({t.culture for t in XENOTECH})
    done = sum(1 for t in XENOTECH if xeno_sim.is_incorporated(game, t.id))
    return [f"{len(XENOTECH)} alien technologies from {len(cultures)} "
            f"cultures: " + ", ".join(cultures) + ".",
            f"You have incorporated {done}."]


@fact("stations")
def _stations(game) -> list:
    from ..data.beginnings import CREW_CHOICES
    held = {o.stat: o for o in game.officers}
    lines = [f"{len(CREW_CHOICES)} stations. Yours:"]
    for station in CREW_CHOICES:
        officer = held.get(station)
        lines.append(f"  {station} — "
                     + (f"{officer.name}, level {officer.level}" if officer
                        else "nobody"))
    return lines


@fact("hulls")
def _hulls(game) -> list:
    from ..data.chassis import CHASSIS, FAMILY_LABEL
    by_family = {}
    for chassis in CHASSIS:
        by_family[chassis.family] = by_family.get(chassis.family, 0) + 1
    lines = [f"{len(CHASSIS)} hulls across {len(by_family)} families:"]
    for family, count in sorted(by_family.items(), key=lambda kv: -kv[1]):
        lines.append(f"  {FAMILY_LABEL.get(family, family)} — {count}")
    return lines


@fact("layers")
def _layers(game) -> list:
    lines = ["Your hull, outermost first. Damage lands outside in:"]
    for layer in game.ship.layers:
        share = layer.hp / layer.max if layer.max else 1.0
        lines.append(f"  {layer.name} — {share * 100:.0f}%"
                     + ("  (the pressure vessel)" if layer.critical else ""))
    return lines


@fact("colony_classes")
def _colony_classes(game) -> list:
    from ..data.colonies import COLONIES
    from ..data.works import WORKS
    online = sum(1 for c in game.colonies if c.online)
    return [f"{len(COLONIES)} colony and station classes, {len(WORKS)} works "
            f"that develop them.",
            f"You hold {len(game.colonies)}, {online} of them online."]


@fact("powers")
def _powers(game) -> list:
    from ..data.factions import FACTIONS, standing
    lines = []
    for faction in FACTIONS:
        if faction.hidden:
            continue
        value = game.rep.get(faction.id, 0)
        band, _tint = standing(value)
        lines.append(f"  {faction.name} — {band} ({value:+.0f}). "
                     f"{faction.creed}")
    return [f"{len(lines)} powers, and how each regards you:"] + lines


@fact("instruments")
def _instruments(game) -> list:
    from . import telemetry
    lines = ["Instruments, and what each says right now:"]
    for name, reading in telemetry.all_readings(game).items():
        lines.append(f"  {reading['title']} — {reading['note']}")
    return lines


@fact("detection")
def _detection(game) -> list:
    """How far *this* hull sees, against what is hiding — from the array
    actually fitted, so the answer changes when the captain buys a better
    one and cannot go stale in the prose."""
    from ..data import countermeasures as cm
    from . import detection
    array = detection.sensor_of(game)
    lines = [f"Your array reads {array:.1f} ly. Against a hull, that is:"]
    for hiding in cm.ALL:
        lines.append(f"  {hiding.name} — "
                     f"{detection.SENSOR_KM * array * hiding.share:,.0f} km")
    lines.append("Stars, worlds and quays are seen at any range: they are "
                 "enormous, lit, or squawking because being found is the job.")
    # **The range only means something against the stopping distance.** Seen
    # with less room than it takes to stop is seen too late, so quote both or
    # the table above is trivia. From the drive actually fitted.
    from . import thrusters
    accel = max(1e-6, float(thrusters.summary(game.ship)["main_accel"]))
    for speed in (100.0, 300.0):
        lines.append(f"  at {speed:,.0f} m/s you need "
                     f"{speed * speed / (2.0 * accel) / 1000.0:,.0f} km to "
                     f"stop")
    return lines


@fact("keys")
def _keys(game) -> list:
    from ..data.screens import NAV_KEYS
    return ["Keyboard:"] + [f"  {key} — {screen}"
                            for key, screen in NAV_KEYS]


# ── reading a topic ────────────────────────────────────────────────────────

def resolve(game, name: str) -> list:
    reader = FACTS.get(name)
    if reader is None:
        return [f"(no such fact: {name})"]
    try:
        return list(reader(game))
    except Exception as err:              # noqa: BLE001 - a manual must open
        return [f"(could not read {name}: {type(err).__name__}: {err})"]


def page(game, topic_id: str) -> dict:
    """One topic: its prose, its resolved facts, and where it points."""
    topic = TOPICS_BY_ID.get(topic_id)
    if topic is None:
        return {}
    facts = []
    for name in topic.facts:
        facts.extend(resolve(game, name))
    return {"topic": topic, "title": topic.title, "screen": topic.screen,
            "body": list(topic.body), "facts": facts,
            "see": [TOPICS_BY_ID[t] for t in topic.see if t in TOPICS_BY_ID]}


def search(query: str) -> list:
    """Topics whose title or prose mentions this. Plain, and enough."""
    wanted = query.strip().lower()
    if not wanted:
        return list(TOPICS)
    out = []
    for topic in TOPICS:
        haystack = " ".join((topic.title, *topic.body)).lower()
        if wanted in haystack:
            out.append(topic)
    return out


def for_screen(screen: str) -> list:
    return [t for t in TOPICS if t.screen == screen]
