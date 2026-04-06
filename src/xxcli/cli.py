"""CLI entry point for xxcli."""

from __future__ import annotations

import asyncio
import json
import os
from pathlib import Path
import sys
from uuid import uuid4

import click
import tweepy

from xxcli import __version__
from xxcli.client import (
    get_api_v1,
    get_client,
    get_client_from_config,
    get_home_timeline,
    get_me,
    get_user_tweets,
    like_tweet,
    parse_tweet_id,
    post_tweet,
    upload_media,
)
from xxcli.config import get_default_repo, load_config, update_streak
from xxcli.context import build_work_context, format_context_for_prompt
from xxcli.digest import load_last_digest, load_sample_tweets, parse_since, run_digest, save_last_digest
from xxcli.feedback import get_few_shot_examples, load_preference_rules, log_signal, maybe_distill
from xxcli.format import (
    console,
    print_debug_info,
    print_digest,
    print_digest_json,
    print_empty_digest,
    print_error,
    print_feed,
    print_filtered_items,
    print_my_tweets,
    print_profile,
    print_success,
)
from xxcli.llm import LLMConfigurationError, LLMError
from xxcli.onboarding import run_setup_wizard

_X_CONFIG_KEYS = {
    "X_API_KEY": "x_api_key",
    "X_API_SECRET": "x_api_secret",
    "X_ACCESS_TOKEN": "x_access_token",
    "X_ACCESS_TOKEN_SECRET": "x_access_token_secret",
}


class DigestConfigError(RuntimeError):
    """Configuration failure for the digest workflow."""


def _handle_api_error(e: tweepy.errors.TweepyException):
    if isinstance(e, tweepy.errors.Unauthorized):
        print_error("Unauthorized (401). This endpoint may require a higher API tier.")
        print_error("Free tier supports: post, feed, like, reply. User timeline requires Basic ($100/mo).")
    elif isinstance(e, tweepy.errors.Forbidden):
        print_error(f"Forbidden (403): {e}")
    elif isinstance(e, tweepy.errors.TooManyRequests):
        print_error("Rate limited. Wait a few minutes and try again.")
    else:
        print_error(str(e))
    raise SystemExit(1)


class DefaultPostGroup(click.Group):
    """Click group that defaults to 'post' when the first arg isn't a known command."""

    def parse_args(self, ctx, args):
        if args and args[0] not in self.commands and not args[0].startswith("-"):
            args = ["post"] + args
        return super().parse_args(ctx, args)


@click.group(cls=DefaultPostGroup)
@click.version_option(version=__version__, prog_name="xx")
def main():
    """xx — Twitter/X from the terminal. No browser, no doom scroll."""
    pass


@main.command()
@click.option("-n", "--count", default=20, help="Number of tweets to show.", show_default=True)
def feed(count):
    """Read your home timeline."""
    try:
        client = get_client()
        tweets, users = get_home_timeline(client, count=count)
        print_feed(tweets, users)
    except tweepy.errors.TweepyException as e:
        _handle_api_error(e)


@main.command()
@click.argument("text")
@click.argument("images", nargs=-1, type=click.Path(exists=True))
def post(text, images):
    """Post a tweet. Attach images by passing file paths after the text."""
    if len(text) > 280:
        console.print(f"[xx.warning]Warning:[/xx.warning] Tweet is {len(text)} chars (max 280)")
        if not click.confirm("Post anyway?"):
            raise SystemExit(0)

    try:
        client = get_client()
        media_ids = None
        if images:
            api_v1 = get_api_v1()
            media_ids = upload_media(api_v1, list(images))
            if media_ids:
                console.print(f"[xx.dim]Uploaded {len(media_ids)} image(s)[/xx.dim]")

        data = post_tweet(client, text, media_ids=media_ids)
        tweet_id = data["id"]
        print_success(f"Posted! https://x.com/i/web/status/{tweet_id}")
    except tweepy.errors.TweepyException as e:
        _handle_api_error(e)


@main.command()
@click.argument("tweet_id_or_url")
@click.argument("text")
def reply(tweet_id_or_url, text):
    """Reply to a tweet."""
    if len(text) > 280:
        console.print(f"[xx.warning]Warning:[/xx.warning] Reply is {len(text)} chars (max 280)")
        if not click.confirm("Post anyway?"):
            raise SystemExit(0)

    try:
        tweet_id = parse_tweet_id(tweet_id_or_url)
        client = get_client()
        data = post_tweet(client, text, reply_to=tweet_id)
        reply_id = data["id"]
        print_success(f"Replied! https://x.com/i/web/status/{reply_id}")
    except tweepy.errors.TweepyException as e:
        _handle_api_error(e)


@main.command()
@click.argument("tweet_id_or_url")
def like(tweet_id_or_url):
    """Like a tweet."""
    try:
        tweet_id = parse_tweet_id(tweet_id_or_url)
        client = get_client()
        like_tweet(client, tweet_id)
        print_success(f"Liked tweet {tweet_id}")
    except tweepy.errors.TweepyException as e:
        _handle_api_error(e)


