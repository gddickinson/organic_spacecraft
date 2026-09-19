"""One lever per effect the sky claims, for `test_phenomena`. Not a suite.

Each is an `efficacy.Lever`: the door that carries the effect, a neutral
stand-in for it, and a scene measured both ways. A scene is found in the
seed's own sky (`phenomena_kit.find`) and every probe works on a fresh twin
of it, decoded from the save, so the two measurements start from one state.
"""

from __future__ import annotations

from ..core import save as save_mod
from ..sim import comms, detection, inquiry, reach, survey, telemetry
from ..sim import actions
from ..sim import market as market_sim
from ..sim import phenomena as sky_sim
from ..sim import phenomena_bodies as bodies_sim
from ..sim import phenomena_nova as nova_sim
from . import phenomena_kit as kit
from .efficacy import Lever

_SCENES: dict = {}


def _twin(game):
    twin = save_mod.decode(save_mod.encode({"game": game}))["game"]
    twin.recompute()
    return twin


def _scene(name: str, build):
    if name not in _SCENES:
        _SCENES[name] = build()
    return _twin(_SCENES[name])


def _flare():
    game, flare = kit.find("lever-flare", "flare",
                           lambda g, e: e.end - e.start >= 3)
    kit.at(game, flare)
    return game


def _storm():
    from ..world.galaxy import distance
    game, storm = kit.find("lever-storm", "storm",
                           lambda g, e: e.end - e.start >= 4)
    eye = game.galaxy.systems[storm.system_id]
    near = min((s for s in game.galaxy.systems if s.id != eye.id),
               key=lambda s: distance(s, eye))
    kit.put(game, near.id)
    kit.on_day(game, storm.start + 1)
    game.ship.cargo["volatiles"] = 300
    game.flags["lever_eye"] = eye.id
    return game


def _in_storm():
    game, storm = kit.find("lever-storm", "storm",
                           lambda g, e: e.end - e.start >= 4)
    kit.at(game, storm, 1)
    return game


def _aurora():
    game, event = kit.find("lever-aurora", "aurora", _workable)
    kit.at(game, event, 1)
    game.ship.cargo = {"volatiles": 120}
    return game


def _workable(game, event) -> bool:
    system = game.galaxy.systems[event.system_id]
    return event.end - event.start >= 30 and any(
        sky_sim.aurora_world(b) and b.kind != "gas" for b in system.bodies)


def _aurora_body(game) -> int:
    return next(i for i, b in enumerate(game.system.bodies)
                if sky_sim.aurora_world(b) and b.kind != "gas")


def _comet():
    game, comet = kit.find("lever-comet", "comet",
                           lambda g, e: bool(g.galaxy.systems[e.system_id]
                                             .port))
    kit.put(game, comet.system_id)
    kit.on_day(game, comet.start - 1)
    game.flags["lever_day"] = comet.start
    return game


def _nova():
    game = kit.new_game("lever-nova")
    kit.open_cradle(game)
    game.advance_days(1)
    nova = game.sky.nova
    kit.put(game, nova.system_id)
    kit.on_day(game, nova.bursts - 30)
    return game


# ── the probes ─────────────────────────────────────────────────────────────

def _morale_through_flare() -> float:
    game = _scene("flare", _flare)
    game.advance_days(3)
    return game.ship.morale


def _glare_through_flare() -> float:
    game = _scene("flare", _flare)
    game.advance_days(3)
    return game.ship.stress.get("glare", 0.0)


def _jumped() -> float:
    game = _scene("storm", _storm)
    return 0.0 if actions.jump_to(game, game.flags["lever_eye"])["ok"] else 1.0


def _reachable() -> float:
    return float(len(reach.component(_scene("storm", _storm))))


def _survey_quality() -> float:
    game = _scene("in_storm", _in_storm)
    return survey.preview(game, game.system.bodies[0], "pass")["quality"]


def _despatch_lag() -> float:
    game = _scene("flare", _flare)
    sig = comms.send(game, "charter", "Test", "news", "lag", "lag")
    return sig.due_day - sig.sent_day


def _worked() -> float:
    game = _scene("aurora", _aurora)
    got = actions.extract(game, _aurora_body(game), 5)
    return sum(got.get("got", {}).values())


