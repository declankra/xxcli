"""Interactive setup wizard for xx digest."""

from __future__ import annotations

import os
from pathlib import Path
from datetime import datetime, timezone
import re
from typing import Iterable
from uuid import uuid4

import click
import tweepy

from xxcli.client import get_home_timeline
from xxcli.config import get_credentials, load_config, save_config
from xxcli.feedback import log_signal
from xxcli.llm import check_openai_key

_REPO_SCAN_ROOTS = [
    Path("~/Code").expanduser(),
    Path("~/Projects").expanduser(),
    Path("~/Developer").expanduser(),
    Path("~/repos").expanduser(),
    Path("~/src").expanduser(),
]
_CONTEXT_DOC_CANDIDATES = [
    "README.md",
    "CLAUDE.md",
    "TODO.md",
    "ARCHITECTURE.md",
    "PRODUCT-SENSE.md",
]


def run_setup_wizard(console) -> dict:
    """Run the interactive xx digest setup flow."""
    console.print("[xx.accent]Welcome to xx digest.[/xx.accent]")
    console.print("You'll connect X, validate your OpenAI key, choose a repo, and calibrate the feed filter.")

    config = load_config()
    tthw = config.get("tthw", {}) if isinstance(config.get("tthw"), dict) else {}
    setup_started = datetime.now(timezone.utc)
    tthw["setup_started"] = setup_started.isoformat().replace("+00:00", "Z")
    config["tthw"] = tthw

    credentials = get_credentials()
    if credentials is None:
        credentials = _collect_credentials(console)
        config["credentials"] = credentials
        save_config(config)
        console.print("[xx.success]Credentials saved.[/xx.success]")
    else:
        console.print("[xx.success]Credentials already configured. Skipping credential prompts.[/xx.success]")

    repo_path = _choose_repo(console)
    config["default_repo"] = str(repo_path)

    confirmed_context_files = _confirm_context_files(console, repo_path)
    if confirmed_context_files:
        config["context_files"] = confirmed_context_files

    _run_calibration(console, credentials, repo_path)

    completed = datetime.now(timezone.utc)
    config["tthw"] = {
        "setup_started": tthw["setup_started"],
        "setup_completed": completed.isoformat().replace("+00:00", "Z"),
        "duration_seconds": int((completed - setup_started).total_seconds()),
    }
    config.setdefault("default_since", "24h")
    config.setdefault("default_count", 5)
    save_config(config)
    console.print("[xx.success]Setup complete. Run `xx digest` to get your first curated feed.[/xx.success]")
    return config


def scan_for_repos() -> list[Path]:
    """Find git repositories in common local development directories."""
    repos: list[Path] = []
    seen = set()

    candidates = list(_REPO_SCAN_ROOTS)
    candidates.append(Path.cwd())

    for root in candidates:
        root = root.expanduser()
        if root.is_dir():
            if (root / ".git").is_dir():
                resolved = root.resolve()
                if resolved not in seen:
                    seen.add(resolved)
                    repos.append(resolved)
            for child in root.iterdir():
                if not child.is_dir():
                    continue
                if (child / ".git").is_dir():
                    resolved = child.resolve()
                    if resolved not in seen:
                        seen.add(resolved)
                        repos.append(resolved)

    return sorted(repos, key=lambda path: str(path).lower())


def _collect_credentials(console) -> dict[str, str]:
    console.print("Twitter credentials are available from https://developer.twitter.com/en/portal/dashboard")
    x_credentials = _prompt_for_x_credentials(console)
    console.print("OpenAI keys are available from https://platform.openai.com/api-keys")
    openai_key = _prompt_for_openai_key(console)
    x_credentials["openai_api_key"] = openai_key
    return x_credentials


def _prompt_for_x_credentials(console) -> dict[str, str]:
    fields = [
        ("x_api_key", "X API key"),
        ("x_api_secret", "X API secret"),
        ("x_access_token", "X access token"),
        ("x_access_token_secret", "X access token secret"),
    ]
    while True:
        credentials = {
            key: click.prompt(label, hide_input=True, type=str).strip()
            for key, label in fields
        }
        if _validate_x_credentials(credentials):
            console.print("[xx.success]Twitter credentials validated.[/xx.success]")
            return credentials
        console.print("[xx.error]Twitter credentials did not validate. Please try again.[/xx.error]")


