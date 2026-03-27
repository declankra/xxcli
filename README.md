# xx

**Twitter/X from the terminal. No browser, no doom scroll.**

---

I use X to stay current on AI — new tools, frameworks, techniques, research. The space moves so fast that falling behind means missing things that could 10x my workflow.

But the way I was consuming it — browser tab, infinite scroll, algorithmic feed — was a trap. I'd open X to check one thing and lose 45 minutes. Every time.

The core insight: **good ideas persist over time.** I don't need to check every 30 minutes. I can increase my signal-to-noise ratio dramatically by consuming intentionally — pull the important stuff on my schedule, skip the noise.

A CLI is inherently less addictive than a feed algorithm designed to keep you scrolling. There's no autoplay, no sidebar recommendations, no "you might also like." You get the content, you read it, you close the terminal. That's the whole point.

`xx` is short for "not X." Use X without using X.

---

## Install

```bash
git clone https://github.com/dkbuildsco/xxcli.git
cd xxcli
pip install -e .
```

Requires Python 3.10+ and a Twitter/X API key with OAuth 1.0a User Context.

### API credentials

Set these environment variables (add to your `.zshrc` / `.bashrc`):

```bash
export X_API_KEY="your-api-key"
export X_API_SECRET="your-api-secret"
export X_ACCESS_TOKEN="your-access-token"
export X_ACCESS_TOKEN_SECRET="your-access-token-secret"
```

You need a [Twitter Developer account](https://developer.twitter.com/) with at least Free tier access. The Free tier supports posting and reading your home timeline.

## Usage

### Read your feed

```bash
xx feed           # last 20 tweets from your timeline
xx feed -n 50     # last 50
```

### Post a tweet

```bash
xx post "shipping xxcli v0.1 today"
xx post "check this out" screenshot.png     # with image
```

### Reply to a tweet

```bash
xx reply 123456789 "great point"
xx reply https://x.com/user/status/123456789 "agreed"
```

### Like a tweet

```bash
xx like 123456789
xx like https://x.com/user/status/123456789
```

### See your own tweets

```bash
xx me             # last 10 tweets
xx me -n 20       # last 20
```

## What's next

This is v0.1 — the basics. Things I'm building toward:

- **AI-powered relevance filtering** — surface tweets most applicable to what I'm working on
- **Smart follow suggestions** — based on who shows up in my For You and Following feeds
- **Time-gating** — block CLI access during deep focus hours
- **Thread support** — post multi-tweet threads from a file

## License

MIT
