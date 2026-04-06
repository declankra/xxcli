# Codex Execution Plans (ExecPlans)

This document defines the repo standard for an execution plan ("ExecPlan"), a design document that a coding agent can follow to deliver a working feature or system change.

Source inspiration:
- OpenAI Cookbook, "Using PLANS.md for multi-hour problem solving" by Aaron Friel, published October 7, 2025
- https://developers.openai.com/cookbook/articles/codex_exec_plans

Repo usage:
- Use an ExecPlan for complex features, significant refactors, or work that is likely to span multiple focused sessions.
- Active plans live in `docs/exec-plans/active/`; shipped plans move to `docs/exec-plans/completed/`.
- In this repo, source-of-truth docs outrank an ExecPlan, but the plan must restate any context a future agent will need to continue from the plan and the working tree alone.

## How to use ExecPlans and PLANS.md

When authoring an executable specification (ExecPlan), follow this file closely. If it is not in your context, read the entire file before drafting or revising the plan. Be thorough in reading and re-reading source material so the specification is accurate. Start from the skeleton and flesh it out as you do your research.

When implementing an ExecPlan, do not stop to ask for generic next steps. Proceed to the next milestone unless blocked by missing external input or a high-risk unresolved decision. Keep all living sections current at every stopping point so another agent can resume work without reconstruction.

When discussing or revising an ExecPlan, record decisions in the plan itself so it is always clear why the specification changed. ExecPlans are living documents. It should be possible to restart from only the ExecPlan and the current working tree.

When researching a design with meaningful unknowns, use milestones to validate feasibility with prototypes or proof-of-concept implementations. Read source code where needed, research deeply, and include enough context that the path to a full implementation is clear.

## Requirements

NON-NEGOTIABLE REQUIREMENTS:

- Every ExecPlan must be fully self-contained. In its current form it must contain all knowledge and instructions needed for a novice to succeed.
- Every ExecPlan is a living document. Contributors must revise it as progress is made, discoveries occur, and design decisions are finalized. Each revision must remain self-contained.
- Every ExecPlan must enable a complete novice to implement the feature end-to-end without prior knowledge of this repo.
- Every ExecPlan must produce demonstrably working behavior, not merely code changes that satisfy an internal definition.
- Every ExecPlan must define every term of art in plain language or avoid using it.

Purpose and intent come first. Begin by explaining, in a few sentences, why the work matters from a user's perspective: what someone can do after the change that they could not do before, and how to see it working. Then guide the reader through the exact steps to achieve that outcome, including what to edit, what to run, and what they should observe.

The agent executing the plan can list files, read files, search, run the project, and run tests. It does not know prior session context and cannot infer what you meant from earlier milestones. Repeat every assumption you rely on. Do not point vaguely to external posts or docs when the plan needs that knowledge; embed the needed explanation in the plan itself. If an ExecPlan builds on an earlier checked-in ExecPlan, incorporate it by reference. If it does not, include the relevant context directly.

## Formatting

Format and envelope are simple and strict. Each ExecPlan should be one single Markdown document. If the file contains only the ExecPlan, do not wrap it in an outer fence. Do not nest extra fenced code blocks when indentation will do; when showing commands, transcripts, diffs, or code, prefer indented examples so the plan remains easy to maintain as a single document.

Use correct Markdown headings, spacing, and list syntax. Use two newlines after headings. Keep formatting boring and stable.

Write in plain prose. Prefer sentences over lists. Avoid checklists, tables, and long enumerations unless brevity would otherwise obscure meaning. Checklists are permitted only in the `Progress` section, where they are mandatory. Narrative sections should remain prose-first.

## Guidelines

Self-containment and plain language are paramount. If you introduce a phrase that is not ordinary English, define it immediately and remind the reader how it manifests in this repository by naming the files, commands, or runtime surfaces involved. Do not say "as defined previously" or "according to the architecture doc" when the explanation is needed for success. Include the explanation here even if it feels repetitive.

Avoid common failure modes. Do not rely on undefined jargon. Do not describe a feature so narrowly that the resulting code compiles but does nothing meaningful. Do not outsource key decisions to the reader. When ambiguity exists, resolve it in the plan itself and explain why that path was chosen. Err on the side of over-explaining user-visible effects and under-specifying incidental implementation details.

