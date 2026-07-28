"""Planetary bodies and what a survey party finds standing on them."""

from __future__ import annotations

from dataclasses import dataclass, field

from ..core.save import register
from ..data.lifeforms import (ANOMALIES, BEHAVIOURS, BIOMES, FORMS, METABOLISMS,
                              TRAITS, biome_life, biome_name, specimen_value)

#: kind -> (label, tint, landable)
BODY_KINDS = {
    "rocky": ("Rocky World", "osteo", True),
    "ocean": ("Ocean World", "lumen", True),
    "ice": ("Ice World", "lumen", True),
    "moon": ("Moon", "dim", True),
    "asteroid": ("Asteroid", "osteo", True),
    "comet": ("Comet", "lumen", True),
    "gas": ("Gas Giant", "xeno", False),
    "star": ("Inner Orbit", "warn", False),
}

ROMAN = ["I", "II", "III", "IV", "V", "VI", "VII", "VIII", "IX", "X", "XI", "XII"]


@register
@dataclass
class Lifeform:
    name: str
    metabolism: str
    metabolism_name: str
    metabolism_note: str
    traits: list          # list of (id, name, note, gives)
    behaviour: str
    value: int
    catalogued: bool = False


@register
@dataclass
class Anomaly:
    id: str
    name: str
    tint: str
    research: int
    text: str
    found: bool = False


@register
@dataclass
class Body:
    id: str
    name: str
    kind: str
    biome: str
    orbit: float
    radius_km: int
    gravity: float
    temp_k: int
    resources: dict[str, float]
    lifeforms: list[Lifeform] = field(default_factory=list)
    anomaly: Anomaly | None = None
    surveyed: bool = False
    depleted: float = 0.0
    colony: int | None = None
    relic: str | None = None      # xenotech id buried here
    relic_found: bool = False
    digs: int = 0                 # how often it has been worked

    @property
    def kind_name(self) -> str:
        return BODY_KINDS[self.kind][0]

    @property
    def summary(self) -> str:
        return (f"{self.kind_name} · {biome_name(self.biome)} · "
                f"{self.temp_k} K · {self.gravity:.2f} g")

    def best_resource(self) -> str | None:
        """The richest single resource, for map icons and colony prompts."""
        best, v = None, 0.18
        for k, n in self.resources.items():
            if n > v:
                best, v = k, n
        return best


def _kind_for_orbit(rng, t: float) -> str:
    """Pick a body kind appropriate to how far out it orbits (0 hot, 1 cold)."""
    if t < 0.12:
        return rng.weighted([(3, "rocky"), (1, "asteroid")])
    if t < 0.35:
        return rng.weighted([(4, "rocky"), (2, "asteroid"), (1, "ocean")])
    if t < 0.60:
        return rng.weighted([(3, "rocky"), (3, "asteroid"), (2, "gas"), (1, "ocean")])
    if t < 0.82:
        return rng.weighted([(4, "gas"), (3, "ice"), (2, "asteroid"), (1, "moon")])
    return rng.weighted([(4, "ice"), (3, "comet"), (2, "asteroid"), (1, "gas")])


def _biome_for(rng, kind: str, t: float, star_heat: float) -> str:
    warmth = star_heat * (1 - t)
    if kind == "gas":
        return "aerial" if rng.chance(0.3) else "barren"
    if kind == "comet":
        return "cryo" if rng.chance(0.25) else "barren"
    if kind == "asteroid":
        return "regolith" if rng.chance(0.15) else "barren"
    if kind == "ice":
        return "subsurface" if rng.chance(0.45) else "cryo"
    if kind == "ocean":
        return "verdant" if warmth > 0.45 else "subsurface"
    if kind == "moon":
        return rng.weighted([(4, "regolith"), (2, "cryo"), (1, "subsurface")])
    if warmth > 0.62:
        return rng.weighted([(3, "sulfuric"), (2, "regolith"), (1, "microbial")])
    if warmth > 0.34:
        return rng.weighted([(3, "microbial"), (2, "verdant"), (2, "regolith")])
    return rng.weighted([(3, "regolith"), (2, "cryo"), (1, "barren")])