def _dive_odds() -> float:
    game = _scene("aurora", _aurora)
    index = _aurora_body(game)
    game.system.bodies[index].biome = "subsurface"
    from ..sim import flight
    flight.ensure_at(game, index)          # there first: the clock recomputes
    game.ship_stats.can_dive = True
    heard = kit.Recorder()
    real = game.rng
    game.rng = lambda tag="": heard if tag == "dive" else real(tag)
    actions.dive(game, index)
    return heard.asked[0]


def _comet_day(game):
    kit.on_day(game, game.flags["lever_day"])
    return game


def _volatiles_price() -> float:
    game = _comet_day(_scene("comet", _comet))
    return float(market_sim.quote_buy(game, game.system, "volatiles"))


def _bodies_on_the_day() -> float:
    return float(len(_comet_day(_scene("comet", _comet)).system.bodies))


def _morale_by_the_nova() -> float:
    game = _scene("nova", _nova)
    game.advance_days(10)
    return game.ship.morale


def _bench() -> float:
    game = kit.new_game("lever-bench")
    game.research.current, game.research.progress = "melanin", 0.0
    for kind in ("survey", "specimen", "hardware", "reading", "phenomena"):
        inquiry.add(game.research, kind, 400)
    game.advance_days(20)
    return game.research.progress


def _berth_dose() -> float:
    game, flare = kit.find("lever-berth", "flare",
                           lambda g, e: bool(g.galaxy.systems[e.system_id]
                                             .port))
    kit.at(game, flare)
    from ..sim import flight
    flight.hold_at(game, kit.berth_body(game))
    return sky_sim.dose(game) + 1.0


def levers() -> list:
    """Every effect of the sky, each with the door that carries it."""
    _SCENES.clear()
    open_air = {"share": 0.0, "how": "", "by": "", "text": ""}
    return [
        Lever("flare-dose", "a flare's dose takes morale",
              (sky_sim, "dose", lambda g, st=None: 0.0),
              _morale_through_flare, "higher", 0.005),
        Lever("flare-glare", "a flare feeds the living hull's glare",
              (sky_sim, "flare_power", lambda g: 0.0),
              _glare_through_flare, "lower"),
        Lever("flare-sensor", "a flare lights the array",
              (sky_sim, "sensor_scale", lambda g: 1.0),
              lambda: detection.sensor_of(_scene("flare", _flare)), "lower"),
        Lever("flare-scope", "and the scope with it",
              (sky_sim, "sensor_scale", lambda g: 1.0),
              lambda: telemetry.scope(_scene("flare", _flare))["reach"],
              "lower"),
        Lever("flare-comms", "a flare slows a despatch",
              (sky_sim, "comms_delay", lambda g, a, b: 0.0),
              _despatch_lag, "lower"),
        Lever("storm-jump", "a storm refuses the jump",
              (sky_sim, "lane_closed", lambda g, a, b: ""), _jumped, "lower"),
        Lever("storm-reach", "and reach walks round it",
              (sky_sim, "closed_systems", lambda g: frozenset()),
              _reachable, "higher"),
        Lever("storm-survey", "a survey reads less in a storm",
              (sky_sim, "survey_scale", lambda g: 1.0),
              _survey_quality, "higher"),
        Lever("aurora-yield", "an aurora yields more",
              (sky_sim, "aurora_yield", lambda g, b: 1.0), _worked, "lower"),
        Lever("aurora-risk", "and a dive is safer",
              (sky_sim, "aurora_risk", lambda g, b: 1.0), _dive_odds,
              "higher"),
        Lever("comet-glut", "a comet gluts the quays",
              (bodies_sim, "gluts", lambda g: {}),
              _volatiles_price, "higher"),
        Lever("comet-body", "a comet is a body",
              (bodies_sim, "arrive", lambda g, sky, e: None),
              _bodies_on_the_day, "lower"),
        Lever("nova-dose", "the brightening star's dose",
              (nova_sim, "dose_at", lambda g, s: 0.0),
              _morale_by_the_nova, "higher", 0.01),
        Lever("bench-uplift", "watched phenomena speed their programmes",
              (inquiry, "_uplift", lambda res, t, d, s: 1.0), _bench,
              "lower"),
        Lever("shelter", "a berth keeps the dose off",
              (sky_sim, "shelter", lambda g: dict(open_air)), _berth_dose,
              "higher"),
    ]
