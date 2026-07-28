"""Ground expeditions — the tables a landing party is assembled from.

Surveying a world from orbit tells you what is there. Walking on it is a
different proposition: a lander, a rover, a handful of officers, a finite number
of days of air and food, and a map you can only see one step at a time.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class Terrain:
    id: str
    name: str
    tint: str
    cost: int          # days of supply to cross
    danger: float      # chance of a hazard when entering
    blurb: str


TERRAIN: dict[str, Terrain] = {t.id: t for t in [
    Terrain("plain", "Regolith Flat", "dim", 1, 0.05,
            "Dust, boulders, and a horizon closer than it ought to be."),
    Terrain("ridge", "Ridge", "osteo", 2, 0.12,
            "Broken ground rising. The rover complains; the view is worth it."),
    Terrain("crevasse", "Crevasse Field", "warn", 2, 0.30,
            "Ice or rock split into a lattice of drops. Every route is a guess."),
    Terrain("vent", "Vent Field", "warn", 2, 0.22,
            "Something warm is escaping from below, and it is not steam."),
    Terrain("basin", "Sink Basin", "lumen", 1, 0.10,
            "A low pan where whatever this world has instead of weather collects."),
    Terrain("forest", "Standing Growth", "chloro", 2, 0.16,
            "Structures that are probably alive, in ranks, taller than the lander."),
    Terrain("shelf", "Ice Shelf", "lumen", 2, 0.18,
            "Kilometres of it, and the sound it makes is not encouraging."),
    Terrain("scarp", "Scarp", "steel", 3, 0.20,
            "A wall of layered rock. Going up costs a day; going down costs more."),
    Terrain("dunes", "Dune Sea", "osteo", 2, 0.14,
            "Sorted grains marching very slowly somewhere. Tracks fill in behind you."),
]}


@dataclass(frozen=True)
class Feature:
    id: str
    name: str
    tint: str
    blurb: str
    #: (label, stat checked, difficulty, reward kind)
    options: tuple = ()


#: Reward kinds: research, xenolith, sample, ore, volatiles, biomass, credits,
#: study (alien understanding), lore, none
FEATURES: dict[str, Feature] = {f.id: f for f in [
    Feature("ruin", "Worked Stone", "xeno",
            "Cut faces, deliberate angles, and a doorway sized for something "
            "that walked upright and was not us.",
            (("Survey the geometry", "science", 3, "research"),
             ("Force the doorway", "engineering", 4, "study"),
             ("Leave it undisturbed", "", 0, "none"))),
    Feature("seam", "Exposed Seam", "osteo",
            "A band of ore running out of the cliff face, weathered clean.",
            (("Cut a sample", "engineering", 2, "ore"),
             ("Assay it properly", "science", 3, "research"))),
    Feature("vent_field", "Hydrothermal Vent", "lumen",
            "Black smoke in a place with no fire, and things crowded around it "
            "that have never needed light.",
            (("Sample the chimney", "science", 3, "sample"),
             ("Tap it for volatiles", "engineering", 3, "volatiles"))),
    Feature("wreck", "Downed Hull", "steel",
            "Somebody came down hard here, long enough ago that the dust has "
            "settled over the impact scar.",
            (("Strip the salvage", "engineering", 2, "credits"),
             ("Read the flight recorder", "comms", 3, "lore"),
             ("Search for survivors", "medicine", 4, "lore"))),
    Feature("cache", "Sealed Cache", "chloro",
            "A hatch, flush with the ground, with a seal that is still holding "
            "whatever pressure it was set to hold.",
            (("Cut it open", "engineering", 3, "credits"),
             ("Work the mechanism", "science", 4, "study"))),
    Feature("nest", "Aggregation", "chloro",
            "A great many of the local organisms, in one place, doing something "
            "with evident coordination.",
            (("Observe from cover", "science", 2, "research"),
             ("Take a specimen", "medicine", 4, "sample"),
             ("Withdraw quietly", "", 0, "none"))),
    Feature("monolith", "Standing Array", "xeno",
            "A single upright element, warm to the touch, humming below hearing.",
            (("Record the emission", "science", 4, "study"),
             ("Match its resonance", "engineering", 5, "study"))),
    Feature("shaft", "Ice Shaft", "lumen",
            "A bore going down further than the lamp reaches, and it was not "
            "made by water.",
            (("Descend on a line", "engineering", 4, "study"),
             ("Drop a probe", "science", 2, "research"))),
    Feature("bloomscar", "Bloom Scar", "warn",
            "Tissue that is still, faintly, metabolising, with nothing left "
            "here to metabolise.",
            (("Take a lineage sample", "medicine", 3, "research"),
             ("Burn it out", "tactical", 2, "none"))),
    Feature("garden", "Cultivated Ground", "chloro",
            "Rows. Unmistakably rows, gone wild a very long time ago.",
            (("Catalogue the survivors", "science", 3, "biomass"),
             ("Look for the farmers", "comms", 4, "lore"))),
]}


@dataclass(frozen=True)
class Hazard:
    id: str
    name: str
    blurb: str
    #: stat that mitigates it, and what it costs on a failure
    stat: str
    supply: int = 0
    injury: float = 0.0
    rover: int = 0


HAZARDS: list[Hazard] = [
    Hazard("storm", "Dust Storm",
           "The horizon closes to twenty metres and stays there.",
           "nav", supply=2),
    Hazard("collapse", "Ground Collapse",
           "The crust gives way under the near-side track.",
           "engineering", rover=2, injury=0.15),
    Hazard("breach", "Suit Breach",
           "A seal fails at the worst possible moment, as they do.",
           "medicine", injury=0.30),
    Hazard("cold", "Thermal Trap",
           "The shadow is two hundred degrees colder than the sunlight and the "
           "party is standing in it.",
           "engineering", supply=1, injury=0.10),
    Hazard("lost", "Navigation Error",
           "The inertial platform has been quietly wrong for some hours.",
           "nav", supply=3),
    Hazard("fauna", "Hostile Aggregation",
           "The local organisms have decided the party is a category of thing "
           "they have a response to.",
           "tactical", injury=0.25, supply=1),
    Hazard("toxin", "Contact Toxin",
           "Something on the rock is getting through the glove polymer.",
           "medicine", injury=0.20),
    Hazard("quake", "Seismic Event",
           "The whole shelf moves about a metre, all at once.",
           "nav", rover=1, injury=0.12),
]

#: Rough loot per successful action, before skill margin is applied.
REWARD_SCALE = {
    "research": (18, 45),
    "study": (14, 34),
    "xenolith": (1, 2),
    "sample": (1, 3),
    "ore": (8, 26),
    "volatiles": (6, 20),
    "biomass": (6, 18),
    "credits": (900, 3400),
    "lore": (0, 0),
    "none": (0, 0),
}

#: Fragments of setting the party can bring home. Purely flavour, and the
#: reason anyone reads an expedition report twice.
LORE = [
    "The recorder's last entry is a cargo manifest. The cargo was seed husks, "
    "and the count does not match what the Charter says it issued that year.",
    "Someone scratched a tally into the bulkhead — four hundred and eleven "
    "marks — and then stopped, neatly, mid-stroke.",
    "The rows run north-south for eleven kilometres and then stop at a line as "
    "straight as a ruler. Nothing grows past it. Nothing has tried.",
    "The array's emission resolves, when slowed by a factor of nine hundred, "
    "into something with the statistical structure of speech.",
    "Under the dust the floor is tiled, and the tiles are worn deepest along a "
    "path from the doorway to a window that faces nothing in particular.",
    "The hull is Concordat, forty years old, and the breach is from the inside.",
    "There is a second doorway behind the first, sized for something much larger, "
    "and it has been bricked up from this side.",
    "The vent chemistry is a nine-to-one match for the Abyssal sample library. "
    "This world has no ocean and has never had one.",
]

#: What the lander can carry back before the party has to leave something behind.
PARTY_CAPACITY = 60.0
BASE_SUPPLY = 24

#: What you can load a lander with: (label, tonnes of biomass, days of supply).
#: Committing more biomass buys more time on the ground and costs the ship.
SUPPLY_LOADS = [
    ("Light — a look around", 12, 24),
    ("Standard — a proper survey", 20, 40),
    ("Heavy — a season on the ground", 32, 64),
]
