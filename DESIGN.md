# Design System — xx

## Product Context
- **What this is:** Terminal client for Twitter/X. Stay current on AI/tech/software without the doom scroll.
- **Who it's for:** Developers and builders who live in the terminal and want focused, actionable consumption of X.
- **Space/industry:** Developer tools, social media clients, terminal UIs
- **Project type:** TUI (Terminal User Interface) — interactive, keyboard-driven, polished

## Visual Reference
- **Preview:** [DESIGN-PREVIEW.html](./DESIGN-PREVIEW.html) — open in a browser to see the full TUI mockup (feed, digest, compose, profile, states, color system). Supports dark/light toggle.
- **Use as implementation drift check:** If the terminal output doesn't match the preview, the code has drifted from the design system.

## Aesthetic Direction
- **Direction:** Polished Interactive — clean panels, structured layouts, Rich spinners, interactive prompts. Think Claude Code meets Charm.sh meets a content-first social reader.
- **Decoration level:** Intentional — Rich panels for tweet cards, rule lines for section breaks, structured empty states. Every decoration serves readability or navigation. No bare text dumps, but no gratuitous box-drawing either.
- **Mood:** Focused but fun. The terminal is inherently anti-doom-scroll (you can't infinitely scroll), so the experience inside should feel great. More time in xx is good because it's actionable time, not mindless time.
- **Inspirations:** Claude Code (interactive polish), Vercel CLI (brand identity), Linear (keyboard-first), Charm.sh/Textual (TUI craft)

## Brand Identity
- **Accent color:** Cyan — rare in CLIs (most default to green/blue), pops on both dark and light terminals, energetic
- **Logo/header:** Compact `xx` wordmark in cyan, displayed in the TUI navigation header
- **Voice:** Direct, builder-to-builder. No marketing speak. Match the README tone.

## Color System
- **Approach:** Balanced — five distinct roles, every color has a job, no decorative color
- **Philosophy:** Content is king. Engagement metrics (likes/RTs/replies) are deliberately dim, not color-coded. The numbers aren't the point, the content is.

### Roles

| Role | Rich Style | ANSI | Purpose |
|------|-----------|------|---------|
| Brand accent | `cyan` | Cyan | xx identity, interactive highlights, keyboard hints, active selections |
| System: success | `green` | Green | Confirmations, posted messages |
| System: error | `red bold` | Red+Bold | Error titles, destructive states |
| System: warning | `yellow` | Yellow | Warnings, confirmation prompts |
| System: info | `blue` | Blue | Informational notes (used sparingly) |
| Content: author | `bold` | Bold | Tweet author display names |
| Content: body | *(default)* | Default FG | Tweet text, primary content |
| Content: handle | `dim` | Dim | @usernames, timestamps, separators |
| Content: metrics | `dim` | Dim | Likes, RTs, replies (no color) |
| Interactive: key | `cyan` | Cyan | Keyboard shortcut labels |
| Chrome: dim | `dim` | Dim | IDs, secondary metadata |

### Rich Theme Tokens

```python
# src/xxcli/theme.py
from rich.theme import Theme

xx_theme = Theme({
    "xx.author":  "bold",
    "xx.handle":  "dim",
    "xx.content": "",
    "xx.metrics": "dim",
    "xx.accent":  "cyan",
    "xx.success": "green",
    "xx.error":   "red bold",
    "xx.warning": "yellow",
    "xx.info":    "blue",
    "xx.key":     "cyan",
    "xx.dim":     "dim",
})
```

Use named styles (`[xx.author]`, `[xx.accent]`) instead of inline colors (`[bold]`, `[red]`). This keeps styling centralized and semantic.

## Information Hierarchy
1. **Author + time** (header line) — bold name, dim handle and relative timestamp
2. **Content** (body) — default foreground, full terminal width, the most visually prominent element
3. **Metrics** (footer) — dim, no color, deliberately de-emphasized
4. **Actions** (interactive, on active card only) — cyan keyboard hints

## Layout & Structure
- **Tweet cards:** Rich panels with border, active card gets cyan border highlight
- **TUI header:** Navigation bar showing available views with keyboard shortcuts
- **Status bar:** Bottom bar with context (current view, position in feed, navigation hints)
- **Spacing:** One blank line between cards, consistent internal padding
- **Terminal width:** Respect terminal width, wrap content naturally, no hard-coded widths

## Interaction Patterns
- **Navigation:** j/k to move between tweets, arrow keys as alternative
- **Actions on active card:** r(reply), l(like), t(retweet), o(open in browser), y(copy link)
- **View switching:** f(feed), d(digest), p(post), m(me), ?(help)
- **Compose:** Inline text input with live character count, ctrl+enter to post, esc to cancel
- **Loading:** Rich spinner with descriptive text ("Fetching your timeline...")
- **Confirmation:** y/N prompts for destructive or over-limit actions

## Interaction States

### Loading
```
◐ Fetching your timeline...
```
Rich spinner (dots, line, or similar), descriptive text, no raw "loading..."

### Success
```
✓ Posted! https://x.com/i/web/status/123456
✓ Liked tweet 123456
```
Green checkmark, confirmation message, link when relevant.

### Warning
```
⚠ Tweet is 312 chars (max 280). Post anyway? [y/N]
```
Yellow warning symbol, clear description, actionable prompt.

### Error
```
✗ Rate limited
  X API returned 429. Too many requests in the current window.
  Hint: wait a few minutes and try again. Free tier allows 15 requests per 15-minute window.
```
Red bold title, explanation on next line, hint with actionable guidance. Never just dump the exception.

### Empty
```
  ○ No tweets in your timeline yet
  Follow some accounts on X, then run xx feed again
```
Centered, calm, helpful. Suggest next action.

## Pipe & Scripting Support
- **NO_COLOR:** Respect the `NO_COLOR` environment variable (strip all ANSI markup)
- **TTY detection:** Rich handles this automatically. When piped, output is plain text.
- **Machine-readable:** Future consideration: `--json` flag for structured output
- **Highlight:** Disable Rich auto-highlighting (`highlight=False` on Console)

## Typography
- **Font:** Monospace, inherited from the user's terminal. No font choices to make.
- **Emphasis levels:** Bold (authors, error titles), default weight (content), dim (metadata, metrics)
- **No underline, italic, or strikethrough** in normal output. Keep the text register simple.

## Motion & Feedback
- **Spinners:** Rich spinner for any API call that might take >200ms
- **Response time:** Acknowledge user action within 100ms (show spinner immediately)
- **No animations in piped output:** Skip spinners and progress when not TTY

## Implementation Path
- **Current:** Rich library (print-style output with panels and themes)
- **Future:** Textual (full TUI framework, same ecosystem, same theme tokens)
- **Migration:** Rich panels → Textual widgets. The design system and theme tokens carry over directly. Textual is built on Rich by the same team (Will McGugan).

## Decisions Log
| Date | Decision | Rationale |
|------|----------|-----------|
| 2026-04-04 | Initial design system created | Created by /design-consultation. Cyan accent, dim metrics, paneled cards, TUI-first. |
| 2026-04-04 | Engagement metrics deliberately dim | xx's thesis is anti-doom-scroll. Colored metrics recreate the dopamine UI. Content should be the visual focus, not numbers. |
| 2026-04-04 | Rich → Textual migration path | Same ecosystem, same team. Design tokens carry over. Start with Rich panels, graduate to Textual widgets. |
| 2026-04-04 | Cyan as brand accent | Rare in CLIs (most use green/blue), works on dark and light terminals, energetic but not aggressive. |