def _resources_for(rng, kind: str, biome: str) -> dict[str, float]:
    """Ore grades. Metal-rich rocks are common; phosphorus never is."""
    r = {"ore": 0.0, "volatiles": 0.0, "phosphate": 0.0, "biomass": 0.0}
    if kind == "asteroid":
        r["ore"] = rng.float(0.5, 1.0)
        r["phosphate"] = rng.float(0.25, 0.9) if rng.chance(0.28) else rng.float(0, 0.18)
        r["volatiles"] = rng.float(0, 0.35)
    elif kind in ("comet", "ice"):
        r["volatiles"] = rng.float(0.6, 1.0)
        r["ore"] = rng.float(0, 0.25)
        r["phosphate"] = rng.float(0, 0.10)
    elif kind in ("rocky", "moon"):
        r["ore"] = rng.float(0.25, 0.8)
        r["phosphate"] = rng.float(0.2, 0.7) if rng.chance(0.35) else rng.float(0, 0.15)
        r["volatiles"] = rng.float(0, 0.5)
    elif kind == "ocean":
        r["volatiles"] = rng.float(0.7, 1.0)
        r["biomass"] = rng.float(0.3, 0.9)
        r["phosphate"] = rng.float(0.1, 0.5)
    elif kind == "gas":
        r["volatiles"] = rng.float(0.4, 0.9)
    r["biomass"] = max(r["biomass"], biome_life(biome) * rng.float(0.4, 1.0))
    return r


def _make_lifeform(rng, biome: str) -> Lifeform:
    met = rng.pick(METABOLISMS)
    traits = rng.sample(TRAITS, rng.weighted([(5, 0), (4, 1), (2, 2)]))
    return Lifeform(rng.pick(FORMS), met[0], met[1], met[2], list(traits),
                    rng.pick(BEHAVIOURS), specimen_value(rng, met[0], traits))


def make_body(rng, system_name: str, index: int, count: int, star_heat: float) -> Body:
    """One body, unsurveyed. Everything interesting is hidden until you look."""
    t = index / (count - 1) if count > 1 else 0.5
    kind = _kind_for_orbit(rng, t)
    biome = _biome_for(rng, kind, t, star_heat)
    life = biome_life(biome)
    n_life = rng.int(1, 3 + int(life * 3)) if rng.chance(life) else 0

    if kind == "gas":
        radius = rng.int(24000, 71000)
    elif kind == "asteroid":
        radius = rng.int(2, 240)
    elif kind == "comet":
        radius = rng.int(1, 18)
    else:
        radius = rng.int(900, 7200)

    if kind == "gas":
        gravity = rng.float(1.6, 2.9)
    elif kind in ("asteroid", "comet"):
        gravity = rng.float(0.001, 0.04)
    else:
        gravity = rng.float(0.09, 1.35)

    anomaly = None
    if rng.chance(0.13):
        a = rng.pick(ANOMALIES)
        anomaly = Anomaly(a[0], a[1], a[2], a[3], a[4])

    return Body(
        id=str(index),
        name=f"{system_name} {ROMAN[index] if index < len(ROMAN) else index + 1}",
        kind=kind, biome=biome, orbit=t, radius_km=radius, gravity=gravity,
        temp_k=round(90 + star_heat * 420 * (1 - t * 0.85) + rng.float(-30, 30)),
        resources=_resources_for(rng, kind, biome),
        lifeforms=[_make_lifeform(rng, biome) for _ in range(n_life)],
        anomaly=anomaly,
    )


def survey_body(body: Body, quality: float, rng, finds=None) -> dict:
    """Survey quality 0..1 decides how much of a body you actually learn.

    `finds` is what the method being used can detect at all — see
    `data/surveys.py`. A long-range sweep reads a spectrum and cannot see
    anything that moves; only a deep survey reliably reaches what is buried.
    Left as None, everything is detectable, which is what a close pass does
    and what this did before there was a choice.
    """
    can = set(finds if finds is not None else
              ("resources", "lifeforms", "anomaly", "relic"))
    found = {"new_body": not body.surveyed, "lifeforms": [], "anomaly": None,
             "data": 0, "research": 0, "relic": None}
    body.surveyed = True

    # Buried alien work is easy to walk past and hard to miss twice.
    if "relic" in can and body.relic and not body.relic_found \
            and rng.chance(0.35 + quality * 0.55):
        body.relic_found = True
        found["relic"] = body.relic
        found["research"] += 20

    for lf in body.lifeforms:
        if lf.catalogued or "lifeforms" not in can:
            continue
        if rng.chance(0.45 + quality * 0.5):
            lf.catalogued = True
            found["lifeforms"].append(lf)
            found["research"] += round(lf.value * 0.25)

    if "anomaly" in can and body.anomaly and not body.anomaly.found \
            and rng.chance(0.28 + quality * 0.55):
        body.anomaly.found = True
        found["anomaly"] = body.anomaly
        found["research"] += body.anomaly.research

    found["data"] = round((1 + len(found["lifeforms"])) * (0.6 + quality))
    found["research"] += round(8 + quality * 22)
    return found


