"""The living sky: what the stars are doing, and the one door for each effect.

The sky is **scheduled, not rolled**. Each system's season is drawn from its
own key, `RNG(f"{seed}:sky:{system}:{season}")`, so the sky is the same
whoever looks, a chart opened a thousand times changes nothing, and none of
it takes a number from the chronicle's own luck. Every kind draws the same
count of numbers whether it happens or not (`data/phenomena.KINDS` is
append-only), and a region's stars have no sky before it was opened.

Each effect is one function here, read by the one system it affects and
switched off by a check in `tests/test_phenomena.py`:

- `dose` / `irradiate` — a flare's hard light and the nova's mounting dose,
  after `shelter` and the hull's own shielding (`regions.shield`, which is
  where the living hull's `dose_multiplier` is applied), beside the Cradle's
  dose in `core/shiptime.hull`; a flare also feeds the `glare` channel;
- `lane_closed` / `closed_systems` — an ion storm, read by `actions.jump_to`
  and its quote, `reach` (and so `lineroute`) and `gates.quote`;
- `survey_scale` (the survey), `sensor_scale` (`detection`, `telemetry`),
  `comms_delay` (`comms.send`), `aurora_yield` / `aurora_risk`
  (`actions.extract`, `actions.dive`);
- `transient_bodies` — the comets and rogues passing through.

The clock calls `tick` in sector time; `sim/phenomena_tick.py` does the
work. The forecast is `sim/phenomena_forecast.py`; shelter from a flare
`sim/phenomena_shelter.py`; observing and selling what was seen
`sim/phenomena_science.py`; the nova `sim/phenomena_nova.py`; bodies that
come and go `sim/phenomena_bodies.py`.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from ..core.rng import RNG
from ..core.save import register
from ..data import phenomena as data
from ..data.regions import VERGE


@register
@dataclass
class Observation:
    """One phenomenon watched: what it was, where, and whether it is sold."""
    event: str
    kind: str
    system_id: int
    day: int
    quality: float
    evidence: float
    #: "" for most; the nova's two: "brightening" and "burst".
    stage: str = ""
    sold: bool = False


@register
@dataclass
class NovaState:
    """The chronicle's one nova: chosen when the Cradle opens, never again."""
    system_id: int
    begins: int
    bursts: int
    burst: bool = False
    forecast: bool = False


@register
@dataclass
class SkyState:
    """What the sky has done that has to be remembered.

    The schedule itself is never stored — it is derived from the seed. This
    is only what an event *left*: bodies still passing (event id → [system,
    body id]), what the captain has been told, what was forecast, what was
    watched, the shadow the hull is keeping, and the nova.
    """
    transients: dict = field(default_factory=dict)
    told: list = field(default_factory=list)
    forecast: list = field(default_factory=list)
    observed: list = field(default_factory=list)
    lee: str | None = None
    nova: object | None = None


@dataclass(frozen=True)
class Event:
    """One scheduled phenomenon. Derived, never saved."""
    id: str
    kind: str
    system_id: int
    start: int
    end: int
    #: False for a flicker the observatory may mistake for the real thing.
    real: bool
    #: Three numbers off the event's own draw: whether a forecaster tells a
    #: false alarm from a real one, its strength, and its particulars.
    noticed: float
    power: float
    pick: float

    @property
    def spec(self):
        return data.KINDS_BY_ID[self.kind]

    def left(self, day: int) -> int:
        return max(0, self.end - day)


def peek(game) -> SkyState | None:
    """The sky's state if the clock has made one. Readers use this: asking
    must never write, or opening a screen would change the save."""
    return getattr(game, "sky", None)


def state(game) -> SkyState:
    """The sky's state, made on first use — for the tick and the acts only."""
    if getattr(game, "sky", None) is None:
        game.sky = SkyState()
    return game.sky


# ── the schedule ───────────────────────────────────────────────────────────

def season_of(day: int) -> int:
    return int(day) // data.SEASON_DAYS


_PROFILE: dict = {}
_SEASON: dict = {}
_TODAY: dict = {}


