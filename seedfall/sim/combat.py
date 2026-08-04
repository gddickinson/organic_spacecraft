"""Tactical combat on a five-band range track.

Two things make this different from the usual exchange of fire. First, damage
lands on a stack of named layers — a grown hull sheds its epidermis, gives up its
rind, and only really cares once the pneumostat opens. Second, killing the other
ship is not the only way to win: every combatant has a resolve, and a hull that
simply refuses to die will break the other side's will to keep paying for the
ammunition. TESTUDO doctrine, fitted as a mechanic.
"""

from __future__ import annotations

from ..core.util import clamp
from .battle_state import Battle, Side
from . import damage
from .damage import _disable, _say, _who
from . import firing
from . import stations as st_mod
from . import turnplan
from . import tactical as tac
from . import abilities
from .abilities import use_ability as _fire_ability
from .enemy_ai import enemy_turn as _enemy_turn
from . import consorts as consort_sim
from . import parley
from ..data.part_types import BANDS
from ..data.parts import part
from .ship import add_cargo, hull_pct, is_breached, is_destroyed

VARIANCE = (0.82, 1.18)

#: The most dazzle and jam together may take off accuracy. Unbounded, a
#: refreshed dazzle pinned any opponent at the 0.05 floor for a whole fight
#: — the cheapest organ in the game won 62% of engagements on its own.
DAZZLE_CAP = 0.35

MAX_TURNS = 40

GRIND_TURN = 9      # turns of clean fighting before either side starts wanting out

#: The thermal rule lives in `sim/ship.py`, next to `cool()`, because the hull
#: owns its own physics and both the guns and the helm put heat into it. Kept
#: importable from here because that is where the fight reads it.
from .ship import HEAT_CEILING, add_heat, cook  # noqa: E402,F401

def start(player_ship, player_stats, enemy, *, bonuses=None, officers=(),
          rep=0.0, no_parley=False, band=3, game=None, rng=None,
          fleet=()) -> Battle:
    b = Battle(
        player=Side(player_ship, player_stats, "player"),
        enemy=Side(enemy["ship"], enemy["stats"], enemy.get("personality", "balanced")),
        enemy_name=enemy.get("name", "Unknown contact"),
        enemy_faction=enemy.get("faction"),
        no_parley=no_parley, rep=rep,
        bonuses=dict(bonuses or {}), officers=list(officers), game=game,
        loot=dict(enemy.get("loot", {})),
    )
    b.enemy.resolve = enemy.get("resolve", 100)
    if rng is not None:
        b.player.body, b.enemy.body = tac.initial_layout(rng, band)
    else:
        b.player.body = tac.Body2D(0, 0, 0, 0)
        b.enemy.body = tac.Body2D(0, -(band + 0.5) * tac.BAND_UNITS, 180, 0)

    if fleet:
        consort_sim.deploy(b, list(fleet), rng, bonuses)
        names = ", ".join(c.name for c in b.consorts)
        _say(b, f"In company: {names}.", "good")
    _say(b, f"{b.enemy_name} at {BANDS[b.band].lower()} range, "
            f"{round(b.range_units)} units off.", "warn")
    return b


# ── shooting ───────────────────────────────────────────────────────────────

