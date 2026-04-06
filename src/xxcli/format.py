"""Terminal output formatting with Rich."""

from __future__ import annotations

from datetime import datetime, timezone
import json
from typing import Any

from rich.console import Console
from rich.panel import Panel
from rich.text import Text

from xxcli.theme import xx_theme

console = Console(theme=xx_theme, highlight=False)


def _relative_time(dt: datetime) -> str:
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    now = datetime.now(timezone.utc)
    diff = now - dt
    seconds = int(diff.total_seconds())
    if seconds < 60:
        return f"{seconds}s"
    minutes = seconds // 60
    if minutes < 60:
        return f"{minutes}m"
    hours = minutes // 60
    if hours < 24:
        return f"{hours}h"
    days = hours // 24
    return f"{days}d"


def _metrics_line(metrics: dict) -> str:
    parts = []
    likes = metrics.get("like_count", 0)
    rts = metrics.get("retweet_count", 0)
    replies = metrics.get("reply_count", 0)
    if likes:
        parts.append(f"{likes} likes")
    if rts:
        parts.append(f"{rts} RTs")
    if replies:
        parts.append(f"{replies} replies")
    return "  ".join(parts) if parts else ""


def format_author(name: str, username: str, time_str: str) -> str:
    name_part = f"[xx.author]{name}[/xx.author]" if name else "[xx.author]Unknown[/xx.author]"
    handle_part = f"[xx.handle]@{username}[/xx.handle]" if username else "[xx.handle]@unknown[/xx.handle]"
    time_part = f" [xx.handle]· {time_str}[/xx.handle]" if time_str else ""
    return f"{name_part} {handle_part}{time_part}"


def print_tweet(tweet, author_name: str = "", author_username: str = "", index: int | None = None):
    """Print a single tweet with formatting."""
    time_str = _relative_time(tweet.created_at) if getattr(tweet, "created_at", None) else ""
    header = format_author(author_name, author_username, time_str)

    lines = [f"[xx.content]{tweet.text}[/xx.content]"]
    if getattr(tweet, "public_metrics", None):
        metrics = _metrics_line(tweet.public_metrics)
        if metrics:
            lines.append(f"[xx.metrics]{metrics}[/xx.metrics]")
    lines.append(f"[xx.dim]id:{tweet.id}[/xx.dim]")

    title = f"[xx.dim]{index}.[/xx.dim] {header}" if index is not None else header
    console.print(Panel("\n".join(lines), title=title, title_align="left", border_style="dim", padding=(0, 1)))


def print_feed(tweets, users: dict):
    """Print a list of tweets as a feed."""
    if not tweets:
        console.print("[xx.dim]No tweets found.[/xx.dim]")
        return

    for i, tweet in enumerate(tweets, 1):
        author = users.get(tweet.author_id)
        name = author.name if author else ""
        username = author.username if author else ""
        print_tweet(tweet, author_name=name, author_username=username, index=i)


def print_my_tweets(tweets, username: str, name: str):
    """Print user's own tweets."""
    if not tweets:
        console.print("[xx.dim]No tweets found.[/xx.dim]")
        return

    for i, tweet in enumerate(tweets, 1):
        print_tweet(tweet, author_name=name, author_username=username, index=i)


