# DX Review: xx digest — Developer Experience Plan Review

**Branch:** main
**Plan:** `docs/designs/xx-digest-ceo-plan.md` + `docs/designs/xx-digest-design.md`
**Status:** DX REVIEWED — 14 decisions made, 0 unresolved

## Context

xx digest is a context-aware feed digest for the xx CLI (Python/Click/Tweepy/Rich). This DX review evaluated the plan across TWO developer personas before implementation:

1. **Human CLI user** — types `xx digest` in terminal, expects rich TUI
2. **AI agent** (Claude Code, Codex) — invokes xx programmatically, needs structured output

## Initial Assessment

**Initial DX score: 5/10.** Two critical gaps:
1. Agent path entirely unspecified (no --json, no skill wrapper, no discovery)
2. Credential wall at T0 (5 env vars across 2 external sites before first run)

**TTHW:** ~10-15 minutes. Target: ~8 minutes with credential wizard.

## Developer Empathy Narratives

### Human persona

> I clone the repo, pip install. Then I hit the wall. 5 environment variables from 2 different sites. I paste them into .zshrc, restart my terminal, run `xx digest`. The setup wizard kicks in. Picks my repo, walks me through calibration on real tweets. The first time I mark something "Useful" and it says "Got it. Prioritizing [topic] for [repo]" — that's the aha moment. The first digest renders. 3 items, 93% noise filtered. Each one references my actual code. "This knows what I'm building." That's the magic moment. But I almost didn't get here. The credential setup almost lost me.

### Agent persona

> I'm Claude Code. User says "What's on my Twitter feed that's important?" I run `xx --help`, see `digest`. I run `xx digest --json`. I get structured JSON: items with tweet_id, score, classification, explanation. I present this to the user and offer to run `xx like <id>`. Clean.

## Decisions Made (14 total)

### Pass 1: Getting Started (4/10 → 7/10)

1. **Credential wizard as Phase 0 of onboarding.** The setup wizard now starts with credential collection, not repo selection. Walks user through pasting API keys, validates them live against the APIs, stores in `~/.xxcli/config.yaml`. Env vars still work as override for CI/cron. One continuous flow, never leaves the terminal.

2. **`--json` flag + auto-detect pipe.** When `--json` is passed or stdout is not a TTY, output structured JSON. Same Pydantic schema the LLM already produces, plus a `meta` envelope. GitHub CLI does this exact pattern.

   ```json
   {"items": [{"tweet_id": "123", "score": 8, "classification": "adopt",
     "author": "@simonw", "text": "...", "explanation": "..."}],
    "meta": {"scanned": 47, "filtered": 44, "repo": "xxcli", "streak_days": 5}}
   ```

3. **`.claude/skills/xx-digest/SKILL.md` ships with the repo.** AI agents discover xx via this skill wrapper. Includes usage examples, output schema, and exit codes.

### Pass 2: CLI Design (7/10 → 8/10)

4. **`parse_tweet_id()` extended to strip `id:` prefix.** Handles URLs (`https://x.com/user/status/123`), raw IDs (`123`), and digest output format (`id:123`). One function, all formats.

### Pass 3: Error Messages (6/10 → 8/10)

5. **Error message formula.** Every error follows: what happened + why + how to fix + actual values.

   ```
   ✗ Rate limited
     X API returned 429 (15 requests in the current 15-minute window).
     Wait a few minutes and try again. This quota is shared with xx feed.
   ```

6. **JSON errors for agents.** When `--json` is active, errors are JSON on stderr:
   ```json
   {"error": {"code": "rate_limited", "message": "X API returned 429", "fix": "Wait a few minutes and try again"}}
   ```

### Pass 4: Documentation (4/10 → 7/10)

7. **README update promoted to Step 5 (before tests).** Includes digest section with demo output, `xx setup` quick start, flag reference, and "How it works" paragraph.

### Pass 6: Dev Environment (6/10 → 7/10)

8. **`--sample` flag for dev testing.** Loads 19 hand-labeled tweets from eval data instead of calling Twitter API. Still calls OpenAI for scoring. Enables fast prompt iteration without rate limits.

### Pass 8: DX Measurement (7/10)

9. **TTHW timing instrumented in wizard.** Records start time at wizard entry, end time at first digest render, stores duration in config.yaml.

### Outside Voice (Codex)

