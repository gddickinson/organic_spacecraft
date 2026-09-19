"""Whatever language model happens to be on this machine, behind one call.

The game ships with no network and no dependencies beyond PyQt6, and the suite
is hermetic and deterministic. None of that changes because a model is
available: this is **off by default**, every path that speaks has a
deterministic fallback that is good enough to play with, and no check ever
makes a network call.

So the contract is deliberately narrow:

- `providers()` reports what is reachable, without asking any of them anything.
- `enabled()` is false unless the player turned it on *and* something answers.
- `complete()` returns a string or `None`, **and never raises**. `None` is
  not an error — it is the normal state of a machine with nothing installed,
  and callers must already be handling it because they had to work offline
  anyway. It used to raise `AttributeError` on `{"response": null}` or on a
  reply that was a JSON list, which is a promise broken by a stranger's
  server.
- **Nothing touches the network unless `SEEDFALL_LLM` is set in the
  environment.** The options screen can turn speech off, and choose among
  what is allowed, but it cannot grant the permission itself (`permitted`).
- Every call has a **total deadline**, not a per-read timeout: a server that
  accepts and then drips one byte every eleven seconds held the old per-read
  timeout open for ever. And a failure **opens a circuit breaker**: measured
  against an endpoint that accepts and never answers, `voice.speak` blocked
  12 s, and then 12 s again on the next line, and again — with no backoff it
  paid the full timeout on every line. Now the first failure costs one
  deadline and the next minute costs nothing (`cooling`).
- None of it runs on the window's thread: `ui/comms_window.py` shows the
  written line at once and swaps the model's in when it arrives.

Nothing here knows what a ship is. `sim/voice.py` builds the prompts.
"""

from __future__ import annotations

import json
import os
import threading
import time
import urllib.error
import urllib.request
from dataclasses import dataclass

#: Never let a model hold the game up. Speech is a garnish, not a mechanism.
#: The per-read socket timeout, and no longer the whole bound — see DEADLINE.
TIMEOUT = 12.0

#: The most a completion may take, start to finish, in seconds. Twelve was a
#: per-read timeout and bounded nothing: a reply that trickles resets it on
#: every byte. A local model writing a line of 160 tokens answers in two to
#: five seconds on a laptop, so this leaves it twice that and more.
DEADLINE = 12.0

#: How long to leave a model alone after it failed, doubling with each
#: failure in a row up to `COOL_OFF_MAX`. A minute is several lines of
#: dialogue: long enough that a dead endpoint costs one deadline, not one per
#: line; short enough that a model that was merely restarting is back soon.
COOL_OFF = 60.0
COOL_OFF_MAX = 600.0

#: The environment switch. Absent or "0" means the deterministic path only.
SWITCH = "SEEDFALL_LLM"


@dataclass(frozen=True)
class Provider:
    id: str
    name: str
    kind: str            # "ollama" | "anthropic" | "openai"
    endpoint: str
    model: str
    key_env: str = ""

    @property
    def local(self) -> bool:
        return self.kind == "ollama"


def _env(name: str, fallback: str = "") -> str:
    return os.environ.get(name, fallback).strip()


def candidates() -> list:
    """Every provider this machine is *configured* for, unprobed."""
    found = []
    host = _env("OLLAMA_HOST", "http://127.0.0.1:11434").rstrip("/")
    if not host.startswith("http"):
        host = f"http://{host}"
    found.append(Provider("ollama", "Ollama", "ollama", f"{host}/api/generate",
                          _env("SEEDFALL_LLM_MODEL", "llama3.2")))
    if _env("ANTHROPIC_API_KEY"):
        found.append(Provider(
            "anthropic", "Claude", "anthropic",
            "https://api.anthropic.com/v1/messages",
            _env("SEEDFALL_LLM_MODEL", "claude-sonnet-5"), "ANTHROPIC_API_KEY"))
    if _env("OPENAI_API_KEY"):
        found.append(Provider(
            "openai", "OpenAI-compatible", "openai",
            _env("OPENAI_BASE_URL",
                 "https://api.openai.com/v1").rstrip("/") + "/chat/completions",
            _env("SEEDFALL_LLM_MODEL", "gpt-4o-mini"), "OPENAI_API_KEY"))
    return found


def permitted() -> bool:
    """Whether this process may reach a model at all: `SEEDFALL_LLM` is set.

    The one gate on the network. `_probe` and `_post` both ask it, so a
    check, a screen or a stray call cannot open a socket by any other route.
    """
    return _env(SWITCH) not in ("", "0", "off", "false")


