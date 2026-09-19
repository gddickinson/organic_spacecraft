"""Every computed value, by key. The single table `docscheck` compares against."""

from . import budget, growth, habitat, lifesupport, metabolism, meteoroids, navis, thermal

MODULES = (navis, thermal, meteoroids, lifesupport, growth, metabolism, habitat, budget)


def all_values():
    out = {}
    for mod in MODULES:
        vals = mod.values()
        clash = set(vals) & set(out)
        if clash:
            raise KeyError(f"duplicate calcs keys: {sorted(clash)}")
        out.update(vals)
    return out
