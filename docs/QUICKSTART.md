# Quickstart

## 1. Create a starter bundle

```bash
context-handoff-bundle init --slug portfolio-synthesis --with-graph
```

## 2. Generate a starter bundle from structured notes

```bash
context-handoff-bundle generate examples/sample-notes.md --output examples --slug portfolio-synthesis --title "Portfolio Synthesis" --with-graph
```

## 3. Validate a bundle

```bash
context-handoff-bundle validate examples/2026-04-06-portfolio-synthesis
```

## Notes format

For `generate`, the easiest input is a markdown file with sections like:
- `## Scope`
- `## Projects mentioned`
- `## Findings`
- `## Opportunities`
- `## Open questions`
- `## Evidence anchors`

Use bullet lists under those headings.

## Current reality

This is an early prototype.
It is useful for creating a starter handoff bundle, not for perfect semantic extraction.
