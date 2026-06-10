# Quickstart

## Install

```bash
pip install git+https://github.com/ucsandman/context-handoff-bundle.git
```

## 1. Save a handoff at the end of a session

From your project directory:

```bash
context-handoff-bundle save --title "Auth refactor progress"
```

This auto-gathers context from the repo (active areas, work in progress, recent history, evidence paths) and stores a scored bundle in the global store (`~/.context-handoff-bundles`).

For a much richer bundle, save from structured session notes:

```bash
context-handoff-bundle save --title "Auth refactor progress" --notes notes.md
```

Notes format -- a markdown file with bullet lists under these headings:

- `## Scope`
- `## Projects mentioned`
- `## Findings`
- `## Opportunities`
- `## Open questions`
- `## Evidence anchors`

See [examples/sample-notes.md](../examples/sample-notes.md).

## 2. Resume in any new terminal

```bash
context-handoff-bundle load              # latest for current repo
context-handoff-bundle load auth-refactor # by slug
```

You get an operational resume (state, drift since save, what to open first, next moves) plus a token line showing what the resume cost versus re-deriving the context from source:

```
[tokens] resume: ~640 | re-deriving from source (6 files): ~23.0k | saved: ~97% (chars/4 estimate)
```

## 3. Manage bundles

```bash
context-handoff-bundle list               # all bundles with quality ratings
context-handoff-bundle show latest        # inspect one
context-handoff-bundle diff <old> <new>   # what changed between two bundles
context-handoff-bundle prune --keep 1     # clean old duplicates
```

## Claude Code users

Copy the slash commands once and use `/handoff-save` and `/handoff-load` in any session:

```bash
cp commands/handoff-*.md ~/.claude/commands/
```

See the [README](../README.md) for the full command reference, drift intelligence, and quality scoring details.