def _probe(provider: Provider) -> bool:
    """Is it actually answering? Only ever called for a local endpoint."""
    if not permitted():
        return False
    if not provider.local:
        return True                      # a key is as much as we can check
    root = provider.endpoint.rsplit("/api/", 1)[0]
    try:
        with urllib.request.urlopen(f"{root}/api/tags", timeout=1.5) as reply:
            return reply.status == 200
    except (urllib.error.URLError, OSError, ValueError):
        return False


_chosen: Provider | None = None
_looked = False

#: Set from the options screen. `None` means "follow the environment", which
#: is what a fresh process does and what every check measures. The screen can
#: turn this on; nothing else can, and it is not persisted outside the save.
_asked: dict = {"enabled": None, "provider": "", "model": ""}


def configure(enabled=None, provider_id: str = "", model: str = "") -> None:
    """What the player chose. Overrides the environment where it is set."""
    if enabled is not None:
        _asked["enabled"] = bool(enabled)
    if provider_id is not None:
        _asked["provider"] = provider_id
    if model is not None:
        _asked["model"] = model
    reset()


def settings() -> dict:
    return dict(_asked)


def switched_on() -> bool:
    """The player's switch if they set one, otherwise the environment's.

    This is whether a model is *wanted*. Whether one may be reached is
    `permitted`, and the options screen cannot grant that: with the switch
    thrown and `SEEDFALL_LLM` unset, nothing is asked and `describe` says why.
    """
    if _asked["enabled"] is not None:
        return bool(_asked["enabled"])
    return permitted()


def may_ask() -> bool:
    """Worth asking a model for a line — without asking anything to find out.

    Wanted, permitted, and not cooling off after a failure. The window's
    test, because `enabled` probes the provider and a window must not.
    """
    return switched_on() and permitted() and not cooling()


def wanted_provider() -> str:
    return _asked["provider"] or _env("SEEDFALL_LLM_PROVIDER")


def _as_asked(candidate: Provider) -> Provider:
    """The candidate, with the player's model if they named one."""
    model = _asked["model"]
    if not model or model == candidate.model:
        return candidate
    return Provider(candidate.id, candidate.name, candidate.kind,
                    candidate.endpoint, model, candidate.key_env)


def provider() -> Provider | None:
    """The provider we will use, probed once. None when there is nothing."""
    global _chosen, _looked
    if _looked:
        return _chosen
    _looked = True
    if not switched_on():
        _chosen = None
        return None
    wanted = wanted_provider()
    for candidate in candidates():
        if wanted and candidate.id != wanted:
            continue
        if _probe(candidate):
            _chosen = _as_asked(candidate)
            return _chosen
    _chosen = None
    return None


def enabled() -> bool:
    return provider() is not None


def reset() -> None:
    """Forget what was probed, so the next call looks again — and close the
    breaker, because a player pressing "look again" means *now*."""
    global _chosen, _looked
    _chosen, _looked = None, False
    with _lock:
        _breaker.update(until=0.0, fails=0)


# ── the circuit breaker ────────────────────────────────────────────────────

#: Consecutive failures, and the monotonic time before which nothing is
#: asked. Shared by every thread that speaks, so behind one lock.
_breaker: dict = {"until": 0.0, "fails": 0}
_lock = threading.Lock()


def cooling() -> bool:
    """Is the model being left alone after a failure?"""
    with _lock:
        return time.monotonic() < _breaker["until"]


def _failed() -> None:
    with _lock:
        _breaker["fails"] += 1
        wait = min(COOL_OFF_MAX, COOL_OFF * 2 ** (_breaker["fails"] - 1))
        _breaker["until"] = time.monotonic() + wait


def _answered() -> None:
    with _lock:
        _breaker.update(until=0.0, fails=0)


def forget() -> None:
    """Forget the probe *and* what the player chose. Tests use this."""
    _asked.update({"enabled": None, "provider": "", "model": ""})
    reset()


def offer() -> list:
    """Every provider that could be chosen, and whether it is answering.

    This is the only place that probes on purpose rather than in passing, and
    it is called by the options screen when a player asks. Nothing calls it in
    the ordinary course of play, and nothing calls it in a check.
    """
    out = []
    for candidate in candidates():
        out.append({"id": candidate.id, "name": candidate.name,
                    "model": _asked["model"] or candidate.model,
                    "local": candidate.local,
                    "needs": candidate.key_env,
                    "answering": _probe(candidate)})
    return out


