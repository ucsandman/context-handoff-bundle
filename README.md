# Context Handoff Bundle

**Stop re-explaining your codebase every time you open a new AI terminal.**

Context Handoff Bundle captures what your AI coding agent learned during a session -- architecture decisions, findings, evidence, open questions -- and packages it into a structured bundle that any future session can load in seconds.

```
Terminal 1 (done for the day):
$ context-handoff-bundle save --title "Auth refactor progress"

Terminal 2 (next morning):
$ context-handoff-bundle load
# Agent immediately knows: what was done, what's left, what not to re-research
```

No more wasting the first 15 minutes of every session on "let me look at the codebase..."

---

## The Problem

AI coding agents (Claude Code, Copilot, Cursor, Aider, etc.) build deep understanding of your codebase during a session:

- Which files matter and why
- How components connect
- What was tried and what worked
- What decisions were made and the reasoning behind them
- What's still uncertain

**All of that disappears when the session ends.**

The next session starts from zero. You re-explain context. The agent re-reads files. You repeat the same research. Every. Single. Time.

## The Solution

Context Handoff Bundle creates a structured, disk-backed package of session understanding that survives across terminals, sessions, and time.

```
save:  session understanding --> structured bundle --> registry
load:  registry --> bundle resolution --> freshness check --> resume context
```

It's not a chat log export. It's not a summary. It's a **structured knowledge package** with findings, evidence anchors, entity relationships, open questions, quality scores, and freshness checks.

---

## Install

```bash
pip install context-handoff-bundle
```

Or for development:

```bash
git clone https://github.com/ucsandman/context-handoff-bundle.git
cd context-handoff-bundle
pip install -e .
```

## Quick Start

### Save what your agent learned

```bash
context-handoff-bundle save --title "API migration analysis"
```

The tool automatically gathers:
- Project structure and tech stack
- Recent git history and uncommitted changes
- README and CLAUDE.md descriptions
- TODO/FIXME counts
- Evidence file paths

Quality score: `strong` / `acceptable` / `weak` -- with honest warnings if coverage is thin.

### Load it later, anywhere

```bash
# Load the latest bundle for this repo
context-handoff-bundle load

# Load by name
context-handoff-bundle load api-migration

# Deep load for complex architecture work
context-handoff-bundle load --deep
```

On load, the tool checks freshness:
- Has the branch changed?
- How many commits since the bundle was saved?
- Are referenced evidence files still there?
- Is the bundle older than 7 days?

**Stale bundles are never silently trusted.**

### See what's saved

```bash
context-handoff-bundle list
```
```
ID                                  Title                    Date         Quality    Store
--------------------------------------------------------------------------------------------
20260406-143022-api-migration       API Migration Analysis   2026-04-06   strong     repo-local
20260405-091544-auth-refactor       Auth Refactor Progress   2026-04-05   acceptable global
```

### Inspect a bundle

```bash
context-handoff-bundle show latest
```

### Update instead of accumulate

```bash
# Re-save with the same title/slug/tags as the latest bundle
context-handoff-bundle save --update
```

### Clean up old bundles

```bash
# Keep only the newest bundle per slug
context-handoff-bundle prune --keep 1

# Delete a specific bundle
context-handoff-bundle delete <bundle-id>
```

---

## Claude Code Integration

