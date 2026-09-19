"""The nova: one of the Cradle's giants, once per chronicle, slowly then all at once.

Chosen the day the Cradle is open (`world/regions.Region.opened_day`), from
its own key, and never again: `SkyState.nova` is set once and stays set. It
brightens for months — every hull within `NOVA_RADIUS_LY` takes a mounting
dose — and the observatory says so on the first day of it, so the burst is
forecast at least `NOVA.days[0]` days ahead. Then it goes:

- the star becomes what a supernova leaves (`data/remnants.NEUTRON`), and
  every world round it is recast by that table, from its own identity — the
  same derivation the generator uses for a remnant, so no number is drawn;
- the worlds are stripped: no life, their volatiles boiled off, their charts
  wrong (unsurveyed again — something new to look at);
- ports are evacuated, the powers' people with them, and a holding of yours
  there is scoured back to its seed;
- a hull still in the system is scoured too.

Bodies are recast in place rather than removed, so nothing that points at
one — an orbit, a trench, a contract — is left pointing at nothing.
"""

from __future__ import annotations

from ..core.rng import RNG, hash_seed
from ..data import phenomena as data
from ..data import remnants as remnant_data


def _cradle(game):
    return next((r for r in getattr(game.galaxy, "regions", ()) or ()
                 if r.id == "cradle"), None)


def ensure(game, sky):
    """Choose the chronicle's nova, once the Cradle is open. At most one."""
    if sky.nova is not None:
        return sky.nova
    opened = _cradle(game)
    if opened is None:
        return None
    from ..world.regions import systems_of
    from .phenomena import NovaState
    stars = [s for s in systems_of(game.galaxy, "cradle")
             if s.id != opened.entry_id]
    if not stars:
        return None
    rng = RNG(f"{game.seed}:sky:nova")
    star = stars[int(rng.next() * len(stars)) % len(stars)]
    lo, hi = data.NOVA_DELAY
    begins = opened.opened_day + lo + int(rng.next() * (hi - lo + 1))
    lo, hi = data.NOVA.days
    bursts = begins + lo + int(rng.next() * (hi - lo + 1))
    sky.nova = NovaState(system_id=star.id, begins=begins, bursts=bursts)
    return sky.nova


def _nova(game):
    return getattr(getattr(game, "sky", None), "nova", None)


def event(game):
    """The brightening, as an event the sky can list; None before it."""
    nova = _nova(game)
    if nova is None:
        return None
    from .phenomena import Event
    return Event(f"nova:{nova.system_id}", "nova", nova.system_id,
                 nova.begins, nova.bursts, True, 0.0, 1.0, 0.0)


def phase(game) -> str:
    """"unknown", "brightening" or "burst" — what anybody can see."""
    nova = _nova(game)
    if nova is None or game.day < nova.begins:
        return "unknown"
    return "burst" if nova.burst else "brightening"


def fraction(game) -> float:
    """How far through its brightening the star is, 0 to 1."""
    nova = _nova(game)
    if nova is None or nova.burst or game.day < nova.begins:
        return 0.0
    return min(1.0, (game.day - nova.begins)
               / max(1, nova.bursts - nova.begins))


def dose_at(game, system) -> float:
    """The brightening star's dose at a system: rising with the square of how
    far through it is, falling off to nothing at `NOVA_RADIUS_LY`."""
    frac = fraction(game)
    if frac <= 0:
        return 0.0
    from ..world.galaxy import distance
    star = game.galaxy.systems[_nova(game).system_id]
    far = distance(star, system)
    if far >= data.NOVA_RADIUS_LY:
        return 0.0
    return data.NOVA_DOSE * frac * frac * (1.0 - far / data.NOVA_RADIUS_LY)


def burst_visible(game) -> bool:
    """Can the burst's light be taken from where the hull is? From another
    system within `NOVA_WATCH_LY`, for `NOVA_WATCH_DAYS` after it went."""
    nova = _nova(game)
    if nova is None or not nova.burst:
        return False
    if game.day >= nova.bursts + data.NOVA_WATCH_DAYS:
        return False
    if game.location_id == nova.system_id:
        return False
    from ..world.galaxy import distance
    return distance(game.galaxy.systems[nova.system_id],
                    game.system) <= data.NOVA_WATCH_LY


