"""Who talks to a captain, about what, and in what tone.

The Verge was a quiet place. Things happened — a war opened, a port woke, a
power's regard for you crossed from cool to warm, a market moved under a price
you had written down — and the only thing that ever *told* you was a line in
your own log, in your own voice, as though you had noticed it yourself. Nobody
called. Traffic control cleared you to a mast without a word passing either
way; a faction's opinion of you changed and the faction never mentioned it.

A signal is somebody speaking to you. It has a sender with a name, a channel,
a subject, a body, and — for the ones that want something — a set of answers.
`sim/comms.py` decides who sends what and when it arrives; this says what the
channels are and what each sort of traffic sounds like.

**The register is the point.** A harbourmaster is curt because a harbour is
busy; a sector bulletin is flat because it is a bulletin; a power writes like
a power. `sim/voice.py` and `data/personas.py` already know how to make a
named individual speak, and a signal that comes from a person routes through
them — this table is for the traffic that comes from an *office*.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Channel:
    """One sort of traffic, and how a board should treat it."""

    id: str
    name: str
    tint: str
    #: Does this one expect an answer, or is it telling you?
    asks: bool
    blurb: str


#: The harbour talking to a hull: clearance, berths, boats, refusals. Short,
#: procedural, and the only channel that is ever about *right now*.
CONTROL = Channel(
    "control", "Traffic control", "lumen", True,
    "Harbours, quays and the boats that work them.")

#: What the sector is doing. Nobody expects a reply to a bulletin.
NEWS = Channel(
    "news", "Sector bulletin", "dim", False,
    "What has happened somewhere, relayed as far as the Weave reaches.")

#: Cargo, prices, commissions. A desk with a proposal.
TRADE = Channel(
    # "dim" and "osteo", not "ink2" and "gold": a channel tint is a
    # `theme.TINTS` key, and those two were not in the table — both fell
    # back to the body colour and the channels were indistinguishable.
    "trade", "Commercial", "osteo", True,
    "Desks, brokers and anybody with a hold to fill.")

#: A power addressing you as a power does — about standing, licence, or war.
POWER = Channel(
    "power", "Despatch", "warn", True,
    "The powers, when they have noticed you.")

#: Somebody who knows you. Routed through `sim/voice` so it sounds like them.
PERSONAL = Channel(
    "personal", "Personal", "chloro", False,
    "People. They remember what you did.")

ALL = (CONTROL, NEWS, TRADE, POWER, PERSONAL)
BY_ID = {c.id: c for c in ALL}


def of(channel_id: str) -> Channel:
    return BY_ID.get(channel_id or "", NEWS)


#: How long a signal takes to cross the sector, in days per light year, when
#: it has to go the slow way.
#:
#: **This is the law that makes the Weave matter.** A relay hung on a lit
#: anchor passes a signal in a day or so however far apart the two ends are;
#: light does not. A system off the lit network is not merely inconvenient to
#: reach — it is *years out of date*, and so are you while you sit in it.
#: One light year is one year, which is what a light year means.
DAYS_PER_LY = 365.0

#: Days per light year for word carried by ordinary shipping.
#:
#: **The middle regime, and the first draft was missing it.** Off the lit
#: Weave the only carrier considered was light, so a captain starting in a
#: system with no anchor — which is most of them — heard nothing from
#: anywhere for decades. That is not what happens: hulls cross on their own
#: drives all the time and word goes with them. It is far slower than a
#: relay and far faster than light, which is exactly the gap the Weave is
#: sold on. Only somewhere genuinely unreachable falls back to `DAYS_PER_LY`.
DAYS_PER_LY_SHIPPED = 11.0

#: What a relayed signal costs in days per hop of lit Weave. Not free: an
#: anchor has to be reached, read and passed on, and a chain of them adds up.
DAYS_PER_HOP = 0.75

#: Inside one system, a signal is a radio call. Minutes, which is nothing
#: against a calendar that steps in days.
SAME_SYSTEM_DAYS = 0.0


#: Frames for the traffic that comes from an office rather than a person.
#: `{who}` is the sender, `{what}` the thing that happened, `{where}` the
#: place. Chosen by channel and picked stably per signal, so the same event
#: does not read differently on a second look.
FRAMES = {
    "control": (
        "{who}: {what}",
        "{who} to inbound hull: {what}",
        "{who}, traffic: {what}",
    ),
    "news": (
        "Relayed from {where}: {what}",
        "Sector bulletin — {what}",
        "{where} reports: {what}",
    ),
    "trade": (
        "{who} has a proposal: {what}",
        "From the desk at {where}: {what}",
        "{who} writes: {what}",
    ),
    "power": (
        "{who} takes note: {what}",
        "Despatch from {who}: {what}",
        "{who} would have you know: {what}",
    ),
    "personal": (
        "{who}: {what}",
        "{who} sends word: {what}",
    ),
}
