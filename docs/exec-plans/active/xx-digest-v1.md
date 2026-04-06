# Implement xx digest: Context-Aware Feed Digest with Learning System

This ExecPlan is a living document. The sections Progress, Surprises & Discoveries, Decision Log, Outcomes & Retrospective, and Refinement Pass must be kept up to date as work proceeds. This document must be maintained in accordance with `.agents/PLANS.md` at the repository root.

## Purpose / Big Picture

After this change, a developer can run `xx digest` in their terminal and see 3-5 tweets from their X/Twitter feed that are relevant to what they are currently building, scored by an LLM that reads their git context. 93% of the timeline is filtered away. Each item is classified as ADOPT (start using), AVOID (your approach may be wrong), or COPY (learn from adjacent builder), with a one-sentence explanation referencing their specific code.

The product has two personas. A human types `xx digest` and gets a rich terminal experience with spinners, colors, interactive feedback, and a setup wizard. An AI agent (Claude Code, Codex) runs `xx digest --json` and gets structured JSON it can parse and present to the user. Both paths are first-class.

To see it working after implementation: run `xx digest` from a git repo with `OPENAI_API_KEY` and Twitter credentials set. The setup wizard guides you through credential validation, repo selection, tweet calibration, and renders your first digest. Run `xx digest --json` to see structured output. Run `xx digest --sample --debug` to test with eval data and see full LLM reasoning.

## Progress

- [ ] Milestone 1: Foundation (config.py, context.py, theme.py)
- [ ] Milestone 2: LLM agents (llm.py, Pydantic models)
- [ ] Milestone 3: Digest engine (digest.py)
- [ ] Milestone 4: Feedback system (feedback.py)
- [ ] Milestone 5: Setup wizard (onboarding.py)
- [ ] Milestone 6: CLI wiring (cli.py, format.py, client.py)
- [ ] Milestone 7: Agent interface (--json, SKILL.md, exit codes)
- [ ] Milestone 8: Tests, eval, README, version bump

## Surprises & Discoveries

(Populated during implementation.)

## Decision Log

All decisions below were made during the design and review pipeline (office-hours, eng review, design review, CEO review, DX review). They are restated here so this plan is self-contained.

- Decision: Use OpenAI Agents SDK with Pydantic structured output, not raw JSON parsing.
  Rationale: Eliminates malformed-JSON error class entirely. SDK handles validation natively.

- Decision: Credential wizard as Phase 0 of setup, stored in ~/.xxcli/config.yaml.
  Rationale: Reduces time-to-first-digest from 15 min to ~8 min by merging credential collection into the wizard instead of requiring manual .zshrc editing.

- Decision: --json flag + auto-detect pipe for machine-readable output.
  Rationale: GitHub CLI pattern. Agents need structured data. JSON schema matches DigestResult Pydantic model.

- Decision: No caching between runs. Always re-score.
  Rationale: Once-daily usage pattern. Stateless is simpler. last_digest.json exists only for `xx why`.

- Decision: Ship with 19-tweet eval dataset, grow via feedback.jsonl.
  Rationale: The product IS the eval loop. Each digest run generates new labeled data.

- Decision: Exit codes 0=success, 1=config error, 2=API error, 3=LLM error.
  Rationale: Agents can programmatically distinguish error types and decide whether to retry.

## Outcomes & Retrospective

(Populated after implementation.)

## Context and Orientation

xxcli is a Python CLI for Twitter/X. Version 0.1.0 ships five commands: `feed`, `post`, `reply`, `like`, `me`. The codebase lives in `src/xxcli/` with four modules:

- `src/xxcli/__init__.py` — version string ("0.1.0")
- `src/xxcli/cli.py` — Click command group with `DefaultPostGroup` (lets `xx "hello"` default to `xx post "hello"`). Commands: feed, post, reply, like, me. Error handler `_handle_api_error()` wraps Tweepy exceptions.
- `src/xxcli/client.py` — Tweepy v2 wrapper. `get_client()` reads 4 env vars (X_API_KEY, X_API_SECRET, X_ACCESS_TOKEN, X_ACCESS_TOKEN_SECRET). `get_home_timeline()` returns (tweets, users_dict). `parse_tweet_id()` handles URLs and raw IDs.
- `src/xxcli/format.py` — Rich Console output. `console` singleton, `_relative_time()`, `_metrics_line()`, `print_tweet()`, `print_feed()`, `print_error()`, `print_success()`, `print_profile()`.