def _fire(b: Battle, frm: Side, to: Side, weapon_id: str, rng,
          scale: float = 1.0) -> None:
    from . import gunfire
    w = part(weapon_id)
    if w is None or w.wpn is None:
        return
    # The band is between these two hulls. For the flag and its enemy that is
    # b.band; for a consort out on a flank it is emphatically not.
    band = tac.band_for(tac.separation(frm.body, to.body))
    pen = w.wpn.bears_at(band)
    if pen > firing.CAN_FIRE:
        _say(b, f"{_who(b, frm)} cannot bring the {w.name} to bear at this range.", "dim")
        gunfire.record(b, frm, to, w.name, w.wpn, gunfire.NO_BEAR)
        return
    in_arc, gap = st_mod.bears_on(frm, to, w)
    if not in_arc:
        _say(b, f"The {w.name} will not train that far — {round(gap)}° outside its "
                f"{tac.arc_name(tac.arc_of(w)).lower()} arc.", "dim")
        gunfire.record(b, frm, to, w.name, w.wpn, gunfire.NO_ARC)
        return

    if w.wpn.ammo:
        cid, per = w.wpn.ammo
        if frm.ship.cargo.get(cid, 0) < per:
            _say(b, f"{_who(b, frm)}: the {w.name} is dry — no {cid} in the hold.", "dim")
            gunfire.record(b, frm, to, w.name, w.wpn, gunfire.DRY)
            return
        add_cargo(frm.ship, cid, -per)

    add_heat(frm.ship, w.wpn.heat, frm.st.heat_cap)
    seeking = "seeking" in w.wpn.traits

    if seeking and to.st.flak > 0 and rng.chance(clamp(0.22 * to.st.flak, 0, 0.72)):
        _say(b, f"{_who(b, to)}'s point defence swats the {w.name} round out of the sky.",
             "dim")
        gunfire.record(b, frm, to, w.name, w.wpn, gunfire.SWATTED)
        return

    evade = 0.0 if seeking else to.st.evade + (0.08 if to.braced else 0)
    directed = frm.station == "gunnery"
    officers = b.officers if frm is b.player else ()
    # Sensory interference saturates (see DAZZLE_CAP): dazzled is a
    # handicap, not the fight's decision.
    dazzle = min(DAZZLE_CAP, (0.22 if frm.blind else 0.0)
                 + (0.25 if frm.jammed else 0.0))
    acc = (frm.st.accuracy + w.wpn.acc - pen - dazzle
           + (frm.ship.morale - 0.7) * 0.15
           + st_mod.accuracy_modifier(frm, directed, officers))
    if not rng.chance(clamp(acc - evade, 0.05, 0.95)):
        _say(b, f"{w.name} misses {_who(b, to)}.", "dim")
        gunfire.record(b, frm, to, w.name, w.wpn, gunfire.MISS)
        return

    dmg = w.wpn.dmg * rng.float(*VARIANCE) * scale
    if to.braced:
        dmg *= 0.72
    if to.interpose > 0:
        dmg *= 0.45
        to.interpose -= 1
        _say(b, f"{_who(b, to)} interposes its carapace.", "dim")
    # A hull interposed between you and the gun wears part of the blow. See
    # `consorts.interception`: the order's `shield` had never been read, so
    # "hold between the enemy and your flag" cost the escort and saved you
    # nothing. Taken before your own armour soaks, because the part the screen
    # wears never reaches your plating at all.
    arriving = 1.0
    if to is b.player and b.consorts:
        whole = dmg
        dmg, worn = consort_sim.interception(b, dmg)
        arriving = dmg / whole if whole > 0 else 1.0
        for screen, share in worn:
            took = damage._apply_to_layers(b, screen, share, w.wpn.traits, rng)
            screen.taken += took
            if took >= 1:
                _say(b, f"{screen.name} takes {round(took)} of it, holding "
                        f"station.", "warn")

    # Armour soaks, but never entirely: something always gets through, or two
    # well-armoured hulls would shoot at each other until the sun went out.
    #
    # The floor is scaled by how much of the blow actually arrived. Flat — a
    # share of the weapon's *nominal* output — it quietly erases interception
    # against an armoured hull, because the part a screen wore never reaches
    # the comparison. Measured over six identical shots at a flag with 34
    # armour: with the floor scaled, a screen cuts what the flag takes from
    # 26.5 to 15.1; with it flat, only to 21.6. A rule that stops armour
    # negating a weapon must not also negate the hull standing in front.
    dmg = max(w.wpn.dmg * 0.15 * arriving, dmg - abilities.armour_of(to))

    # Bloom tissue remembers what killed the last lineage. Keep using one kind
    # of weapon and it stops working; vary the loadout and the memory fades.
    if b.game is not None and b.enemy_faction == "bloom" and to is b.enemy:
        from . import bloom as bloom_sim
        resist = bloom_sim.resistance(b.game, w.family)
        if resist > 0:
            dmg *= 1 - resist
            if rng.chance(0.25):
                _say(b, f"The tissue shrugs off much of the {w.name} — it has "
                        f"seen this before.", "warn")

    dealt = damage._apply_to_layers(b, to, dmg, w.wpn.traits, rng)
    if b.game is not None and b.enemy_faction == "bloom" and to is b.enemy:
        from . import bloom as bloom_sim
        bloom_sim.record_damage(b.game, w.family, dealt)
    frm.dealt += dealt
    to.taken += dealt
    to.resolve -= dealt * 0.10
    frm.resolve += dealt * 0.03
    # "hits for 0" thirty turns running is what a swallowed floor looked like
    # from the bridge, and it reads identically to a weapon that is working.
    # Below a point, say what is actually happening instead of rounding it away.
    if dealt < 1:
        _say(b, f"{w.name} glances off {_who(b, to)} — their armour takes "
                f"almost all of it.", "dim")
    else:
        _say(b, f"{w.name} hits {_who(b, to)} for {round(dealt)}.",
             "good" if frm is b.player else "bad")
    gunfire.record(b, frm, to, w.name, w.wpn, gunfire.HIT, dealt)
    damage._apply_traits(b, frm, to, w, rng)


