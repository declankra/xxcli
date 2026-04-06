# Add Codex/ChatGPT Subscription Backend To xx Digest

This ExecPlan is a living document. The sections Progress, Surprises & Discoveries, Decision Log, Outcomes & Retrospective, and Refinement Pass must be kept up to date as work proceeds. This document must be maintained in accordance with `.agents/PLANS.md` at the repository root.

## Purpose / Big Picture

After this change, a developer can run `xx setup`, choose either `ChatGPT subscription via Codex` or `OpenAI API key`, and then use `xx digest` without needing `OPENAI_API_KEY` when they already have a ChatGPT-backed Codex login. The digest feature remains agent-friendly and scriptable, but the product is no longer forced into API billing for human users who already pay for ChatGPT and use Codex CLI.

To see it working after implementation, run `codex login status` and confirm it reports a ChatGPT-backed login, then run `xx setup` and choose the Codex backend. After setup, `xx digest --backend codex --sample --debug` should score the sample timeline without any `OPENAI_API_KEY` set. `xx digest --backend api --sample --json` should still work when an API key is available. The two backends must produce the same digest JSON schema and the same exit-code contract.

## Progress

- [x] Researched the current repo state, Codex CLI capabilities, and the OpenClaw product pattern. 2026-04-06 10:36 CDT
- [ ] Milestone 1: Backend abstraction and config schema
- [ ] Milestone 2: Codex backend implementation
- [ ] Milestone 3: Setup wizard and auth UX
- [ ] Milestone 4: CLI wiring, errors, and output parity
- [ ] Milestone 5: Tests, docs, and migration cleanup

## Surprises & Discoveries

- Observation: The local `codex` CLI already exposes exactly the primitives this feature needs: `codex exec`, `codex login`, and `codex login status`.
  Evidence: `codex --help` lists `exec` and `login`, and `codex login --help` documents `status`.

- Observation: On this machine, `codex login status` exits successfully and prints `Logged in using ChatGPT`.
  Evidence: Direct command output from `/Users/macbook/Code/xxcli`.

- Observation: OpenClaw’s public docs do not describe a generic “use ChatGPT subscription for arbitrary third-party API calls” mechanism. They describe either direct API-key mode, reusing Codex auth, or a Codex-specific OAuth flow.
  Evidence: Product research before drafting this plan. This matters because `xx` should not assume a public ChatGPT-web-login API exists for arbitrary Python model clients.

## Decision Log

- Decision: Add a second scoring backend instead of replacing the existing API backend.
  Rationale: Human users want ChatGPT-subscription support, but agent and CI users still benefit from a plain API-key path. The product should support both.
  Date/Author: 2026-04-06 / Codex

- Decision: Use the local Codex CLI as the source of truth for ChatGPT-subscription auth instead of implementing custom OAuth and token storage in `xx`.
  Rationale: Codex CLI is the documented first-party product that supports `Sign in with ChatGPT`. Reusing it is lower-risk, requires less secret handling, and matches how OpenClaw treats Codex-backed auth.
  Date/Author: 2026-04-06 / Codex

- Decision: `xx` will never store ChatGPT or Codex auth tokens in `~/.xxcli/config.yaml`.
  Rationale: Codex should own its own auth state. `xx` should store only backend selection and related preferences, not first-party session material.
  Date/Author: 2026-04-06 / Codex

- Decision: The digest feature, not the whole CLI, is in scope for Codex backend support.
  Rationale: `feed`, `post`, `reply`, `like`, and `me` are X API operations and do not need model-provider abstraction. The model backend only affects digest scoring and preference distillation.
  Date/Author: 2026-04-06 / Codex

- Decision: Preserve the existing JSON schema and exit codes across both backends.
  Rationale: Agent consumers should not care whether the digest was scored by the API backend or the Codex backend.
  Date/Author: 2026-04-06 / Codex

## Outcomes & Retrospective

