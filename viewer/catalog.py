"""GESTALT document catalog — the single source of truth for the viewer.

Maps each published artifact to its local file, route slug, title and blurb,
and records the original claude.ai artifact id so cross-document links inside
the pages can be rewritten to local routes.

See ../INTERFACE.md for how the viewer modules connect.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class Doc:
    slug: str          # local route: /d/<slug>
    filename: str      # file under docs/
    artifact_id: str   # original claude.ai/code/artifact/<id>
    title: str         # display title
    kind: str          # short category label
    favicon: str       # emoji
    blurb: str         # one-line description for the index card


# Order here is the order shown on the landing page.
DOCS = [
    Doc("dossier", "gestalt.html",
        "285ef29f-751e-4767-b5a6-9cd178faddb1",
        "Design Dossier", "Starship · concept", "🌱",
        "The living, grown-from-a-seed starship: structural anatomy, an exact "
        "closed-loop metabolism, space-environment defenses, a bioengineering "
        "roadmap and a python-grounded growth curve — with 18 real citations."),
    Doc("starship", "gestalt-drawings.html",
        "bd2c2c98-84cf-42c9-91ea-f0ec1c749fc5",
        "Starship Drawings", "Starship · drawings", "📐",
        "Architectural drawing set of the 120 m grown vessel: external "
        "elevation, longitudinal section, and transverse sections A/B/C keyed "
        "to the prolate-spheroid width law."),
    Doc("habitat", "gestalt-habitat.html",
        "9b90d7e5-2a71-426a-b2bf-d3a96b32a82e",
        "Habitat · ARCA", "Habitat · drawings", "🌍",
        "The million-person habitat drum: transverse and long sections, "
        "layered anatomy, unrolled biome map, a ~113 Mt atmosphere and a "
        "150 W/m² sun-cord light budget that closes the oxygen loop."),
    Doc("fleet", "gestalt-fleet.html",
        "7eeb70c7-e076-4b0d-b6e3-9e942c4d1091",
        "Fleet Registry", "Fleet · registry", "🛰️",
        "Grown-vehicle classes from seed-couriers to million-person habitats, "
        "a technology-readiness scorecard mapped to Earth-Program phases, and "
        "the governance & containment regime."),
    Doc("lichen", "gestalt-lichen.html",
        "94531439-d04d-480e-9d04-bad6fcdacd9a",
        "LICHEN", "Surface habitat · drawings", "🍄",
        "A settlement grown into the regolith of the Moon or Mars: layered "
        "dome anatomy, a pressure-balanced over-blanket (ρgh = 52 kPa) and "
        "perchlorate → O₂ detox chemistry."),
    Doc("gravid", "gestalt-gravid.html",
        "2433fa54-e582-4194-8245-d63acee8fb85",
        "GRAVID", "Nursery · drawings", "🥚",
        "The nursery organism that gestates the fleet from seeds: placental "
        "cradle sections, the seed-to-ship sequence, and a ~26 t/day "
        "throughput model (double the wild growth rate)."),
    Doc("compendium", "gestalt-compendium.html",
        "d619e9af-9787-4d1b-8f1c-5a658789e075",
        "Engineering & Biology Compendium", "Technical reference", "🧬",
        "The deep technical reference — chassis organisms, genome and "
        "morphogenesis circuits, materials chemistry, metabolism, defenses, "
        "biomining, canonical parameters — with 20 real citations."),
    Doc("earth", "gestalt-earthprogram.html",
        "bc243583-d959-4284-841a-70ab529d40ed",
        "Earth Program", "R&D roadmap", "🌱",
        "The complete ground R&D/testing/prototyping roadmap: a 5-phase TRL "
        "ladder, six work packages, an integration ladder, a 40-year Gantt "
        "with a phased ~$30–40B budget, and a gated go/no-go framework."),
    Doc("classes", "gestalt-classref.html",
        "7ca9c965-1932-4c5a-b0f1-a99e9febae58",
        "Fleet Class Reference", "Class reference", "🚀",
        "A detailed profile of each of the 18 grown-vehicle classes — role, "
        "form, full spec, seed-to-vessel growth protocol, and hardest "
        "challenge — with links to the flagship drawing sets."),
    Doc("models", "gestalt-3d.html",
        "1c6f18ca-eeda-4d83-bd97-fd9c1622823d",
        "3D Models", "Interactive 3D", "🛸",
        "Interactive, rotatable/zoomable 3D solid models of all seven main "
        "forms (NAVIS, ARCA, LICHEN, GRAVID, SPORE, LEVIATHAN, TESTUDO), "
        "rendered live by a self-contained software engine — with a dynamic "
        "scale bar, labelled hotspots, and cutaway views that reveal the "
        "interior components (cores, decks, cradles, shelters)."),
]

BY_SLUG = {d.slug: d for d in DOCS}
BY_ARTIFACT_ID = {d.artifact_id: d for d in DOCS}


def artifact_id_to_slug():
    """Map every known artifact id to its local slug (for link rewriting)."""
    return {d.artifact_id: d.slug for d in DOCS}
