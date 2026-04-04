# Eng Review: xx digest — Context-Aware Feed Digest

**Branch:** main
**Design doc:** `~/.gstack/projects/declankra-xxcli/macbook-main-design-20260327-140704.md`
**Status:** ENG CLEARED

## Context

xxcli v0.1 is a working CLI (feed, post, reply, like, me) built with Python/Click/Tweepy/Rich. The next feature is `xx digest` — a context-aware feed digest that uses the OpenAI Agents SDK to score tweets against the user's current work (git log, README, deps). The design doc was produced by /office-hours on 2026-03-27 and approved.

## Step 0: Scope Challenge

### What existing code solves sub-problems?

| Sub-problem | Existing code | Reusable? |
|---|---|---|
| Pull home timeline | `client.py:get_home_timeline()` | YES — returns tweets + users dict |
| Rich terminal output | `format.py` (console, print_tweet, _metrics_line, _relative_time) | YES — extend with print_digest() |
| Twitter API error handling | `cli.py:_handle_api_error()` | YES — same pattern |
| Click command structure | `cli.py` (@main.command pattern) | YES — add digest command |
| Tweet ID parsing | `client.py:parse_tweet_id()` | YES — for follow-up actions in output |

### Minimum set of changes

3 new files + 3 modified files = 6 total files touched.

**New:**
- `src/xxcli/context.py` — work context builder (git log, README, deps)
- `src/xxcli/digest.py` — digest orchestration (pull tweets, filter by time, call LLM, format results)
- `src/xxcli/llm.py` — OpenAI Agents SDK agent definition (prompt, model, structured output)

**Modified:**
- `src/xxcli/cli.py` — add `xx digest` command
- `src/xxcli/format.py` — add `print_digest()` for Rich-formatted digest output
- `pyproject.toml` — add `openai-agents` dependency

### Complexity check

6 files < 8 threshold. 3 new modules is at the edge of the 2-module threshold, but each has a distinct, justified responsibility:
- context.py = reads the local filesystem (git, files)
- digest.py = orchestration layer (input → LLM → output)
- llm.py = LLM-specific code (agent, prompt, model)

This separation is clean. No scope reduction needed.

### Deferrable work

- `--schedule` flag for cron management — explicitly deferred in design.
- Multi-repo context — explicitly deferred.
- Digest history / seen-items cache — explicitly deferred.
- Tweet deduplication before LLM call — deferred to TODOS.md.

### What already exists

- `get_home_timeline()` already returns the data the digest needs. No new Twitter API work required.
- `format.py` has all the building blocks (Rich console, relative time, metrics formatting). Just needs a new `print_digest()` function.
- The eval data at `evals/xx-feed-20260327.md` provides ground truth for prompt iteration.

### Distribution check

Already handled — ships as part of existing `pip install -e .` package. `pyproject.toml` just needs the new dependency.

---

## Section 1: Architecture Review — 4 issues, all resolved

1. **llm.py vs digest.py separation** → KEEP SEPARATE. Clean for testing, future multi-agent.
2. **Subprocess security in context.py** → LIST-FORM subprocess. `subprocess.run(['git', 'log', ...], cwd=path)`. No shell=True.
3. **Pydantic structured output** → USE PYDANTIC. Define `DigestItem` and `DigestResult` as Pydantic models. SDK handles validation. Eliminates JSON parsing error path entirely.
4. **Rate limit message for digest** → BETTER ERROR MESSAGE. When digest hits 429, mention shared quota with feed.

## Section 2: Code Quality Review — 2 issues, all resolved

5. **OPENAI_API_KEY check** → IN llm.py. Validate at agent creation time, fail early with clear message.
6. **_parse_since() location** → PRIVATE IN digest.py. No new utils.py file for one function.

## Section 3: Test Review

**Current state: zero tests, zero test infrastructure.**

Test strategy:
- **Stand up pytest** — add `pytest` to dev deps, create `tests/` directory
- **Unit tests** for pure logic: context.py parsing, digest.py time filtering/sorting, format.py output
- **Eval** against 19 hand-labeled tweets (evals/xx-feed-20260327.md) for LLM quality validation
- **Mock Twitter API + OpenAI API** for integration tests of the full pipeline

