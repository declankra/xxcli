"""Run the sample digest scorer against labeled fixture tweets."""

from __future__ import annotations

import asyncio
import json
from pathlib import Path

from xxcli.context import build_work_context, format_context_for_prompt
from xxcli.digest import load_sample_tweets, parse_since, run_digest

ROOT = Path(__file__).resolve().parents[1]
LABELS_FILE = ROOT / "evals" / "labeled_tweets.json"


async def main() -> None:
    tweets, users = load_sample_tweets()
    labels = json.loads(LABELS_FILE.read_text(encoding="utf-8"))
    label_map = {entry["tweet_id"]: entry["label"] for entry in labels}

    result = await run_digest(
        tweets=tweets,
        users=users,
        work_context_str=format_context_for_prompt(build_work_context(str(ROOT))),
        preference_rules_str=None,
        few_shot_str=None,
        since=parse_since("24h"),
        count=5,
        sample=True,
        debug=False,
    )

    predicted_keep = {item["tweet_id"] for item in result["items"]}
    expected_keep = {tweet_id for tweet_id, label in label_map.items() if label == "keep"}

    true_positives = len(predicted_keep & expected_keep)
    precision = true_positives / len(predicted_keep) if predicted_keep else 0.0
    recall = true_positives / len(expected_keep) if expected_keep else 0.0

    print("xx digest eval")
    print(f"fixture tweets: {len(labels)}")
    print(f"predicted keep: {len(predicted_keep)}")
    print(f"expected keep: {len(expected_keep)}")
    print(f"precision: {precision:.2f}")
    print(f"recall: {recall:.2f}")


if __name__ == "__main__":
    asyncio.run(main())
