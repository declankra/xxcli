---
name: xx-digest
description: >
  Get an AI-scored digest of your Twitter/X feed,
  filtered by relevance to what you're currently building.
---

# xx digest

Returns tweets relevant to your current work, scored and
classified as adopt/avoid/copy by an LLM that reads your
git context.

## Usage

```bash
# Machine-readable output (for agents)
xx digest --json

# Human-readable output
xx digest

# Specify repo context
xx digest --repo ~/Code/my-project

# Pass a preference signal
xx signal 'interested in agent architecture'

# Explain a score
xx why 1234567890
```

## Output schema (--json)

```json
{
  "items": [
    {
      "tweet_id": "string",
      "relevance_score": 8,
      "classification": "adopt",
      "author": "@username",
      "text": "tweet content",
      "explanation": "Why this matters to your work"
    }
  ],
  "meta": {
    "scanned": 47,
    "filtered": 44,
    "repo": "xxcli",
    "streak_days": 5,
    "since": "24h"
  }
}
```

## Exit codes

- 0: success
- 1: config error (missing API key, invalid config)
- 2: API error (Twitter rate limit, timeout, network)
- 3: LLM error (OpenAI failure, malformed output)

## Error output (--json mode)

Errors are JSON on stderr:

```json
{"error": {"code": "rate_limited", "message": "...", "fix": "..."}}
```

## Prerequisites

- Twitter API credentials (Free tier) for live timeline pulls
- OpenAI API key (from ChatGPT/Codex subscription)
- Run `xx setup` first, or provide credentials via env vars