def _profile(game, system) -> tuple:
    """(has an outer body, has an aurora world) off the resident bodies.
    Keyed on the star: only a nova changes either, and it changes the star."""
    key = (game.seed, system.id, system.star)
    got = _PROFILE.get(key)
    if got is None:
        passing = {id(b) for b in transient_bodies(system)}
        fixed = [b for b in system.bodies if id(b) not in passing]
        got = (any(b.orbit >= data.OUTER_ORBIT for b in fixed),
               any(aurora_world(b) for b in fixed))
        if len(_PROFILE) > 20_000:
            _PROFILE.clear()
        _PROFILE[key] = got
    return got


def aurora_world(body) -> bool:
    """A gas giant, or a world big enough to hold a dynamo."""
    if body.kind == "gas":
        return True
    return (body.kind in ("rocky", "ocean", "ice")
            and body.radius_km >= data.MAGNETISED_KM)


def _rate(kind, system, profile, season: int) -> float:
    region = getattr(system, "region", VERGE) or VERGE
    slot = (season + system.id) % data.TRANSIENT_SLOT == 0
    if kind.id == "flare":
        return data.FLARE_RATE.get(system.star, 0.0)
    if kind.id == "comet":
        return data.COMET_RATE if slot and profile[0] else 0.0
    if kind.id == "storm":
        return data.STORM_RATE.get(region, 0.0)
    if kind.id == "rogue":
        return (data.ROGUE_RATE.get(region, data.ROGUE_ELSEWHERE)
                if slot and system.bodies else 0.0)
    if kind.id == "aurora":
        return data.AURORA_RATE if profile[1] else 0.0
    return 0.0


def _opened(game) -> dict:
    return {r.id: r.opened_day for r in getattr(game.galaxy, "regions", ())
            or ()}


def planned(game, system, season: int, opened: dict | None = None) -> tuple:
    """Every phenomenon this system's season holds, real or a flicker."""
    opened = _opened(game) if opened is None else opened
    region = getattr(system, "region", VERGE) or VERGE
    since = opened.get(region, 0) if region != VERGE else 0
    rng = RNG(f"{game.seed}:sky:{system.id}:{season}")
    profile = _profile(game, system)
    out = []
    taken = False
    for kind in data.KINDS:
        u, at, span, real, noticed, power, pick = (rng.next() for _ in range(7))
        if u >= _rate(kind, system, profile, season):
            continue
        window = data.TRANSIENT_START if kind.transient else data.SEASON_DAYS
        start = season * data.SEASON_DAYS + int(at * window)
        lo, hi = kind.days
        end = start + lo + int(span * (hi - lo + 1))
        if start < since:
            continue                # the region was dark: nobody saw it
        if kind.transient:
            if taken:
                continue            # one body passing at a time
            taken = True
        out.append(Event(f"{kind.id}:{system.id}:{season}", kind.id,
                         system.id, start, end, real < kind.real,
                         noticed, power, pick))
    return tuple(out)


def season_map(game, season: int) -> dict:
    """System id → its planned events, for the whole sky, once a season."""
    return _season(game, season)[0]


def _season(game, season: int) -> tuple:
    """(system id → events, every event flat): built once a season, so a day
    walks a few dozen events rather than drawing every star's key again."""
    key = (game.seed, season, len(game.galaxy.systems), _signature(game))
    got = _SEASON.get(key)
    if got is None:
        opened = _opened(game)
        by_system = {s.id: planned(game, s, season, opened)
                     for s in game.galaxy.systems}
        by_system = {sid: evs for sid, evs in by_system.items() if evs}
        got = (by_system, tuple(e for evs in by_system.values() for e in evs))
        if len(_SEASON) > 256:
            _SEASON.clear()
        _SEASON[key] = got
    return got


def _signature(game) -> tuple:
    """What, besides the seed and the calendar, the sky depends on."""
    nova = getattr(getattr(game, "sky", None), "nova", None)
    return (tuple((r.id, r.opened_day) for r in
                  getattr(game.galaxy, "regions", ()) or ()),
            (nova.system_id, nova.burst) if nova is not None else None)