Pending implementation.

## Context and Orientation

This repo already contains a completed first version of `xx digest`, described in `docs/exec-plans/active/xx-digest-v1.md`. That implementation is API-key-only on the model side. The current code paths to understand before editing are:

- `src/xxcli/cli.py`
  The `digest` command currently calls `_ensure_digest_credentials()`, which requires `OPENAI_API_KEY` for all digest runs and requires X credentials only for live timeline pulls. It then calls `run_digest()` and renders either Rich output or compact JSON.

- `src/xxcli/llm.py`
  This file currently contains the only model backend. It uses the OpenAI Agents SDK, requires `OPENAI_API_KEY`, exposes `score_tweets()`, `distill_preferences()`, and `check_openai_key()`, and captures some debug metadata.

- `src/xxcli/onboarding.py`
  The setup wizard currently asks for X credentials and an OpenAI API key. It has no concept of backend choice.

- `src/xxcli/config.py`
  The config schema currently assumes a single credential source for the model side: `credentials.openai_api_key`.

- `src/xxcli/digest.py`
  The digest engine is already backend-agnostic enough that it can continue accepting “score these tweets” and “distill these preferences” functions from a dispatcher. This file should not gain Codex-specific shell logic.

- `src/xxcli/format.py`
  The user-facing and JSON-facing digest output contracts are already implemented here. The new backend must fit into these outputs without changing their shape.

Current product behavior:

- `xx digest --sample --debug` works today, but only when `OPENAI_API_KEY` is available.
- `xx digest --json` returns a compact schema with:

      {
        "items": [
          {
            "tweet_id": "...",
            "relevance_score": 8,
            "classification": "adopt",
            "author": "@username",
            "text": "...",
            "explanation": "..."
          }
        ],
        "meta": {
          "scanned": 14,
          "filtered": 14,
          "repo": "xxcli",
          "streak_days": 1,
          "since": "24h"
        }
      }

Desired product behavior after this plan:

- `xx setup` begins by asking how the user wants `xx digest` to talk to OpenAI:
  - `ChatGPT subscription via Codex`
  - `OpenAI API key`

- If the user chooses the Codex path:
  - `xx` detects whether `codex` is installed.
  - `xx` runs `codex login status`.
  - If status is already good, setup continues without asking for an API key.
  - If not, setup offers to run `codex login`, which is the first-party browser-based sign-in path.

- If the user chooses the API path:
  - existing OpenAI API key behavior remains intact.

- `xx digest --backend codex` and `xx digest --backend api` are both supported. If no `--backend` flag is provided, the configured backend is used. Existing API-key-based users should continue working without reconfiguration.

The crucial product difference is that `xx` stops being a pure OpenAI API client. It becomes a dual-backend product:

- API mode is best for CI, automation, and environments where a raw API credential is preferable.
- Codex mode is best for individual users who already have a ChatGPT/Codex login and want subscription-backed usage.

This is the same product shape OpenClaw exposes publicly: it supports direct API-key mode and Codex-backed subscription mode as separate model-provider options rather than pretending they are the same auth surface.

## Plan of Work

### Milestone 1: Backend abstraction and config schema

The first milestone is to stop hardcoding “OpenAI API key” as the only model path. Introduce a model-backend abstraction in `src/xxcli/llm.py` or in a small adjacent module such as `src/xxcli/model_backends.py`.

At the end of this milestone, there must be a small typed configuration object that describes the selected backend. Keep it boring and explicit. The config file should gain a section like:

    model_backend:
      provider: "api" | "codex"
      model: "gpt-4.1-mini"
      codex_profile: null

Do not store ChatGPT tokens or Codex credentials in this file. The purpose of this schema is only to remember which backend the user selected and which model/profile overrides should be used.

Refactor `llm.py` so that:

