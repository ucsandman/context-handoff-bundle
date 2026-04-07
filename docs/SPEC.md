# Context Handoff Bundle Spec

This project packages expensive session understanding into a reusable bundle.

## Required files
- `CONTEXT_HANDOFF.md`
- `summary.json`
- `entities.json`
- `relations.json`
- `evidence_index.json`
- `open_questions.json`
- `resume_prompt.txt`

## Optional files
- `graph.json`
- `sources.json`
- `diff-from-prior.md`

## Core idea
Different files serve different purposes:
- narrative orientation
- structured summary
- entity registry
- typed relationships
- evidence anchors
- uncertainty preservation
- resume bootstrap

## Bundle directory pattern
- `YYYY-MM-DD-slug/`

Example:
- `2026-04-06-portfolio-synthesis/`

## Quality bar
A good bundle lets a fresh agent answer:
- what work was done?
- what was learned?
- what matters now?
- what should not be re-researched from scratch?
- what still needs verification?

See templates and schemas for concrete structure.
