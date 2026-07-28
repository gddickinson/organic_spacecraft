"""Whatever language model happens to be on this machine, behind one call.

The game ships with no network and no dependencies beyond PyQt6, and the suite
is hermetic and deterministic. None of that changes because a model is
available: this is **off by default**, every path that speaks has a
deterministic fallback that is good enough to play with, and no check ever
makes a network call.

So the contract is deliberately narrow:

- `providers()` reports what is reachable, without asking any of them anything.
- `enabled()` is false unless the player turned it on *and* something answers.
- `complete()` returns a string or `None`. `None` is not an error — it is the
  normal state of a machine with nothing installed, and callers must already
  be handling it because they had to work offline anyway.
- Everything has a hard timeout. A model that hangs must not hang the game.

Nothing here knows what a ship is. `sim/voice.py` builds the prompts.
"""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from dataclasses import dataclass

#: Never let a model hold the game up. Speech is a garnish, not a mechanism.
TIMEOUT = 12.0

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


def _probe(provider: Provider) -> bool:
    """Is it actually answering? Only ever called for a local endpoint."""
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
    """The player's switch if they set one, otherwise the environment's."""
    if _asked["enabled"] is not None:
        return bool(_asked["enabled"])
    return _env(SWITCH) not in ("", "0", "off", "false")


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
    """Forget what was probed, so the next call looks again."""
    global _chosen, _looked
    _chosen, _looked = None, False


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
    live = provider()
    if live is None:
        configured = ", ".join(p.name for p in candidates())
        return f"On, but nothing answered. Looked for: {configured}."
    return f"On, through {live.name} ({live.model})."


def _post(url: str, payload: dict, headers: dict) -> dict | None:
    body = json.dumps(payload).encode()
    request = urllib.request.Request(url, data=body, headers=headers)
    try:
        with urllib.request.urlopen(request, timeout=TIMEOUT) as reply:
            return json.loads(reply.read().decode())
    except (urllib.error.URLError, OSError, ValueError, json.JSONDecodeError):
        return None


def complete(prompt: str, system: str = "", temperature: float = 0.8,
             limit: int = 160) -> str | None:
    """One completion, or None. None is ordinary and callers must expect it."""
    live = provider()
    if live is None:
        return None
    if live.kind == "ollama":
        data = _post(live.endpoint, {
            "model": live.model, "prompt": prompt, "system": system,
            "stream": False,
            "options": {"temperature": temperature, "num_predict": limit},
        }, {"Content-Type": "application/json"})
        return (data or {}).get("response", "").strip() or None
    if live.kind == "anthropic":
        data = _post(live.endpoint, {
            "model": live.model, "max_tokens": limit,
            "temperature": temperature, "system": system,
            "messages": [{"role": "user", "content": prompt}],
        }, {"Content-Type": "application/json",
            "x-api-key": _env(live.key_env),
            "anthropic-version": "2023-06-01"})
        blocks = (data or {}).get("content") or []
        text = "".join(b.get("text", "") for b in blocks if isinstance(b, dict))
        return text.strip() or None
    if live.kind == "openai":
        messages = ([{"role": "system", "content": system}] if system else [])
        messages.append({"role": "user", "content": prompt})
        data = _post(live.endpoint, {
            "model": live.model, "messages": messages,
            "temperature": temperature, "max_tokens": limit,
        }, {"Content-Type": "application/json",
            "Authorization": f"Bearer {_env(live.key_env)}"})
        choices = (data or {}).get("choices") or []
        if not choices:
            return None
        return (choices[0].get("message", {}).get("content") or "").strip() \
            or None
    return None
