"""Twitter API client wrapping Tweepy v2 + v1.1."""

import os
import sys
from pathlib import Path

import tweepy


def _get_credentials():
    keys = {
        "consumer_key": os.environ.get("X_API_KEY"),
        "consumer_secret": os.environ.get("X_API_SECRET"),
        "access_token": os.environ.get("X_ACCESS_TOKEN"),
        "access_token_secret": os.environ.get("X_ACCESS_TOKEN_SECRET"),
    }
    missing = [k for k, v in keys.items() if not v]
    if missing:
        print("Missing Twitter API credentials. Set these env vars:", file=sys.stderr)
        print("  X_API_KEY, X_API_SECRET, X_ACCESS_TOKEN, X_ACCESS_TOKEN_SECRET", file=sys.stderr)
        sys.exit(1)
    return keys


def get_client() -> tweepy.Client:
    creds = _get_credentials()
    return tweepy.Client(
        consumer_key=creds["consumer_key"],
        consumer_secret=creds["consumer_secret"],
        access_token=creds["access_token"],
        access_token_secret=creds["access_token_secret"],
    )


def get_api_v1() -> tweepy.API:
    """v1.1 API — needed for media uploads."""
    creds = _get_credentials()
    auth = tweepy.OAuth1UserHandler(
        creds["consumer_key"],
        creds["consumer_secret"],
        creds["access_token"],
        creds["access_token_secret"],
    )
    return tweepy.API(auth)


def get_me(client: tweepy.Client):
    resp = client.get_me(user_fields=["username", "name", "description", "public_metrics"])
    return resp.data


def get_home_timeline(client: tweepy.Client, count: int = 20):
    resp = client.get_home_timeline(
        max_results=min(count, 100),
        tweet_fields=["created_at", "public_metrics", "author_id", "conversation_id"],
        expansions=["author_id"],
        user_fields=["username", "name"],
    )
    users = {}
    if resp.includes and "users" in resp.includes:
        users = {u.id: u for u in resp.includes["users"]}
    return resp.data or [], users


def get_user_tweets(client: tweepy.Client, user_id: str, count: int = 10):
    resp = client.get_users_tweets(
        id=user_id,
        max_results=min(max(count, 5), 100),
        tweet_fields=["created_at", "public_metrics"],
    )
    return resp.data or []


def post_tweet(client: tweepy.Client, text: str, media_ids: list[int] | None = None, reply_to: str | None = None):
    kwargs = {"text": text}
    if media_ids:
        kwargs["media_ids"] = media_ids
    if reply_to:
        kwargs["in_reply_to_tweet_id"] = reply_to
    resp = client.create_tweet(**kwargs)
    return resp.data


def upload_media(api_v1: tweepy.API, image_paths: list[str]) -> list[int]:
    media_ids = []
    for image_path in image_paths:
        path = Path(image_path).expanduser()
        if not path.exists():
            print(f"Warning: file not found: {image_path}", file=sys.stderr)
            continue
        media = api_v1.media_upload(filename=str(path))
        media_ids.append(media.media_id)
    return media_ids


def like_tweet(client: tweepy.Client, tweet_id: str):
    me = get_me(client)
    client.like(tweet_id=tweet_id, user_auth=True)
    return True


def parse_tweet_id(tweet_id_or_url: str) -> str:
    """Extract tweet ID from a URL or return as-is if already an ID."""
    if "/" in tweet_id_or_url:
        # Handle URLs like https://x.com/user/status/123456
        parts = tweet_id_or_url.rstrip("/").split("/")
        return parts[-1]
    return tweet_id_or_url