Test files to create:
- `tests/test_context.py` — git log parsing, README reading, dep extraction, missing files, non-git path
- `tests/test_digest.py` — _parse_since() all formats, tweet time filtering, score filtering, sorting, truncation
- `tests/test_format.py` — print_digest() output, empty digest, tag rendering
- `evals/test_digest_eval.py` — run digest scoring against labeled tweets, compare verdicts

## Section 4: Performance Review — 1 issue, resolved

8. **--verbose timing flag** → ADD IT. Print timing breakdown (API: Xs, Context: Xs, LLM: Xs) when --verbose passed.

---

## NOT in scope

| Item | Rationale |
|---|---|
| `--schedule` cron management | Cron is already cron-friendly via `crontab -e`. CLI integration deferred. |
| Multi-repo context | One repo at a time. Multiple repos = multiple runs. |
| Digest history / dedup cache | Keep stateless in v1. Add cache if repeats are a problem. |
| `xx ask` follow-up Q&A | Approach C from design doc. Separate feature. |
| PyPI publishing | Currently `git clone + pip install -e .`. Publish when stable. |
| Web UI / email delivery | CLI-native only. The terminal IS the product. |

## What already exists

| Component | Location | Reuse strategy |
|---|---|---|
| Home timeline API | `client.py:get_home_timeline()` | Call directly from digest command |
| Rich console + formatting | `format.py:console, _relative_time, _metrics_line` | Extend with print_digest() |
| Error handling pattern | `cli.py:_handle_api_error()` | Same try/except pattern for digest |
| Click command structure | `cli.py:@main.command()` | Add digest command identically |
| Tweet ID display | `format.py:print_tweet()` | Reference pattern for digest item display |
| Eval ground truth | `evals/xx-feed-20260327.md` | 19 labeled tweets for prompt quality validation |

## Failure modes

| Codepath | Failure | Test? | Error handling? | User sees? |
|---|---|---|---|---|
| Twitter API call | 429 rate limit | Will test | Yes (_handle_api_error) | Clear error + quota hint |
| Twitter API call | Network timeout | Not tested | Yes (Tweepy exception) | Generic error |
| OPENAI_API_KEY missing | No key in env | Will test | Yes (early check in llm.py) | Clear setup instructions |
| LLM call | 429 / 500 / timeout | Will test | Yes (1 retry with backoff) | Error + suggestion |
| LLM response | Invalid Pydantic output | N/A with structured output | SDK handles validation | SDK raises, caught by retry |
| context.py git calls | Not a git repo | Will test | Yes (warning, proceed without context) | Warning message |
| context.py git calls | subprocess error | Will test | Yes (catch CalledProcessError) | Falls back to no-context |
| _parse_since | Invalid format | Will test | Yes (raise Click error) | Clear format guidance |
| Zero tweets | Empty timeline | Will test | Yes (skip LLM, print message) | "No tweets found" message |
| All low-scored | No items >= 7 | Will test | Yes (show empty digest) | Header shows 0 surfaced |

**Critical gaps: 0.** All failure modes have either planned tests or built-in error handling (or both). The Pydantic structured output decision eliminated the "malformed JSON" failure mode entirely.

## Data flow diagram

```
User runs: xx digest --repo ~/Code/project --since 24h --count 5
                │
                v
    ┌──────────────────────┐
    │   cli.py:digest()    │  Parse CLI args, resolve repo path
    │                      │  Validate OPENAI_API_KEY (early fail)
    └──────────┬───────────┘
               │
       ┌───────┴────────┐
       │                │
       v                v
┌─────────────┐  ┌──────────────┐
│ client.py   │  │ context.py   │
│ get_home_   │  │ build_work_  │
│ timeline()  │  │ context()    │
│ (100 tweets)│  │ (git, README,│
└──────┬──────┘  │  deps, files)│
       │         └──────┬───────┘
       │                │
       v                v
    ┌──────────────────────┐
    │   digest.py          │
    │   _parse_since()     │  Filter tweets by created_at
    │   run_digest()       │  Build prompt: tweets + context
    │                      │  Call LLM agent
    └──────────┬───────────┘
               │
               v
    ┌──────────────────────┐
    │   llm.py             │
    │   DigestAgent        │  OpenAI Agents SDK
    │   (gpt-5.4-mini)     │  Pydantic structured output:
    │                      │  DigestItem(tweet_id, score,
    │                      │    classification, explanation)
    └──────────┬───────────┘
               │
               v
    ┌──────────────────────┐
    │   digest.py          │  Filter score >= 7
    │   (post-processing)  │  Sort by score desc
    │                      │  Truncate to --count
    └──────────┬───────────┘
               │
               v
    ┌──────────────────────┐
    │   format.py          │  Rich terminal output:
    │   print_digest()     │  Header: "3 items / 44 ignored"
    │                      │  Items: [ADOPT] @user · text
    │                      │         Why: explanation
    └──────────────────────┘
```

