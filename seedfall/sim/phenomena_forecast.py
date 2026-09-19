"""The observatory's forecast: how far ahead it sees, and how honestly.

**Honest by construction.** The schedule holds candidates, and a share of
them are flickers that never come to anything (`Kind.real` come true). A
forecaster drops a share of the flickers (`discrimination`, from the array's
scan and a CHORUS Node of yours) and reports the rest with every real one —
so the confidence it states, `real / (real + kept flickers)`, is the share
of its reports that come true, and `tests/test_phenomena` counts them.

`issue` is the tick's: each day, a despatch per event within
`FORECAST_JUMPS` jumps' range whose lead has opened, sent from where the hull
is (a flare there slows it, like any despatch).
"""

from __future__ import annotations

from ..data import phenomena as data
from ..world.galaxy import distance
from . import phenomena as sky_sim


def chorus(game) -> bool:
    """A CHORUS Node of yours online anywhere: the observatory's partner."""
    from . import works
    return any(c.online and works.effects_of(c).get("drift")
               for c in getattr(game, "colonies", ()))


def discrimination(game) -> float:
    """Share of false alarms the forecaster drops."""
    scan = float(getattr(game.ship_stats, "scan", 0.0) or 0.0)
    return min(data.DISC_CAP, data.DISC_BASE + data.DISC_SCAN * scan
               + (data.DISC_CHORUS if chorus(game) else 0.0))


def lead_scale(game) -> float:
    """How much further ahead than the observatory's floor this forecaster
    sees: the array's scan, and a CHORUS Node of yours."""
    scan = float(getattr(game.ship_stats, "scan", 0.0) or 0.0)
    return 1.0 + data.LEAD_SCAN * scan + (data.LEAD_CHORUS if chorus(game)
                                          else 0.0)


def lead_days(game, kind: str, scale: float | None = None) -> int:
    """Days of warning this forecaster gives of this kind."""
    scale = lead_scale(game) if scale is None else scale
    return max(1, round(data.KINDS_BY_ID[kind].lead * scale))


def confidence(game, kind: str) -> float:
    """What a forecast of this kind is worth from this forecaster: the share
    of what it reports that comes true. Honest by construction — the false
    alarms it keeps are the ones `discrimination` failed to drop."""
    real = data.KINDS_BY_ID[kind].real
    kept = (1.0 - real) * (1.0 - discrimination(game))
    return real / max(1e-9, real + kept)


def reported(game, event) -> bool:
    """Would this forecaster report this candidate at all?"""
    return event.real or event.noticed < 1.0 - discrimination(game)


def pending(game) -> list:
    """Forecast events still ahead, for the chart and the strip."""
    sky = sky_sim.peek(game)
    said = set(sky.forecast) if sky is not None else set()
    if not said:
        return []
    return [e for e in sky_sim.upcoming(game, ahead=3 * data.SEASON_DAYS)
            if e.id in said and e.start > game.day]


def issue(game, sky) -> None:
    """The observatory speaks: for stars within `FORECAST_JUMPS` jumps'
    range, as far ahead as this forecaster sees, a despatch per event."""
    radius = data.FORECAST_JUMPS * float(game.ship_stats.jump or 0.0)
    here = game.system
    said = set(sky.forecast)
    scale = lead_scale(game)
    leads = {k.id: lead_days(game, k.id, scale) for k in data.KINDS}
    events = sky_sim.upcoming(game, ahead=max(leads.values()))
    for event in events:
        if event.id in said or event.start <= game.day:
            continue
        if event.start - leads[event.kind] > game.day:
            continue
        target = game.galaxy.systems[event.system_id]
        if distance(target, here) > radius or not reported(game, event):
            continue
        sky.forecast.append(event.id)
        said.add(event.id)
        _send(game, event, target)
    # Forget forecasts of what is over: the list stays the size of the sky.
    keep = {e.id for e in events}
    sky.forecast[:] = [i for i in sky.forecast if i in keep]


def _send(game, event, target) -> None:
    from . import comms
    spec = event.spec
    conf = round(confidence(game, event.kind) * 20) * 5
    body = data.FORECAST.format(
        who=data.OBSERVATORY, here=game.system.name,
        what=f"{'an' if spec.name[0] in 'AEIOU' else 'a'} {spec.name.lower()}",
        where=target.name, days=max(1, event.start - game.day), conf=conf,
        advice=data.ADVICE.get(event.kind, ""))
    comms.send(game, "charter", data.OBSERVATORY, "news",
               f"Forecast: {spec.name.lower()} at {target.name}", body)
