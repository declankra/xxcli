import json

from rich.console import Console

from xxcli.format import print_digest, print_digest_json, print_empty_digest
from xxcli.theme import xx_theme


def test_print_digest_contains_expected_content(capsys):
    print_digest(
        [
            {
                "tweet_id": "123",
                "relevance_score": 8,
                "classification": "adopt",
                "author_name": "Test User",
                "author_username": "tester",
                "text": "Ship the thing",
                "explanation": "Directly relevant to the repo.",
                "created_at": "2026-04-06T15:00:00Z",
            }
        ],
        {"filtered": 9, "within_since": 10, "repo": "xxcli", "since": "24h", "streak_days": 2},
        Console(record=False, force_terminal=False, theme=xx_theme, highlight=False),
    )
    captured = capsys.readouterr().out
    assert "xx digest" in captured
    assert "ADOPT" in captured
    assert "Ship the thing" in captured


def test_print_digest_json_schema(capsys):
    print_digest_json(
        [
            {
                "tweet_id": "123",
                "relevance_score": 8,
                "classification": "adopt",
                "author_name": "Test User",
                "author_username": "tester",
                "text": "Ship the thing",
                "explanation": "Directly relevant to the repo.",
            }
        ],
        {"scanned": 10, "filtered": 9, "repo": "xxcli", "streak_days": 2, "since": "24h"},
    )
    payload = json.loads(capsys.readouterr().out)
    assert payload["items"][0]["author"] == "@tester"
    assert payload["meta"]["repo"] == "xxcli"


def test_print_empty_digest_output(capsys):
    print_empty_digest({"repo": "xxcli"})
    captured = capsys.readouterr().out
    assert "No relevant signals" in captured