## Worktree parallelization strategy

| Step | Modules touched | Depends on |
|---|---|---|
| A: context.py + tests | src/xxcli/context.py, tests/ | — |
| B: llm.py + Pydantic models | src/xxcli/llm.py, pyproject.toml | — |
| C: digest.py + tests | src/xxcli/digest.py, tests/ | A (needs context types), B (needs agent) |
| D: CLI + format + wiring | src/xxcli/cli.py, format.py | A, B, C |
| E: eval against labeled data | evals/ | B, C (needs working agent + digest engine) |

**Parallel lanes:**
- Lane 1: A (context.py) — independent, no deps
- Lane 2: B (llm.py) — independent, no deps
- Lane 3: C → D → E (sequential, depends on A+B)

**Execution:** Launch A + B in parallel. When both complete, run C → D → E sequentially. 2 parallel lanes, 1 sequential chain.

**Conflict flags:** Lanes 1 and 2 both touch tests/ — minor merge conflict possible on test file organization. Lane 3 merges output of both.

## Outside Voice Findings (Codex)

Ran Codex plan review. 13 findings. 4 substantive tensions resolved with user:

1. **Privacy boundary** → Acknowledge in README. Note OpenAI API data usage controls.
2. **--since false precision** → Show 100-tweet cap in digest header stats.
3. **Config premature** → User chose to keep config in v1. Accepted.
4. **Work context signal quality** → Add `git diff --stat` + current branch to context.py. Sharp improvement from Codex.

Remaining findings already handled by design doc or explicitly deferred.

## Additions from review (beyond original design doc)

These items were added during the eng review, not in the original design:

1. **Pydantic structured output** — replaces raw JSON parsing. Eliminates malformed response error path.
2. **--verbose timing flag** — prints breakdown (API: Xs, Context: Xs, LLM: Xs).
3. **Rate limit message** — digest-specific hint about shared quota with feed.
4. **Config file support** — `~/.xxcli/config.yaml` with default_repo, default_since, default_count.
5. **Eval runner** — automated scoring against labeled tweets, precision/recall reporting.
6. **Full tweet text** — referenced_tweets expansion in get_home_timeline().
7. **git diff --stat + branch** — added to work context for better relevance signal.
8. **Header shows 100-tweet cap** — "Scanned: X of 100 max tweets"
9. **README privacy note** — repo context goes to OpenAI, note data usage controls.

## Implementation plan

### Build order (sequential, with parallel start for A+B)

**Step 1 (parallel):**
- A: `src/xxcli/context.py` — build_work_context(repo_path) → structured string
  - git log --oneline -20 (subprocess list-form, cwd=repo_path)
  - git diff --stat (uncommitted changes)
  - git branch --show-current
  - README.md first 200 lines
  - pyproject.toml / requirements.txt deps
  - Recently changed file paths
  - Graceful fallback: if not a git repo, return empty context + warning

- B: `src/xxcli/llm.py` — OpenAI Agents SDK agent
  - Pydantic models: DigestItem(tweet_id, relevance_score, classification, explanation), DigestResult(items: list[DigestItem])
  - Agent definition: gpt-5.4-mini, system prompt from design doc
  - OPENAI_API_KEY check at creation time
  - 1 retry with 3s backoff on API failure

**Step 2:**
- C: `src/xxcli/digest.py` — digest orchestration
  - _parse_since() — parse '24h', '3d', '1w', ISO date → datetime
  - run_digest(tweets, users, work_context, since, count, verbose) → list[DigestItem]
  - Client-side time filtering by created_at
  - Build prompt: tweets + context → agent call
  - Post-process: filter score >= 7, sort desc, truncate to count
  - Timing info if verbose

