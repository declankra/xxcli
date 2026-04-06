  Next steps (in order):
  1. ~~/design-consultation — create DESIGN.md to formalize the terminal design system before implementation.~~ ✓ Done (2026-04-04)
  2. ~~/plan-ceo-review — review scope, vision, product principles for xx digest learning system.~~ ✓ Done (2026-04-04)
     Scope: EXPANSION mode. 7 expansions accepted. Plan: docs/designs/xx-digest-ceo-plan.md
  3. ~~/plan-devex-review — review the developer experience of xx digest before implementation.~~ ✓ Done (2026-04-06)
     Score: 5/10 → 7/10. 14 decisions: credential wizard, --json flag, SKILL.md, --sample, exit codes, error formula, TTHW tracking.
     Full DX review: docs/designs/xx-digest-dx-review.md
  4. BUILD — implement xx digest complete learning system per the CEO plan, eng review, and DX review.
     Build order: context.py + llm.py (parallel) → digest.py → feedback.py + onboarding.py → cli.py wiring → format.py → tests

  Product principles (from CEO review + WIRING-PLAN + autoresearch):
  - No manual config editing — the setup wizard handles all configuration through questions
  - Self-improve always — agent evolves scoring rules from feedback, triggered every 10 new signals
  - Not adding more work — using the product IS the eval, zero-friction feedback
  - Not rigid — light harness, model improvements naturally improve the product
  - Progressive disclosure — setup wizard reveals complexity gradually
  - Close loops — every digest feels complete

  Design review TODOs (from /plan-design-review):
  - `--brief` flag for xx digest — suppress "Why" explanations for power users. Deferred to post-v1.
    Pick up after a week of daily digest use. Depends on: digest v1 live.

  Deferred from CEO review (v2+):
  - `--export` markdown (shell piping covers this)
  - Digest history diff (`--diff`)
  - Multi-source intelligence (HN, RSS, GitHub trending)
  - Action routing (ADOPT → GitHub issue)
  - Full promotion chain with experiment/verdict (when multiple users need statistical rigor)
