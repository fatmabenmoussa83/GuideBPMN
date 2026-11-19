"""One LLM client for every GuideBPMN component.

A model is named by a spec "provider:model"; the two providers of the study:
    openai:gpt-6-luna            (needs OPENAI_API_KEY)
    anthropic:claude-haiku-5-5   (needs ANTHROPIC_API_KEY)
Any other model of these two providers can be typed the same way, for example
openai:gpt-4.1 or anthropic:claude-sonnet-4-5. Each component (generator,
orchestrator, retriever, expert) gets its own spec, chosen on the site or on
the command line; the study gives the same model to the four components.
"""
from __future__ import annotations

import json
import os
import re
import time
import urllib.error

DEFAULT_MODELS = {
    "generator": "openai:gpt-6-luna",
    "orchestrator": "openai:gpt-6-luna",
    "retriever": "openai:gpt-6-luna",
    "expert": "openai:gpt-6-luna",
}
COMPONENTS = tuple(DEFAULT_MODELS)
PROVIDERS = ("openai", "anthropic")
KEY_VARS = {"openai": "OPENAI_API_KEY", "anthropic": "ANTHROPIC_API_KEY"}
# provider names used by bpmn_generator_catalogue/generator.py
GENERATOR_PROVIDER = {"openai": "gpt", "anthropic": "claude"}


def parse_spec(spec: str) -> tuple[str, str]:
    provider, _, model = str(spec).partition(":")
    provider = provider.strip().lower()
    if provider not in PROVIDERS or not model.strip():
        raise ValueError(f"Model must be 'provider:model' with provider openai or anthropic; got {spec!r}")
    return provider, model.strip()


def resolve_models(models: dict | None) -> dict:
    out = dict(DEFAULT_MODELS)
    for name, spec in (models or {}).items():
        if name not in out:
            raise ValueError(f"Unknown component {name!r}; expected one of {COMPONENTS}")
        if spec:
            parse_spec(spec)
            out[name] = spec
    return out


def missing_requirements(models: dict) -> list[str]:
    """Human-readable reasons why these models cannot run right now (a missing key)."""
    problems = []
    for name, spec in models.items():
        provider, _ = parse_spec(spec)
        key = KEY_VARS[provider]
        if not os.getenv(key, "").strip():
            problems.append(f"{name}: {key} is not set on the server")
    return sorted(set(problems))


def parse_json(text: str) -> dict:
    """First JSON object in a model reply (tolerates code fences / thinking)."""
    text = re.sub(r"<think>.*?</think>", "", str(text), flags=re.S).strip()
    text = re.sub(r"^```(?:json)?|```$", "", text, flags=re.M).strip()
    try:
        return json.loads(text)
    except ValueError:
        start, end = text.find("{"), text.rfind("}")
        if start != -1 and end > start:
            return json.loads(text[start:end + 1])
        raise


# Errors of the provider's service, not of the request: worth trying again.
# (OpenAI and Anthropic clients raise their own classes, matched by name.)
TRANSIENT_ERRORS = {"APIConnectionError", "APITimeoutError", "RateLimitError",
                    "InternalServerError", "ServiceUnavailableError", "OverloadedError"}


def transient(exc: Exception) -> bool:
    if isinstance(exc, (urllib.error.URLError, TimeoutError, ConnectionError)):
        return True
    if type(exc).__name__ in TRANSIENT_ERRORS:
        return True
    status = getattr(exc, "status_code", None)
    return isinstance(status, int) and status >= 500


# An agent step lost to one of these did not run as designed: the example is
# run again by Resume (see run_batch.finished_example).
INFRASTRUCTURE_MARKERS = tuple(TRANSIENT_ERRORS) + ("unreachable", "Connection error",
                                                    "JSONDecodeError", "not valid JSON")


# output cap of an agent answer (orchestrator, retriever, expert) on Claude
AGENT_MAX_OUTPUT_TOKENS = 64000   # thinking tokens count toward it on Claude

class LLM:
    """complete(system, user) -> text;  complete_json(system, user) -> dict."""

    def __init__(self, spec: str, timeout: int = 300):
        self.spec = spec
        self.provider, self.model = parse_spec(spec)
        self.timeout = timeout

    # ---- providers
    def _openai(self, system, user, want_json):
        from openai import OpenAI
        client = OpenAI(timeout=self.timeout)
        kwargs = {"model": self.model,
                  "messages": [{"role": "system", "content": system},
                               {"role": "user", "content": user}]}
        if want_json:
            kwargs["response_format"] = {"type": "json_object"}
        return client.chat.completions.create(**kwargs).choices[0].message.content or ""

    def _anthropic(self, system, user, want_json):
        import anthropic
        client = anthropic.Anthropic(timeout=self.timeout)
        # streamed, so the cap is not limited by the SDK's non-streaming rule; adaptive
        # thinking tokens count toward it, and a cut answer is an error, never a partial text
        with client.messages.stream(
                model=self.model, max_tokens=AGENT_MAX_OUTPUT_TOKENS, system=system,
                messages=[{"role": "user", "content": user}]) as stream:
            message = stream.get_final_message()
        if message.stop_reason == "max_tokens":
            raise RuntimeError(f"{self.spec} answer truncated at max_tokens ({AGENT_MAX_OUTPUT_TOKENS})")
        return "".join(block.text for block in message.content
                       if getattr(block, "type", "") == "text")

    def complete(self, *, system: str, user: str, want_json: bool = False) -> str:
        call = {"openai": self._openai, "anthropic": self._anthropic}[self.provider]
        last = None
        for attempt in range(5):
            try:
                return call(system, user, want_json)
            except Exception as exc:                      # noqa: BLE001 - filtered below
                if not transient(exc):
                    raise
                last = exc
                time.sleep(min(2 ** (attempt + 1), 30))     # 2, 4, 8, 16, 30 s
        raise RuntimeError(f"{self.spec} unreachable after 5 attempts: "
                           f"{type(last).__name__}: {last}")

    def complete_json(self, *, system: str, user: str) -> dict:
        """A reply that is not valid JSON is asked for once more."""
        text = self.complete(system=system, user=user, want_json=True)
        try:
            return parse_json(text)
        except ValueError:
            text = self.complete(system=system, user=user + "\n\nYour previous reply was "
                                 "not valid JSON. Reply with one valid JSON object only.",
                                 want_json=True)
            try:
                return parse_json(text)
            except ValueError as exc:
                raise ValueError(f"not valid JSON after one retry: {exc}") from exc