10. **Exit codes defined:** 0=success, 1=config error, 2=API error, 3=LLM error.
11. **Token caps: skipped.** Existing limits (200-line README, 20-commit git log) are sufficient. Monitor via --debug.
12. **No cache: stateless by design.** Once-daily usage pattern makes caching unnecessary.
13. **Keep adopt/avoid/copy taxonomy.** Labels encode distinct action modes that pure scores don't capture.
14. **Ship with 19-tweet eval.** The product IS the eval loop. feedback.jsonl grows the dataset naturally.

## NOT in scope (DX review)

| Item | Rationale |
|------|-----------|
| PyPI publishing | Git clone for now. Publish when stable + shared. |
| Tab completion | Minor ergonomic. Add when command count grows. |
| Windows path handling | macOS/Linux only for now. Personal tool. |
| CI/CD pipeline | No GitHub Actions needed for solo dev. |
| Docs site | README is sufficient for this product stage. |
| Token budget truncation | Monitor via --debug, cap if needed. |
| Digest caching | Stateless by design. Once-daily use. |
| Interactive tutorial | Setup wizard IS the tutorial. |

## What already exists

| Component | Location | Reuse strategy |
|-----------|----------|----------------|
| Click group + commands | `cli.py` | Add digest, setup, why, signal commands |
| Rich console + formatting | `format.py` | Extend with print_digest() |
| `_relative_time()` | `format.py:11` | Reuse for tweet timestamps |
| `print_error()` | `format.py:99` | Upgrade with error formula |
| `_handle_api_error()` | `cli.py:28` | Extend for digest-specific errors |
| `parse_tweet_id()` | `client.py:102` | Extend to strip `id:` prefix |
| `get_home_timeline()` | `client.py:52` | Call from digest command |
| Eval data (19 tweets) | `evals/xx-feed-20260327.md` | Source for --sample flag |

## Files Impacted by DX Review

### New files (added by DX review)
- `.claude/skills/xx-digest/SKILL.md` — Agent discovery wrapper

### Modified plans (sections to add)
- `onboarding.py` — Phase 0: credential collection + validation (before repo selection)
- `cli.py` — `--json` flag on digest, `--sample` flag, exit codes 0/1/2/3
- `format.py` — JSON output mode, error formula upgrade
- `config.py` — credential storage + retrieval, TTHW timing
- `client.py` — `parse_tweet_id()` strips `id:` prefix
- `README.md` — Digest section promoted to Step 5

## Updated Setup Wizard Flow

```
FIRST RUN: xx digest (or xx setup)
     │
     ├─── Phase 0: Credentials (NEW from DX review)
     │    ├─── Check env vars first (skip if all present)
     │    ├─── "You need a free Twitter Developer account"
     │    │    → https://developer.twitter.com/en/portal/dashboard
     │    ├─── Paste 4 Twitter tokens, validate with API call
     │    ├─── "Uses your ChatGPT/Codex subscription"
     │    │    → https://platform.openai.com/api-keys
     │    ├─── Paste OpenAI key, validate with API call
     │    ├─── Save to ~/.xxcli/config.yaml
     │    └─── Record TTHW start timestamp
     │
     ├─── Phase 1: Pick repo (scan dev directories, present list)
     ├─── Phase 2: Scan for project docs
     ├─── Phase 3: Calibrate on real tweets (10-15 tweets)
     │    └─── First "Useful" → aha moment
     ├─── Phase 4: First digest with calibrated context
     │    └─── Record TTHW end timestamp
     └─── Save all to ~/.xxcli/config.yaml
```

## DX Scorecard

```
+====================================================================+
|              DX PLAN REVIEW — SCORECARD                             |
+====================================================================+
| Dimension            | Score  |
|----------------------|--------|
| Getting Started      |  7/10  |
| API/CLI/SDK          |  8/10  |
| Error Messages       |  8/10  |
| Documentation        |  7/10  |
| Upgrade Path         |  6/10  |
| Dev Environment      |  7/10  |
| Community            |  3/10  |
| DX Measurement       |  7/10  |
+--------------------------------------------------------------------+
| TTHW                 | ~8 min |
| Product Type         | CLI Tool + Claude Code Skill              |
| Overall DX           |  7/10  |
+====================================================================+
```

## Outside Voice (Codex)

15 findings. 6 already resolved in prior reviews. 4 substantive tensions resolved with user:
1. Token budget: deferred (monitor via --debug)
2. Classification taxonomy: kept (adopt/avoid/copy)
3. Caching: rejected (stateless by design)
4. Eval size: shipped with 19 (product IS the eval loop)

Remaining findings accepted as v1 risks: referenced_tweets complexity, test scaffolding scope, repo edge cases.

## Unresolved Decisions

None. All 14 decisions resolved.
