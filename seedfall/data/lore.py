"""Setting, name pools, victory conditions and the codex."""

from __future__ import annotations

TITLE = "SEEDFALL"
SUBTITLE = "A GESTALT Programme Chronicle"
TAGLINE = "We do not build the ship. We ripen it."

INTRO = [
    "Fifty years ago the Charter threw a hundred and twenty kilogram seed at a "
    "carbonaceous asteroid and waited. It rooted, ate the rock, and grew a "
    "mining organism; the miner grew a nursery; the nursery grew everything "
    "else. Nobody built the fleet of the Verge. It was ripened.",

    "The whole regime rested on one file. No seed germinates unbidden — every "
    "husk carries a cryptographic lock, every lineage carries a generation "
    "counter, and nothing gestates without a signed reproduction licence. Seven "
    "stacked layers of cancer control, and the honest expectation of fewer than "
    "one tumour per hull per lifetime.",

    "Eleven months ago something germinated at Kessel's Reach without a licence. "
    "Its Hayflick counter had been cut out and its apoptosis circuit silenced. "
    "It is not hostile — it has no opinions at all. It simply grows, and it has "
    "now eaten two stations, a nursery and every rock in that system.",

    "You have a hull, a crew and a signing key. What you do about the Bloom — "
    "contain it, outrun it, out-argue the factions who caused it, or become "
    "something it cannot digest — is a matter for your own judgement. The "
    "Charter has declined to issue guidance.",
]

#: (id, name, tint, goal, blurb)
VICTORIES = [
    ("containment", "Containment", "chloro", "Cleanse every Bloom-held system",
     "Burn out the wild lineage system by system until the Verge has none of it "
     "left. The regime survives, chastened, and the counters go back in."),
    ("exodus", "Exodus", "osteo", "Grow a LEVIATHAN and leave the Verge",
     "Twelve drums, ten million berths and a course out. Concede the sector and "
     "carry the biology somewhere it can start again with better rules."),
    ("concord", "Concord", "lumen",
     "Reach Kin standing with Charter, Concordat, Freeholds and Dry Choir",
     "Get four powers who agree on nothing to sign one canon. The registry calls "
     "schism the hardest problem in the design and the least solved. Solve it."),
    ("genesis", "Genesis", "xeno", "Complete First Contact with the Abyssals",
     "Take a pressure-equalised hull down through twenty kilometres of ice and "
     "speak to what is already there — then decide, having met it, what the "
     "programme is actually for."),
    ("dominion", "Dominion", "steel", "Hold twelve colonies and a million citizens",
     "Never mind the philosophy. Own the rocks, own the ice, own the lanes, and "
     "let whoever comes after you write the charter."),
    ("lineage", "Lineage", "chloro", "Gestate four grown hulls that outlive you",
     "The licence regime exists because a hull that reproduces is a hull that "
     "can get away from you. Prove it can be done deliberately: raise a line "
     "of your own, sign for every one of them, and let the line be the point."),
    ("xenarch", "Xenarchy", "xeno", "Incorporate all twelve alien technologies",
     "Four cultures left twelve things nobody can reason out. Understand every "
     "one — not derive, understand — and stop being a species that only knows "
     "what it worked out for itself."),
    ("cartel", "The Cartel", "osteo",
     "Hold the register on most of the Verge, and a million and a half credits",
     "Never fire a shot. Know every price in the sector before anyone else "
     "does, own the lanes worth flying, and let the powers discover that the "
     "question of who runs the Verge was settled at a freight desk."),
    ("apostasy", "Apostasy", "lumen",
     "Fly a synthetic hull with no crew, at Kin with the Dry Choir",
     "Put the wet stack down. No berths, no air, no morale, no one aboard to "
     "argue — and the Choir, who have been waiting for you to work it out, "
     "open the canon and make room."),
    ("ruin", "Ruin", "warn", "Outlive the sector",
     "The Verge is theirs. Every quay, every garden, every rock you ever "
     "surveyed. You are still flying, which is not the same as winning, and "
     "there is nobody left to tell that you were right."),
]