- `DigestItem`, `DigestResult`, `FewShotExample`, and `PreferenceRules` remain the shared contract types.
- Public entry points become backend-dispatching functions such as:

      async def score_tweets(..., backend_config: ModelBackendConfig, ...) -> DigestResult
      async def distill_preferences(..., backend_config: ModelBackendConfig, ...) -> PreferenceRules
      def check_backend_ready(backend_config: ModelBackendConfig) -> BackendStatus

- The current OpenAI Agents SDK implementation is preserved as the API backend implementation, ideally moved behind a named helper such as `_score_with_api_backend()`.

Update `src/xxcli/config.py` to load and save this new `model_backend` section. Add migration behavior:

- If existing config has `credentials.openai_api_key` and no `model_backend`, infer `provider: "api"`.
- If config has neither `model_backend` nor `openai_api_key`, leave backend unset so setup can decide.

Verification for this milestone:

- Run from repo root:

      PYTHONPATH=src python3 - <<'PY'
      from xxcli.config import load_config
      from xxcli.llm import DigestResult
      print(DigestResult(items=[]).model_dump_json())
      print(load_config().get("model_backend"))
      PY

- Confirm the model contract types still import and that old configs do not crash when read.

### Milestone 2: Codex backend implementation

The second milestone adds the new backend without changing CLI behavior yet.

Create a Codex-backed scoring implementation in a new file such as `src/xxcli/codex_backend.py`. This module is responsible for:

- Detecting whether `codex` is installed by running `codex --version`.
- Detecting whether Codex is authenticated by running `codex login status`.
- Running non-interactive scoring with `codex exec`.

Use the real local CLI behavior already observed in research:

- `codex exec` exists and supports non-interactive prompts.
- `codex exec --output-schema <FILE>` can be used so the final response shape matches the same Pydantic/JSON contract the API backend uses.
- `codex login status` returns success and human-readable status text such as `Logged in using ChatGPT`.

The Codex backend should not scrape `~/.codex/auth.json` directly as its primary mechanism. It may inspect it only if the CLI offers no structured way to determine auth status, but the preferred integration is to ask the Codex CLI itself.

Implementation details:

- Write one JSON Schema file or generate one at runtime from the Pydantic models so `codex exec --output-schema` can enforce the final output shape.
- The prompt content should remain semantically identical to the current API backend prompts so the product logic does not fork.
- Capture debug information:
  - command line used (without secrets)
  - runtime duration
  - raw last message from Codex
  - stderr if the subprocess fails

Use `subprocess.run()` with list-form arguments and no `shell=True`.

Error mapping must be explicit:

- Codex not installed -> config error
- Codex installed but not logged in -> config error with a fix message that tells the user to run `xx setup` or `codex login`
- Codex command execution failure -> LLM error

Verification for this milestone:

- Run:

      codex --version
      codex login status

- Then, from repo root, run a small backend smoke test command or Python snippet that dispatches `score_tweets(..., backend_config=codex)` against one or two sample tweets and prints the structured result.

### Milestone 3: Setup wizard and auth UX

The third milestone makes backend choice a first-class product decision in onboarding.

Update `src/xxcli/onboarding.py` so setup starts with:

1. “How do you want xx digest to talk to OpenAI?”
2. Option A: `ChatGPT subscription via Codex`
3. Option B: `OpenAI API key`

For the Codex path:

- Check `codex --version`.
- If missing, show a clear install hint and allow the user to choose the API backend instead or abort.
- Run `codex login status`.
- If authenticated, print a success message and continue.
- If not authenticated, ask whether to launch login now.
- When the user agrees, run `codex login` attached to the user’s terminal, wait for it to exit, then re-run `codex login status`.

For the API path:

- Keep the current `OpenAI API key` prompt and validation flow.

For both paths:

- Continue with the existing repo-pick and calibration phases.
- Save the chosen backend under `model_backend`.
- Save `credentials.openai_api_key` only for the API path.

Never make the wizard ask for both ChatGPT/Codex auth and an API key during the same happy path.

