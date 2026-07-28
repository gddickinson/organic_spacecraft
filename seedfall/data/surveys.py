"""Ways of looking at a body, and what each of them can and cannot see.

There used to be one. Every body took the same three days, cost nothing but
time, carried no risk, and returned the same kind of answer whether it was a
comet or an ocean world — while thirteen sensor fittings and a drone
technology sat in the tables doing nothing but nudging a single `scan` float.

So: four methods, each with something it is good at and something it cannot
do. The point is that they are not a ladder. A long-range sweep is not a worse
close pass, it is a different question — it costs no travel and cannot see
life. A probe swarm goes where the hull will not. A deep survey is the only
thing that finds what is buried, and it is slow and it wants real equipment.

Each names what it `finds`, and `world/planets.survey_body` is filtered by it,
so a method that says it cannot see lifeforms genuinely cannot.
"""

from __future__ import annotations

from dataclasses import dataclass, field

#: What there is to find on a body. A method sees some of these and not others.
CATEGORIES = ("resources", "lifeforms", "anomaly", "relic")


@dataclass(frozen=True)
class Method:
    id: str
    name: str
    blurb: str
    #: What this method can detect at all.
    finds: tuple
    #: Days, before the scan rating is applied.
    days: float
    #: Multiplier on scan quality — how well it reads what it *can* see.
    quality: float
    #: Consumed per attempt, by commodity.
    cost: dict = field(default_factory=dict)
    #: Must the ship fly alongside first?
    alongside: bool = True
    #: Minimum scan rating, and the technology it wants, if any.
    needs_scan: float = 0.0
    needs_tech: str | None = None
    #: What the player should understand about the trade.
    gives: str = ""
    costs: str = ""


METHODS = [
    Method("sweep", "Long-range sweep",
           "Point the array at it from wherever you happen to be and read "
           "what comes back. Mass, orbit, spectrum, the rough grade of what "
           "is on the surface. Nothing that moves and nothing underground.",
           finds=("resources",), days=1.0, quality=0.75, alongside=False,
           gives="No flying and no stores. Minutes, not weeks.",
           costs="It cannot see life, anomalies or anything buried — and it "
                 "only reaches as far as your sensors do."),

    Method("pass", "Close pass",
           "Take the hull alongside and look properly: optical, thermal, a "
           "gravimetric profile, and long enough in the sky to catch "
           "something moving.",
           finds=("resources", "lifeforms", "anomaly"), days=3.0, quality=1.0,
           gives="The ordinary survey. Everything except what is under the "
                 "ground.",
           costs="You have to fly there, and it will not find a buried site "
                 "except by luck."),

    Method("probes", "Probe swarm",
           "Seed a dozen drones and let them do the flying. They go where the "
           "hull will not — inside a ring, down a vent, through a cloud deck "
           "— and most of them come back.",
           finds=("resources", "lifeforms", "anomaly"), days=5.0, quality=1.15,
           cost={"silicon": 3, "alloy": 2}, alongside=False,
           needs_tech="dronework",
           gives="No transit at all, and it reads life better than a hull can.",
           costs="Three tonnes of silicon and two of alloy, every time, and "
                 "five days waiting for them to come home."),

    Method("deep", "Deep survey",
           "Sounding charges, a long baseline, and somebody in the polyp lab "
           "with the returns. The only way to be sure what is under the "
           "regolith rather than on it.",
           finds=("resources", "lifeforms", "anomaly", "relic"), days=9.0,
           quality=1.3, cost={"volatiles": 4}, needs_scan=0.55,
           gives="The only method that reliably turns up a buried site, and "
                 "it reads everything else better too.",
           costs="Nine days alongside, reaction mass for the charges, and it "
                 "wants a real sensor suite to be worth doing."),
]
METHODS_BY_ID = {m.id: m for m in METHODS}

#: What `actions.survey` uses when nobody chose — the behaviour that shipped.
DEFAULT = "pass"
