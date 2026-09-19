"""Formatting and small maths helpers shared by the simulation and the GUI."""

from __future__ import annotations


def clamp(v: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, v))


def num(v: float) -> str:
    """Thousands-separated integer."""
    return f"{round(v):,}"


def credits(v: float) -> str:
    """Credits, with the game's currency mark."""
    return f"₡{num(v)}"


def mass(tonnes: float) -> str:
    """Compact mass: 940 kg / 24.0 kt / 2.5 Gt."""
    if tonnes < 1:
        return f"{round(tonnes * 1000)} kg"
    if tonnes < 1000:
        return f"{tonnes:.1f} t" if tonnes < 10 else f"{tonnes:.0f} t"
    if tonnes < 1e6:
        return f"{tonnes / 1e3:.1f} kt"
    if tonnes < 1e9:
        return f"{tonnes / 1e6:.1f} Mt"
    return f"{tonnes / 1e9:.1f} Gt"


def reaction_mass(tonnes: float) -> str:
    """Reaction mass, one way everywhere: tonnes, to a tenth.

    It was printed three ways for one tank — "48.0" with no unit on the conn
    panel, "48.00 t" on the flight controls and "48 t" at the helm — so a
    pilot comparing two windows could not tell whether they agreed. Not
    `mass`, which changes unit with size: a tank is read against a burn quoted
    in tenths of a tonne, and 0.4 t and "400 kg" are the same fact in two
    languages.
    """
    return f"{max(0.0, tonnes):,.1f} t"


def stardate(day: int) -> str:
    """Days since epoch as an in-fiction stardate: ``Y3 D141``."""
    # Coerced on the way in: a formatting helper is never the right place for
    # the game to fall over, whatever it is handed.
    day = int(day)
    return f"Y{day // 365 + 1} D{day % 365 + 1:03d}"


def duration(days: float) -> str:
    """A span of days, spoken the way the crew would say it."""
    if days < 1:
        return "hours"
    if days < 45:
        return f"{round(days)} d"
    if days < 730:
        return f"{days / 30.4:.1f} mo"
    return f"{days / 365:.1f} yr"


def pct(v: float) -> str:
    return f"{round(v * 100)}%"


def cost_line(cost: dict) -> str:
    """Render a materials bill: ``₡12,000 · 20 t biomass · 20 t ore``."""
    bits = []
    for key, n in cost.items():
        bits.append(credits(n) if key == "credits" else f"{n:g} t {key}")
    return " · ".join(bits)


_ONES = ("zero one two three four five six seven eight nine ten eleven twelve "
         "thirteen fourteen fifteen sixteen seventeen eighteen nineteen").split()
_TENS = "_ _ twenty thirty forty fifty sixty seventy eighty ninety".split()


def spelled(n: int) -> str:
    """A count as prose writes it, under a hundred; digits above.

    For text that states a count from the data rather than from memory — the
    tutorial said "fifty-eight nodes" of a sixty-two node tree and "six powers"
    of four, both true once and neither updated since.
    """
    if not 0 <= n < 100:
        return f"{n:,}"
    if n < 20:
        return _ONES[n]
    tens, ones = divmod(n, 10)
    return _TENS[tens] + (f"-{_ONES[ones]}" if ones else "")