Dependencies in `pyproject.toml`: tweepy>=4.14, click>=8.0, rich>=13.0. Entry point: `xx = "xxcli.cli:main"`.

Data directory: `~/.xxcli/` (created on first use). Will contain: `config.yaml`, `feedback.jsonl`, `preference_rules.json`, `last_digest.json`.

Terminal design system is defined in `DESIGN.md`. Key rules: cyan accent color, bold for authors, dim for metadata/handles, no colored engagement metrics, `[xx.accent]` style tokens. The Rich theme tokens defined there should be used via `src/xxcli/theme.py`.

Eval data exists at `evals/xx-feed-20260327.md` — 19 hand-labeled tweets from a real feed session.

## Plan of Work

The implementation is organized into 8 milestones. Each milestone produces testable, working code. The milestones must be executed in order because later milestones import from earlier ones.

### Milestone 1: Foundation

Create three new files that other milestones depend on.

`src/xxcli/theme.py` defines the Rich Theme from DESIGN.md. It exports an `xx_theme` Theme object with named styles: `xx.author` (bold), `xx.handle` (dim), `xx.content` (empty string), `xx.metrics` (dim), `xx.accent` (cyan), `xx.success` (green), `xx.error` (red bold), `xx.warning` (yellow), `xx.info` (blue), `xx.key` (cyan), `xx.dim` (dim). Update `format.py` to pass this theme to the Console constructor.

`src/xxcli/config.py` manages `~/.xxcli/config.yaml`. It provides:
- `load_config() -> dict` — reads config.yaml, returns empty dict if missing or corrupt. Never raises.
- `save_config(data: dict) -> None` — writes to config.yaml, creates ~/.xxcli/ if needed.
- `get_credentials() -> dict | None` — returns Twitter + OpenAI credentials from config, or None if not stored. Env vars take precedence over config file values.
- `get_default_repo() -> str | None` — returns default_repo from config.
- `get_streak() -> dict` — returns streak data (last_digest_run, consecutive_days).
- `update_streak() -> dict` — called after each digest run. Increments consecutive_days if last run was yesterday, resets to 1 if gap > 1 day.

Config file schema (YAML):

    credentials:
      x_api_key: "..."
      x_api_secret: "..."
      x_access_token: "..."
      x_access_token_secret: "..."
      openai_api_key: "..."
    default_repo: "~/Code/xxcli"
    default_since: "24h"
    default_count: 5
    streak:
      last_digest_run: "2026-04-04T09:00:00Z"
      consecutive_days: 5
    tthw:
      setup_started: "2026-04-04T08:55:00Z"
      setup_completed: "2026-04-04T09:02:00Z"
      duration_seconds: 420

Credential resolution order: env var > config.yaml > None (triggers wizard).

`src/xxcli/context.py` builds work context from a git repository. It provides:
- `build_work_context(repo_path: str) -> WorkContext` where WorkContext is a dataclass with fields: repo_name (str), branch (str), git_log (str, last 20 commits), git_diff_stat (str, uncommitted changes), readme_excerpt (str, first 200 lines), deps_summary (str, from pyproject.toml or requirements.txt), changed_files (list[str], recently modified paths).
- `format_context_for_prompt(ctx: WorkContext) -> str` — formats the WorkContext into the prompt string the LLM expects.

All git operations use `subprocess.run()` with list-form arguments (never `shell=True`). If the path is not a git repo, return a WorkContext with empty fields and set `repo_name` to the directory basename.

Verification: after this milestone, you can import `config`, `context`, and `theme` from `xxcli` and call their functions. Run `python -c "from xxcli.context import build_work_context; print(build_work_context('.'))"` from the repo root to see the context output.

### Milestone 2: LLM Agents

Create `src/xxcli/llm.py` with the OpenAI Agents SDK integration. This file defines two agents and all Pydantic models.

Add dependencies to `pyproject.toml`: `openai-agents>=0.1`, `pyyaml>=6.0`.