def upcoming(game, day: int | None = None, ahead: int = 0) -> list:
    """Every event, real or not, running today or starting within `ahead`."""
    day = game.day if day is None else day
    out = []
    first = season_of(max(0, day - 2 * data.SEASON_DAYS))
    for season in range(first, season_of(day + ahead) + 1):
        out.extend(e for e in _season(game, season)[1]
                   if e.end > day and e.start <= day + ahead)
    return out


def _today(game) -> dict:
    """System id → the real events live there today, the nova included."""
    key = (game.seed, game.day, len(game.galaxy.systems), _signature(game))
    got = _TODAY.get(key)
    if got is None:
        got = {}
        for e in upcoming(game):
            if e.real and e.start <= game.day:
                got.setdefault(e.system_id, []).append(e)
        from . import phenomena_nova as nova_sim
        star = nova_sim.event(game)
        if star is not None and star.start <= game.day < star.end:
            got.setdefault(star.system_id, []).append(star)
        if len(_TODAY) > 64:
            _TODAY.clear()
        _TODAY[key] = got
    return got


def active(game, system=None) -> list:
    """The real phenomena live at a system today (here, if None)."""
    sid = game.location_id if system is None else getattr(system, "id", system)
    return list(_today(game).get(sid, ()))


def live(game) -> dict:
    """Every system with something live today: id → events."""
    return {sid: list(evs) for sid, evs in _today(game).items()}


def _of(game, kind: str, system=None) -> list:
    return [e for e in active(game, system) if e.kind == kind]


# ── the dose, and the shelter from it ──────────────────────────────────────

def flare_power(game) -> float:
    """Today's flare strength here, in dose units a day: 0 when none."""
    lo, hi = data.FLARE_DOSE
    return sum(lo + (hi - lo) * e.power for e in _of(game, "flare"))


def shelter(game) -> dict:
    """How much of a flare the hull is out of: 1 at a berth or in a body's
    lee, the orbit's shadowed share when holding orbit, and the geometry in
    free space. `{share, how, by, text}`."""
    from . import phenomena_shelter as shelter_sim
    return shelter_sim.of(game)


def dose(game, stats=None) -> float:
    """Today's sky dose on this crew, 0 to about 1.5, after the shelter and
    the hull's own shielding — the flare and the nova, not the Cradle."""
    from . import phenomena_nova as nova_sim
    from . import regions as regions_sim
    flare = flare_power(game)
    if flare > 0:
        flare *= 1.0 - shelter(game)["share"]
    raw = flare + nova_sim.dose_at(game, game.system)
    if raw <= 0:
        return 0.0
    return raw * regions_sim.shield(game, stats)


def irradiate(game, days: float, stats) -> dict:
    """A day aboard under a flaring or brightening star. Called once a day
    from `core/shiptime.hull`, beside the Cradle's own dose."""
    if days <= 0:
        return {"dose": 0.0}
    burned = _keep_station(game, days)
    taken = dose(game, stats) * days
    if taken <= 0:
        return {"dose": 0.0, "lee": burned}
    ship = game.ship
    ship.morale = max(0.0, ship.morale - data.FLARE_MORALE * taken)
    if flare_power(game) > 0:
        from . import adaptation
        adaptation.record(ship, "glare", days)     # the living hull remembers
    return {"dose": taken, "lee": burned}


def _keep_station(game, days: float) -> float:
    """Pay a day's station-keeping in a body's lee while a flare is live.
    Before the dose is read, so a hull that runs dry is out in the light."""
    if days <= 0 or flare_power(game) <= 0:
        return 0.0
    from . import phenomena_shelter as shelter_sim
    return shelter_sim.spend_lee(game, days)


def keep_lee(game) -> dict:
    """Keep station in the shadow of the body the hull is holding at."""
    from . import phenomena_shelter as shelter_sim
    return shelter_sim.keep_lee(game)


