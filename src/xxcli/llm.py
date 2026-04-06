"""LLM integrations for digest scoring and preference distillation."""

from __future__ import annotations

import asyncio
import os
from typing import Literal
from typing import Any

from pydantic import BaseModel

_LAST_SCORE_RUN: dict[str, Any] | None = None
_LAST_DISTILL_RUN: dict[str, Any] | None = None


class LLMError(RuntimeError):
    """Raised when the LLM call fails."""


class LLMConfigurationError(LLMError):
    """Raised when OpenAI configuration is missing or invalid."""


class DigestItem(BaseModel):
    tweet_id: str
    relevance_score: int
    classification: Literal["adopt", "avoid", "copy", "skip"]
    explanation: str


class DigestResult(BaseModel):
    items: list[DigestItem]


class FewShotExample(BaseModel):
    tweet_summary: str
    action: str
    reason: str


class PreferenceRules(BaseModel):
    rules: list[str]
    few_shot_examples: list[FewShotExample]


async def score_tweets(
    tweets_json: str,
    work_context: str,
    preference_rules: str | None = None,
    few_shot_examples: str | None = None,
    model: str = "gpt-5.4-mini-2026-03-17",
) -> DigestResult:
    """Score tweets for digest relevance with one retry on failure."""
    preference_section = _build_preference_section(preference_rules, few_shot_examples)
    instructions = _SCORING_SYSTEM_PROMPT.format(preference_section=preference_section)
    prompt = (
        "Score each tweet for relevance to the developer's current work.\n\n"
        f"Work context:\n{work_context}\n\n"
        f"Tweets JSON:\n{tweets_json}\n\n"
        "Return every tweet in the response. Classification must be one of: adopt, avoid, copy, skip. "
        "Use classification 'skip' and an empty explanation for irrelevant items."
    )
    agent = _build_agent(
        name="xx digest scorer",
        instructions=instructions,
        output_type=DigestResult,
        model=model,
    )
    result = await _run_with_retry(agent, prompt)
    _store_score_debug(prompt=prompt, instructions=instructions, result=result, model=model)
    return result.final_output


async def distill_preferences(
    feedback_signals: str,
    current_rules: str | None = None,
    model: str = "gpt-5.4-mini-2026-03-17",
) -> PreferenceRules:
    """Distill raw feedback into preference rules."""
    prompt = (
        f"Feedback signals:\n{feedback_signals}\n\n"
        f"Current rules:\n{current_rules or '(none)'}\n\n"
        "Produce updated rules and a compact set of few-shot examples."
    )
    agent = _build_agent(
        name="xx preference distiller",
        instructions=(
            "You are analyzing a user's tweet curation behavior. Summarize their "
            "preferences as concise scoring rules. Reference specific topics, "
            "content types, and patterns. Keep rules actionable and specific."
        ),
        output_type=PreferenceRules,
        model=model,
    )
    result = await _run_with_retry(agent, prompt)
    _store_distill_debug(prompt=prompt, result=result, model=model, current_rules=current_rules)
    return result.final_output


def check_openai_key(api_key: str | None = None) -> bool:
    """Validate an OpenAI API key with a lightweight request."""
    key = api_key or os.environ.get("OPENAI_API_KEY")
    if not key:
        return False

    try:
        from openai import OpenAI

        client = OpenAI(api_key=key)
        client.models.list()
    except Exception:
        return False
    return True


def get_last_score_run() -> dict[str, Any] | None:
    return _LAST_SCORE_RUN


def get_last_distill_run() -> dict[str, Any] | None:
    return _LAST_DISTILL_RUN


def _build_preference_section(
    preference_rules: str | None,
    few_shot_examples: str | None,
) -> str:
    if preference_rules:
        return f"User preference rules:\n{preference_rules}"
    if few_shot_examples:
        return (
            "Here are examples of what this developer considers useful/not useful:\n"
            f"{few_shot_examples}"
        )
    return ""


def _build_agent(*, name: str, instructions: str, output_type: type[BaseModel], model: str):
    if not os.environ.get("OPENAI_API_KEY"):
        raise LLMConfigurationError("Missing OPENAI_API_KEY")

    try:
        from agents import Agent
    except ImportError as exc:  # pragma: no cover - environment dependent
        raise LLMConfigurationError("openai-agents is not installed") from exc

    return Agent(name=name, instructions=instructions, output_type=output_type, model=model)


async def _run_with_retry(agent, prompt: str):
    runner = _get_runner()
    last_error: Exception | None = None

    for attempt in range(2):
        try:
            return await runner.run(agent, prompt)
        except Exception as exc:  # pragma: no cover - network/runtime dependent
            last_error = exc
            if attempt == 0:
                await asyncio.sleep(3)

    raise LLMError(str(last_error)) from last_error


def _get_runner():
    try:
        from agents import Runner
    except ImportError as exc:  # pragma: no cover - environment dependent
        raise LLMConfigurationError("openai-agents is not installed") from exc
    return Runner


def _store_score_debug(*, prompt: str, instructions: str, result, model: str) -> None:
    global _LAST_SCORE_RUN
    _LAST_SCORE_RUN = {
        "model": model,
        "instructions": instructions,
        "prompt": prompt,
        "raw_responses": _serialize_raw_responses(getattr(result, "raw_responses", None)),
        "final_output": result.final_output.model_dump(),
    }


def _store_distill_debug(*, prompt: str, result, model: str, current_rules: str | None) -> None:
    global _LAST_DISTILL_RUN
    _LAST_DISTILL_RUN = {
        "model": model,
        "prompt": prompt,
        "current_rules": current_rules,
        "raw_responses": _serialize_raw_responses(getattr(result, "raw_responses", None)),
        "final_output": result.final_output.model_dump(),
    }


def _serialize_raw_responses(raw_responses: Any) -> list[Any]:
    if not raw_responses:
        return []

    serialized = []
    for response in raw_responses:
        if hasattr(response, "model_dump"):
            serialized.append(response.model_dump())
        elif hasattr(response, "dict"):
            serialized.append(response.dict())
        else:
            serialized.append(str(response))
    return serialized


_SCORING_SYSTEM_PROMPT = """You are a relevance filter for a developer's Twitter/X feed. You score
tweets by how relevant they are to the developer's CURRENT work, not
general interest. Be ruthless — most tweets score 0-3.

Filter rules:
- Hype/reaction tweets that just amplify news without adding perspective: score 0.
- Tweets that are merely "interesting" but not actionable: score 1-3.
- The acid test: "does this change what the developer builds or how they think?"
- SERENDIPITY ALLOWANCE: For up to 1 item, you may score a tweet 7+ if it
  is genuinely novel/surprising and connects to the developer's domain in a
  non-obvious way, even if not directly about their current repo. Creativity
  comes from association. Do not let relevance filtering become a black hole.
- Valid classifications: adopt, avoid, copy, skip.

{preference_section}"""
