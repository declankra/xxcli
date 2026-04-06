"""Digest orchestration and sample-data loading."""

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from time import perf_counter
import re
from types import SimpleNamespace
from typing import Any

from xxcli.config import CONFIG_DIR
from xxcli.llm import get_last_score_run, score_tweets

LAST_DIGEST_FILE = CONFIG_DIR / "last_digest.json"
_EVAL_FIXTURE = Path(__file__).resolve().parents[2] / "evals" / "xx-feed-20260327.md"
_HEADER_RE = re.compile(r"^(\d+)\.\s+(.+?)\s+@([A-Za-z0-9_]+)\s+·\s+(.+)$", re.MULTILINE)
_ID_RE = re.compile(r"id:(\d+)")
_METRIC_RE = {
    "like_count": re.compile(r"(\d+)\s+likes?"),
    "retweet_count": re.compile(r"(\d+)\s+RTs?"),
    "reply_count": re.compile(r"(\d+)\s+replies?"),
}


def parse_since(since: str) -> datetime:
    """Parse relative windows like 24h, 3d, 1w or an ISO timestamp/date."""
    value = since.strip()
    if not value:
        raise ValueError("since cannot be empty")

    now = datetime.now(timezone.utc)
    relative = re.fullmatch(r"(\d+)([hdw])", value.lower())
    if relative:
        amount = int(relative.group(1))
        unit = relative.group(2)
        delta = {
            "h": timedelta(hours=amount),
            "d": timedelta(days=amount),
            "w": timedelta(weeks=amount),
        }[unit]
        return now - delta

    normalized = value.replace("Z", "+00:00")
    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError as exc:
        raise ValueError(f"Unsupported since value: {since}") from exc

    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


async def run_digest(
    tweets: list,
    users: dict,
    work_context_str: str,
    preference_rules_str: str | None,
    few_shot_str: str | None,
    since: datetime,
    count: int,
    model: str = "gpt-5.4-mini-2026-03-17",
    debug: bool = False,
    sample: bool = False,
) -> dict[str, Any]:
    """Run the full digest scoring pipeline."""
    timing: dict[str, float] = {}
    debug_info: dict[str, Any] | None = None

    phase_start = perf_counter()
    if sample:
        timeline = list(tweets)
    else:
        timeline = [tweet for tweet in tweets if _normalize_datetime(tweet.created_at) >= since]
    timing["filter_since"] = perf_counter() - phase_start

    phase_start = perf_counter()
    tweet_payload = _build_tweet_payload(timeline, users)
    tweets_json = json.dumps(tweet_payload, ensure_ascii=False, indent=2)
    timing["build_prompt_payload"] = perf_counter() - phase_start

    phase_start = perf_counter()
    scored = await score_tweets(
        tweets_json=tweets_json,
        work_context=work_context_str,
        preference_rules=preference_rules_str,
        few_shot_examples=few_shot_str,
        model=model,
    )
    timing["score_tweets"] = perf_counter() - phase_start

    phase_start = perf_counter()
    all_scored = _enrich_scored_items(scored.items, tweet_payload)
    relevant = [item for item in all_scored if item["relevance_score"] >= 7]
    relevant.sort(key=lambda item: item["relevance_score"], reverse=True)
    top_items = relevant[:count]
    timing["post_process"] = perf_counter() - phase_start

    meta = {
        "scanned": len(tweets),
        "within_since": len(timeline),
        "filtered": max(len(timeline) - len(top_items), 0),
        "returned": len(top_items),
        "model": model,
        "sample": sample,
        "generated_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
    }

    if debug:
        debug_info = {
            "timing": timing,
            "score_run": get_last_score_run(),
        }

    return {
        "items": top_items,
        "meta": meta,
        "all_scored": all_scored,
        "debug_info": debug_info,
    }


def load_sample_tweets() -> tuple[list[SimpleNamespace], dict[str, SimpleNamespace]]:
    """Load the checked-in eval fixture into Tweepy-like objects."""
    content = _EVAL_FIXTURE.read_text(encoding="utf-8")
    header_lines = content.splitlines()
    base_time = _parse_fixture_timestamp(header_lines[0])
    matches = list(_HEADER_RE.finditer(content))

    tweets: list[SimpleNamespace] = []
    users: dict[str, SimpleNamespace] = {}

    for index, match in enumerate(matches):
        block_start = match.end()
        block_end = matches[index + 1].start() if index + 1 < len(matches) else len(content)
        block = content[block_start:block_end]

        display_name = match.group(2).strip()
        username = match.group(3).strip()
        relative_time = match.group(4).strip()
        author_id = username
        text, metrics, tweet_id = _parse_fixture_block(block)
        if not tweet_id:
            continue

        users[author_id] = SimpleNamespace(id=author_id, name=display_name, username=username)
        tweets.append(
            SimpleNamespace(
                id=tweet_id,
                text=text,
                author_id=author_id,
                created_at=_apply_relative_offset(base_time, relative_time),
                public_metrics=metrics,
            )
        )

    return tweets, users