def _salvo(b: Battle, frm: Side, to: Side, rng) -> None:
    """Everything that can bear, fired together.

    This is what weapon mounts are for: a battleship's five hardpoints only
    matter if they all speak at once. The cost is heat and ammunition, which is
    why a single aimed shot stays a real option.
    """
    # `turnplan.bearing_set` is the one definition of what bears, so the count
    # in this log line, the count under the button and the heat in the hull are
    # the same count.
    bearing = turnplan.bearing_set(frm, to)
    if not bearing:
        _say(b, f"{_who(b, frm)} has nothing that will bear at this range.", "dim")
        return
    _say(b, f"{_who(b, frm)} fires everything that will bear — "
            f"{len(bearing)} mount(s).", "dim")
    for w in bearing:
        if is_destroyed(to.ship):
            break
        _fire(b, frm, to, w.id, rng)


# ── abilities ──────────────────────────────────────────────────────────────

# ── turn resolution ────────────────────────────────────────────────────────


def take_turn(b: Battle, action: dict, rng) -> Battle:
    from . import gunfire
    gunfire.clear(b)
    """Run one full exchange. ``action`` is the player's choice."""
    if b.over:
        return b
    b.player.braced = False
    b.enemy.braced = False       # a brace that never cleared is permanent
    kind = action.get("type")

    # Legacy orders map onto the stations so older callers keep working.
    if kind == "move":
        b.player.station = "helm"
        b.player.helm_order = "close" if action.get("dir", 1) < 0 else "open"
        # Without the pending order, `_run_stations` handed the helm None
        # and `run_helm` overwrote the order this mapping had just written.
        b.pending_order = b.player.helm_order
        kind = "station"
    elif kind in ("fire", "salvo", "volley"):
        b.player.station = "gunnery"
    elif kind == "brace":
        b.player.station = "engineering"
    elif kind == "station":
        order = st_mod.ORDERS_BY_ID.get(action.get("order", ""))
        if order is None:
            return b
        b.player.station = order.station
        if order.station == "helm":
            b.player.helm_order = order.id
        b.pending_order = order.id

    if kind == "station":
        _run_stations(b, rng)
        _run_consorts(b, rng)
        if not b.over and is_destroyed(b.enemy.ship):
            return _finish(b, "destroyed")
        broke = None
        if not b.over:
            broke = _enemy_turn(b, rng, _say, _fire, _salvo, use_ability)
        if broke:
            return _finish(b, broke)
        if not b.over and is_destroyed(b.player.ship):
            return _finish(b, "lost")
        if not b.over:
            _end_of_turn(b, rng)
        return b

    # The seats the captain is *not* in are held by officers whichever way
    # the turn was ordered. Only the `station` path used to do this.
    if kind in ("fire", "salvo", "volley", "ability", "brace"):
        said = _run_seats(b, b.player.station)
        if said:
            _say(b, f"{b.player.ship.name}: {', '.join(said)}.", "dim")

    if kind == "fire":
        _fire(b, b.player, b.enemy, action["weapon_id"], rng)
    elif kind == "salvo":
        _salvo(b, b.player, b.enemy, rng)
    elif kind == "volley":
        # The gunner's own choice of mounts. `_salvo` fires everything that
        # bears, which on a five-mount hull is 69 points of heat against a
        # fault line of 40; this is the middle that did not exist.
        from . import gunnery
        out = gunnery.volley(b, action.get("mounts") or [], rng)
        if not out["fired"]:
            _say(b, out["why"], "dim")
        else:
            _say(b, f"{_who(b, b.player)} fires {len(out['fired'])} of "
                    f"{len([w for w in b.player.st.weapons if w.wpn])} "
                    "mounts.", "dim")
    elif kind == "ability":
        use_ability(b, b.player, action["id"], rng)
    elif kind == "brace":
        b.player.braced = True
        b.player.resolve += 6
        b.player.ship.heat = max(0.0, b.player.ship.heat - b.player.st.vent)
        _say(b, "You turn the thickest tissue into the fire and hold.", "good")
    elif kind == "hail":
        return parley.hail(b, rng, _ops())
    elif kind == "flee":
        return parley.flee(b, rng, _ops())

    if kind in ("ability", "brace"):
        # Nobody is laying a mount by hand on these turns, and the panel's
        # preview already promises the gunner keeps working.
        _idle_gunner(b, rng)

    _run_consorts(b, rng)
    if not b.over and is_destroyed(b.enemy.ship):
        return _finish(b, "destroyed")
    if not b.over:
        broke = _enemy_turn(b, rng, _say, _fire, _salvo, use_ability)
        if broke:
            return _finish(b, broke)
    if not b.over and is_destroyed(b.player.ship):
        return _finish(b, "lost")
    if not b.over:
        _end_of_turn(b, rng)
    return b