Pydantic models:

    from pydantic import BaseModel

    class DigestItem(BaseModel):
        tweet_id: str
        relevance_score: int  # 0-10
        classification: str   # "adopt", "avoid", "copy", "skip"
        explanation: str      # one sentence, empty if skip

    class DigestResult(BaseModel):
        items: list[DigestItem]

    class FewShotExample(BaseModel):
        tweet_summary: str
        action: str  # "keep" or "discard"
        reason: str

    class PreferenceRules(BaseModel):
        rules: list[str]
        few_shot_examples: list[FewShotExample]

Scoring Agent function:

    async def score_tweets(
        tweets_json: str,
        work_context: str,
        preference_rules: str | None = None,
        few_shot_examples: str | None = None,
        model: str = "gpt-4.1-mini",
    ) -> DigestResult:

This function creates an `Agent` from `openai-agents` with the system prompt (provided below), calls `Runner.run()` with the user prompt containing tweets + context + preferences, and returns the Pydantic `DigestResult`. On failure, it retries once after 3 seconds. Uses `result_type=DigestResult` for structured output.

System prompt for the scoring agent:

    You are a relevance filter for a developer's Twitter/X feed. You score
    tweets by how relevant they are to the developer's CURRENT work, not
    general interest. Be ruthless — most tweets score 0-3.

    Filter rules:
    - Hype/reaction tweets that just amplify news without adding perspective: score 0.
    - Tweets that are merely "interesting" but not actionable: score 1-3.
    - The acid test: "does this change what the developer builds or how they think?"
    - SERENDIPITY ALLOWANCE: For up to 1 item, you may score a tweet 7+ if it
      is genuinely novel/surprising and connects to the developer's domain in a
      non-obvious way, even if not directly about their current repo. Creativity
      comes from association. Do not let relevance filtering become a black hole.

    {preference_section}

The `{preference_section}` is either:
- Phase 1 (< 20 signals): few-shot examples from feedback, formatted as "Here are examples of what this developer considers useful/not useful: ..."
- Phase 2 (20+ signals): distilled rules from preference_rules.json, formatted as "User preference rules: ..."
- Empty string if no feedback exists yet.

Distillation Agent function:

    async def distill_preferences(
        feedback_signals: str,
        current_rules: str | None = None,
        model: str = "gpt-4.1-mini",
    ) -> PreferenceRules:

System prompt: "You are analyzing a user's tweet curation behavior. Summarize their preferences as concise scoring rules. Reference specific topics, content types, and patterns. Keep rules actionable and specific."

Also provide a synchronous wrapper `check_openai_key() -> bool` that validates the OPENAI_API_KEY by making a lightweight API call (list models or similar). Returns True if valid, False if not.

Verification: `python -c "from xxcli.llm import DigestItem, DigestResult; print(DigestResult(items=[]).model_dump_json())"` should print `{"items":[]}`.

### Milestone 3: Digest Engine

Create `src/xxcli/digest.py` which orchestrates the full digest pipeline.

    import asyncio
    from datetime import datetime, timezone, timedelta

    def parse_since(since: str) -> datetime:
        """Parse '24h', '3d', '1w', or ISO date into a UTC datetime."""

    async def run_digest(
        tweets: list,
        users: dict,
        work_context_str: str,
        preference_rules_str: str | None,
        few_shot_str: str | None,
        since: datetime,
        count: int,
        model: str = "gpt-4.1-mini",
        debug: bool = False,
        sample: bool = False,
    ) -> dict:
        """
        Full digest pipeline. Returns dict with:
        - items: list[DigestItem] (filtered, sorted, truncated)
        - meta: dict (scanned, filtered, repo, timing, etc.)
        - all_scored: list[DigestItem] (all items including skipped, for caching)
        - debug_info: dict | None (prompt, raw response, timing per phase)
        """

Steps inside run_digest:
1. Filter tweets by `created_at >= since`.
2. Format tweets as JSON array (tweet_id, author_name, author_username, text, created_at).
3. Call `score_tweets()` from llm.py.
4. Filter items where `relevance_score >= 7`.
5. Sort by score descending.
6. Truncate to `count`.
7. Return the result dict.

If `debug=True`, capture timing for each phase and the full prompt/response.

Also provide `load_sample_tweets() -> tuple[list, dict]` that reads `evals/xx-feed-20260327.md`, parses the 19 tweets into mock Tweepy-like objects (SimpleNamespace or dataclass with fields: id, text, author_id, created_at, public_metrics), and returns (tweets, users_dict) in the same format as `get_home_timeline()`.

