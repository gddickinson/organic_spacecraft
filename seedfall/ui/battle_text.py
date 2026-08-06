"""The battle screen's words: forecasts and aftermath, as sentences.

Lifted out of `ui/battle_view.py` when the prize choice pushed that file at
the five-hundred-line ceiling. Nothing here decides anything — every figure
comes out of `sim/parley` and `sim/aftermath`, which is what stops the panel
promising a chance the dice will not see or a payout the ledger will not
move. The view draws widgets; this writes what they say.
"""

from __future__ import annotations

from ..core.util import credits as cr
from ..data.factions import FACTIONS_BY_ID
from ..sim import aftermath as aftermath_sim
from ..sim import parley as parley_sim


def parley_lines(b) -> list:
    """What the two ways out are worth, for the panel. From `sim/parley`."""
    out = []
    talk = parley_sim.odds(b)
    if talk["mute"]:
        out.append((f"Hailing them: {talk['why']}", "warn"))
    else:
        out.append((f"Hailing them: {talk['chance']:.0%} they stand down"
                    + (" — " + _terms(talk["terms"]) if talk["terms"] else "")
                    + ". Refused, they fire anyway.", "dim"))
    if b.fleeable:
        run = parley_sim.escape_odds(b)
        if run["held"]:
            out.append((f"Disengaging: {run['why']}", "warn"))
        else:
            out.append((f"Disengaging: {run['chance']:.0%} you shake them"
                        + (" — " + _terms(run["terms"]) if run["terms"] else "")
                        + ". Short, and they get the turn.", "dim"))
    return out


def _terms(terms) -> str:
    """Each named part of a chance, in points, worst or best first."""
    ranked = sorted(terms, key=lambda pair: -abs(pair[1]))
    return " · ".join(f"{name} {value * 100:+.0f}" for name, value in ranked)


def parley_tip(b, which: str) -> str:
    told = (parley_sim.odds(b) if which == "hail" else parley_sim.escape_odds(b))
    if told.get("mute") or told.get("held"):
        return told["why"]
    return (f"{told['chance']:.0%}. " + _terms(told["terms"])
            + ". If it fails they take their turn regardless.")


def aftermath_lines(out: dict) -> list[str]:
    """Turn what happened into what the bridge is told."""
    lines: list[str] = []
    if out["dead"]:
        lines.append("Lost in the action: " + ", ".join(out["dead"]) + ".")
    if out["result"] == "destroyed":
        lines.append(f"{round(out['salvage'])} units of their hardware came "
                     "off the wreck intact.")
        lines.append(f"Salvage: {cr(out['credits'])} and "
                     f"{out['research']} points of research.")
        for cid, take in out["recovered"].items():
            lines.append(f"{round(take)} t of {cid} pulled out of the wreck.")
        if out.get("recovered_worth"):
            # The cargo is the larger half of a wreck — measured, 1.5–10×
            # the credit loot — and the screen never priced it, so the
            # reason to fight was a number the captain could not see.
            lines.append("The recovered cargo is worth about "
                         f"{cr(out['recovered_worth'])} at a counter.")
        for c in out["bounties"]:
            lines.append(f"Bounty progress: {c.title} "
                         f"({int(c.progress)}/{int(c.amount)})"
                         + (" — paid." if c.done else "."))
        seized = out["seized"]
        if seized:
            lines.append("Their xenology files came out intact: "
                         f"{round(seized['points'])} points toward "
                         f"{seized['tech'].name}.")
            if seized["incorporated"]:
                lines.append(f"{seized['tech'].name} is now yours.")
    elif out["result"] == "driven-off":
        lines.append("They broke first. Your hull held and theirs did not "
                     "want to find out how long.")
    elif out["result"] == "struck":
        lines.append("Their colours are down and their bridge is waiting on "
                     "your word.")
    elif out["result"] == "parley" and out["fee"]:
        lines.append("They pay a courtesy for the trouble.")

    for fid, delta in out["standing"]:
        short = FACTIONS_BY_ID[fid].short
        lines.append(f"{short} standing "
                     + ("has fallen." if delta < 0 else f"+{delta:g}."))
    if out["pleased"]:
        # The half that never existed: everyone glad to see them lose one.
        lines.append("Word travels — "
                     + aftermath_sim.phrase_pleased(out["pleased"]) + ".")
    return lines
