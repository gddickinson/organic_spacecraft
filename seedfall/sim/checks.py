"""Two dice, a skill and a characteristic: one grammar under everything.

*Traveller* has resolved every task the same way since 1977, and the reason
it has never needed replacing is that the whole of it fits in one line:

    2d6 + skill + characteristic DM + difficulty DM  ≥  8

Everything else in that game is a way of changing one of those four terms.
SEEDFALL has resolved a dozen acts a dozen different ways — a percentage
here, a weighted pick there, a bespoke curve for digging — and none of them
can be compared, taught, or shown to a player as a number they can improve.
This is the one grammar, offered for new acts and for old ones as they are
brought across. **It replaces nothing on its own**: an act that already has a
tuned curve keeps it until somebody re-pins the curve.

**The Effect is the part people forget.** A check does not answer yes or no;
it answers *by how much*, and the margin is what turns one roll into a
sentence — how long the work took, how much was salvaged, how badly it went.
`Check.effect` is the roll minus the target, and every caller is expected to
use it for something.

Nothing here draws its own luck. An `RNG` comes in, which is how the caller
stays responsible for whether this roll moves the chronicle's own stream.
"""

from __future__ import annotations

from dataclasses import dataclass

#: The six characteristics, in Traveller's own order, and what each is called
#: in a game about grown hulls on a frontier.
#:
#: `SOC` is kept because the Verge has powers, licences and standing, and a
#: captain's name opening a door is exactly what it is for.
CHARACTERISTICS = (
    ("str", "Strength", "what you can shift, and take"),
    ("dex", "Dexterity", "hands, and how fast they are"),
    ("end", "Endurance", "how long you last at it"),
    ("int", "Intellect", "what you work out"),
    ("edu", "Education", "what you were taught, and remember"),
    ("soc", "Standing", "whose name opens which door"),
)
CHARACTERISTIC_IDS = tuple(c[0] for c in CHARACTERISTICS)

#: The dice modifier a characteristic is worth. Traveller's own table: a
#: score of 7-8 is average and worth nothing, and the ends are worth ±3. It
#: is steep on purpose — a characteristic of 2 is a real problem.
def modifier(score: int) -> int:
    """The DM for a characteristic score, -3 to +3."""
    if score <= 0:
        return -3
    if score <= 2:
        return -2
    if score <= 5:
        return -1
    if score <= 8:
        return 0
    if score <= 11:
        return 1
    if score <= 14:
        return 2
    return 3


#: What a task's difficulty is worth, as a DM. Traveller's ladder, and the
#: names are the ones a referee says out loud — which matters, because a
#: screen that says "difficult" and rolls "average" is the kind of quiet lie
#: this project keeps hunting down.
DIFFICULTIES = (
    ("simple", "Simple", 6),
    ("easy", "Easy", 4),
    ("routine", "Routine", 2),
    ("average", "Average", 0),
    ("difficult", "Difficult", -2),
    ("very_difficult", "Very difficult", -4),
    ("formidable", "Formidable", -6),
)
DIFFICULTY_DM = {d[0]: d[2] for d in DIFFICULTIES}
DIFFICULTY_NAME = {d[0]: d[1] for d in DIFFICULTIES}

#: What a check has to reach. Eight, always — the difficulty is a modifier,
#: not a moving target. One number is what lets a player learn the odds.
TARGET = 8

#: What being untrained costs. Traveller charges -3 for a skill you have
#: never had, which is the difference between "I have not done this" and "I
#: am bad at it" — and it is why a crew with the wrong specialists is in real
#: trouble rather than mildly inconvenienced.
UNTRAINED = -3


@dataclass(frozen=True)
class Check:
    """One roll, and everything a caller needs to say what happened."""

    rolled: int                 # the two dice alone
    skill: int
    characteristic: int         # the DM, not the score
    difficulty: int
    extra: int                  # whatever the caller added
    #: What it was for, for the log and the screen.
    about: str = ""
    what: str = ""              # the skill's name
    how: str = "average"        # the difficulty's id

    @property
    def total(self) -> int:
        return (self.rolled + self.skill + self.characteristic
                + self.difficulty + self.extra)

    @property
    def effect(self) -> int:
        """By how much. Negative is by how much it failed."""
        return self.total - TARGET

    @property
    def ok(self) -> bool:
        return self.effect >= 0

    @property
    def exceptional(self) -> bool:
        """Six or better over: the outcome nobody planned for."""
        return self.effect >= 6

    @property
    def disaster(self) -> bool:
        """Six or worse under: the outcome that costs something."""
        return self.effect <= -6

    def __str__(self) -> str:
        return line(self)


def roll(rng, skill: int = 0, score: int = 7, how: str = "average",
         extra: int = 0, about: str = "", what: str = "") -> Check:
    """Make a check. `skill` is levels, `score` is the characteristic itself.

    `skill` below zero is taken as untrained rather than as a penalty the
    caller worked out, so every site spells the same rule the same way:
    passing `-1` and passing `UNTRAINED` mean the same thing and both mean
    "has never done this".
    """
    dice = rng.int(1, 6) + rng.int(1, 6)
    trained = int(skill) if skill >= 0 else UNTRAINED
    return Check(rolled=dice, skill=trained, characteristic=modifier(score),
                 difficulty=DIFFICULTY_DM.get(how, 0), extra=int(extra),
                 about=about, what=what, how=how)


def chance(skill: int = 0, score: int = 7, how: str = "average",
           extra: int = 0) -> float:
    """How likely that check is to pass, 0..1 — the *forecast*.

    **Preview equals act**: every screen that offers a check has to be able
    to say the odds before the player commits, and it must be the same
    arithmetic the roll uses. Two dice have 36 outcomes and the table is
    exact, so this is a count rather than an estimate.
    """
    trained = int(skill) if skill >= 0 else UNTRAINED
    need = TARGET - (trained + modifier(score)
                     + DIFFICULTY_DM.get(how, 0) + int(extra))
    hits = sum(1 for a in range(1, 7) for b in range(1, 7) if a + b >= need)
    return hits / 36.0


def line(check: Check) -> str:
    """One sentence about a roll that has happened."""
    verdict = ("outstanding" if check.exceptional
               else "a bad business" if check.disaster
               else "clear" if check.ok else "short")
    what = f"{check.what} " if check.what else ""
    return (f"{what}{DIFFICULTY_NAME.get(check.how, 'Average').lower()}: "
            f"{check.rolled} on two dice {check.total:+d} against {TARGET} — "
            f"{verdict} by {abs(check.effect)}.")