def print_digest(items, meta, active_console: Console | None = None):
    active_console = active_console or console
    pct_noise = int((meta["filtered"] / meta["within_since"]) * 100) if meta.get("within_since") else 0

    context_bits = []
    if meta.get("repo"):
        context_bits.append(meta["repo"])
    if meta.get("since"):
        context_bits.append(f"since {meta['since']}")
    subtitle = f"[xx.dim]{' · '.join(context_bits)}[/xx.dim]" if context_bits else ""

    active_console.print(Panel(
        f"[bold]{len(items)}[/bold] signals  [xx.dim]·  {pct_noise}% of your timeline was noise[/xx.dim]",
        title="[xx.accent]xx digest[/xx.accent]",
        subtitle=subtitle,
        title_align="left",
        subtitle_align="left",
        border_style="cyan",
        padding=(0, 1),
    ))

    tag_styles = {"adopt": "green", "avoid": "red", "copy": "cyan"}
    for index, item in enumerate(items, 1):
        tag = item["classification"].upper()
        tag_style = tag_styles.get(item["classification"], "dim")
        border_style = tag_styles.get(item["classification"], "dim")
        time_str = ""
        if item.get("created_at"):
            created = datetime.fromisoformat(item["created_at"].replace("Z", "+00:00"))
            time_str = _relative_time(created)

        header = format_author(item.get("author_name", ""), item.get("author_username", ""), time_str)
        body_lines = [
            f"[xx.content]{item.get('text', '')}[/xx.content]",
            f"[xx.dim]Why:[/xx.dim] {item.get('explanation', '')}",
            f"[xx.dim]id:{item['tweet_id']}[/xx.dim]",
        ]
        title = f"[xx.dim]{index}.[/xx.dim] [{tag_style}]{tag}[/{tag_style}]  {header}"
        active_console.print(Panel(
            "\n".join(body_lines),
            title=title,
            title_align="left",
            border_style=border_style,
            padding=(0, 1),
        ))

    active_console.print("[xx.dim]Run xx like <id> or xx reply <id> \"text\" to interact.[/xx.dim]")
    if meta.get("streak_days", 0) > 1:
        active_console.print(f"[xx.dim]Streak: {meta['streak_days']} days[/xx.dim]")


def print_digest_json(items, meta):
    json_items = [
        {
            "tweet_id": item["tweet_id"],
            "relevance_score": item["relevance_score"],
            "classification": item["classification"],
            "author": f"@{item.get('author_username', '')}" if item.get("author_username") else item.get("author_name", ""),
            "text": item.get("text", ""),
            "explanation": item.get("explanation", ""),
        }
        for item in items
    ]
    json_meta = {
        "scanned": meta.get("scanned", 0),
        "filtered": meta.get("filtered", 0),
        "repo": meta.get("repo"),
        "streak_days": meta.get("streak_days", 0),
        "since": meta.get("since"),
    }
    console.print_json(json.dumps({"items": json_items, "meta": json_meta}))


def print_debug_info(debug_info, active_console: Console | None = None):
    active_console = active_console or console
    if not debug_info:
        return
    active_console.print("[xx.dim]Debug[/xx.dim]")
    if debug_info.get("timing"):
        for phase, duration in debug_info["timing"].items():
            active_console.print(f"[xx.dim]  {phase}: {duration:.2f}s[/xx.dim]")
    score_run = debug_info.get("score_run")
    if score_run:
        active_console.print(f"[xx.dim]  model: {score_run.get('model')}[/xx.dim]")
        active_console.print("[xx.dim]  prompt and raw responses captured for inspection.[/xx.dim]")
    active_console.print()


def print_empty_digest(meta, active_console: Console | None = None):
    active_console = active_console or console
    repo = meta.get("repo") or "your repo"
    active_console.print(Panel(
        f"[xx.dim]○ No relevant signals in this window\n"
        f"Try a wider --since window or switch repo context from {repo}.[/xx.dim]",
        border_style="dim",
        padding=(0, 1),
    ))


def print_filtered_items(items, active_console: Console | None = None):
    active_console = active_console or console
    if not items:
        active_console.print("[xx.dim]No filtered items to review.[/xx.dim]")
        return
    active_console.print("[xx.info]Filtered items[/xx.info]")
    for item in items:
        active_console.print(
            f"  [xx.dim]id:{item['tweet_id']}[/xx.dim] "
            f"[xx.handle]@{item.get('author_username', '')}[/xx.handle] "
            f"{item.get('text', '')}"
        )


def print_success(message: str):
    console.print(f"[xx.success]{message}[/xx.success]")


def print_error(message: str, *, hint: str | None = None):
    console.print(f"[xx.error]✗ {message}[/xx.error]")
    if hint:
        console.print(f"  [xx.dim]Hint: {hint}[/xx.dim]")


def print_profile(user):
    """Print user profile info."""
    console.print(f"[xx.author]{user.name}[/xx.author] [xx.handle]@{user.username}[/xx.handle]")
    if user.description:
        console.print(f"  [xx.content]{user.description}[/xx.content]")
    m = user.public_metrics
    if m:
        console.print(
            f"  [xx.metrics]{m['followers_count']} followers · "
            f"{m['following_count']} following · "
            f"{m['tweet_count']} tweets[/xx.metrics]"
        )
    console.print()