Provide `save_last_digest(all_scored: list, meta: dict) -> None` that writes to `~/.xxcli/last_digest.json`.

Provide `load_last_digest() -> dict | None` that reads from the cache file. Returns None if missing or > 24h old.

Verification: with the --sample flag, the digest should process the 19 eval tweets against the current repo's work context and return scored results.

### Milestone 4: Feedback System

Create `src/xxcli/feedback.py`.

    from pathlib import Path
    import json
    from datetime import datetime, timezone

    FEEDBACK_FILE = Path.home() / ".xxcli" / "feedback.jsonl"
    PREFERENCE_FILE = Path.home() / ".xxcli" / "preference_rules.json"

    def log_signal(signal_type: str, tweet_id: str | None, score: int | None,
                   classification: str | None, digest_run_id: str,
                   context_repo: str, items_shown: list[str] | None = None) -> None:
        """Append one record to feedback.jsonl."""

    def get_signal_count() -> int:
        """Count explicit signals (keep, discard, recover) in feedback.jsonl."""

    def get_signals_since_last_distillation() -> int:
        """Count signals since the last distillation ran."""

    def load_recent_signals(limit: int = 50) -> list[dict]:
        """Load last N signals from feedback.jsonl for distillation input."""

    def load_preference_rules() -> dict | None:
        """Load preference_rules.json. Returns None if missing."""

    def save_preference_rules(rules: dict) -> None:
        """Write preference_rules.json."""

    def get_few_shot_examples(limit: int = 5) -> list[dict]:
        """Get recent feedback examples for few-shot prompting (Phase 1, < 20 signals)."""

    async def maybe_distill(context_repo: str, model: str = "gpt-4.1-mini") -> str | None:
        """Check if distillation should run (10+ new signals since last).
        If yes, run distillation agent, save rules, return summary string.
        If no, return None."""

feedback.jsonl records use this schema (one JSON object per line):

    {"ts": "ISO8601", "type": "keep|discard|recover|accepted_digest",
     "tweet_id": "...", "score": 8, "classification": "adopt",
     "digest_run_id": "uuid", "context_repo": "~/Code/xxcli",
     "items_shown": ["id1", "id2"]}

The `items_shown` field is only present for `accepted_digest` type.

If feedback.jsonl is corrupt or missing, treat as empty. Recreate on next write.

Verification: `python -c "from xxcli.feedback import log_signal; log_signal('keep', '123', 8, 'adopt', 'test-run', '~/Code/xxcli')"` should create/append to `~/.xxcli/feedback.jsonl`.

### Milestone 5: Setup Wizard

Create `src/xxcli/onboarding.py`. This is the interactive setup experience.

    import click
    from pathlib import Path
    from datetime import datetime, timezone

    def run_setup_wizard(console) -> dict:
        """Full setup wizard. Returns config dict with credentials, repo, calibration results."""

The wizard has 4 phases, run sequentially:

Phase 0 — Credentials. Check if credentials exist (env vars or config). If all present, skip. Otherwise:
1. Print "Welcome to xx digest." and explain what's needed.
2. Twitter credentials: print the URL (`https://developer.twitter.com/en/portal/dashboard`), prompt for each of the 4 tokens using `click.prompt()` with `hide_input=True`. After all 4 collected, validate by calling `get_me()` from client.py. If valid, print green checkmark. If invalid, print error and reprompt.
3. OpenAI key: print URL (`https://platform.openai.com/api-keys`), prompt for key with `hide_input=True`. Validate with `check_openai_key()` from llm.py. If valid, print green checkmark. If invalid, reprompt.
4. Save all credentials to config.yaml.
5. Record `tthw.setup_started` timestamp.

Phase 1 — Pick repo. Scan these directories for git repos (macOS): `~/Code/`, `~/Projects/`, `~/Developer/`, `~/repos/`, `~/src/`, and the current working directory. Depth: 1 level (direct children with `.git/` directory). Present a numbered list. User picks one or enters a custom path. Save as `default_repo` in config.yaml. If no repos found, prompt for manual path entry.