def _run_consorts(b: Battle, rng) -> None:
    """Your consorts manoeuvre to their standing orders and shoot."""
    if not b.consorts or b.over:
        return
    before = {c.uid for c in b.consorts if not c.out}
    consort_sim.run(b, rng, _say, _fire)
    for c in b.consorts:
        if c.uid in before and is_destroyed(c.ship):
            _say(b, f"{c.name} breaks apart.", "bad")
            b.player.resolve -= 12


def _ops() -> parley.Ops:
    return parley.Ops(say=_say, fire=_fire, salvo=_salvo,
                      use_ability=use_ability, enemy_turn=_enemy_turn,
                      finish=_finish, end_of_turn=_end_of_turn)


def use_ability(b: Battle, s: Side, ability_id: str, rng) -> bool:
    """Fire a defensive ability and log what it did."""
    fired, message, kind = _fire_ability(b, s, ability_id, rng)
    if fired and message:
        _say(b, f"{_who(b, s)} {message}", kind)
    return fired


def _run_seats(b: Battle, seat: str, order=None) -> list:
    """Fly the ship and run the engineering section. Returns what they report.

    `seat` is where the captain is standing; the other two are held by
    officers, or by the battle computer if one is fitted.

    Split out because the seats were only ever run on the `station` path.
    Firing a named mount or using an ability goes through the older path,
    which the battle screen still uses for the firing picture and the ability
    buttons — and on those turns nobody flew the ship and nobody stood in the
    engineering section at all. Measured: heat 30 became 24.0 through the old
    door against 19.44 through the new one, and `helm_order` stayed `None`.
    """
    # Engineering first, because it is what decides where the power goes and
    # both the other seats spend it. `route_guns` was read by the guns, which
    # fire after the seats, so it landed on the turn it was given;
    # `route_engines` was read by the helm, which used to run *before*
    # engineering set it, so it landed a turn late. Measured: ordering "power
    # to the drive" left the ship at a dead stop, and it leapt to 74.9 on the
    # following turn — the turn the captain had ordered *hold station*.
    eng_text = st_mod.run_engineering(
        b.player, order.id if order and order.station == "engineering" else None,
        seat == "engineering", b.officers, b.enemy)
    helm_text = st_mod.run_helm(
        b.player, b.enemy,
        order.id if order and order.station == "helm" else None,
        seat == "helm", b.officers)
    return [t for t in (eng_text, helm_text) if t]


def _idle_gunner(b: Battle, rng) -> None:
    """The gunner keeps working while the captain is elsewhere, less well.

    `turnplan.idle_gunnery` is asked what they do, because the orders panel
    asks the same function to cost it — quoted separately, the panel once
    forecast *vent* while the walked-away-from gunner fired everything.
    """
    idle = turnplan.idle_gunnery(b.player, b.enemy, b.officers)
    if idle["order"] == "salvo":
        _salvo(b, b.player, b.enemy, rng)
    elif idle["mounts"]:
        _fire(b, b.player, b.enemy, idle["mounts"][0].id, rng)