Verification for this milestone:

- `xx setup` should present the backend choice.
- On a machine where `codex login status` says `Logged in using ChatGPT`, choosing Codex should skip the API key prompt entirely.
- Choosing API should still prompt for and validate an OpenAI API key.

### Milestone 4: CLI wiring, errors, and output parity

The fourth milestone makes `xx digest` actually use the chosen backend.

Update `src/xxcli/cli.py`:

- Add `--backend` to `xx digest` with values `api` or `codex`.
- Resolution order:
  1. explicit `--backend`
  2. `config.model_backend.provider`
  3. migration fallback: if `OPENAI_API_KEY` or stored API key exists, use `api`
  4. otherwise require setup

- Update `_ensure_digest_credentials()` into a backend-aware readiness check:
  - `api` requires `OPENAI_API_KEY` or stored API key
  - `codex` requires `codex --version` and `codex login status`

- Pass the resolved backend config into `run_digest()` and the feedback distillation path.

- Keep `xx digest --json` compact and backend-agnostic.
- Ensure JSON errors on stderr still use:

      {"error": {"code": "...", "message": "...", "fix": "..."}}

Suggested new error codes:

- `config_error`
- `backend_unavailable`
- `codex_not_installed`
- `codex_not_logged_in`
- `llm_error`

Do not change the numeric exit-code contract unless absolutely necessary:

- 0 success
- 1 config/backend readiness error
- 2 X API error
- 3 model backend execution error

Verification for this milestone:

- `env -u OPENAI_API_KEY xx digest --backend codex --sample --json` succeeds when `codex login status` is healthy.
- `env -u OPENAI_API_KEY xx digest --backend api --sample --json` fails with JSON stderr and exit code 1.
- `xx digest --backend codex --sample --debug` renders the same human-facing output layout as the API backend.

### Milestone 5: Tests, docs, and migration cleanup

The final milestone locks in the dual-backend product.

Update tests under `tests/`:

- Add backend-selection tests to `tests/test_config.py` and `tests/test_digest.py`.
- Add subprocess-mocking tests for the Codex backend:
  - installed + logged in
  - installed + not logged in
  - not installed
  - malformed structured output

- Add CLI tests for:
  - `--backend codex`
  - `--backend api`
  - config fallback behavior
  - JSON stderr error envelope

Update docs:

- `README.md`
  Document both setup paths clearly:
  - ChatGPT subscription via Codex
  - OpenAI API key

- `.claude/skills/xx-digest/SKILL.md`
  Update prerequisites so Codex/ChatGPT subscription is a supported first-class path.

- `docs/exec-plans/active/xx-digest-v1.md`
  Add a note in Outcomes or Decision Log that the original API-key-only model path has been superseded by the dual-backend plan once implementation is complete.

Consider adding a tiny status command if implementation friction suggests it is necessary:

    xx digest-auth-status

This is not mandatory for the first pass. Only add it if debugging backend readiness becomes messy enough that setup alone is not sufficient.

Verification for this milestone:

- Run:

      python3 -m pytest tests/ -v
      PATH="$HOME/Library/Python/3.11/bin:$PATH" xx digest --backend codex --sample --debug
      PATH="$HOME/Library/Python/3.11/bin:$PATH" xx digest --backend api --sample --json

- Confirm both backends reach the same JSON schema.

## Concrete Steps

Work from `/Users/macbook/Code/xxcli`.

1. Refactor configuration and `llm.py` dispatch so the backend can be selected without breaking current API behavior.
2. Add `src/xxcli/codex_backend.py` and implement subprocess-based scoring and distillation using `codex exec`.
3. Update onboarding to choose and validate the backend.
4. Update `xx digest` CLI resolution and error handling.
5. Add tests and docs, then run the full validation commands.

Short command transcripts that prove the environment assumptions on this machine:

    $ codex --help
    ... exec ...
    ... login ...

    $ codex login status
    Logged in using ChatGPT