def tick(game, sky) -> None:
    """Choose, forecast, burst — whichever today holds."""
    nova = ensure(game, sky)
    if nova is None or nova.burst:
        return
    if game.day >= nova.begins and not nova.forecast:
        nova.forecast = True
        _forecast(game, nova)
    if game.day >= nova.bursts:
        burst(game, nova)


def _forecast(game, nova) -> None:
    from . import comms
    star = game.galaxy.systems[nova.system_id]
    days = max(1, nova.bursts - game.day)
    body = data.NOVA_FORECAST.format(
        who=data.OBSERVATORY, here=game.system.name, star=star.star_name,
        where=star.name, days=days, radius=data.NOVA_RADIUS_LY)
    comms.send(game, "charter", data.OBSERVATORY, "news",
               f"Forecast: {star.name} will go nova", body)
    game.add_log(f"{star.name} is brightening. The observatory gives it "
                 f"about {days} days.", "warn")


def burst(game, nova) -> None:
    """It goes. Everything in the system is recast by what it leaves."""
    from ..world.galaxy import STAR_CLASSES
    system = game.galaxy.systems[nova.system_id]
    nova.burst = True
    row = next(c for c in STAR_CLASSES if c[0] == data.NOVA_REMNANT)
    was = system.name
    system.star, system.star_name, system.heat, system.tint = (
        row[0], row[1], row[2], row[3])
    leavings = remnant_data.of(data.NOVA_REMNANT)
    for index, body in enumerate(system.bodies):
        if getattr(body, "transient_until", None) is None:
            _scour(body, leavings, f"nova|{system.name}|{index}", system.heat)
    lost = _evacuate(game, system)
    if game.location_id == system.id:
        _scour_hull(game, system)
    from . import comms
    comms.send(game, "charter", data.OBSERVATORY, "news",
               f"{was} has gone nova",
               f"The star at {was} has burst. What is left is a neutron star "
               "and the rubble round it. The light will be arriving for a "
               f"month and a half; the Dry Choir is buying it.{lost}")
    game.add_log(f"The star at {was} has gone nova.{lost}", "bad")


def _scour(body, leavings, ident: str, heat: float) -> None:
    """One world, recast as the remnant table says and stripped."""
    from ..world.planets import _dead_biome
    share = (hash_seed(ident) % 100_000) / 100_000.0
    kind, radius, gravity = remnant_data.recast(leavings, ident, share)
    body.kind, body.radius_km, body.gravity = kind, radius, gravity
    body.orbit = remnant_data.survivor_t(leavings, body.orbit)
    body.biome = _dead_biome(kind)
    body.lifeforms = []
    body.temp_k = round(90 + heat * 420 * (1 - body.orbit * 0.85))
    body.resources = {cid: grade * data.SCOURED.get(cid, 1.0)
                      for cid, grade in body.resources.items()}
    # The chart of it is a chart of a world that is not there any more.
    body.surveyed, body.survey_q, body.surveyed_on = False, 0.0, -1


def _evacuate(game, system) -> str:
    """Ports, the powers' people and your holdings: gone or scoured."""
    said = []
    if system.port is not None:
        said.append(f"the berth at {system.name} was evacuated")
        system.port = None
        system.market = None
    before = len(getattr(game, "settlements", ()) or ())
    game.settlements = [s for s in getattr(game, "settlements", ()) or ()
                        if s.system_id != system.id]
    if len(game.settlements) < before:
        said.append("the settlers were taken off")
    for colony in getattr(game, "colonies", ()) or ():
        if colony.system_id != system.id:
            continue
        colony.online, colony.days, colony.pop = False, 0.0, 0.0
        colony.works, colony.job, colony.job_days = [], None, 0.0
        said.append(f"{colony.name} was scoured back to its seed")
    return (" " + "; ".join(said).capitalize() + ".") if said else ""


def _scour_hull(game, system) -> None:
    """A hull that stayed for it."""
    ship = game.ship
    for layer in ship.layers:
        layer.hp = max(0.0, layer.hp - layer.max * data.NOVA_HULL)
    lost = round(ship.crew * data.NOVA_CREW)
    ship.crew = max(0, ship.crew - lost)
    ship.morale = max(0.0, ship.morale - 0.3)
    game.orbit_alt_km = 0.0
    game.add_log(f"The burst went through the hull at {system.name}: "
                 f"{round(data.NOVA_HULL * 100)}% of every layer and {lost} "
                 "of the crew.", "bad")
    if not any(layer.hp > 0 for layer in ship.layers):
        game.die(f"Scoured by the nova at {system.name}.")