**Step 3:**
- D: Modified files
  - `src/xxcli/cli.py` — add digest command with --repo, --since, --count, --verbose
  - `src/xxcli/format.py` — add print_digest() with adopt/avoid/copy tags, header stats showing 100-tweet cap
  - `src/xxcli/client.py` — add referenced_tweets expansion to get_home_timeline()
  - `pyproject.toml` — add openai-agents, pyyaml deps, pytest dev dep

**Step 4:**
- E: Config + tests + eval
  - `src/xxcli/config.py` — load ~/.xxcli/config.yaml, return defaults if missing
  - `tests/test_context.py` — unit tests for context building
  - `tests/test_digest.py` — unit tests for _parse_since, time filtering, scoring
  - `tests/test_format.py` — unit tests for print_digest
  - `evals/eval_digest.py` — eval runner: labeled tweets → agent → precision/recall report
  - `evals/labeled_tweets.json` — structured version of evals/xx-feed-20260327.md

**Step 5:**
- F: Documentation
  - README.md — new usage section for digest, privacy note about repo context + OpenAI data controls
  - TODOS.md — add tweet deduplication as deferred item

### Files to create
- `src/xxcli/context.py`
- `src/xxcli/digest.py`
- `src/xxcli/llm.py`
- `src/xxcli/config.py`
- `tests/__init__.py`
- `tests/test_context.py`
- `tests/test_digest.py`
- `tests/test_format.py`
- `evals/eval_digest.py`
- `evals/labeled_tweets.json`

### Files to modify
- `src/xxcli/cli.py`
- `src/xxcli/client.py`
- `src/xxcli/format.py`
- `pyproject.toml`
- `README.md`
- `TODOS.md` (create if needed)

### Verification

1. **Unit tests:** `pytest tests/ -v` — all pass
2. **Manual smoke test:** `xx digest --repo . --since 24h --count 3 --verbose`
3. **Eval:** `python evals/eval_digest.py` — reports precision/recall vs labeled data
4. **Error paths:** Run without OPENAI_API_KEY set → clear error. Run with non-git --repo path → warning + runs without context.
5. **Edge cases:** Run with empty timeline, run when rate limited

## TODOS.md entries

### Dedup tweets before LLM call
**What:** Strip RTs of already-seen tweet IDs before passing to agent.
**Why:** Saves tokens, improves scoring quality. Eval data confirmed RTs of truncated content are mostly noise.
**Pros:** Better token efficiency, cleaner scoring input.
**Cons:** ~15 lines of code, minor complexity.
**Context:** Design doc Open Question #1. Home timeline can include RTs and quote tweets of the same content.
**Depends on:** digest.py must exist first.

## Completion Summary

- Step 0: Scope Challenge — scope accepted as-is, no reduction needed
- Architecture Review: 4 issues found, all resolved
- Code Quality Review: 2 issues found, all resolved
- Test Review: diagram produced, 27 gaps identified, test strategy agreed (pytest + eval)
- Performance Review: 1 issue found, resolved (--verbose timing flag)
- NOT in scope: written (6 items)
- What already exists: written (6 components reused)
- TODOS.md updates: 1 item deferred (dedup), 3 items pulled into v1 (eval runner, config, full tweet text)
- Failure modes: 0 critical gaps flagged
- Outside voice: ran (codex), 4 tensions resolved with user
- Parallelization: 2 lanes parallel start, then sequential chain
- Lake Score: 9/10 recommendations chose complete option (user pulled 3 items from TODO into v1 build)

## GSTACK REVIEW REPORT

| Review | Trigger | Why | Runs | Status | Findings |
|--------|---------|-----|------|--------|----------|
| CEO Review | `/plan-ceo-review` | Scope & strategy | 0 | — | — |
| Codex Review | `/codex review` | Independent 2nd opinion | 0 | — | — |
| Eng Review | `/plan-eng-review` | Architecture & tests (required) | 1 | CLEAR | 8 issues, 0 critical gaps |
| Design Review | `/plan-design-review` | UI/UX gaps | 0 | — | — |

- **OUTSIDE VOICE:** Codex plan review ran. 13 findings, 4 substantive tensions resolved (privacy note, header cap display, config kept, context quality improved).
- **UNRESOLVED:** 0
- **VERDICT:** ENG CLEARED — ready to implement.