## Validation and Acceptance

Acceptance is not “the code compiles.” Acceptance is:

1. A human with a working Codex ChatGPT login can set up digest without an OpenAI API key.
2. An existing API-key-based user can keep using digest without changing behavior.
3. `xx digest --backend codex --json` returns the same schema shape as `xx digest --backend api --json`.
4. `xx setup` clearly explains the two product modes and never implies that a ChatGPT subscription and API key are the same thing.
5. The CLI tells the truth when Codex is missing or not logged in, and the fix messages are actionable.
6. All tests in `tests/` pass.

## Idempotence and Recovery

This plan is additive and safe to retry.

- Running `xx setup` multiple times should simply overwrite the selected backend and related config values.
- If the user switches from Codex to API or back, no auth tokens should be deleted by `xx`.
- If the Codex backend is selected but `codex login status` later fails, the fix path is to rerun `xx setup` or `codex login`, not to edit config files manually.
- Existing configs without `model_backend` must continue to load cleanly.

## Refinement Pass

Pending implementation.

### Ontology alignment

Pending. Check whether “backend”, “provider”, “auth mode”, and “subscription” are described consistently across config, help text, and README. The user should understand that the X API and the model backend are two separate concepts.

### Design fidelity

Pending. The new setup questions and readiness errors must use the existing terminal design system in `DESIGN.md`, especially the cyan accent and dim secondary guidance.

### Product behavior

Pending. Confirm the backend choice feels like a product decision, not a leaky implementation detail. Setup should explain why someone might choose Codex vs API in one sentence each.

### Tangential discoveries

Pending. If this work reveals that model-provider abstraction would help future features beyond digest, route that as a follow-up rather than growing scope here.

## Artifacts and Notes

Relevant current files:

- `src/xxcli/cli.py`
- `src/xxcli/config.py`
- `src/xxcli/llm.py`
- `src/xxcli/onboarding.py`
- `src/xxcli/digest.py`
- `docs/exec-plans/active/xx-digest-v1.md`

External product research that motivated this plan:

- OpenAI documents ChatGPT-vs-API billing separation, which is why the current API-key-only implementation exists.
- OpenAI also documents that Codex CLI supports `Sign in with ChatGPT`.
- OpenClaw publicly presents both API-key mode and Codex-backed subscription mode, which validates the product shape of “two backends, one UX”.

These facts matter because they justify a dual-backend design rather than trying to fake a generic ChatGPT-web-login flow inside `xx`.

## Interfaces and Dependencies

New or modified interfaces that must exist at the end of implementation:

    src/xxcli/config.py
      load_config() -> dict
      save_config(data: dict) -> None
      get_model_backend() -> ModelBackendConfig | None
      save_model_backend(config: ModelBackendConfig) -> None

    src/xxcli/llm.py
      class ModelBackendConfig(...)
      async def score_tweets(..., backend_config: ModelBackendConfig, ...) -> DigestResult
      async def distill_preferences(..., backend_config: ModelBackendConfig, ...) -> PreferenceRules
      def check_backend_ready(backend_config: ModelBackendConfig) -> BackendStatus

    src/xxcli/codex_backend.py
      def codex_installed() -> bool
      def codex_login_status() -> CodexLoginStatus
      async def score_with_codex(...) -> DigestResult
      async def distill_with_codex(...) -> PreferenceRules

    src/xxcli/onboarding.py
      run_setup_wizard(console) -> dict
      chooses `api` vs `codex`

    src/xxcli/cli.py
      xx digest --backend api|codex

Expected external tools and libraries:

- `codex` CLI on PATH for the Codex backend
- existing `openai-agents` and `openai` packages for the API backend
- no new browser automation dependency inside `xx` itself

The implementation bar is that a single stateless agent can follow this file and add ChatGPT-subscription support to `xx digest` without inventing missing product decisions on the fly.
