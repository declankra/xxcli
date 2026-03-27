"""CLI entry point for xxcli."""

import click
import tweepy

from xxcli import __version__
from xxcli.client import (
    get_api_v1,
    get_client,
    get_home_timeline,
    get_me,
    get_user_tweets,
    like_tweet,
    parse_tweet_id,
    post_tweet,
    upload_media,
)
from xxcli.format import (
    console,
    print_error,
    print_feed,
    print_my_tweets,
    print_profile,
    print_success,
)


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


@click.group()
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
    """Post a tweet. Attach images by passing file paths after the text.

    \b
    Examples:
      xx post "hello world"
      xx post "check this out" screenshot.png
    """
    if len(text) > 280:
        console.print(f"[yellow]Warning:[/yellow] Tweet is {len(text)} chars (max 280)")
        if not click.confirm("Post anyway?"):
            raise SystemExit(0)

    try:
        client = get_client()
        media_ids = None
        if images:
            api_v1 = get_api_v1()
            media_ids = upload_media(api_v1, list(images))
            if media_ids:
                console.print(f"[dim]Uploaded {len(media_ids)} image(s)[/dim]")

        data = post_tweet(client, text, media_ids=media_ids)
        tweet_id = data["id"]
        print_success(f"Posted! https://x.com/i/web/status/{tweet_id}")
    except tweepy.errors.TweepyException as e:
        _handle_api_error(e)


@main.command()
@click.argument("tweet_id_or_url")
@click.argument("text")
def reply(tweet_id_or_url, text):
    """Reply to a tweet.

    \b
    Examples:
      xx reply 123456789 "great point"
      xx reply https://x.com/user/status/123456789 "agreed"
    """
    if len(text) > 280:
        console.print(f"[yellow]Warning:[/yellow] Reply is {len(text)} chars (max 280)")
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
    """Like a tweet.

    \b
    Examples:
      xx like 123456789
      xx like https://x.com/user/status/123456789
    """
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
            console.print("[dim]User timeline requires Basic API tier ($100/mo).[/dim]")
            console.print("[dim]Profile shown above. Use 'xx feed' to see your timeline.[/dim]")
    except tweepy.errors.TweepyException as e:
        _handle_api_error(e)