@main.command()
@click.option("-n", "--count", default=10, help="Number of tweets to show.", show_default=True)
def me(count):
    """See your own recent tweets."""
    try:
        client = get_client()
        user = get_me(client)
        print_profile(user)
        try:
            tweets = get_user_tweets(client, user.id, count=count)
            print_my_tweets(tweets, username=user.username, name=user.name)
        except tweepy.errors.Unauthorized:
            console.print("[xx.dim]User timeline requires Basic API tier ($100/mo).[/xx.dim]")
            console.print("[xx.dim]Profile shown above. Use 'xx feed' to see your timeline.[/xx.dim]")
    except tweepy.errors.TweepyException as e:
        _handle_api_error(e)


@main.command()
@click.option("-n", "--count", default=5, help="Max digest items.", show_default=True)
@click.option("--repo", default=None, help="Git repo for work context.")
@click.option("--since", default="24h", help="Time window (e.g., 24h, 3d, 1w).", show_default=True)
@click.option("--debug", is_flag=True, help="Show full LLM reasoning and timing.")
@click.option("--json", "json_output", is_flag=True, help="Output as JSON.")
@click.option("--sample", is_flag=True, help="Use eval data instead of live API.")
def digest(count, repo, since, debug, json_output, sample):
    """Score your feed against the repo you're actively building."""
    try:
        repo_path = _resolve_repo_path(repo)
        _ensure_digest_credentials(sample=sample, json_output=json_output)

        distillation_summary = _run_async(maybe_distill(str(repo_path)))
        if distillation_summary and not _wants_json(json_output):
            print_success(distillation_summary)

        if sample:
            tweets, users = load_sample_tweets()
        else:
            with console.status("Fetching your timeline..."):
                client = get_client_from_config()
                tweets, users = get_home_timeline(client, count=100)

        work_context = build_work_context(str(repo_path))
        work_context_str = format_context_for_prompt(work_context)
        since_dt = parse_since(since)

        preference_rules, few_shot_examples = _load_preference_context()

        with console.status(f"[xx.dim]Scoring {len(tweets)} tweets for {work_context.repo_name}...[/xx.dim]"):
            result = _run_async(
                run_digest(
                    tweets=tweets,
                    users=users,
                    work_context_str=work_context_str,
                    preference_rules_str=preference_rules,
                    few_shot_str=few_shot_examples,
                    since=since_dt,
                    count=count,
                    debug=debug,
                    sample=sample,
                )
            )

        streak = update_streak()
        meta = result["meta"]
        digest_run_id = str(uuid4())
        meta.update(
            {
                "repo": work_context.repo_name,
                "since": since,
                "streak_days": streak["consecutive_days"],
                "digest_run_id": digest_run_id,
                "work_context": work_context_str,
                "preference_rules": json.loads(preference_rules) if preference_rules else None,
            }
        )
        save_last_digest(result["all_scored"], meta)

        if _wants_json(json_output):
            print_digest_json(result["items"], meta)
            return

        if debug:
            print_debug_info(result["debug_info"], console)

        if result["items"]:
            print_digest(result["items"], meta, console)
        else:
            print_empty_digest(meta, console)

        log_signal(
            signal_type="accepted_digest",
            tweet_id=None,
            score=None,
            classification=None,
            digest_run_id=digest_run_id,
            context_repo=str(repo_path),
            items_shown=[item["tweet_id"] for item in result["items"]],
        )

        if console.is_terminal and click.confirm("See filtered items?", default=False):
            shown_ids = {item["tweet_id"] for item in result["items"]}
            filtered_items = [item for item in result["all_scored"] if item["tweet_id"] not in shown_ids]
            print_filtered_items(filtered_items, console)
            recover_ids = click.prompt(
                "Recover any filtered tweet ids? (comma-separated, blank to skip)",
                default="",
                show_default=False,
            ).strip()
            for tweet_id in [token.strip() for token in recover_ids.split(",") if token.strip()]:
                match = next((item for item in filtered_items if item["tweet_id"] == tweet_id), None)
                if not match:
                    continue
                log_signal(
                    signal_type="recover",
                    tweet_id=tweet_id,
                    score=match["relevance_score"],
                    classification=match["classification"],
                    digest_run_id=digest_run_id,
                    context_repo=str(repo_path),
                )
                print_success(f"Recovered {tweet_id}")

    except DigestConfigError as exc:
        _fail(exc, exit_code=1, json_output=json_output, code="config_error", fix="Run xx setup or set the required credentials.")
    except ValueError as exc:
        _fail(exc, exit_code=1, json_output=json_output, code="invalid_input", fix="Use --since values like 24h, 3d, 1w, or an ISO date.")
    except tweepy.errors.TweepyException as exc:
        _fail(exc, exit_code=2, json_output=json_output, code="api_error", fix="Check your X credentials, rate limits, and network access.")
    except LLMConfigurationError as exc:
        _fail(exc, exit_code=1, json_output=json_output, code="llm_config_error", fix="Set OPENAI_API_KEY or run xx setup.")
    except LLMError as exc:
        _fail(exc, exit_code=3, json_output=json_output, code="llm_error", fix="Retry the command or switch models later if the error persists.")