Anchor the plan with observable outcomes. State what the user can do after implementation, the commands to run, and the outputs they should see. Phrase acceptance as behavior a human can verify, not as internal attributes. If the change is internal, explain how its impact can still be demonstrated, such as through a failing test that passes after the change or a small scenario that exercises the new behavior.

Specify repository context explicitly. Name files with full repository-relative paths, name functions and modules precisely, and describe where new files should be created. If the work touches multiple areas, include an orientation paragraph explaining how those parts fit together so a novice can navigate confidently. When running commands, show the working directory and the exact command line. When outcomes depend on environment, state the assumptions and provide reasonable alternatives.

Be idempotent and safe. Write steps that can be run multiple times without damage or drift. If a step can fail halfway through, explain how to retry or adapt. If a migration or destructive operation is necessary, spell out safe fallbacks. Prefer additive, testable changes that can be validated as you go.

Validation is not optional. Include instructions to run tests, start the system if applicable, and observe useful behavior. Describe comprehensive testing for the new feature or capability. Include expected outputs and error messages so a novice can distinguish success from failure. Where possible, show how to prove the change is effective beyond compilation through an end-to-end scenario, CLI invocation, or request/response transcript. State the exact test commands appropriate to the project's toolchain and how to interpret their results.

Capture evidence. When the work produces terminal output, short diffs, logs, or screenshots, include concise examples focused on what proves success. Prefer file-scoped diffs or short excerpts that the reader could recreate by following the instructions rather than pasting large blobs.

## Milestones

Milestones are narrative, not bureaucracy. If you break the work into milestones, introduce each with a brief paragraph that explains the scope, what will exist at the end of the milestone that did not exist before, the commands to run, and the acceptance you expect to observe. Keep it readable as a story: goal, work, result, proof. Progress and milestones are distinct. Milestones tell the story; progress tracks granular work. Both must exist.

Never abbreviate a milestone merely for brevity, and do not omit details that could matter to a future implementation. Each milestone must be independently verifiable and incrementally advance the overall goal of the ExecPlan.

## Living plans and design decisions

- ExecPlans are living documents. As key decisions are made, update the plan to record both the decision and the reasoning in the `Decision Log`.
- ExecPlans must contain and maintain a `Progress` section, a `Surprises & Discoveries` section, a `Decision Log`, an `Outcomes & Retrospective` section, and a `Refinement Pass` section. These are mandatory. The Refinement Pass is populated after implementation milestones are complete and tracks iterative improvements across ontology alignment, design fidelity, product behavior, and tangential discoveries.
- When you discover optimizer behavior, performance tradeoffs, unexpected bugs, or inverse semantics that shape the approach, capture them in `Surprises & Discoveries` with short evidence snippets when possible.
- If you change course mid-implementation, document why in the `Decision Log` and reflect the implications in `Progress`.
- At completion of a major task or the full plan, write an `Outcomes & Retrospective` entry summarizing what was achieved, what remains, and lessons learned.

## Prototyping milestones and parallel implementations

It is acceptable, and often useful, to include explicit prototyping milestones when they de-risk a larger change. Examples include proving a library is viable in isolation, validating a low-level behavior before building on top of it, or comparing two approaches while measuring tradeoffs. Keep prototypes additive and testable. Clearly label them as prototyping, describe how to run and observe them, and state the criteria for promoting or discarding the result.

Prefer additive changes followed by subtractions that keep tests passing. Parallel implementations can be acceptable during large migrations when they reduce risk or keep validation possible. If you use them, explain how to validate both paths and how the temporary path will be retired safely.

When working with multiple new libraries or feature areas, consider spikes that evaluate feasibility independently before committing to the integrated design.

## Repo-specific expectations

Read the relevant source-of-truth docs first: `PRODUCT-SENSE.md`, `ARCHITECTURE.md`, `DESIGN.md`, `docs/ontology/README.md`, and `docs/decisions/README.md`, plus any relevant plan in `docs/exec-plans/active/`, spec in `docs/product-specs/`, or reference in `docs/references/`.