Drop-in slash commands for [Claude Code](https://docs.anthropic.com/en/docs/claude-code):

```
/handoff-save          Save a handoff for the current session
/handoff-load          Load and resume from a saved handoff  
/handoff-list          List available bundles
/handoff-show          Inspect a specific bundle
```

### Setup

Copy `.claude/commands/handoff-*.md` into your project's `.claude/commands/` or `~/.claude/commands/` for global access.

The slash commands are thin wrappers -- all logic lives in the Python CLI, not in prompt text.

---

## What's Inside a Bundle

Each bundle is a directory containing structured files that serve different purposes:

| File | Purpose |
|------|---------|
| `CONTEXT_HANDOFF.md` | Human-readable narrative -- read this first |
| `summary.json` | Structured summary with findings, recommendations, resume instructions |
| `entities.json` | Normalized entities (projects, repos, modules, concepts) |
| `relations.json` | Typed relationships between entities |
| `evidence_index.json` | Source file anchors backing the findings |
| `open_questions.json` | What's still uncertain -- with verification paths |
| `resume_prompt.txt` | Bootstrap prompt for a fresh agent session |
| `bundle_metadata.json` | Git state, tags, generator info, quality score |

**Why multiple files instead of one?** Different consumers need different things. A human reads the markdown. An agent parses the JSON. A quality check scans the evidence index. A single file is either too lossy or too rigid.

---

## Quality Scoring

Every bundle is scored across 8 dimensions:

| Dimension | What it measures |
|-----------|-----------------|
| Completeness | Are all required files present with real content? |
| Evidence coverage | Do findings point to actual source files? |
| Entity richness | Are enough entities extracted for the project size? |
| Relation richness | Are entity relationships captured? |
| Open question honesty | Does the bundle admit what it doesn't know? |
| Resume usability | Is the resume prompt actually useful? |
| Markdown clarity | Is the narrative handoff well-structured? |
| Repo specificity | Does the bundle contain repo-specific detail? |

Ratings:
- **strong** (>= 0.65) -- Good enough to trust for continuation
- **acceptable** (>= 0.4) -- Usable but may have gaps  
- **weak** (< 0.4) -- Saved but flagged -- don't rely on it without enrichment

**Zero fake certainty.** If evidence is weak, the tool says so. If no open questions exist, it warns "suspiciously certain."

---

## Storage Model

```
Repo-local:  .context-handoffs/index.json   (per-repo, gitignored)
Global:      ~/.context-handoff-bundles/index.json  (cross-repo)
```

Each store maintains a registry (`index.json`) for fast lookup by ID, slug, title, repo, or tags.

`save` defaults to repo-local if you're in a git repo. Override with `--global` or `--repo-local`.

`load` searches both stores. If the query is ambiguous (multiple matches), it tells you instead of guessing.

---

## Richer Bundles from Notes

For even stronger bundles, save from structured session notes:

```bash
context-handoff-bundle save --title "Architecture review" --notes session-notes.md
```

Notes format:
```markdown
## Scope
What this session covered.

## Projects mentioned
- Project A
- Project B

## Findings  
- Finding one with specific detail
- Finding two with evidence

## Opportunities
- What could be improved

## Open questions
- What still needs verification

## Evidence anchors  
- path/to/important/file.ts
- path/to/another/key/module.py
```

---

## All CLI Commands

| Command | Purpose |
|---------|---------|
| `save` | Generate, score, and store a handoff bundle |
| `save --update` | Regenerate the latest bundle with fresh context |
| `load` | Resolve a bundle and emit resume context |
| `list` | List stored bundles |
| `show` | Inspect a single bundle in detail |
| `score` | Recompute quality score for a bundle directory |
| `prune` | Remove old duplicates, keep newest per slug |
| `delete` | Remove a specific bundle |
| `validate` | Validate bundle files and JSON schemas |
| `init` | Create a new bundle directory from templates |
| `generate` | Generate a bundle from structured notes |

---

## Works With Any AI Coding Agent

While the slash commands are built for Claude Code, the CLI and bundle format are agent-agnostic. Any tool that can:

1. Run a shell command (`context-handoff-bundle save`)
2. Read the output files

...can use this for cross-session continuity.

The bundle format is plain JSON and Markdown -- no proprietary formats, no cloud dependencies, no API keys.

---

## Design Principles

1. **No fake certainty.** If evidence is weak, mark it weak.
2. **No silent ambiguity resolution.** If multiple bundles match, surface it.
3. **No prompt-only magic.** Core logic lives in code, not prompt text.
4. **No giant raw dumps.** Load orients, it doesn't flood.
5. **No hidden session dependency.** Everything lives on disk.
6. **No pretending bundles are fresh when the repo drifted.**

---

## Contributing

PRs welcome. The roadmap includes:

- Smarter entity/relation extraction from direct repo inspection
- Bundle comparison and drift tracking
- Source manifest ingestion for multi-input generation
- Integrations with other AI coding tools
- Bundle update/merge from multiple sessions

See [docs/ROADMAP.md](docs/ROADMAP.md) for the full list.

## License

MIT