def _run_stations(b: Battle, rng) -> None:
    """Resolve the player's chosen seat, then the two the officers hold."""
    order_id = getattr(b, "pending_order", None)
    order = st_mod.ORDERS_BY_ID.get(order_id or "")
    seat = b.player.station

    bits = _run_seats(b, seat, order)

    if order and order.station == "gunnery":
        if order.id == "salvo":
            _salvo(b, b.player, b.enemy, rng)
        elif order.id == "aimed":
            usable = [w for w in b.player.st.weapons
                      if w.wpn.bears_at(b.band) <= firing.WORTH_FIRING
                      and st_mod.bears_on(b.player, b.enemy, w)[0]]
            if usable:
                best = max(usable, key=lambda w: w.wpn.dmg)
                _fire(b, b.player, b.enemy, best.id, rng)
            else:
                _say(b, "Nothing will bear for an aimed shot.", "dim")
    elif seat != "gunnery":
        _idle_gunner(b, rng)

    if bits:
        _say(b, f"{b.player.ship.name}: {', '.join(bits)}.", "dim")
    b.pending_order = None


def _end_of_turn(b: Battle, rng) -> None:
    from . import gunnery
    for s in (b.player, b.enemy):
        s.ship.heat = max(0.0, s.ship.heat - s.st.vent)
        # `gunnery.fault_line` is the same number, and the gunner's board
        # quotes it before the trigger. Asked here rather than written twice.
        if s.ship.heat > gunnery.fault_line(s):
            over = s.ship.heat - gunnery.fault_line(s)
            _say(b, f"{_who(b, s)} is overheating — systems faulting.", "warn")
            s.resolve -= over * 0.3
            if rng.chance(0.25):
                _disable(b, s, rng, "Thermal shutdown takes")
        if is_breached(s.ship):
            s.resolve -= 6
        s.blind = max(0, s.blind - 1)
        s.jammed = max(0, s.jammed - 1)
        s.grappled = max(0, s.grappled - 1)
        for k in list(s.cd):
            s.cd[k] = max(0, s.cd[k] - 1)
        # Living hulls close wounds even mid-fight, slowly.
        if s.st.regen > 0:
            for L in reversed(s.ship.layers):
                if 0 < L.hp < L.max:
                    L.hp = min(L.max, L.hp + L.max * L.regen * s.st.regen * 0.5)
                    break

    b.turn += 1
    # Nobody fights forever. Past a dozen turns without resolution the
    # ammunition and the heat stop being worth it. It starts late deliberately:
    # a decisive hull should still be able to finish the job on its own terms.
    # Nerve goes when a hull is being taken apart and is not giving as good as
    # it gets. This used to be a pure function of the turn counter — and the
    # enemy lost it twice as fast as the player — so a ship with no armament at
    # all drove off a battleship three times in four simply by waiting. The
    # clock term survives only to guarantee the fight ends.
    grind = max(0, b.turn - GRIND_TURN) * 0.12
    for side, other in ((b.player, b.enemy), (b.enemy, b.player)):
        hurt = max(0.0, 1.0 - hull_pct(side.ship))
        behind = max(0.0, (other.dealt - side.dealt) / 220.0)
        # Futility is what makes endurance a real strategy: a hull built to be
        # hit and not break wins by convincing the other side there is no point
        # continuing. Weighted by how little progress the attacker has made, so
        # a ship that *is* being taken apart cannot outlast anybody.
        progress = 1.0 - hull_pct(other.ship)
        futile = max(0.0, (b.turn - GRIND_TURN) / 16.0) * (1.0 - progress)
        side.resolve -= grind + hurt * 3.6 + behind * 2.4 + futile * 1.8

    if b.enemy.resolve <= 0:
        _finish(b, "driven-off")
    elif b.player.resolve <= -40:
        _finish(b, "routed")
    elif b.turn > MAX_TURNS:
        _finish(b, "stalemate")


_ENDINGS = {
    "destroyed": "{enemy} comes apart across three compartments.",
    "driven-off": "{enemy} breaks off. Whatever they came for, it was not worth this.",
    "escaped": "You break contact and run dark.",
    "parley": "They stand down. Somebody on that bridge wanted a reason to.",
    "routed": "You have nothing left to hold with. They let you go.",
    "stalemate": "Neither hull can finish the other. You drift apart, both of you "
                 "poorer and neither of you satisfied.",
    "lost": "{player} is lost.",
}


def _finish(b: Battle, result: str) -> Battle:
    b.over = True
    b.result = result
    line = _ENDINGS.get(result, result).format(enemy=b.enemy_name,
                                               player=b.player.ship.name)
    _say(b, line, "bad" if result == "lost" else "good")
    return b


__all__ = ["Battle", "Side", "start", "take_turn", "use_ability", "BANDS",
           "MAX_TURNS", "GRIND_TURN", "HEAT_CEILING", "cook"]