Phase 2 — Scan for project docs. In the selected repo, check for well-known files: README.md, CLAUDE.md, TODO.md, ARCHITECTURE.md, PRODUCT-SENSE.md. Present what was found: "I found these files — use for context? [Y/n]". Save the list of confirmed context files in config.yaml.

Phase 3 — Calibration. Pull real tweets using `get_home_timeline()`. Walk through 10-15 tweets one by one. For each tweet, show the author, text, and prompt: "Is this useful? [U]seful / [M]aybe / [S]kip / [N]oise". On the first "Useful" response, print the aha moment: "Got it. Prioritizing [inferred_topic] for [repo_name]." Save calibration responses as initial feedback signals in feedback.jsonl.

After Phase 3, record `tthw.setup_completed` timestamp.

Return the complete config dict.

Verification: `xx setup` should launch the wizard interactively.

### Milestone 6: CLI Wiring and Formatting

Modify `src/xxcli/cli.py` to add four new commands: `digest`, `setup`, `why`, `signal`.

The `digest` command:

    @main.command()
    @click.option("-n", "--count", default=5, help="Max digest items.", show_default=True)
    @click.option("--repo", default=None, help="Git repo for work context.")
    @click.option("--since", default="24h", help="Time window (e.g., 24h, 3d, 1w).", show_default=True)
    @click.option("--debug", is_flag=True, help="Show full LLM reasoning and timing.")
    @click.option("--json", "json_output", is_flag=True, help="Output as JSON.")
    @click.option("--sample", is_flag=True, help="Use eval data instead of live API.")
    def digest(count, repo, since, debug, json_output, sample):

Flow:
1. Resolve credentials (env > config > trigger wizard).
2. Check if distillation should run (maybe_distill from feedback.py). If yes, show spinner "Evolving preferences..." then summary.
3. If `--sample`: load sample tweets. Else: pull timeline with `get_home_timeline()`.
4. Resolve repo path (--repo flag > config default_repo > cwd). Build work context.
5. Load preference rules or few-shot examples from feedback.py.
6. Run digest pipeline (digest.py).
7. Save last_digest.json for `xx why`.
8. Update streak.
9. Render output: if json_output or not console.is_terminal, print JSON. Else print Rich output.
10. If console.is_terminal and not json_output: prompt "See filtered items? [y/N]". If yes, show discarded items with recover option. Log feedback.

Exit codes: wrap the entire command in try/except. Catch config errors (sys.exit(1)), API errors (sys.exit(2)), LLM errors (sys.exit(3)).

The `setup` command:

    @main.command()
    def setup():
        """Run the setup wizard."""
        run_setup_wizard(console)

The `why` command:

    @main.command()
    @click.argument("tweet_id_or_url")
    def why(tweet_id_or_url):
        """Show why a tweet was scored the way it was."""

Reads from `~/.xxcli/last_digest.json`. Displays: tweet text, author, score, classification, explanation, matched work context, current preference rules. Uses `parse_tweet_id()` (which now strips `id:` prefix).

The `signal` command:

    @main.command()
    @click.argument("text")
    def signal(text):
        """Manually inject a preference signal."""

Logs a manual signal to feedback.jsonl with type "manual_signal" and the text as the topic.

Modify `src/xxcli/format.py` to add:

- `print_digest(items, meta, console)` — Rich-formatted digest output. Header: `[bold]xx digest[/bold] [dim]—[/dim] [bold]{count}[/bold] signals`. Subheader: `{pct}% of your timeline was noise.` Context line. Then numbered items with ADOPT/AVOID/COPY tags (green/red/cyan bold), author line, tweet text (2-space indent), Why line (dim label + explanation, 2-space indent), tweet ID (dim, 2-space indent). Footer: `[dim]Run xx like <id> or xx reply <id> "text" to interact.[/dim]` Streak counter if > 1 day.
- `print_digest_json(items, meta)` — prints JSON to stdout. Schema: `{"items": [...], "meta": {...}}`.
- `print_debug_info(debug_info, console)` — renders debug output in dim above the digest.
- `print_empty_digest(meta, console)` — warm empty state for 0 signals.
- `print_filtered_items(items, console)` — shows discarded items for the feedback loop.
- `_format_author(name, username, time_str)` — extracted from print_tweet, shared between feed and digest.

