"""Watching the sky, and selling what was seen.

**Observe** is an act at a live phenomenon: it spends days and gives
*phenomena* evidence, a kind the research bench keeps with the other four
(`data/inquiry.EVIDENCE`) and spends as a bonus on the sensor, shielding and
Deep Weave programmes (`inquiry.draw`). Each event is watched once — the
nova twice, once brightening and once as the burst from a safe distance.
`observe_quote` states the days, the evidence and what the data would fetch,
and `observe` spends exactly those days and gives exactly that: nothing in
either is rolled.

**Selling** is at a Charter or Dry Choir counter: every observation not yet
sold, priced by the rarity of its kind (`Kind.value`), how well it was
taken, a premium on the first of each kind, and — the Choir's fortune — a
multiple on burst data. Through `wharfage.collect`, like every sale.
"""

from __future__ import annotations

from ..data import phenomena as data
from . import phenomena as sky_sim
from . import phenomena_nova as nova_sim


def quality(game) -> float:
    """How well this array takes a phenomenon."""
    scan = float(getattr(game.ship_stats, "scan", 0.0) or 0.0)
    lo, hi = data.OBS_RANGE
    return max(lo, min(hi, data.OBS_BASE + data.OBS_SCAN * scan))


def _watched(game) -> set:
    sky = sky_sim.peek(game)
    return {o.event for o in getattr(sky, "observed", ()) or ()}


def _candidates(game) -> list:
    """(event id, kind, stage, system id) watchable from here, best first."""
    seen = _watched(game)
    out = [(e.id, e.kind, "", e.system_id) for e in sky_sim.active(game)
           if e.kind != "nova"]
    nova = nova_sim.event(game)
    if nova is not None:
        if (nova_sim.phase(game) == "brightening"
                and nova_sim.dose_at(game, game.system) > 0):
            out.append((f"{nova.id}:brightening", "nova", "brightening",
                        nova.system_id))
        if nova_sim.burst_visible(game):
            out.append((f"{nova.id}:burst", "nova", "burst", nova.system_id))
    out = [row for row in out if row[0] not in seen]
    out.sort(key=lambda row: (data.PRIORITY.index(row[1]),
                              row[2] != "burst"))
    return out


def observe_quote(game) -> dict:
    """What watching the best thing in this sky would take and give."""
    rows = _candidates(game)
    if not rows:
        live = sky_sim.active(game)
        why = ("Already watched — there is nothing new in it."
               if live else "Nothing in this sky worth the watch.")
        return {"ok": False, "why": why, "days": 0, "evidence": 0.0,
                "worth": 0}
    event_id, kind, stage, sid = rows[0]
    spec = data.KINDS_BY_ID[kind]
    q = quality(game)
    scale = data.BURST_SCALE if stage == "burst" else 1.0
    evidence = round(spec.evidence * q * scale, 1)
    worth = round(spec.value * q * scale)
    name = spec.name + (f", {stage}" if stage else "")
    return {"ok": True, "why": "", "event": event_id, "kind": kind,
            "stage": stage, "system_id": sid, "name": name,
            "days": spec.watch, "quality": round(q, 3),
            "evidence": evidence, "worth": worth}


def observe(game) -> dict:
    """Watch it: the days pass, the evidence is banked, the data is kept."""
    said = observe_quote(game)
    if not said["ok"]:
        return said
    from . import inquiry
    from .phenomena import Observation
    sky = sky_sim.state(game)
    game.advance_days(said["days"])
    inquiry.add(game.research, "phenomena", said["evidence"])
    sky.observed.append(Observation(
        event=said["event"], kind=said["kind"], system_id=said["system_id"],
        day=game.day, quality=said["quality"], evidence=said["evidence"],
        stage=said["stage"]))
    text = (f"Watched the {said['name'].lower()} for {said['days']} days: "
            f"{said['evidence']:g} phenomena evidence, and data a buyer "
            "will want.")
    # In the Cradle the Kith sing about their stars (`sim/kith.observe`):
    # watching one with them teaches their words for place.
    from . import kith
    if kith.observe(game, said["evidence"]) > 0:
        text += " The Kith sang about it; you understood a little more."
    game.add_log(text, "good")
    return {**said, "text": text}


# ── the data sale ──────────────────────────────────────────────────────────

def price(obs, buyer: str, first: bool) -> int:
    """What one observation fetches from this buyer."""
    spec = data.KINDS_BY_ID[obs.kind]
    worth = spec.value * obs.quality
    if obs.stage == "burst":
        worth *= data.BURST_SCALE
        if buyer == "sanhedrin":
            worth *= data.CHOIR_BURST
    if first:
        worth *= data.FIRST_OF_KIND
    return round(worth)


def sale_quote(game) -> dict:
    """What this counter would pay for everything watched and not yet sold."""
    port = game.system.port
    if port is None or port.faction not in data.BUYERS:
        return {"ok": False, "why": "Only the Charter and the Dry Choir buy "
                                    "sky data.", "lots": [], "total": 0}
    sky = sky_sim.peek(game)
    seen = list(getattr(sky, "observed", ()) or ())
    sold = {o.kind for o in seen if o.sold}
    lots = []
    for obs in seen:
        if obs.sold:
            continue
        lots.append((obs, price(obs, port.faction, obs.kind not in sold)))
        sold.add(obs.kind)
    if not lots:
        return {"ok": False, "why": "No sky data aboard that has not been "
                                    "sold.", "lots": [], "total": 0}
    # **Quoted as it lands:** the button once read 4,819 and paid 4,738,
    # the quay's wharfage never mentioned (play-test, 2026-09-18). And the
    # buyer pays out of its own purse — nothing is conjured.
    from . import exchequer
    from . import wharfage as wharfage_sim
    total = sum(p for _o, p in lots)
    if exchequer.purse(game, port.faction).credits < total:
        return {"ok": False, "why": "Their purse cannot cover it today.",
                "lots": [], "total": 0}
    due = wharfage_sim.due_on(game, game.system, total)
    return {"ok": True, "why": "", "lots": lots, "buyer": port.faction,
            "total": total, "due": due, "net": total - due}


def sell(game) -> dict:
    """Hand it over. Each observation sells once."""
    said = sale_quote(game)
    if not said["ok"]:
        return said
    from . import wharfage as wharfage_sim
    system = game.system
    from . import exchequer
    took = said["total"]
    exchequer.purse(game, said["buyer"]).credits -= took
    game.credits += took
    due = wharfage_sim.collect(game, system, took)
    for obs, _price in said["lots"]:
        obs.sold = True
    game.adjust_rep(said["buyer"], min(data.DATA_REP_CAP,
                                       data.DATA_REP * len(said["lots"])))
    n = len(said["lots"])
    text = (f"Sold {n} lot{'s' if n != 1 else ''} of sky data for {took:,}."
            + (f" Wharfage {due:,}, {took - due:,} clear." if due else ""))
    game.add_log(text, "good")
    return {**said, "due": due, "net": took - due, "text": text}
