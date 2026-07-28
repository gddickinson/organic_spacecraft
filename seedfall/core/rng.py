"""Seeded pseudo-random number generation.

Every world in SEEDFALL is reproducible from a single seed string, so the
galaxy, its markets and its lifeforms regenerate identically on reload. The
generator is a mulberry32 rather than :mod:`random` so that a saved seed always
grows the same sky regardless of interpreter version.
"""

from __future__ import annotations

import math
from typing import Any, Iterable, Sequence

MASK = 0xFFFFFFFF


def hash_seed(text: str) -> int:
    """Hash a string into a 32-bit integer seed (xmur3)."""
    h = (1779033703 ^ len(text)) & MASK
    for ch in text:
        h = (h ^ ord(ch)) & MASK
        h = (h * 3432918353) & MASK
        h = ((h << 13) | (h >> 19)) & MASK
    h = (h ^ (h >> 16)) & MASK
    h = (h * 2246822507) & MASK
    h = (h ^ (h >> 13)) & MASK
    h = (h * 3266489909) & MASK
    return (h ^ (h >> 16)) & MASK


class RNG:
    """A small, fast, well-distributed generator with the helpers we need."""

    __slots__ = ("_a", "seed")

    def __init__(self, seed: str | int):
        self.seed = hash_seed(seed) if isinstance(seed, str) else int(seed) & MASK
        self._a = self.seed

    def next(self) -> float:
        """Float in [0, 1)."""
        self._a = (self._a + 0x6D2B79F5) & MASK
        t = self._a
        t = ((t ^ (t >> 15)) * (1 | t)) & MASK
        t = ((t + (((t ^ (t >> 7)) * (61 | t)) & MASK)) & MASK) ^ t
        return ((t ^ (t >> 14)) & MASK) / 4294967296.0

    def float(self, lo: float = 0.0, hi: float = 1.0) -> float:
        return lo + self.next() * (hi - lo)

    def int(self, lo: int, hi: int) -> int:
        """Integer in [lo, hi] inclusive."""
        return int(math.floor(lo + self.next() * (hi - lo + 1)))

    def chance(self, p: float) -> bool:
        return self.next() < p

    def pick(self, items: Sequence[Any]) -> Any:
        return items[int(self.next() * len(items))]

    def sample(self, items: Sequence[Any], n: int) -> list:
        """n distinct elements (or all of them, if n is larger)."""
        pool = list(items)
        out: list = []
        while len(out) < n and pool:
            out.append(pool.pop(int(self.next() * len(pool))))
        return out

    def weighted(self, pairs: Iterable[tuple[float, Any]]) -> Any:
        """Pick from ``(weight, value)`` pairs."""
        pairs = list(pairs)
        total = sum(w for w, _ in pairs)
        r = self.next() * total
        for w, v in pairs:
            r -= w
            if r <= 0:
                return v
        return pairs[-1][1]

    def shuffle(self, items: list) -> list:
        """In-place Fisher-Yates; returns the list."""
        for i in range(len(items) - 1, 0, -1):
            j = int(self.next() * (i + 1))
            items[i], items[j] = items[j], items[i]
        return items

    def gauss(self, mean: float, spread: float,
              lo: float = -math.inf, hi: float = math.inf) -> float:
        """Roughly normal (sum of three uniforms), clamped."""
        u = (self.next() + self.next() + self.next()) / 3
        return max(lo, min(hi, mean + (u - 0.5) * 2 * spread))