Follow the repo boundaries in the plan itself. Routes and pages belong in `app/`. Shared deterministic business logic, operations, and types belong in `lib/`. AI-specific prompts, tools, contracts, and orchestration belong in `ai/`. `ai/` may call `lib/`; `lib/` must not depend on `ai/`.

If the work changes product behavior, architecture, ontology, or other durable decisions, the plan should say which source-of-truth files must be updated as part of the same effort. If the owner doctrine or repo protocol changes, update `AGENTS.md`. If the work produces a durable lesson for future agents, update `AGENTS-LEARNINGS.md`.

This repo already stores ExecPlans under `docs/exec-plans/active/` and `docs/exec-plans/completed/`. Use that structure instead of inventing a second location.

## Skeleton of a good ExecPlan

# <Short, action-oriented description>

This ExecPlan is a living document. The sections `Progress`, `Surprises & Discoveries`, `Decision Log`, and `Outcomes & Retrospective` must be kept up to date as work proceeds.

If `PLANS.md` is checked into the repo, reference the path from the repository root and note that the document must be maintained in accordance with it.

## Purpose / Big Picture

Explain in a few sentences what someone gains after this change and how they can see it working. State the user-visible behavior the change enables.

## Progress

Use a checklist to summarize granular steps. Every stopping point must be documented here, even if that means splitting a partially completed task into what is done and what remains. This section must always reflect the actual current state of the work.

- [x] Example completed step with timestamp.
- [ ] Example incomplete step.
- [ ] Example partially completed step, with what is done and what remains.

Use timestamps to measure the rate of progress.

## Surprises & Discoveries

Document unexpected behaviors, bugs, optimizations, or insights discovered during implementation. Provide concise evidence.

- Observation: ...
  Evidence: ...

## Decision Log

Record every consequential decision made while working on the plan.

- Decision: ...
  Rationale: ...
  Date/Author: ...

## Outcomes & Retrospective

Summarize outcomes, gaps, and lessons learned at major milestones or at completion. Compare the result against the original purpose.

## Context and Orientation

Describe the current state relevant to the task as if the reader knows nothing. Name the key files and modules by full path. Define non-obvious terms. Do not rely on prior plans being in the reader's head.

## Plan of Work

Describe, in prose, the sequence of edits and additions. For each edit, name the file and location, such as the function, module, or route, and say what will change. Keep it concrete and minimal.

## Concrete Steps

State the exact commands to run and where to run them. When a command generates output, show a short expected transcript so the reader can compare. Update this section as work proceeds.

## Validation and Acceptance

Describe how to start or exercise the system and what to observe. Phrase acceptance as behavior, with concrete inputs and outputs. If tests are involved, say exactly what command to run and what should pass.

## Idempotence and Recovery

If steps can be repeated safely, say so. If a step is risky, provide a safe retry or rollback path. Keep the environment clean after completion.

## Refinement Pass

After implementation milestones are complete, the milestone enters a refinement phase. This section tracks iterative improvements to reach stakeholder-ready quality. Each item is individually shippable with its own atomic commit.

### Ontology alignment

Does the UI accurately represent the domain model? Do labels, behaviors, and data flows match the ontology docs? Each item gets a status (pending, fixed, accepted, deferred) and notes.

### Design fidelity

Does the implementation match DESIGN.md? Interaction states (loading, empty, error, success, pending), spacing, typography, semantic colors, motion.

### Product behavior

Does the interaction model feel right? Edge cases, keyboard flow, feedback quality, polish. Is it better than the thing it replaces?

### Tangential discoveries

Issues found during refinement that are out of scope for this milestone. Each gets routed to: TODOS.md, next milestone spec, or fix now.

## Artifacts and Notes

Include the most important transcripts, diffs, snippets, or screenshots as concise indented examples focused on proving success.

## Interfaces and Dependencies

Be prescriptive. Name the libraries, modules, services, interfaces, and function signatures that must exist at the end of the milestone. Prefer stable names and explicit paths.

The bar is that a single stateless agent, or a human novice, can read the ExecPlan from top to bottom and produce a working, observable result. When revising a plan, ensure changes are reflected across all relevant sections, especially the living-document sections. ExecPlans must describe not only what to do, but why.
