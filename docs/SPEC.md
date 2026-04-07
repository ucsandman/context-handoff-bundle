# Context Handoff Bundle Spec

## Purpose

Package expensive AI session understanding into durable, structured bundles that survive across terminals, sessions, and time -- with drift detection that tells future sessions what's still safe to trust.

## Core concept

Different files serve different purposes in a handoff:
- Narrative orientation (CONTEXT_HANDOFF.md)
- Structured summary with resume instructions (summary.json)
- Entity registry (entities.json)
- Typed relationships (relations.json)
- Evidence anchors tying findings to source files (evidence_index.json)
- Honest uncertainty preservation (open_questions.json)
- Fast resume bootstrap (resume_prompt.txt)
- Git state and quality metadata (bundle_metadata.json)

## Bundle directory pattern

`{timestamp}-{slug}/` stored in a registry-backed location.

Example: `20260406-143022-auth-refactor/`

## Storage

| Store | Path | Purpose |
|-------|------|---------|
| Repo-local | `.context-handoffs/` | Per-project, gitignored |
| Global | `~/.context-handoff-bundles/` | Cross-project |

Each store has `index.json` for fast lookup by id, slug, title, repo, or tags.

## Required files

- `CONTEXT_HANDOFF.md`
- `summary.json`
- `entities.json`
- `relations.json`
- `evidence_index.json`
- `open_questions.json`
- `resume_prompt.txt`
- `bundle_metadata.json`

## Optional files

- `graph.json`
- `sources.json`

## Quality bar

A good bundle lets a fresh agent answer:
- What work was done?
- What was learned?
- What matters now?
- What should not be re-researched from scratch?
- What still needs verification?
- What changed since this was saved?

Quality is scored across 9 weighted dimensions prioritizing evidence coverage, open question honesty, repo specificity, and findings substance over structural completeness.

## Drift contract

On load, the system must answer:
- Which files changed since save?
- Which evidence anchors are affected?
- Which findings may be stale?
- Which recommendations may be unsafe?
- What is the overall drift severity?

Stale bundles are never silently trusted.

## Resume contract

The resume output is operational, not archival. It must provide:
- **State**: What's true, what was established
- **Drift**: What changed, severity, per-file detail
- **Section confidence**: Per-section trust levels (strong/partial/STALE)
- **Open First**: Which files to look at, guided by drift
- **Must Reverify**: What not to trust blindly
- **Next Moves**: Specific actions

## Non-negotiable rules

1. No fake certainty
2. No silent ambiguity resolution
3. Core logic in code, not prompt text
4. Orient on load, don't flood
5. Everything on disk, no hidden session state
6. Quality scores trustworthiness, not prettiness
7. Drift is surfaced, never hidden
