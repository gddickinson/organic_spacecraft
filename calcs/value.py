"""The `V` record every calcs module returns, and helpers to collect them.

A value is compared with the number printed in a document either
relatively (``mode="rel"``: |shown - calc| <= tol * |calc|, default 5 %) or
by order of magnitude (``mode="log"``: |log10 shown - log10 calc| <= tol).
The printed number is also allowed its own rounding (see docscheck).
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class V:
    value: float
    unit: str = ""
    note: str = ""
    tol: float = 0.05
    mode: str = "rel"          # 'rel' | 'log'


def collect(prefix, **kw):
    """Namespace a module's values: collect('navis', area=V(...)) -> {'navis.area': V}."""
    return {f"{prefix}.{k}": v for k, v in kw.items()}