@main.command()
def setup():
    """Run the setup wizard."""
    run_setup_wizard(console)


@main.command()
@click.argument("tweet_id_or_url")
def why(tweet_id_or_url):
    """Show why a tweet was scored the way it was."""
    cached = load_last_digest()
    if not cached:
        print_error("No recent digest cache found. Run `xx digest` first.")
        raise SystemExit(1)

    tweet_id = parse_tweet_id(tweet_id_or_url)
    item = next((entry for entry in cached.get("all_scored", []) if entry.get("tweet_id") == tweet_id), None)
    if not item:
        print_error(f"Tweet {tweet_id} is not in the last cached digest.")
        raise SystemExit(1)

    meta = cached.get("meta", {})
    console.print(f"[xx.author]{item.get('author_name') or 'Unknown'}[/xx.author] [xx.handle]@{item.get('author_username') or 'unknown'}[/xx.handle]")
    console.print(item.get("text", ""))
    console.print()
    console.print(
        f"[xx.dim]Score:[/xx.dim] {item.get('relevance_score')}  "
        f"[xx.dim]Classification:[/xx.dim] {item.get('classification')}"
    )
    console.print(f"[xx.dim]Why:[/xx.dim] {item.get('explanation') or '(no explanation)'}")
    if meta.get("work_context"):
        console.print()
        console.print("[xx.info]Matched work context[/xx.info]")
        console.print(meta["work_context"])
    if meta.get("preference_rules"):
        console.print()
        console.print("[xx.info]Current preference rules[/xx.info]")
        console.print(json.dumps(meta["preference_rules"], ensure_ascii=False, indent=2))


@main.command()
@click.argument("text")
def signal(text):
    """Manually inject a preference signal."""
    repo_path = _resolve_repo_path(None)
    digest_run_id = f"manual-{uuid4()}"
    log_signal(
        signal_type="manual_signal",
        tweet_id=None,
        score=None,
        classification=text,
        digest_run_id=digest_run_id,
        context_repo=str(repo_path),
    )
    print_success("Saved manual preference signal.")


def _resolve_repo_path(repo: str | None) -> Path:
    if repo:
        return Path(repo).expanduser().resolve()
    configured = get_default_repo()
    if configured:
        return Path(configured).expanduser().resolve()
    return Path.cwd().resolve()


def _ensure_digest_credentials(*, sample: bool, json_output: bool) -> None:
    config = load_config()
    stored = config.get("credentials", {}) if isinstance(config.get("credentials"), dict) else {}
    openai_key = os.environ.get("OPENAI_API_KEY") or stored.get("openai_api_key")
    if not openai_key:
        if json_output or not console.is_terminal:
            raise DigestConfigError("Missing OpenAI API key")
        config = run_setup_wizard(console)
        stored = config.get("credentials", {}) if isinstance(config.get("credentials"), dict) else {}
        openai_key = stored.get("openai_api_key")
    if not openai_key:
        raise DigestConfigError("Missing OpenAI API key")
    os.environ["OPENAI_API_KEY"] = openai_key

    if sample:
        return

    has_x_credentials = all(os.environ.get(env_name) or stored.get(config_key) for env_name, config_key in _X_CONFIG_KEYS.items())
    if has_x_credentials:
        return
    if json_output or not console.is_terminal:
        raise DigestConfigError("Missing X API credentials")

    refreshed = run_setup_wizard(console)
    stored = refreshed.get("credentials", {}) if isinstance(refreshed.get("credentials"), dict) else {}
    has_x_credentials = all(os.environ.get(env_name) or stored.get(config_key) for env_name, config_key in _X_CONFIG_KEYS.items())
    if not has_x_credentials:
        raise DigestConfigError("Missing X API credentials")


def _load_preference_context() -> tuple[str | None, str | None]:
    rules = load_preference_rules()
    if rules and rules.get("rules"):
        return json.dumps(rules["rules"], ensure_ascii=False, indent=2), None

    few_shot = get_few_shot_examples(limit=5)
    if few_shot:
        return None, json.dumps(few_shot, ensure_ascii=False, indent=2)
    return None, None


def _run_async(awaitable):
    return asyncio.run(awaitable)


def _wants_json(json_output: bool) -> bool:
    return json_output or not console.is_terminal


def _fail(exc: Exception, *, exit_code: int, json_output: bool, code: str, fix: str) -> None:
    if json_output:
        click.echo(
            json.dumps({"error": {"code": code, "message": str(exc), "fix": fix}}, ensure_ascii=False),
            err=True,
        )
    else:
        print_error(str(exc))
    raise SystemExit(exit_code)
