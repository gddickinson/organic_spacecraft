"""A Kith gathering: the lexicon, the gift, and what may be asked.

Hosted by `ui/port_view.py` in place of the market — a gathering posts no
prices and has no counter (`sim/enforce.may_trade` says so if anything
tries). Four panels, and every figure on them is `sim/kith`'s:

- **The lexicon**, a row of glyphs per domain, each lit by how well it is
  understood, with the gate each domain opens;
- **Listening and the bench**: attend for ten or thirty days (the gain
  quoted before the clock runs), and work a recording of a phrase;
- **The gift**: pick a good from the hold, see what is known of this
  gathering's taste and how sure that is, the stated misread odds, and the
  expected answer — then ask first, or offer;
- **What may be asked**: a berth, passage, the accord and the pilot, each
  with its odds or the reason it is shut.
"""

from __future__ import annotations

from PyQt6.QtWidgets import QComboBox, QHBoxLayout, QWidget

from ..data import kith as data
from ..data.commodities import BY_ID
from ..sim import kith as kith_sim
from ..sim import kith_acts
from ..sim import kith_world
from . import theme
from .widgets import Bar, Panel, Pill, body_or, button, defer, label, note

#: Tonnages the gift panel offers, as buttons.
LOTS = (5, 10, 25)
#: A sign is a picture: drawn at a size the eye can read, not a word's.
GLYPH_PX = 22


def hosts(system) -> bool:
    """Does this port get the Kith panel rather than a market?"""
    return kith_world.is_gathering(system)


def tint_for(value: float) -> str:
    """How lit a glyph is: understood, half understood, glimpsed, dark."""
    if value >= data.ACCORD_NEEDS:
        return "chloro"
    if value >= data.TRADE_NEEDS:
        return "lumen"
    if value >= 0.15:
        return "osteo"
    return "dim"


def glyph_row(game, domain_id: str) -> QWidget:
    """One domain: its six glyphs, each lit by comprehension."""
    row = QWidget()
    h = QHBoxLayout(row)
    h.setContentsMargins(0, 0, 0, 0)
    h.setSpacing(10)
    for sign in (s for s in data.SIGNS if s.domain == domain_id):
        have = kith_sim.comprehension(game, sign.id)
        mark = label(sign.glyph)
        mark.setStyleSheet(f"color: {theme.tint(tint_for(have))}; "
                           f"font-size: {GLYPH_PX}px;")
        mark.setToolTip(f"{sign.gloss} — understood {have:.0%}"
                        if have >= data.TRADE_NEEDS else
                        f"not yet understood ({have:.0%})")
        mark.setAccessibleName(f"{sign.id} {have:.0%}")
        h.addWidget(mark)
    h.addStretch(1)
    return row


def lexicon(game) -> Panel:
    panel = Panel("The lexicon", "lumen")
    gates = {"exchange": f"a gift at {data.TRADE_NEEDS:.1f}",
             "place": f"berth, passage at {data.PASSAGE_NEEDS:.1f}",
             "intent": f"berth, passage at {data.PASSAGE_NEEDS:.1f}",
             "kin": f"the accord at {data.ACCORD_NEEDS:.1f}"}
    for domain_id, name in data.DOMAINS.items():
        value = kith_sim.domain(game, domain_id)
        panel.add_row(name, f"{value:.2f} · opens {gates[domain_id]}",
                      tint_for(value))
        panel.add(glyph_row(game, domain_id))
        panel.add(Bar(value, tint_for(value)))
    panel.add(note(f"Every domain at {data.ACCORD_NEEDS:.1f} and standing "
                   f"{data.ACCORD_STANDING} open the accord."))
    return panel