def describe() -> str:
    """One line for the options screen."""
    if not switched_on():
        return ("Off. Every voice in the game is written by the game itself, "
                "which is the default and is not a lesser mode.")
    if not permitted():
        return ("On, but nothing answered: SEEDFALL_LLM is not set, so the "
                "game does not reach out to any model. Set SEEDFALL_LLM=1 "
                "before starting it to allow that.")
    live = provider()
    if live is None:
        configured = ", ".join(p.name for p in candidates())
        return f"On, but nothing answered. Looked for: {configured}."
    return f"On, through {live.name} ({live.model})."


def _post(url: str, payload: dict, headers: dict):
    """POST and parse, inside `DEADLINE` from start to finish, or None.

    The request runs on a daemon thread that is abandoned at the deadline:
    `urlopen`'s timeout is per socket operation, so it cannot bound a reply
    that arrives slowly, and nothing short of a thread can. An abandoned
    request dies at its own socket timeout, and the breaker stops another
    being started meanwhile.
    """
    if not permitted():
        return None
    body = json.dumps(payload).encode()
    request = urllib.request.Request(url, data=body, headers=headers)
    box: list = []

    def fetch() -> None:
        try:
            with urllib.request.urlopen(request, timeout=TIMEOUT) as reply:
                box.append(json.loads(reply.read().decode()))
        except Exception:                                  # noqa: BLE001
            # Anything at all: the contract is "a string or None", and a
            # traceback on a daemon thread is noise on the player's console.
            pass

    worker = threading.Thread(target=fetch, daemon=True, name="seedfall-llm")
    worker.start()
    worker.join(DEADLINE)
    return box[0] if box else None


def _text(kind: str, data) -> str | None:
    """The words in a reply, or None — whatever shape the reply came in.

    Every provider's JSON is read defensively: a `null` where a string goes,
    a list where an object goes, or a field missing altogether is a reply
    with nothing in it, not an exception.
    """
    if not isinstance(data, dict):
        return None
    text = None
    if kind == "ollama":
        text = data.get("response")
    elif kind == "anthropic":
        blocks = data.get("content")
        if isinstance(blocks, list):
            text = "".join(b["text"] for b in blocks
                           if isinstance(b, dict)
                           and isinstance(b.get("text"), str))
    elif kind == "openai":
        choices = data.get("choices")
        first = choices[0] if isinstance(choices, list) and choices else None
        message = first.get("message") if isinstance(first, dict) else None
        text = message.get("content") if isinstance(message, dict) else None
    if not isinstance(text, str):
        return None
    return text.strip() or None


def _request(live: Provider, prompt: str, system: str, temperature: float,
             limit: int) -> tuple:
    """(url, payload, headers) for one completion from this provider."""
    if live.kind == "ollama":
        return live.endpoint, {
            "model": live.model, "prompt": prompt, "system": system,
            "stream": False,
            "options": {"temperature": temperature, "num_predict": limit},
        }, {"Content-Type": "application/json"}
    if live.kind == "anthropic":
        return live.endpoint, {
            "model": live.model, "max_tokens": limit,
            "temperature": temperature, "system": system,
            "messages": [{"role": "user", "content": prompt}],
        }, {"Content-Type": "application/json",
            "x-api-key": _env(live.key_env),
            "anthropic-version": "2023-06-01"}
    messages = ([{"role": "system", "content": system}] if system else [])
    messages.append({"role": "user", "content": prompt})
    return live.endpoint, {
        "model": live.model, "messages": messages,
        "temperature": temperature, "max_tokens": limit,
    }, {"Content-Type": "application/json",
        "Authorization": f"Bearer {_env(live.key_env)}"}


def complete(prompt: str, system: str = "", temperature: float = 0.8,
             limit: int = 160) -> str | None:
    """One completion, or None. Never raises; None is ordinary.

    A provider that fails — no answer inside the deadline, an error, a
    reply with no words in it — opens the breaker, and until it closes this
    returns None without asking anything.
    """
    try:
        if cooling():
            return None
        live = provider()
        if live is None:
            return None                  # nothing configured: not a failure
        url, payload, headers = _request(live, prompt, system, temperature,
                                         limit)
        text = _text(live.kind, _post(url, payload, headers))
    except Exception:                                      # noqa: BLE001
        text = None
    if text is None:
        _failed()
        return None
    _answered()
    return text
