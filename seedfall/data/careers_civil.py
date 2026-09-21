"""The lives a concourse is made of: six careers that are not a ship's crew.

The eight services in `data/careers.py` are all ways of being aboard
something — a Charter cutter, a yard, a hauler, a survey, a picket. That was
the whole of what a person in the Verge could have been, which meant every
officer's history was a variation on *went to space young*.

A sector with arcologies, hospitals, courts, hiring halls, brokerages, body
shops and fight pits has other lives in it, and the people who lived them end
up on bridges: a ship's physician who spent fifteen years in a trauma house
is a different person from one the Orders trained, and a purser who came off
a brokerage floor is a different person from a drifter who learned to haggle.

Six, chosen so that each one explains something the game now has:

- **Clinician** — the hospitals, the rejuvenation clinics, the body shops.
- **Factor** — the brokerages, the counting houses, the cargo floors.
- **Entertainer** — the playhouses, the vault concerts, the gaming floors.
- **Constable** — the port constabulary, and everybody it hands over.
- **Magistrate** — the licence office, the forum, the warrant.
- **Syndicate** — the other concourse: the fence, the chop shop, the way in.

Every one of them **ends somewhere a ship's officer can be hired from**,
which is the only reason a career belongs in this file at all.
"""

from __future__ import annotations

from .career_types import Career

CIVIL: tuple = (
    Career(
        "clinician", "Clinical Service",
        "Wards, theatres, and somebody on the desk at four in the morning.",
        qualify=("edu", 6), survive=("end", 4), advance=("edu", 8),
        ranks=("Orderly", "Nurse", "Physician", "Consultant",
               "Chief of medicine"),
        skills=("medic", "sciences", "pharmacy", "admin", "steward",
                "investigate"),
        officer_skills=("medic", "leadership", "cybernetics"),
        mishaps=(
            "Lost a patient who should not have been lost, and said so.",
            "Signed for a drug that was not what the label said.",
            "Struck off in one jurisdiction; nobody asks in the next.",
            "Burned out after a shipping accident took forty at once."),
        events=(
            "Spent a year in a trauma house and never slept properly again.",
            "Trained under somebody who had been doing it for sixty years.",
            "Worked a season on a plague world for the Orders.",
            "Fitted a limb for somebody who could not pay, and was owed."),
        benefits=("a physician's licence", "a surgical kit",
                  "a reference from a consultant", "a name in three ports"),
        station="medic"),

    Career(
        "factor", "The Factors",
        "Lots called, cargo moved, and nobody touching any of it.",
        qualify=("int", 6), survive=("soc", 4), advance=("int", 8),
        ranks=("Clerk", "Agent", "Factor", "Senior factor", "Principal"),
        skills=("broker", "admin", "trade", "persuade", "computers",
                "investigate"),
        officer_skills=("broker", "leadership", "law"),
        mishaps=(
            "Carried a position that went against them, and the house fell.",
            "Named in an audit they had warned about twice.",
            "Undercut by a partner who is still trading.",
            "Signed for a cargo that was not aboard."),
        events=(
            "Made a market in something nobody else would touch.",
            "Spent two years on a floor where everybody knew everybody.",
            "Learned what a manifest looks like when it is lying.",
            "Kept a shipping house solvent through a blockade."),
        benefits=("a letter of credit", "a seat on a floor",
                  "a list of buyers", "a partner who still owes them"),
        station="comms"),

    Career(
        "entertainer", "The Companies",
        "Four hours about somebody else's problems, six nights a week.",
        qualify=("soc", 5), survive=("dex", 4), advance=("soc", 8),
        ranks=("Walk-on", "Player", "Principal", "Leading player",
               "Company master"),
        skills=("art", "persuade", "carouse", "deception", "athletics",
                "steward"),
        officer_skills=("persuade", "leadership", "diplomat"),
        mishaps=(
            "The company folded between ports and left them on the quay.",
            "Said the wrong thing about the wrong power, on a stage.",
            "An injury that never came right.",
            "Followed somebody who was not worth following."),
        events=(
            "Played a season in a vault where the acoustics made them.",
            "Toured four systems in a hull that should not have flown.",
            "Learned to read a room before it read them.",
            "Was recognised in a port they had never been to."),
        benefits=("an instrument", "a following", "a costume trunk",
                  "an invitation that still works"),
        station="comms"),

    Career(
        "constable", "Port Constabulary",
        "Where a charge is answered, and where one is laid.",
        qualify=("end", 6), survive=("end", 5), advance=("int", 7),
        ranks=("Constable", "Senior constable", "Sergeant", "Inspector",
               "Port marshal"),
        skills=("security", "gun_combat", "investigate", "law", "recon",
                "admin"),
        officer_skills=("leadership", "tactics", "law"),
        mishaps=(
            "Took a beating in a dock riot and was pensioned for it.",
            "Gave evidence against a superior, and had no career after it.",
            "Shot somebody who turned out to be nobody.",
            "Transferred out after refusing to lose a file."),
        events=(
            "Worked customs, and learned exactly how a hold lies.",
            "Spent three years on the night shift of a bad concourse.",
            "Put away somebody who is out now and remembers.",
            "Was the one everybody called when it went wrong."),
        benefits=("a warrant card that still opens doors", "a sidearm",
                  "a contact in three constabularies",
                  "a pension somebody is still paying"),
        station="tactical"),

    Career(
        "magistrate", "The Forum",
        "Papers, precedent, and the people who hold them.",
        qualify=("edu", 7), survive=("soc", 4), advance=("edu", 8),
        ranks=("Clerk", "Advocate", "Assessor", "Magistrate",
               "Presiding magistrate"),
        skills=("law", "admin", "persuade", "investigate", "diplomat",
                "computers"),
        officer_skills=("law", "diplomat", "leadership"),
        mishaps=(
            "Ruled against a power that could reach them, and it did.",
            "A verdict overturned, loudly, by somebody with an interest.",
            "Resigned rather than sign what they were handed.",
            "Found to have known somebody they should have declared."),
        events=(
            "Sat on a tribunal that everybody in the Verge read about.",
            "Wrote a judgment three courts still quote.",
            "Spent four years on licences, and learned where the bodies are.",
            "Granted a clemency that a whole port remembers."),
        benefits=("an advocate's licence", "a precedent with their name on it",
                  "a robe nobody can take back",
                  "a favour owed by a sitting magistrate"),
        station="comms"),

    Career(
        "syndicate", "The Other Concourse",
        "No sign, no receipt, and a wider catalogue.",
        qualify=("dex", 5), survive=("int", 5), advance=("soc", 8),
        ranks=("Runner", "Hand", "Broker", "Lieutenant", "Principal"),
        skills=("streetwise", "deception", "security", "gun_combat",
                "cybernetics", "broker"),
        officer_skills=("leadership", "persuade", "tactics"),
        mishaps=(
            "The house was rolled up and they were the one left standing.",
            "Owed money to somebody who does not write it off.",
            "Informed on, by somebody they would still vouch for.",
            "Fitted with something in an afternoon, by somebody who left."),
        events=(
            "Ran a fence on a free port for two years without a word said.",
            "Learned which customs officers read a manifest and which do not.",
            "Moved something they will not name, for somebody they will not.",
            "Got a whole crew off a world that was closing."),
        benefits=("a contact in every free port", "a name that opens a door",
                  "a weapon with no papers",
                  "somebody who owes them their life"),
        station="tactical"),
)
