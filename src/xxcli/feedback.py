"""Feedback logging and preference distillation helpers."""

from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any

from xxcli.config import CONFIG_DIR
from xxcli.llm import distill_preferences

FEEDBACK_FILE = Path.home() / ".xxcli" / "feedback.jsonl"
PREFERENCE_FILE = Path.home() / ".xxcli" / "preference_rules.json"
_DISTILL_SIGNAL_TYPES = {"keep", "discard", "recover", "manual_signal"}
_EXPLICIT_SIGNAL_TYPES = {"keep", "discard", "recover"}


def log_signal(
    signal_type: str,
    tweet_id: str | None,
    score: int | None,
    classification: str | None,
    digest_run_id: str,
    context_repo: str,
    items_shown: list[str] | None = None,
) -> None:
    """Append a single feedback record to the JSONL log."""
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    record: dict[str, Any] = {
        "ts": _now_iso(),
        "type": signal_type,
        "tweet_id": tweet_id,
        "score": score,
        "classification": classification,
        "digest_run_id": digest_run_id,
        "context_repo": context_repo,
    }
    if items_shown is not None:
        record["items_shown"] = items_shown

    with FEEDBACK_FILE.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(record, ensure_ascii=False) + "\n")


def get_signal_count() -> int:
    """Count explicit digest-improving signals."""
    return sum(1 for signal in _load_feedback_lines() if signal.get("type") in _EXPLICIT_SIGNAL_TYPES)


def get_signals_since_last_distillation() -> int:
    """Count distillation-relevant signals written after the latest rules update."""
    signals = _load_feedback_lines()
    if not PREFERENCE_FILE.exists():
        return sum(1 for signal in signals if signal.get("type") in _DISTILL_SIGNAL_TYPES)

    cutoff = datetime.fromtimestamp(PREFERENCE_FILE.stat().st_mtime, tz=timezone.utc)
    count = 0
    for signal in signals:
        if signal.get("type") not in _DISTILL_SIGNAL_TYPES:
            continue
        timestamp = _parse_timestamp(signal.get("ts"))
        if timestamp and timestamp > cutoff:
            count += 1
    return count


def load_recent_signals(limit: int = 50) -> list[dict[str, Any]]:
    """Return the latest feedback records in chronological order."""
    signals = _load_feedback_lines()
    if limit <= 0:
        return []
    return signals[-limit:]


def load_preference_rules() -> dict[str, Any] | None:
    """Load saved preference rules if available."""
    if not PREFERENCE_FILE.exists():
        return None
    try:
        payload = json.loads(PREFERENCE_FILE.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return payload if isinstance(payload, dict) else None


def save_preference_rules(rules: dict[str, Any]) -> None:
    """Persist preference rules to disk."""
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    PREFERENCE_FILE.write_text(json.dumps(rules, ensure_ascii=False, indent=2), encoding="utf-8")


def get_few_shot_examples(limit: int = 5) -> list[dict[str, str]]:
    """Build few-shot examples from recent feedback signals."""
    examples = []
    for signal in reversed(_load_feedback_lines()):
        if signal.get("type") not in _DISTILL_SIGNAL_TYPES:
            continue
        action = "discard" if signal.get("type") == "discard" else "keep"
        tweet_id = signal.get("tweet_id") or "(manual)"
        classification = signal.get("classification") or "(none)"
        examples.append(
            {
                "tweet_summary": f"Tweet {tweet_id} classified as {classification}",
                "action": action,
                "reason": f"Signal type: {signal.get('type')}",
            }
        )
        if len(examples) >= limit:
            break
    examples.reverse()
    return examples


async def maybe_distill(context_repo: str, model: str = "gpt-5.4-mini-2026-03-17") -> str | None:
    """Distill preference rules when enough new signals have accumulated."""
    total_signals = get_signal_count()
    if total_signals < 20 or get_signals_since_last_distillation() < 10:
        return None

    recent_signals = load_recent_signals(limit=50)
    current_rules = load_preference_rules()
    distilled = await distill_preferences(
        feedback_signals=json.dumps(recent_signals, ensure_ascii=False, indent=2),
        current_rules=json.dumps(current_rules, ensure_ascii=False, indent=2) if current_rules else None,
        model=model,
    )
    payload = distilled.model_dump()
    payload["context_repo"] = context_repo
    payload["updated_at"] = _now_iso()
    save_preference_rules(payload)
    rules_preview = "; ".join(payload.get("rules", [])[:3])
    return f"Updated preference rules from {total_signals} signals. {rules_preview}".strip()


def _load_feedback_lines() -> list[dict[str, Any]]:
    if not FEEDBACK_FILE.exists():
        return []

    records: list[dict[str, Any]] = []
    try:
        with FEEDBACK_FILE.open("r", encoding="utf-8") as handle:
            for line in handle:
                raw = line.strip()
                if not raw:
                    continue
                try:
                    record = json.loads(raw)
                except json.JSONDecodeError:
                    continue
                if isinstance(record, dict):
                    records.append(record)
    except OSError:
        return []
    return records


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _parse_timestamp(value: Any) -> datetime | None:
    if not isinstance(value, str):
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)