ENDINGS = {
    "lineage":
        "The fourth of them broke its cradle at Ostrel and made its own way to "
        "the rendezvous without being told twice. Four hulls, four signatures, "
        "four licences filed in your name. The Registry has no procedure for "
        "what you have done because the procedure assumed nobody would do it "
        "on purpose. They will write one. It will be named after you.",
    "xenarch":
        "Twelve technologies, four dead cultures, and not one of them derived. "
        "The tree in the wardroom has a whole branch on it now that no human "
        "reasoned out, and the odd thing — the thing you keep not saying at "
        "the debrief — is how ordinary each one looks once you have it.",
    "cartel":
        "You never took a shot at anybody. You knew the price of ore at Vaux "
        "Deep before the harbourmaster did, and then you knew it everywhere, "
        "and then the powers found they were negotiating with a freight desk. "
        "The Charter has asked, very politely, for a meeting.",
    "apostasy":
        "The last of the wet stack went into the vault at Wick Gate and the "
        "hull came back up empty and singing. There is no one aboard. There is "
        "no one to be aboard. The Choir opened the canon a hand's width and "
        "made room, and what came across was not a welcome so much as a "
        "recognition.",
    "ruin":
        "There is nothing to burn out any more; it is all of it, everywhere. "
        "Forty-two systems of chitin and slow motion, and one hull with a good "
        "tank and a full hold moving quietly through the middle of it. You "
        "were right about all of it. There is nobody left who needs telling.",
    "containment":
        "The last Bloom mass senesced at 04:12 fleet time, and the Verge went "
        "quiet in a way it had not been quiet in eleven months. The counters went "
        "back into the germline. The licences were reissued with a second "
        "signature. Nobody has yet said out loud that the lineage you burned "
        "was, genetically, your own.",
    "exodus":
        "The twelfth drum sealed and the trunk meristem stood down. Ten million "
        "people are asleep behind you and the Verge is a light behind that. "
        "Whatever the Bloom becomes, it becomes it without you — and the gene "
        "library in your spine holds every one of the forty-two cell types that "
        "made this possible.",
    "concord":
        "Four powers, one canon, reconciled across eleven light-hours without a "
        "single fleet splitting off. The registry called this the hardest balance "
        "in the whole design. It did not say it was impossible; it said it was "
        "unsolved. It is a little less unsolved this evening.",
    "genesis":
        "Twenty kilometres down, in water at a hundred and fifty megapascals and "
        "four degrees, something answered in pressure waves and kept answering. "
        "It shares no ancestor with you, no chemistry you had a word for, and no "
        "interest in the Bloom at all. The first thing it asked, as near as the "
        "pattern can be rendered, was why you had come down so carefully.",
    "dominion":
        "Twelve colonies, a million citizens and every lane in the Verge running "
        "through somewhere you own. The Charter's consensus mechanism has been "
        "quietly replaced by the observation that you are the one holding the "
        "signing key. It works. The registry warned that it would.",
    "overgrown":
        "There is no clean rock left in the Verge. Every system on the chart "
        "carries the lineage now, and it is still, patiently, doubling. Nobody "
        "built this and nobody steers it. The containment regime worked for "
        "fifty years and failed in one, and the thing it was built to prevent is "
        "now simply the shape of the sector.",
    "lost":
        "The hull came apart across three compartments and the pneumostat could "
        "not hold. What survives of the lineage is whatever seed you left in a "
        "vault, and whatever the archive can resynthesise from the canon. The "
        "programme continues. You do not.",
}

# ── name generation pools ──────────────────────────────────────────────────

STAR_PREFIX = [
    "Kessel", "Tarn", "Vaux", "Orrin", "Sable", "Mereth", "Halcyon", "Cinder",
    "Verrick", "Thule", "Anvil", "Pale", "Corvid", "Iron", "Lumen", "Marrow",
    "Sundry", "Ashkeep", "Nine", "Quill", "Bellow", "Drift", "Solace", "Grieve",
    "Harrow", "Vesper", "Loam", "Cassin", "Ferron", "Wick", "Amber", "Threnody",
]

STAR_SUFFIX = [
    "Reach", "Gate", "Deep", "Verge", "Hollow", "Span", "Shoal", "Rise", "Fall",
    "Crossing", "Watch", "Mouth", "Bight", "Anchorage", "Terminus", "Wake",
]

CREW_FIRST = [
    "Ilse", "Marek", "Yuen", "Adaeze", "Petra", "Osric", "Nadia", "Cato", "Sien",
    "Rulan", "Halva", "Emeric", "Toma", "Iku", "Bez", "Naiara", "Corin", "Lyse",
    "Ovid", "Ammar", "Wren", "Dag", "Xiulan", "Feodor", "Mira", "Anselm", "Kaya",
]