def listening(view, game) -> Panel:
    panel = Panel("Listening, and the bench")
    state = kith_sim.ensure(game)
    for days in (10, 30):
        said = kith_sim.listen_preview(game, days)
        gain = ", ".join(f"{data.DOMAINS[d]} +{v:.2f}"
                         for d, v in said["gain"].items() if v >= 0.005)
        panel.add(note(f"{days} days: {gain or 'nothing more to overhear'}; "
                       f"{said['recordings']:.1f} recordings."))
    panel.add_buttons(*(button(
        f"Listen {days} days", lambda _=False, n=days: _listen(view, n),
        kind="primary" if days == 10 else "",
        enabled=kith_sim.listen_preview(game, days)["ok"],
        why=kith_sim.listen_preview(game, days)["why"],
        tip="Attend the gathering. The clock runs.") for days in (10, 30)))
    panel.add_row("Recordings", f"{state.recordings:.1f}",
                  "chloro" if state.recordings >= 1 else "dim")
    phrase, known = kith_sim.phrases(game)[0]
    panel.add(note(f"The least understood song is {len(phrase.signs)} signs "
                   f"at {known:.0%}. A solve teaches each of them."))
    panel.add_buttons(button(
        "Work a recording", lambda: _decode(view, phrase.id),
        enabled=state.recordings >= 1,
        why=f"Attend {data.DAYS_PER_RECORDING} days for a recording.",
        tip="The decoding bench, with the Kith's glyphs."))
    return panel


def _held(game) -> list:
    return sorted(cid for cid, t in game.ship.cargo.items()
                  if t >= 0.05 and cid in BY_ID)


def gift(view, game) -> Panel:
    panel = Panel("A gift", "chloro")
    goods = _held(game)
    if not goods:
        panel.add(note("Nothing in the hold to give."))
        return panel
    cid = getattr(view, "kith_good", None)
    if cid not in goods:
        cid = view.kith_good = goods[0]
    tonnes = getattr(view, "kith_tonnes", LOTS[1])
    combo = QComboBox()
    for good in goods:
        combo.addItem(f"{BY_ID[good].name} · {game.ship.cargo[good]:.1f} t",
                      good)
    combo.setCurrentIndex(goods.index(cid))
    combo.activated.connect(lambda _i, cb=combo: defer(
        lambda: _pick(view, cb.currentData())))
    panel.add(combo)
    panel.add_buttons(*(button(f"{n} t", lambda _=False, k=n: _lot(view, k),
                               kind="primary" if n == tonnes else "")
                        for n in LOTS))
    said = kith_acts.preview_gift(game, cid, tonnes)
    source = {"seen": "seen in an exchange",
              "told": "told when you asked — it may be misheard",
              "": "nobody has asked here: what gatherings usually think"}
    panel.add(note(f"{said['tonnes']:g} t, worth {said['value']:,.0f} at "
                   f"base. What they think of it: {source[said['source']]}."))
    row = QWidget()
    h = QHBoxLayout(row)
    h.setContentsMargins(0, 0, 0, 0)
    for reaction, share in said["weights"].items():
        if share > 0:
            h.addWidget(Pill(f"{reaction} {share:.0%}",
                             data.REACTION_TINT[reaction]))
    h.addStretch(1)
    panel.add(row)
    ex = said["expect"]
    panel.add_row("Expected answer", f"{ex['songglass']:.1f} t songglass"
                  + (f", {ex['paid']:,.0f} against what is owed"
                     if ex["paid"] >= 1 else ""))
    panel.add_row("Misread odds", f"{said['misread']:.0%}, a fight "
                  f"{said['fight']:.0%}", "warn" if said["misread"] else "")
    owed = said["debt"]
    if owed[0] > 0:
        panel.add_row("Owed here", f"{owed[0]:,.0f}"
                      + (" — an insult now" if owed[2] else ""),
                      "warn" if owed[2] else "osteo")
    asked = kith_acts.known(game, cid) is not None
    panel.add_buttons(
        button("Ask first", lambda: _ask(view, cid),
               enabled=said["ok"] and not asked,
               why=said["why"] or "You know what they think of it.",
               tip="“More?” — they answer once; the answer can be misheard."),
        button("Offer", lambda: _offer(view, cid, tonnes), kind="primary",
               enabled=said["ok"], why=said["why"],
               tip="Hand it over and take their answer."))
    return panel


