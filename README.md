# Context Handoff Bundle

**Stop re-explaining your codebase every time you open a new AI terminal.**

Context Handoff Bundle captures what your AI coding agent learned during a session and packages it into a structured, evidence-backed bundle that any future session can load in seconds -- with honest drift detection that tells you what's still safe to trust.

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

## Install

```bash
pip install context-handoff-bundle
```

Development:

```bash
git clone https://github.com/ucsandman/context-handoff-bundle.git
cd context-handoff-bundle
pip install -e .
```

Requires Python 3.10+. No external dependencies for core functionality.

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
  "warnings": []
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
/handoff-save    Save a handoff for the current session
/handoff-load    Load and resume from a saved handoff
/handoff-list    List available bundles
/handoff-show    Inspect a specific bundle
```

**Setup:** Copy `.claude/commands/handoff-*.md` to your project's `.claude/commands/` or `~/.claude/commands/` for global access. All logic lives in Python, not prompt text.

---

## Storage

```
Repo-local:  .context-handoffs/index.json     (per-repo, gitignored)
Global:      ~/.context-handoff-bundles/index.json   (cross-repo)
```

Bundles are stored in registry-backed directories with `index.json` for fast lookup by ID, slug, title, repo, or tags. `save` defaults to repo-local. `load` searches both stores.

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