Modify `src/xxcli/client.py`:
- Update `parse_tweet_id()` to strip `id:` prefix: if input starts with "id:", strip it before the URL check.
- Add `referenced_tweets` to the `expansions` list in `get_home_timeline()` and add `"referenced_tweets.id"` to tweet_fields for full tweet text on RTs/quotes.
- Add `get_client_from_config()` that reads credentials from config.yaml if env vars are not set. Falls back to `_get_credentials()` env var path.

Update `src/xxcli/__init__.py` version to `"0.2.0"`.

Verification: `xx digest --sample --debug` should render a complete digest from eval data with debug output. `xx digest --json --sample` should print valid JSON.

### Milestone 7: Agent Interface

Create `.claude/skills/xx-digest/SKILL.md`:

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

    - Twitter API credentials (Free tier)
    - OpenAI API key (from ChatGPT/Codex subscription)
    - Run `xx setup` first, or credentials via env vars

Ensure all error paths in cli.py output JSON to stderr when `--json` is active, using the format: `{"error": {"code": "...", "message": "...", "fix": "..."}}`.

Verification: an AI agent should be able to read the SKILL.md, run `xx digest --json`, and parse the output.

### Milestone 8: Tests, Eval, README, Version Bump

Create `tests/__init__.py` (empty).

Create `tests/test_context.py`:
- Test `build_work_context()` on the xxcli repo itself (should return non-empty fields).
- Test on a non-git directory (should return empty context gracefully).
- Test `format_context_for_prompt()` produces a non-empty string.

Create `tests/test_digest.py`:
- Test `parse_since()` with "24h", "3d", "1w", ISO date, and invalid input.
- Test `load_sample_tweets()` returns 19 tweets.
- Test score filtering (items >= 7 kept, others dropped).
- Test sort order (descending by score).
- Test truncation to count.

Create `tests/test_config.py`:
- Test `load_config()` with missing file returns empty dict.
- Test `save_config()` + `load_config()` roundtrip.
- Test credential resolution order (env > config).

Create `tests/test_format.py`:
- Test `print_digest()` output contains expected Rich markup.
- Test `print_digest_json()` produces valid JSON matching the schema.
- Test empty digest output.

Create `tests/test_feedback.py`:
- Test `log_signal()` appends to feedback.jsonl.
- Test `get_signal_count()` counts correctly.
- Test corrupt/missing file handling.

Create `evals/eval_digest.py`:
- Load the 19 labeled tweets from `evals/xx-feed-20260327.md`.
- Run the scoring agent against them.
- Compare agent verdicts against hand labels.
- Print precision/recall report.

Create `evals/labeled_tweets.json` — structured version of the 19 hand-labeled tweets for programmatic eval use.

Update `README.md`:
- Add a "Digest" section after the Usage table with: demo output mock, `xx setup` quick start, flag reference (--repo, --since, --count, --debug, --json, --sample), one paragraph on "How it works."
- Add a privacy note: "xx digest sends your git context (commit messages, README excerpt, dependency list) to the OpenAI API for relevance scoring. Review OpenAI's data usage policies."

Add `pytest` to dev dependencies in pyproject.toml (optional dependencies or a `[project.optional-dependencies]` dev section).

Bump version in `src/xxcli/__init__.py` to `"0.2.0"` (if not done in Milestone 6).

Verification: `python -m pytest tests/ -v` should pass all tests. `xx digest --sample --debug` should produce a complete digest. `xx digest --json --sample | python -m json.tool` should produce valid, pretty-printed JSON.

## Concrete Steps

All commands assume working directory is the repository root: `/Users/macbook/Code/xxcli`.

After Milestone 1:

    pip install -e .
    python -c "from xxcli.config import load_config; print(load_config())"
    python -c "from xxcli.context import build_work_context; ctx = build_work_context('.'); print(ctx.repo_name, ctx.branch)"
    python -c "from xxcli.theme import xx_theme; print(xx_theme.styles)"

After Milestone 2:

    pip install -e .
    python -c "from xxcli.llm import DigestResult; print(DigestResult(items=[]))"

After Milestone 6:

    xx digest --sample --debug
    xx digest --json --sample | python -m json.tool
    xx setup  # (interactive, tests the wizard)
    xx --version  # should show 0.2.0

After Milestone 8:

    python -m pytest tests/ -v
    python evals/eval_digest.py

## Validation and Acceptance