def asks(view, game) -> Panel:
    panel = Panel("What may be asked")
    words = {"berth": "A berth — the colony tends the hull",
             "passage": "Passage — the way to every gathering",
             "accord": "The accord — their hulls, and a pilot"}
    acts = {"berth": kith_acts.berth, "passage": kith_acts.passage,
            "accord": kith_acts.sign_accord}
    for act, words_for in words.items():
        said = kith_acts.preview_ask(game, act)
        panel.add_row(words_for, f"misread {said['misread']:.0%}"
                      if said["ok"] else "shut",
                      "chloro" if said["ok"] else "dim")
        if not said["ok"]:
            panel.add(note(said["why"]))
        panel.add_buttons(button(
            f"Ask for {'the accord' if act == 'accord' else act}",
            lambda _=False, fn=acts[act]: _act(view, fn),
            enabled=said["ok"], why=said["why"]))
    state = kith_sim.ensure(game)
    if state.pilot == 1:
        panel.add_buttons(button("Take the Kith pilot aboard",
                                 lambda: _act(view, kith_acts.take_pilot),
                                 kind="primary"))
    return panel


def history(game) -> Panel:
    panel = Panel("What has passed between you")
    rows = kith_sim.ensure(game).history[-6:]
    if not rows:
        panel.add(note("Nothing yet."))
    for day, kind, words in reversed(rows):
        panel.add(label(f"Day {day} · {words}", "", "warn" if kind in (
            "misread", "insult", "offended") else "", wrap=True))
    return panel


def build(view, system) -> None:
    """Lay the gathering out on `view`'s column."""
    game = view.game
    state = kith_sim.ensure(game)
    rep = kith_sim.standing(game)
    view.head(f"{system.name} · {system.port.name}",
              f"A Kith gathering — standing {rep:+.0f} · "
              f"{state.exchanges} exchange(s)")
    view.col.addWidget(body_or(view.hint(
        "No price is posted here and nothing is sold. Offer a gift from the "
        "hold; they answer in songglass, more generously than they were "
        "given to — and the surplus is owed back.")))
    view.row(lexicon(game), listening(view, game))
    view.row(gift(view, game), asks(view, game))
    view.col.addWidget(history(game))


# ── the buttons ────────────────────────────────────────────────────────────

def _pick(view, cid) -> None:
    view.kith_good = cid
    view.refresh()


def _lot(view, tonnes: int) -> None:
    view.kith_tonnes = tonnes
    view.refresh()


def _listen(view, days: int) -> None:
    out = kith_sim.listen(view.game, days)
    if not out["ok"]:
        view.win.toast(out["why"], "warn")
        return
    view.win.save()
    view.win.refresh()


def _decode(view, phrase_id: str) -> None:
    out = kith_sim.begin_decode(view.game, phrase_id)
    if not out["ok"]:
        view.win.toast(out["why"], "warn")
        return
    view.win.go("decoding")


def _ask(view, cid: str) -> None:
    out = kith_acts.ask(view.game, cid)
    if not out["ok"]:
        view.win.toast(out["why"], "warn")
        return
    view.win.toast(f"They answer: {out['heard']}.", "lumen")
    view.win.save()
    view.refresh()


def _offer(view, cid: str, tonnes: float) -> None:
    _act(view, lambda game: kith_acts.offer(game, cid, tonnes))


def _act(view, fn) -> None:
    out = fn(view.game)
    if not out.get("ok"):
        view.win.toast(out.get("why", "Refused."), "warn")
        return
    view.win.save()
    if out.get("encounter"):
        view.win.begin_combat(out["encounter"], "port")
        return
    if out.get("misread"):
        view.win.toast("Misread. They pull away.", "warn")
    view.win.refresh()