def exposed(game) -> bool:
    """Is there light on this system worth hiding from — a flare, or the
    nova's? What the shelter mark on the screens is shown for."""
    from . import phenomena_nova as nova_sim
    return flare_power(game) > 0 or nova_sim.dose_at(game, game.system) > 0


# ── lanes, sensors, surveys, despatches, aurorae ───────────────────────────

def closed_systems(game) -> frozenset:
    """Systems an ion storm has shut today. `reach` walks round them."""
    return frozenset(sid for sid, evs in _today(game).items()
                     if any(e.kind == "storm" for e in evs))


def lane_closed(game, a, b) -> str:
    """Why a lane between two systems is shut, or "" if it is open."""
    shut = closed_systems(game)
    for end in (a, b):
        sid = getattr(end, "id", end)
        if sid in shut:
            storm = _of(game, "storm", sid)[0]
            name = game.galaxy.systems[sid].name
            return (f"An ion storm at {name} has closed the lanes in and out "
                    f"— {storm.left(game.day)} days until it blows through.")
    return ""


def sensor_scale(game) -> float:
    """What a flare here does to the array's reach: hard light off
    everything, so it reads further."""
    return data.FLARE_SENSOR if _of(game, "flare") else 1.0


def survey_scale(game) -> float:
    """What an ion storm here leaves of a survey's resolution."""
    return data.STORM_SURVEY if _of(game, "storm") else 1.0


def comms_delay(game, frm: int, to: int) -> float:
    """Days a flare at either end adds to a despatch."""
    ends = {frm, to} - {None, -1}
    return (data.FLARE_COMMS_DAYS
            if any(_of(game, "flare", sid) for sid in ends) else 0.0)


def aurora_yield(game, body) -> float:
    """What an aurora season does to working this body: more, while it lasts."""
    return (data.AURORA_YIELD
            if aurora_world(body) and _of(game, "aurora") else 1.0)


def aurora_risk(game, body) -> float:
    """And what it leaves of a dive's risk."""
    return (data.AURORA_RISK
            if aurora_world(body) and _of(game, "aurora") else 1.0)


def transient_bodies(system) -> list:
    """The comets and rogues passing through a system right now."""
    return [b for b in system.bodies
            if getattr(b, "transient_until", None) is not None]


# ── the forecast, and the chart's fog ─────────────────────────────────────

def forecasts(game) -> list:
    """Forecast events still ahead, for the chart and the strip."""
    from . import phenomena_forecast as forecast_sim
    return forecast_sim.pending(game)


def visible(game) -> list:
    """(event, "live" | "forecast") the chart may mark: what is live within
    forecast range of the hull or where it has been, what the observatory
    has forecast, and the nova once it is brightening. Fog, not the sky."""
    from ..world.galaxy import distance
    radius = data.FORECAST_JUMPS * float(game.ship_stats.jump or 0.0)
    here = game.system
    out = []
    for sid, events in _today(game).items():
        system = game.galaxy.systems[sid]
        near = sid == here.id or distance(system, here) <= radius
        out.extend((e, "live") for e in events
                   if e.kind == "nova" or near or system.visited)
    out.extend((e, "forecast") for e in forecasts(game))
    return out


def tick(game, n: int, r=None) -> None:
    """The sky's day, in sector time. No draw from `r`: the sky has its own
    keys, so a chronicle's luck is untouched by it."""
    from . import phenomena_tick
    phenomena_tick.tick(game, n)


# ── for later: renown ──────────────────────────────────────────────────────

def progress(game) -> dict:
    """What the captain has seen of the sky, for a renown system to read.

    `{"observed": int, "kinds_seen": [kind ids], "nova": str}` — the nova
    one of "unknown" (none yet), "brightening", "burst", or "watched" (a
    burst observed from a safe distance, the Choir's fortune).
    """
    from . import phenomena_nova as nova_sim
    sky = peek(game)
    seen = list(getattr(sky, "observed", ()) or ())
    return {"observed": len(seen),
            "kinds_seen": sorted({o.kind for o in seen}),
            "nova": ("watched" if any(o.stage == "burst" for o in seen)
                     else nova_sim.phase(game))}