def save_last_digest(all_scored: list[dict[str, Any]], meta: dict[str, Any]) -> None:
    """Persist the latest digest result for `xx why`."""
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    payload = {
        "meta": meta,
        "all_scored": all_scored,
    }
    LAST_DIGEST_FILE.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def load_last_digest() -> dict[str, Any] | None:
    """Load the latest digest if it exists and is fresh."""
    if not LAST_DIGEST_FILE.exists():
        return None

    try:
        payload = json.loads(LAST_DIGEST_FILE.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None

    generated_at = payload.get("meta", {}).get("generated_at")
    timestamp = _parse_timestamp(generated_at)
    if timestamp is None:
        timestamp = datetime.fromtimestamp(LAST_DIGEST_FILE.stat().st_mtime, tz=timezone.utc)

    if datetime.now(timezone.utc) - timestamp > timedelta(hours=24):
        return None
    return payload


def _build_tweet_payload(tweets: list, users: dict) -> list[dict[str, Any]]:
    payload = []
    for tweet in tweets:
        author = users.get(tweet.author_id)
        payload.append(
            {
                "tweet_id": str(tweet.id),
                "author_name": getattr(author, "name", ""),
                "author_username": getattr(author, "username", ""),
                "text": tweet.text,
                "created_at": _normalize_datetime(tweet.created_at).isoformat().replace("+00:00", "Z"),
            }
        )
    return payload


def _enrich_scored_items(items, tweet_payload: list[dict[str, Any]]) -> list[dict[str, Any]]:
    payload_by_id = {item["tweet_id"]: item for item in tweet_payload}
    enriched = []
    for item in items:
        base = payload_by_id.get(item.tweet_id, {})
        enriched.append(
            {
                "tweet_id": item.tweet_id,
                "relevance_score": item.relevance_score,
                "classification": item.classification,
                "explanation": item.explanation,
                "author_name": base.get("author_name", ""),
                "author_username": base.get("author_username", ""),
                "text": base.get("text", ""),
                "created_at": base.get("created_at", ""),
            }
        )
    return enriched


def _parse_fixture_timestamp(line: str) -> datetime:
    match = re.search(r"on ([A-Za-z]+) (\d+)(?:st|nd|rd|th), (\d+):(\d+)(am|pm)", line)
    if not match:
        return datetime(2026, 3, 27, 14, 28, tzinfo=timezone.utc)

    month = datetime.strptime(match.group(1), "%B").month
    day = int(match.group(2))
    hour = int(match.group(3))
    minute = int(match.group(4))
    meridiem = match.group(5)
    if meridiem == "pm" and hour != 12:
        hour += 12
    if meridiem == "am" and hour == 12:
        hour = 0
    return datetime(2026, month, day, hour, minute, tzinfo=timezone.utc)


def _parse_fixture_block(block: str) -> tuple[str, dict[str, int], str]:
    lines = [line.rstrip() for line in block.splitlines()]
    text_lines: list[str] = []
    metrics_line = ""
    tweet_id = ""

    for raw_line in lines:
        line = raw_line.strip()
        if not line:
            continue
        id_match = _ID_RE.search(line)
        if id_match:
            tweet_id = id_match.group(1)
            continue
        if line.startswith(">"):
            continue
        if any(token in line for token in ("likes", "RTs", "replies")):
            metrics_line = line
            continue
        text_lines.append(line)

    metrics = {
        key: int(match.group(1)) if (match := pattern.search(metrics_line)) else 0
        for key, pattern in _METRIC_RE.items()
    }
    text = "\n".join(text_lines).strip()
    return text, metrics, tweet_id


def _apply_relative_offset(base_time: datetime, relative_time: str) -> datetime:
    match = re.fullmatch(r"(\d+)([mhdw])", relative_time.lower())
    if not match:
        return base_time
    amount = int(match.group(1))
    unit = match.group(2)
    delta = {
        "m": timedelta(minutes=amount),
        "h": timedelta(hours=amount),
        "d": timedelta(days=amount),
        "w": timedelta(weeks=amount),
    }[unit]
    return base_time - delta


def _normalize_datetime(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


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
