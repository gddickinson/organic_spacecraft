"""Two small games inside the game.

DOCKING is the control loop the nervous-system study sets out: sense with the
wet organs, compute on the dry core, act with the muscles, and hold homeostasis
while you do it. Three axes drift; you can correct one per pass; the ship's
sensors tell you how far off you are and its compute tells you how precisely.

DECODING is what you do with a recording of something that was not speaking to
you. A hidden pattern, a guess, and feedback that says how much of the guess was
right without saying which part.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from ..core.save import register

# ── docking ────────────────────────────────────────────────────────────────

AXES = [("range", "Closing range"), ("attitude", "Attitude"), ("roll", "Roll")]
#: What a botched approach costs when the tug has to bring you in.
TUG_FEE = 900
TOLERANCE = 6
DOCK_PASSES = 8

#: The best a computer-flown approach can be graded. A clean dock, and none
#: of the standing that a good one earns.
AUTO_GRADE = 1


@register
@dataclass
class Docking:
    port_name: str
    error: dict[str, int] = field(default_factory=dict)
    drift: dict[str, int] = field(default_factory=dict)
    passes: int = DOCK_PASSES
    precision: int = 4        # how much one correction moves an axis
    noise: int = 0            # how badly the readout is blurred
    log: list = field(default_factory=list)
    over: bool = False
    won: bool = False
    #: How many passes the drive computer flew. A machine can bring you
    #: alongside; it does not bring you alongside *well*.
    flown: int = 0

    def reading(self, axis: str, rng) -> int:
        """What the instruments say, which is not quite what is true."""
        if self.noise <= 0:
            return self.error[axis]
        return self.error[axis] + rng.int(-self.noise, self.noise)

    @property
    def aligned(self) -> bool:
        return all(abs(v) <= TOLERANCE for v in self.error.values())


def start_docking(rng, port_name: str, stats, officers) -> Docking:
    """Harder in a clumsy hull; easier with a good navigator and a dry core."""
    nav = max((o.level for o in officers if o.stat == "nav"), default=0)
    d = Docking(port_name=port_name)
    for axis, _ in AXES:
        d.error[axis] = rng.int(18, 46) * rng.pick([1, -1])
        d.drift[axis] = rng.int(-3, 3)
    d.precision = 4 + nav + int(stats.accuracy * 6)
    d.noise = max(0, 5 - int(stats.sensor))
    d.passes = DOCK_PASSES + (1 if nav >= 3 else 0)
    say(d, f"Approach to {port_name}. Three axes out of tolerance.", "")
    return d


def say(d: Docking, text: str, kind: str = "") -> None:
    d.log.append((text, kind))
    if len(d.log) > 40:
        d.log.pop(0)


def correct(d: Docking, axis: str, amount: int, rng,
            by_computer: bool = False) -> dict:
    """Fire on one axis. Everything else keeps drifting while you do."""
    if d.over:
        return {"ok": False}
    before = d.error[axis]
    d.error[axis] = before - amount
    for other, _ in AXES:
        if other != axis:
            d.error[other] += d.drift[other]
    d.passes -= 1
    if by_computer:
        d.flown += 1

    label = dict(AXES)[axis]
    say(d, f"{label}: corrected {amount:+d}, now reading "
           f"{d.error[axis]:+d}.", "good" if abs(d.error[axis]) <= TOLERANCE else "")

    if d.aligned:
        d.over, d.won = True, True
        say(d, "All three inside tolerance. The sphincter takes the collar.", "good")
    elif d.passes <= 0:
        d.over, d.won = True, False
        say(d, "Out of passes. The approach is waved off.", "bad")
    return {"ok": True, "aligned": d.aligned}


def forecast(d: Docking, axis: str, amount: int) -> dict:
    """What one correction leaves behind, drift included.

    The approach was three numbers and six buttons. Firing on an axis moves
    it *and* lets the other two drift while you do — which the screen never
    said, so a pilot correcting the worst axis could watch the other two walk
    out of tolerance and never learn why. This states it before the burn.
    """
    after = dict(d.error)
    after[axis] = d.error[axis] - amount
    for other, _label in AXES:
        if other != axis:
            after[other] = d.error[other] + d.drift[other]
    inside = sum(1 for v in after.values() if abs(v) <= TOLERANCE)
    was = sum(1 for v in d.error.values() if abs(v) <= TOLERANCE)
    return {"after": after, "inside": inside, "was": was,
            "aligned": inside == len(AXES),
            "passes_left": max(0, d.passes - 1),
            "worse": [o for o, _l in AXES
                      if o != axis and abs(after[o]) > TOLERANCE
                      and abs(d.error[o]) <= TOLERANCE]}


def autopilot(d: Docking) -> dict:
    """What the drive computer would do next, and why.

    The same bargain as the battle computer: it is competent and it is not
    you. It corrects the axis that costs most to leave — weighing how far out
    it is against how fast it is drifting — and it cannot fire harder than the
    hull's precision allows, so a clumsy hull is clumsy under automation too.
    """
    if d.over:
        return {}
    best, why = None, ""
    for axis, label in AXES:
        error = d.error[axis]
        if abs(error) <= TOLERANCE:
            continue
        # Cost of leaving it: how far out, plus where the drift is taking it.
        drift = d.drift[axis]
        urgency = abs(error) + (abs(drift) * 2 if error * drift >= 0 else 0)
        if best is None or urgency > best[0]:
            step = max(-d.precision, min(d.precision, error))
            best = (urgency, axis, step,
                    f"{label} is {error:+d} and "
                    + (f"drifting further out at {drift:+d} a pass."
                       if error * drift > 0 else
                       "the worst of the three."))
    if best is None:
        return {}
    _urgency, axis, step, why = best
    return {"axis": axis, "amount": step, "why": why,
            "forecast": forecast(d, axis, step)}


def dock_result(d: Docking) -> dict:
    """What a clean approach is worth.

    A hand-flown approach earns its margin; a computer-flown one gets you the
    collar and nothing else. Without this the autopilot matched a careful
    pilot exactly — measured at 59.5% against 58.5% — which makes the
    approach a chore to be automated away rather than a thing worth being
    good at. The machine docks you. It does not dock you well.
    """
    if d.won:
        margin = sum(TOLERANCE - abs(v) for v in d.error.values())
        grade = min(3, 1 + margin // 6)
        if d.flown:
            grade = min(grade, AUTO_GRADE)
        return {"won": True, "grade": grade, "flown": d.flown}
    return {"won": False, "grade": 0}


def come_alongside(game, docking) -> dict:
    """What the approach was worth once you are made fast.

    Was written into `minigame_view._finish()`, so tying up — and the standing
    or the tug fee that comes with it — could not happen without a screen.
    """
    from . import loyalty as loyalty_sim
    res = dock_result(docking)
    port = game.system.port
    faction = port.faction if port else None
    out = {"won": res["won"], "grade": res["grade"], "fee": 0, "standing": 0}
    if res["won"]:
        bonus = res["grade"] * 2
        if faction:
            game.adjust_rep(faction, bonus)
        out["standing"] = bonus
        game.add_log(f"Clean approach at {docking.port_name}; "
                     f"standing +{bonus}.", "good")
    else:
        fee = TUG_FEE
        game.credits = max(0.0, game.credits - fee)
        if faction:
            game.adjust_rep(faction, -1)
        out["fee"], out["standing"] = fee, -1
        game.add_log(f"Tugged in at {docking.port_name}. {fee:,} for the "
                     "service.", "warn")
    loyalty_sim.record(game, "docked_clean" if res["won"] else "")
    game.flags["docked_at"] = game.system.id
    return out


# ── decoding ───────────────────────────────────────────────────────────────

GLYPHS = ["◈", "◆", "✦", "○", "△", "▽"]
CODE_LENGTH = 4
DECODE_TRIES = 8


@register
@dataclass
class Decoding:
    subject: str
    secret: list[int] = field(default_factory=list)
    guesses: list = field(default_factory=list)   # (guess, exact, near)
    tries: int = DECODE_TRIES
    over: bool = False
    won: bool = False
    palette: int = 5

    @property
    def used(self) -> int:
        return len(self.guesses)


def start_decoding(rng, subject: str, stats, officers) -> Decoding:
    """A good science officer narrows the alphabet; good sensors buy attempts."""
    sci = max((o.level for o in officers if o.stat == "science"), default=0)
    palette = max(4, len(GLYPHS) - (1 if sci >= 3 else 0))
    d = Decoding(subject=subject, palette=palette,
                 tries=DECODE_TRIES + (1 if stats.scan > 0.6 else 0))
    d.secret = [rng.int(0, palette - 1) for _ in range(CODE_LENGTH)]
    return d


def score(secret: list[int], guess: list[int]) -> tuple[int, int]:
    """Exact positions, and right glyph in the wrong place."""
    exact = sum(1 for a, b in zip(secret, guess) if a == b)
    left_s = [a for a, b in zip(secret, guess) if a != b]
    left_g = [b for a, b in zip(secret, guess) if a != b]
    near = 0
    pool = list(left_s)
    for g in left_g:
        if g in pool:
            pool.remove(g)
            near += 1
    return exact, near


def guess(d: Decoding, attempt: list[int]) -> dict:
    if d.over or len(attempt) != CODE_LENGTH:
        return {"ok": False}
    exact, near = score(d.secret, attempt)
    d.guesses.append((list(attempt), exact, near))
    d.tries -= 1
    if exact == CODE_LENGTH:
        d.over, d.won = True, True
    elif d.tries <= 0:
        d.over, d.won = True, False
    return {"ok": True, "exact": exact, "near": near,
            "won": d.won, "over": d.over}


def decode_result(d: Decoding) -> dict:
    """Understanding earned. Solving it early is worth more."""
    if not d.won:
        return {"won": False, "points": 0}
    spare = max(0, d.tries)
    return {"won": True, "points": 40 + spare * 12}
