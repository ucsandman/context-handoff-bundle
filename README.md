# Context Handoff Bundle

[![CI](https://github.com/ucsandman/context-handoff-bundle/actions/workflows/ci.yml/badge.svg)](https://github.com/ucsandman/context-handoff-bundle/actions/workflows/ci.yml)
[![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue)](https://github.com/ucsandman/context-handoff-bundle)
[![License: MIT](https://img.shields.io/badge/license-MIT-green)](LICENSE)

**Resume yesterday's AI coding session for ~3% of the tokens.**

Every new session, your AI coding agent re-orients from zero: re-reads the README, re-walks the source tree, re-derives everything it already knew yesterday. With frontier models like Anthropic's Fable 5 and Opus, that cold start burns tens of thousands of input tokens -- every single session -- before any real work happens.

Context Handoff Bundle captures what the agent learned during a session into a structured, evidence-backed bundle. The next session loads it as a compact resume -- typically a few hundred tokens instead of a multi-thousand-token re-read -- with honest drift detection that tells you what's still safe to trust. Plain files on disk. No cloud, no API keys, zero dependencies.

```
Terminal 1 (end of day):
$ context-handoff-bundle save --title "Auth refactor progress"
  saved: strong (0.84) -- 6 findings, 4 evidence anchors, 3 open questions

Terminal 2 (next morning):
$ context-handoff-bundle load

# Resume: Auth refactor progress

## State
- Active areas: middleware, token-validation, session-handling
- Work in progress (2 modified, 1 staged): src/middleware/auth.ts, src/routes/api.ts
- Technology stack: TypeScript, Node.js, Docker

## Drift
Severity: LOW -- 2 commits, 3 files touched since save.
- src/middleware/auth.ts CHANGED
- Findings: **medium** | Evidence: partial (1/4 affected) | Recommendations: **medium**

## Open First
- src/middleware/auth.ts (changed since save)
- src/routes/api.ts (active WIP)

## Next Moves
1. Complete token rotation implementation
2. Add integration tests for session handling
3. Update API docs for new auth flow

[tokens] resume: ~640 | re-deriving from source (6 files): ~23.0k | saved: ~97% (chars/4 estimate)
```

No archaeology. No re-reading. No "let me look at the codebase..."

---

## Why This Exists

AI coding agents build deep understanding during a session: which files matter, how components connect, what was tried, what decisions were made, what's still uncertain.

**All of that disappears when the session ends.**

The next session starts from zero. You re-explain. The agent re-reads. You repeat research. Every time.

Context Handoff Bundle fixes this with three ideas:

1. **Structured save** -- not a chat export, but findings + evidence + open questions
2. **Drift detection** -- on load, tells you exactly what changed and which findings are still safe
3. **No fake certainty** -- quality scores, per-section confidence, honest "I don't know" signals

---

## The Token Math

Cold-starting an agent session means re-reading source files at full input price. A handoff resume replaces that with a few hundred tokens of distilled context.

Measured on this repo (every `load` prints your own numbers):

```
[tokens] resume: ~640 | re-deriving from source (6 files): ~23.0k | saved: ~97% (chars/4 estimate)
```

| | Cold start | Handoff resume |
|---|---|---|
| What the agent reads | Evidence files + README + docs, rediscovered by trial and error | One distilled, drift-checked resume |
| Input tokens (this repo) | ~23,000 | ~640 |
| Multiplied by | every session, every terminal, every teammate | once per save |

Two sessions a day on a mid-size repo easily means 50k-400k tokens/day spent on pure re-orientation. With current frontier-model pricing, that's real money for zero new understanding -- the agent is paying to relearn what it already knew.

**How the estimate works, honestly:** tokens are estimated as `chars / 4` (the standard heuristic), the re-read cost counts the bundle's evidence-anchored files plus standard orientation files (README, CLAUDE.md, etc.) at their current size. It's an order-of-magnitude measurement, not a billing statement -- and it's printed on every load so you can judge it against your own repo.

---

## Install

```bash
pip install git+https://github.com/ucsandman/context-handoff-bundle.git
```

or with [pipx](https://pipx.pypa.io/) for an isolated CLI install:

```bash
pipx install git+https://github.com/ucsandman/context-handoff-bundle.git
```

Development:

```bash
git clone https://github.com/ucsandman/context-handoff-bundle.git
cd context-handoff-bundle
pip install -e .
pytest
```

Requires Python 3.10+. Zero runtime dependencies (`jsonschema` is optional, for schema validation in `validate`).

---

## Core Workflow

### Save

```bash
context-handoff-bundle save --title "API migration analysis"
```

Automatically gathers from your repo:
- Project purpose (README, CLAUDE.md)
- Active code areas from file-path analysis
- Recent git history and diff stats
- Work in progress (staged, modified, untracked)
- Test failure indicators
- Evidence file paths
- TODO/FIXME counts

```json
{
  "saved": true,
  "bundle_id": "20260406-143022-api-migration",
  "quality": "strong",
  "score": 0.84,
  "warnings": [],
  "token_estimates": {
    "bundle_tokens": 3696,
    "source_reread_tokens": 23043,
    "source_files_counted": 6,
    "heuristic": "chars/4"
  }
}
```

### Load

```bash
context-handoff-bundle load              # latest for current repo
context-handoff-bundle load api-migration # by slug
context-handoff-bundle load --deep       # full context mode
```

The resume output is operational, not archival:

| Section | What it tells you |
|---------|-------------------|
| **State** | What's true, what was established, active code areas |
| **Drift** | What changed since save, severity, which files moved |
| **Section confidence** | Findings: strong, Evidence: partial, Recommendations: STALE |
| **Open First** | Which files to look at, guided by drift and evidence |
| **Must Reverify** | What not to trust blindly |
| **Next Moves** | Specific actions, not generic "review the codebase" |

### Diff

```bash
context-handoff-bundle diff <older-bundle> <newer-bundle>
```

Compare two bundles to see what evolved:
- New and gone findings
- Resolved questions
- Dropped recommendations
- Evidence changes

### Manage

```bash
context-handoff-bundle list                # see all bundles
context-handoff-bundle show latest         # inspect one bundle
context-handoff-bundle save --update       # refresh latest bundle
context-handoff-bundle prune --keep 1      # clean old duplicates
context-handoff-bundle delete <bundle-id>  # remove specific bundle
```

---

## Drift Intelligence

This is the core differentiator. When you load a bundle, the tool doesn't just give you a summary -- it tells you how much of that summary is still safe.

```
## Drift
Severity: MEDIUM -- 8 commits, 12 files touched, 2 finding(s) at risk.

Files changed (12):
- src/auth/middleware.ts
- src/auth/session.ts
- tests/auth.test.ts
...

Evidence anchors affected:
- src/auth/middleware.ts CHANGED
- docs/auth-spec.md GONE

Findings that may be stale:
- F2 Auth middleware uses JWT with 24h expiry -- Evidence file changed
- F4 Session tokens stored in httpOnly cookies -- Evidence file changed

Recommendations that may be unsafe:
- Migrate to refresh token rotation -- Repo changed significantly
```

**Severity levels:**
- **NONE** -- Bundle matches current repo state
- **LOW** -- Minor changes, findings likely still valid
- **MEDIUM** -- Significant changes, some findings at risk
- **HIGH** -- Major divergence, many findings may be outdated

---

## Per-Section Confidence

Instead of one overall score, the resume shows confidence where it matters:

```
Section confidence:
- Findings: mixed (2/6 at risk)
- Evidence: partial (2/8 affected)
- Recommendations: STALE
- Overall: MEDIUM - some drift
```

This tells you: trust the findings that aren't flagged, re-check the two that are, and don't act on the recommendations without verifying first.

---

## Quality Scoring

Every bundle is scored on trustworthiness, not prettiness.

| Dimension | Weight | What it measures |
|-----------|--------|-----------------|
| Evidence coverage | 3x | Do findings point to real source files? |
| Open question honesty | 2.5x | Does the bundle admit what it doesn't know? |
| Repo specificity | 2.5x | Is this about a real project, not filler? |
| Findings substance | 2x | Are findings specific and actionable? |
| Resume usability | 2x | Does the resume actually help? |
| Completeness | 1x | Are files present with real content? |
| Markdown clarity | 1x | Is the narrative readable? |
| Entity richness | 0.5x | Structural extras (nice to have) |
| Relation richness | 0.3x | Structural extras (nice to have) |

Evidence, honesty, and specificity are weighted 3-5x more than structural completeness. A bundle with strong evidence and honest uncertainties scores higher than a pretty bundle with vague findings.

**Ratings:**
- **strong** (>= 0.6) -- Trust it for continuation
- **acceptable** (>= 0.35) -- Usable, may have gaps
- **weak** (< 0.35) -- Saved but flagged

---

## Claude Code Integration

Slash commands for [Claude Code](https://docs.anthropic.com/en/docs/claude-code):

```
/handoff-save    Author a notes file from the session, then save a handoff bundle
/handoff-load    Load and resume from a saved handoff
/handoff-list    List available bundles
/handoff-show    Inspect a specific bundle
```

**Setup (global — available in any project):**

```bash
cp commands/handoff-*.md ~/.claude/commands/
```

**Setup (project-local — available only in this repo):**

```bash
cp commands/handoff-*.md .claude/commands/
```

All logic lives in the Python CLI, not in the prompt text. The command files are thin wrappers.

**Important — `/handoff-save` requires `--notes`:** The CLI cannot see your conversation. When you run `/handoff-save`, Claude Code will author a structured notes file from the live session (findings, evidence, open questions) and pass it to the CLI via `--notes`. Saving without notes falls back to a blind directory scan and produces a low-quality stub. See the notes format in [Richer Bundles from Notes](#richer-bundles-from-notes) below.

---

## Storage

```
Repo-local:  .context-handoffs/index.json     (per-repo, gitignored)
Global:      ~/.context-handoff-bundles/index.json   (cross-repo)
```

Bundles are stored in registry-backed directories with `index.json` for fast lookup by ID, slug, title, repo, or tags. `save` defaults to the global store for cross-terminal portability. `load` searches both stores. Use `--repo-local` to force project-scoped storage.

Set `CONTEXT_HANDOFF_HOME` to relocate the global store (the test suite uses this so it never touches your real bundles).

Ambiguous queries surface options instead of guessing.

---

## Bundle Format

Each bundle is a directory of structured files:

| File | Purpose |
|------|---------|
| `CONTEXT_HANDOFF.md` | Human-readable narrative |
| `summary.json` | Findings, recommendations, resume instructions |
| `entities.json` | Normalized entities (projects, modules, concepts) |
| `relations.json` | Typed relationships between entities |
| `evidence_index.json` | Source file anchors backing findings |
| `open_questions.json` | Uncertainties with verification paths |
| `resume_prompt.txt` | Bootstrap prompt for fresh sessions |
| `bundle_metadata.json` | Git state, tags, quality score |

Plain JSON and Markdown. No proprietary formats. No cloud. No API keys.

---

## Richer Bundles from Notes

For maximum quality, save from structured session notes:

```bash
context-handoff-bundle save --title "Architecture review" --notes notes.md
```

```markdown
## Scope
Cross-service auth consolidation review.

## Projects mentioned
- API Gateway
- Auth Service
- User Service

## Findings
- Auth middleware duplicated across 3 services with subtle differences
- Session tokens use inconsistent expiry across services
- Gateway handles rate limiting but auth service doesn't

## Open questions
- Should we consolidate to a shared auth library or API gateway middleware?
- What's the migration path for existing session tokens?

## Evidence anchors
- api-gateway/src/middleware/auth.ts
- auth-service/src/handlers/session.ts
- user-service/src/middleware/verify.ts
```

---

## All Commands

| Command | Purpose |
|---------|---------|
| `save` | Generate, score, and store a handoff bundle |
| `save --update` | Refresh the latest bundle with current context |
| `save --notes <file>` | Generate from structured session notes |
| `load [query]` | Resolve and emit operational resume context |
| `load --deep` | Full context mode with all evidence |
| `diff <a> <b>` | Compare two bundles, show evolution |
| `list` | List stored bundles with quality ratings |
| `show <query>` | Inspect a single bundle in detail |
| `score <path>` | Recompute quality score |
| `prune` | Remove old duplicates per slug |
| `delete <query>` | Remove a specific bundle |
| `validate <path>` | Check bundle files and JSON schemas |
| `init` | Create bundle directory from templates |

---

## Architecture

```
src/context_handoff_bundle/
  cli.py           CLI commands and argument parsing
  autocontext.py   Task-aware repo context gathering
  storage.py       Registry-backed bundle store
  quality.py       Weighted trustworthiness scoring
  drift.py         File-level drift analysis
  freshness.py     Age and branch checks
  resume.py        Operational resume composition
  compare.py       Bundle-to-bundle comparison
  tokens.py        Token estimation (resume cost vs source re-read)
  templates/       Bundle file templates
  schemas/         JSON schemas for validation
```

---

## Design Principles

1. **No fake certainty.** If evidence is weak, say so. If nothing is uncertain, warn "suspiciously certain."
2. **No silent guessing.** Ambiguous queries surface options. Stale bundles surface drift.
3. **Code over prompts.** Core logic in Python, not trapped in prompt text.
4. **Orient, don't flood.** Load gives you re-entry guidance, not a document dump.
5. **Disk-backed.** Everything on disk. No hidden session state. Works across terminals.
6. **Trustworthiness over prettiness.** Quality scores weight evidence and honesty, not formatting.

---

## Works With Any AI Coding Agent

The CLI and bundle format are agent-agnostic. Any tool that can run a shell command and read JSON/Markdown can use this. The slash commands target Claude Code, but the core is portable.

---

## Contributing

PRs welcome. See [docs/ROADMAP.md](docs/ROADMAP.md) for current status and planned work.

Priority areas:
- Sharper auto-context from deeper repo analysis
- Richer drift intelligence (test result comparison, config changes)
- Multi-session bundle merging
- Integrations for Cursor, Copilot, Aider, Windsurf

## License

MIT