The implementation is complete when all of the following are true:

1. `xx digest` from a git repo with valid credentials produces a Rich-formatted digest with numbered items, ADOPT/AVOID/COPY tags, explanations, and a streak counter.
2. `xx digest --json` produces valid JSON matching the schema in the SKILL.md.
3. `xx digest --sample --debug` runs without real API calls (except OpenAI) and shows full debug output.
4. `xx setup` walks through credential validation, repo selection, and tweet calibration in one flow.
5. `xx why <id>` shows the scoring explanation for a digest item.
6. `xx signal 'topic'` logs a manual preference.
7. Missing API keys produce clear error messages with the fix formula (what + why + fix).
8. All tests in `tests/` pass.
9. `.claude/skills/xx-digest/SKILL.md` exists with the correct schema documentation.
10. piping (`xx digest | cat`) produces plain text without ANSI codes or spinners; `xx digest --json | jq .` produces valid JSON.

## Idempotence and Recovery

All milestones are additive. New files can be created in any order within a milestone. If a milestone fails partway through, the working tree contains partial but non-breaking changes (new files that aren't imported yet).

`~/.xxcli/` state files (config.yaml, feedback.jsonl, preference_rules.json, last_digest.json) are all independently recoverable. If any are corrupt or deleted, the system recreates them on next use. feedback.jsonl is append-only.

`pip install -e .` is idempotent and safe to re-run at any point.

## Refinement Pass

(Populated after implementation milestones are complete.)

### Ontology alignment

(Pending.)

### Design fidelity

(Pending.) Check all terminal output against DESIGN.md and DESIGN-PREVIEW.html.

### Product behavior

(Pending.) Test the feedback loop end-to-end: run digest, review filtered items, recover one, run again, verify the next digest reflects the feedback.

### Tangential discoveries

(Populated during implementation.)

## Artifacts and Notes

Source design documents (for deep context, not required for implementation):
- `docs/designs/xx-digest-ceo-plan.md` — CEO plan with vision, scope decisions, data schemas, sub-agent architecture
- `docs/designs/xx-digest-design.md` — Full feature spec from office-hours (prompt template, output format, interaction states)
- `docs/eng-review-digest.md` — Eng review with build order, data flow diagram, test strategy
- `docs/designs/xx-digest-dx-review.md` — DX review with agent path, credential wizard, --json decisions
- `DESIGN.md` — Terminal design system (colors, typography, interaction patterns)

## Interfaces and Dependencies

Runtime dependencies (add to pyproject.toml):
- `openai-agents>=0.1` — OpenAI Agents SDK for structured LLM output
- `pyyaml>=6.0` — YAML config file parsing

Dev dependencies:
- `pytest>=7.0` — test runner

New modules and their key exports:

    src/xxcli/theme.py      → xx_theme: Theme
    src/xxcli/config.py     → load_config, save_config, get_credentials, get_default_repo, get_streak, update_streak
    src/xxcli/context.py    → WorkContext, build_work_context, format_context_for_prompt
    src/xxcli/llm.py        → DigestItem, DigestResult, PreferenceRules, score_tweets, distill_preferences, check_openai_key
    src/xxcli/digest.py     → parse_since, run_digest, load_sample_tweets, save_last_digest, load_last_digest
    src/xxcli/feedback.py   → log_signal, get_signal_count, load_recent_signals, load_preference_rules, save_preference_rules, get_few_shot_examples, maybe_distill
    src/xxcli/onboarding.py → run_setup_wizard

Modified modules:
    src/xxcli/cli.py        → +digest, +setup, +why, +signal commands
    src/xxcli/client.py     → parse_tweet_id (id: prefix), get_home_timeline (referenced_tweets), get_client_from_config
    src/xxcli/format.py     → +print_digest, +print_digest_json, +print_debug_info, +print_empty_digest, +print_filtered_items, +_format_author; Console uses xx_theme
    src/xxcli/__init__.py   → version "0.2.0"
    pyproject.toml          → +openai-agents, +pyyaml

New non-code files:
    .claude/skills/xx-digest/SKILL.md
    evals/labeled_tweets.json
    evals/eval_digest.py
    tests/__init__.py
    tests/test_context.py
    tests/test_digest.py
    tests/test_config.py
    tests/test_format.py
    tests/test_feedback.py