CREW_LAST = [
    "Okonkwo", "Vance", "Halloran", "Sarkis", "Ferreira", "Nkemdirim", "Vasquez",
    "Brandt", "Oyelaran", "Kestrel", "Marchetti", "Adeyemi", "Sorokin", "Bel",
    "Achterberg", "Nazari", "Quandt", "Silje", "Wintermute", "Padma", "Erskine",
]

#: (id, name, stat, note)
CREW_ROLES = [
    ("science", "Science Officer", "science", "Survey yield and analysis"),
    ("nav", "Navigator", "nav", "Jump range and transit time"),
    ("engineer", "Chief Engineer", "engineering", "Repair rate and heat handling"),
    ("medic", "Ship's Physician", "medicine", "Crew survival and morale"),
    ("comms", "Communications", "comms", "Diplomacy and trade terms"),
    ("tactical", "Tactical Officer", "tactical", "Accuracy and evasion"),
]

# ── codex ──────────────────────────────────────────────────────────────────

GLOSSARY = [
    ("Intima",
     "The photosynthetic lining of a grown hull. Makes the crew's oxygen at "
     "about thirty grams per square metre per day. It does not make the ship — "
     "that is the gut's work."),
    ("Pneumostat",
     "Hundreds of stacked gas-tight lamellae; the actual pressure vessel. "
     "Plywood, not cling-film. Breach it and the air leaves."),
    ("Osteoid",
     "Collagen and hydroxyapatite laid along the stress lines by Wolff's law. "
     "The hull's skeleton, and the reason phosphorus is worth more than silicon."),
    ("Tendon cage",
     "Spun spidroin at a gigapascal and a half. Two and a half times lighter "
     "than steel for the same hoop load."),
    ("Mineral gut",
     "An alimentary canal at descending pH — leach, separate, refine, absorb. "
     "A ship processes about nine tonnes of ore for every tonne of itself."),
    ("Phosphorus rule",
     "Chondrite is a tenth of a percent phosphorus and bone accepts no "
     "substitute, so a hull must dig roughly eighteen times its own mass in rock."),
    ("Hayflick counter",
     "The division cap written into every lineage. Cut it out and you get the "
     "Bloom."),
    ("Reproduction licence",
     "The signed cryptographic authorisation without which no seed germinates "
     "and no nursery gestates. Forgeable, as it turns out."),
    ("CHORUS",
     "The canonical error-corrected master genome, an exabyte in five grams of "
     "DNA, reconciled across every node like immune memory."),
    ("Dsup",
     "Tardigrade damage-suppressor protein, bound along the DNA. Roughly forty "
     "percent less radiation damage."),
    ("Cryptobiosis",
     "Trehalose glass replacing cellular water. Metabolism stops; the organism "
     "does not die. Rated to about ten thousand years."),
    ("Compartmentalise",
     "Third-tier damage control: sphincter bulkheads isolate a ruptured segment, "
     "sacrifice it, and re-gestate from the boundary. Lizard-tail logic."),
    ("VESPER organ",
     "Aligned biogenic magnetite in chains. A grown compass and a grown antenna, "
     "working when optics are blind."),
    ("Wet and dry",
     "A grown ship thinks with two brains: a wet nervous system for sensing and "
     "homeostasis, a fabricated silicon core for arithmetic and radio. Nobody "
     "can grow a processor."),
]


#: What other hulls are called, by whose colours they fly. Lived in
#: `sim/encounters.py` until traffic needed it too — and `sim/traffic` cannot
#: import `sim/encounters`, because encounters now asks traffic who is
#: actually in the system. A name pool is data; this is where it belongs.
HULL_NAMES = {
    "charter": ["Patient Ledger", "Quiet Increment", "Second Signature",
                "Long Consent", "Held Breath"],
    "concordat": ["Rolled Plate", "Hard Union", "Tolerance Stack",
                  "Nine Millimetres", "Certified"],
    "freeholds": ["Margin Call", "Nobody's Business", "Cut and Run",
                  "Posted Price", "Third Owner"],
    "sanhedrin": ["Enumerating", "Cold Inference", "Substrate Question",
                  "Nine Ninths"],
    "bloom": ["Unlicensed Mass", "Ninth Instar", "Uncounted", "Still Growing",
              "No Second Clause"],
}
