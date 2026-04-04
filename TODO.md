  Next skills to run (in order):
  1. ~~/design-consultation — create DESIGN.md to formalize the terminal design system before implementation.~~ ✓ Done (2026-04-04)
  2. /plan-ceo-review — review the First-Run Eval Wizard idea (captured in plan). This is a potential v1 scope
     expansion: onboarding becomes a calibration session that builds an eval dataset from your real preferences.
     Needs CEO-level review on scope, timing, and whether it's v1 or v1.1.
  3. /plan-devex-review — review the developer experience of xx digest before implementation.
     How fast is time-to-first-digest? Is the setup flow intuitive? Does --debug give enough for prompt iteration?

  Setup wizard TODO:
  - Flesh out `xx setup` wizard — model after PostHog's setup flow.
    PostHog nails onboarding: step-by-step progress, verify-as-you-go (e.g. "send a test event"),
    contextual guidance at each step, and a clear "you're done" moment.
    Apply this pattern: walk the user through API key entry, source selection, first digest run,
    and confirmation that everything works — each step validates before advancing.
    Related: First-Run Eval Wizard idea (item 2 above) could layer on top of this base setup flow.

  Design review TODOs (from /plan-design-review):
  - `--brief` flag for xx digest — suppress "Why" explanations for power users. Deferred to post-v1.
    Pick up after a week of daily digest use. Depends on: digest v1 live.