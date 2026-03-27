"""Terminal output formatting with Rich."""

from datetime import datetime, timezone

from rich.console import Console
from rich.text import Text

console = Console()


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
        parts.append(f"[red]{likes}[/red] likes")
    if rts:
        parts.append(f"[green]{rts}[/green] RTs")
    if replies:
        parts.append(f"[blue]{replies}[/blue] replies")
    return "  ".join(parts) if parts else ""


def print_tweet(tweet, author_name: str = "", author_username: str = "", index: int | None = None):
    """Print a single tweet with formatting."""
    prefix = f"[dim]{index}.[/dim] " if index is not None else ""

    # Author line
    if author_username:
        author = f"[bold]{author_name}[/bold] [dim]@{author_username}[/dim]"
    else:
        author = f"[dim]@unknown[/dim]"

    # Time
    time_str = ""
    if tweet.created_at:
        time_str = f" [dim]· {_relative_time(tweet.created_at)}[/dim]"

    console.print(f"{prefix}{author}{time_str}")
    console.print(f"  {tweet.text}")

    # Metrics
    if tweet.public_metrics:
        metrics = _metrics_line(tweet.public_metrics)
        if metrics:
            console.print(f"  {metrics}")

    # Tweet ID for reference
    console.print(f"  [dim]id:{tweet.id}[/dim]")
    console.print()


def print_feed(tweets, users: dict):
    """Print a list of tweets as a feed."""
    if not tweets:
        console.print("[dim]No tweets found.[/dim]")
        return

    for i, tweet in enumerate(tweets, 1):
        author = users.get(tweet.author_id)
        name = author.name if author else ""
        username = author.username if author else ""
        print_tweet(tweet, author_name=name, author_username=username, index=i)


def print_my_tweets(tweets, username: str, name: str):
    """Print user's own tweets."""
    if not tweets:
        console.print("[dim]No tweets found.[/dim]")
        return

    for i, tweet in enumerate(tweets, 1):
        print_tweet(tweet, author_name=name, author_username=username, index=i)


def print_success(message: str):
    console.print(f"[green]{message}[/green]")


def print_error(message: str):
    console.print(f"[red]Error:[/red] {message}")


def print_profile(user):
    """Print user profile info."""
    console.print(f"[bold]{user.name}[/bold] [dim]@{user.username}[/dim]")
    if user.description:
        console.print(f"  {user.description}")
    m = user.public_metrics
    if m:
        console.print(
            f"  [dim]{m['followers_count']} followers · "
            f"{m['following_count']} following · "
            f"{m['tweet_count']} tweets[/dim]"
        )
    console.print()
