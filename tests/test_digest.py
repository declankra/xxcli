from datetime import datetime, timezone
from types import SimpleNamespace
import asyncio

import pytest

from xxcli.digest import load_sample_tweets, parse_since, run_digest
from xxcli.llm import DigestItem, DigestResult


def test_parse_since_relative_and_iso():
    assert parse_since("24h") < datetime.now(timezone.utc)
    assert parse_since("3d") < datetime.now(timezone.utc)
    assert parse_since("1w") < datetime.now(timezone.utc)
    parsed = parse_since("2026-03-27T14:28:00Z")
    assert parsed == datetime(2026, 3, 27, 14, 28, tzinfo=timezone.utc)


def test_parse_since_invalid():
    with pytest.raises(ValueError):
        parse_since("later")


def test_load_sample_tweets_returns_fixture_records():
    tweets, users = load_sample_tweets()
    assert len(tweets) == 14
    assert len(users) == 12
    assert tweets[0].id == "2037612219228426491"


def test_run_digest_filters_sorts_and_truncates(monkeypatch):
    async def fake_score_tweets(**kwargs):
        return DigestResult(
            items=[
                DigestItem(tweet_id="1", relevance_score=4, classification="skip", explanation=""),
                DigestItem(tweet_id="2", relevance_score=9, classification="adopt", explanation="Use this."),
                DigestItem(tweet_id="3", relevance_score=8, classification="copy", explanation="Worth copying."),
            ]
        )

    monkeypatch.setattr("xxcli.digest.score_tweets", fake_score_tweets)

    tweets = [
        SimpleNamespace(id="1", text="a", author_id="u1", created_at=datetime.now(timezone.utc), public_metrics={}),
        SimpleNamespace(id="2", text="b", author_id="u2", created_at=datetime.now(timezone.utc), public_metrics={}),
        SimpleNamespace(id="3", text="c", author_id="u3", created_at=datetime.now(timezone.utc), public_metrics={}),
    ]
    users = {
        "u1": SimpleNamespace(id="u1", username="one", name="One"),
        "u2": SimpleNamespace(id="u2", username="two", name="Two"),
        "u3": SimpleNamespace(id="u3", username="three", name="Three"),
    }

    result = asyncio.run(
        run_digest(
            tweets=tweets,
            users=users,
            work_context_str="ctx",
            preference_rules_str=None,
            few_shot_str=None,
            since=parse_since("24h"),
            count=1,
            sample=False,
            debug=False,
        )
    )

    assert [item["tweet_id"] for item in result["items"]] == ["2"]
    assert result["items"][0]["relevance_score"] == 9
    assert len(result["all_scored"]) == 3
