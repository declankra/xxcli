# xx

**Twitter/X from the terminal. Stay up to date without the doom scroll.**

---

I use X to stay current on AI/tech/software/business. This includes new tools, frameworks, techniques, and research I find helpful and interesting as someone who works in the space. The space moves so fast now that it's important to keep up. But it's even more important to protect your focus.

The browser is very addicting. I'd open X to check one thing and lose 45 minutes. Every time.

**Good ideas persist over time.** I don't need to check X every 30 minutes, let alone everyday. I can increase my signal-to-noise ratio dramatically by consuming intentionally.

**The CLI strips away the addicting stuff.** I've found the CLI to be helpful with focusin only on the task at hand. It's even gone so far as to almost entirely replaced my use of ChatGPT in the browser at this point. The CLI is a great question-answer machine.

I've got questions, want to stay up to date and interact with other ideas, without losing my focus. To me, that means using X without X, "not X". 

---

## What's next

Things I'm building towards:

- **Interacting with ideas** - How can I interact with the ideas, in a way that is immediately practical and actionable, based on how I currently work?
< embed tweet where i talk about how i use twitter >  
- **AI-powered relevance filtering** — filter the tweets in my feed most applicable to what my goals are and what I'm working on
- **Agent-native** — what does a claude code/codex terminal agent need (skills, deterministic tools, user context...) so that the user (myself) could do the above?
- **User vs agent UX** — what purpose does me using CLI commands vs agent using them on my behalf? what UI/UX makes most sense given goals of applying the ideas fast and interacting with them (asking follow-ups, "how would this work with what im doing with Y?", etc.)



---

## Install

```bash
git clone https://github.com/declankra/xxcli.git
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

## License

MIT - do whatever