def _prompt_for_openai_key(console) -> str:
    while True:
        api_key = click.prompt("OpenAI API key", hide_input=True, type=str).strip()
        if check_openai_key(api_key=api_key):
            console.print("[xx.success]OpenAI key validated.[/xx.success]")
            return api_key
        console.print("[xx.error]OpenAI key did not validate. Please try again.[/xx.error]")


def _validate_x_credentials(credentials: dict[str, str]) -> bool:
    try:
        client = tweepy.Client(
            consumer_key=credentials["x_api_key"],
            consumer_secret=credentials["x_api_secret"],
            access_token=credentials["x_access_token"],
            access_token_secret=credentials["x_access_token_secret"],
        )
        response = client.get_me(user_fields=["username"])
    except tweepy.errors.TweepyException:
        return False
    return bool(getattr(response, "data", None))


def _choose_repo(console) -> Path:
    repos = scan_for_repos()
    if repos:
        console.print("[xx.info]Found these git repositories:[/xx.info]")
        for index, repo in enumerate(repos, 1):
            console.print(f"  [xx.key]{index}[/xx.key]. {repo}")
        choice = click.prompt(
            "Pick a repo number or enter a custom path",
            default="1",
            show_default=True,
            type=str,
        ).strip()
        if choice.isdigit():
            selected = repos[int(choice) - 1]
            return selected
        return Path(choice).expanduser().resolve()

    manual = click.prompt("No repos found automatically. Enter a repo path", type=str)
    return Path(manual).expanduser().resolve()


def _confirm_context_files(console, repo_path: Path) -> list[str]:
    found = [name for name in _CONTEXT_DOC_CANDIDATES if (repo_path / name).exists()]
    if not found:
        console.print("[xx.dim]No common project docs found. Continuing with git context only.[/xx.dim]")
        return []

    console.print("[xx.info]I found these files for extra context:[/xx.info]")
    for name in found:
        console.print(f"  - {name}")
    use_files = click.confirm("Use these files for context?", default=True)
    return found if use_files else []


def _run_calibration(console, credentials: dict[str, str], repo_path: Path) -> None:
    console.print("[xx.accent]Calibration[/xx.accent]")
    console.print("I’ll show a few real timeline items so the filter can learn your taste.")

    client = tweepy.Client(
        consumer_key=credentials["x_api_key"],
        consumer_secret=credentials["x_api_secret"],
        access_token=credentials["x_access_token"],
        access_token_secret=credentials["x_access_token_secret"],
    )
    try:
        tweets, users = get_home_timeline(client, count=15)
    except tweepy.errors.TweepyException as exc:
        console.print(f"[xx.warning]Skipping calibration because the timeline fetch failed: {exc}[/xx.warning]")
        return

    digest_run_id = f"setup-{uuid4()}"
    first_useful_topic = None
    for index, tweet in enumerate((tweets or [])[:10], 1):
        author = users.get(tweet.author_id)
        author_name = getattr(author, "name", "")
        author_username = getattr(author, "username", "")
        console.rule(f"[xx.accent]Calibration Tweet {index}[/xx.accent]")
        console.print(f"[xx.author]{author_name}[/xx.author] [xx.handle]@{author_username}[/xx.handle]")
        console.print(tweet.text)
        response = click.prompt(
            "Is this useful? [U]seful / [M]aybe / [S]kip / [N]oise",
            type=str,
            default="s",
            show_default=True,
        ).strip().lower()

        signal_type, score, classification = _map_calibration_response(response)
        log_signal(
            signal_type=signal_type,
            tweet_id=str(tweet.id),
            score=score,
            classification=classification,
            digest_run_id=digest_run_id,
            context_repo=str(repo_path),
        )
        if signal_type == "keep" and first_useful_topic is None:
            first_useful_topic = _infer_topic(tweet.text)
            console.print(
                f"[xx.success]Got it. Prioritizing {first_useful_topic} for {repo_path.name}.[/xx.success]"
            )


def _map_calibration_response(response: str) -> tuple[str, int, str]:
    normalized = response[:1].lower()
    mapping = {
        "u": ("keep", 8, "adopt"),
        "m": ("recover", 6, "copy"),
        "s": ("discard", 2, "skip"),
        "n": ("discard", 0, "skip"),
    }
    return mapping.get(normalized, ("discard", 0, "skip"))


def _infer_topic(text: str) -> str:
    words = re.findall(r"[A-Za-z][A-Za-z0-9+-]{3,}", text)
    if not words:
        return "useful developer signals"
    top_words = words[:3]
    return " / ".join(top_words)
