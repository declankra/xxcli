what i want:
- to find the smallest valuable thing i can do to get value out of this everyday. build that.
    - in the best agent + human UX way.
- then publish a website with proper design.



Now we're cooking. The picture is clear:                                               
xx digest — a batch-mode, context-aware summary of your X feed that knows what you're building and surfaces only what's relevant. Scheduled at a time you choose. No pings, no scrolling, no browser. You open the terminal when you're ready, and the signal is waiting for you.                                                                       
                                                                                         
The arc: digest (v1) → context-aware digest that reads your repos (v2) →      digest-to-action pipeline where you can follow up and apply ideas (v3).  


  1. The coolest version is not a digest. It is a standing `xx scout` brief:                        
  "watch for things that should change what I build this week."                                     
  It keeps a live model of your current work from recent commits, touched                           
  files, deps, and repo docs, then watches X for three classes of signal only:                      
  - `adopt`: something you should start using                                                       
  - `avoid`: something that invalidates or weakens your current approach
  - `copy`: something adjacent builders are doing that maps to your exact project         


    The killer move is that each hit comes with the tweet, why it matters to                          
  your repo, and a next action like "open an issue," "save to backlog," or
  "prototype this." That turns X from input addiction into execution leverage.  


    2. The line that reveals what excites them most is:
  "I haven't opened X in 3 days. My agent told me about a new framework
  relevant to what I shipped yesterday."                                                            
  That is the product. Not "better Twitter." Not "AI summaries." It is:
  staying off the feed while still getting the one thing that mattered.


## Dual Interface: Human CLI + Agent Skill

xx has two user personas. This is core to the product vision.

1. **Human at the terminal** — types `xx digest`, reads the rich TUI output, gives feedback (keep/discard/recover), runs the setup wizard. The terminal is the anti-addiction layer. The experience inside it should feel great.

2. **AI agent invoking xx as a skill** — the user opens Claude Code or Codex and asks "What's on my Twitter feed today that's important?" The agent invokes xx as a packaged skill, calls the CLI, parses the output, and answers the question. The user never types `xx digest` themselves.

This means xx needs to work for both:
- Rich TUI output for humans (panels, spinners, colors, interactive prompts)
- Parseable, pipe-friendly output for agents (plain text when piped, structured data via --debug or future --json)

The skill packaging is how most users may actually interact with xx. Through their AI assistant, not by typing commands directly. Every command and output format should consider both personas.


## Operating Principles

Principles that guide how xx should be built. Drawn from the WIRING-PLAN (agent-OS architecture) and Karpathy's autoresearch.

### From the WIRING-PLAN

- **Not adding more work** — effective AI products don't transform work into another format, they automate it and reduce cognitive load. The feedback loop must be zero-friction. Using the product IS the eval. No "rate this 1-5" prompts. No surveys. No config files to edit.

- **Self-improve always** — the product should get better every time you use it, without you doing anything special. The agent reads accumulated feedback and autonomously evolves its scoring rules. The user never touches the prompt.

- **Not rigid** — don't over-constrain the harness. The next model advance will need less scaffolding. Keep the scoring prompt light so model improvements naturally improve the product.

- **Recovery by re-polling, not state restoration** — re-read context each time (git log, feedback signals, preference rules). Don't maintain complex state. The feedback.jsonl is the log of truth. Preference rules are regenerated from it, not cached permanently.

- **Progressive disclosure** — don't dump all information at once. The setup wizard reveals complexity gradually. Phase 1: pick a repo. Phase 2: what do you care about? Phase 3: calibrate on real tweets. Each phase shows you understood the last one before going deeper.

- **Close loops** — don't increase cognitive load with a bunch of "unfinished items." Every digest should feel complete. Recover an item from the discard pile = close the loop on that signal.

- **No manual config editing** — the setup wizard handles all configuration through interactive questions. config.yaml exists as persistence, but the user should never need to open it. If a feature needs a new setting, add it to the wizard or create a CLI command.

- **Forward progress, not backwards compatibility** — don't worry about backwards compat. Move forward. If the preference format changes, migrate it. Don't shim.

### From Karpathy's Autoresearch

The autoresearch model (https://github.com/karpathy/autoresearch) gives us three primitives for self-improvement:

- **Editable asset** — the LLM system prompt + preference rules. This is what the agent modifies autonomously based on feedback.

- **Scalar metric** — signal rate: (explicit keeps + recovers) / (explicit keeps + discards + recovers). Higher = better digest. This is the single number that tells us if the product is improving.

- **Time-boxed cycle** — each digest run IS a cycle. Run digest, get feedback, measure, evolve. The user's keep/discard actions program the agent, like writing program.md programs the autoresearch loop.

The meta-insight: the user programs the program, not the code. In autoresearch, the human writes program.md to direct the AI researcher. In xx, the user's keep/discard actions ARE the program.md. The agent reads feedback, rewrites preference rules autonomously, and the next digest run is the experiment.

### Self-Improvement Architecture

Simplified distillation inspired by autoresearch + the WIRING-PLAN promotion chain:

- Phase 1 (< 20 signals): include 3-5 recent feedback examples as few-shot in the LLM prompt
- Phase 2 (20+ signals): sub-agent distills accumulated signals into preference rules
- Trigger: data-driven (every 10 new signals), not time-driven (not a cron job)
- Visible to the user: "Evolving your preferences... Now prioritizing [X], filtering [Y]"
- The product learns from both what you BUILD (git context) and what you KEEP (feedback signals). Two orthogonal signal sources. Nobody else in this space has both.