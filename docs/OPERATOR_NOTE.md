# Operator Guide

## 30-second version

```bash
pip install -e .                                           # install

# Best results: save with notes authored from the session
context-handoff-bundle save --title "what you worked on" --notes notes.md

# Quick checkpoint (lower quality — blind repo scan only):
context-handoff-bundle save --title "what you worked on"

# ... close terminal, come back later ...
context-handoff-bundle load                                # resume
```

The tool handles context gathering, quality scoring, drift detection, and resume formatting. Bundles with `--notes` score significantly higher because they capture what only the session knows.

## How save works

`save` does five things:
1. **Gathers context** from your repo (git history, active files, tech stack, WIP state, evidence anchors)
2. **Generates** a structured bundle (findings, entities, evidence, open questions, narrative markdown)
3. **Scores quality** across 9 weighted dimensions (evidence and honesty weighted highest)
4. **Stores** the bundle in a registry-backed location with git state metadata
5. **Reports** the result with quality rating and any warnings

For richer bundles, add `--notes session-notes.md` with structured findings.

## How load works

`load` does four things:
1. **Resolves** the right bundle (by id, slug, or latest for current repo)
2. **Analyzes drift** -- file-level diff against current repo, evidence anchor status, findings at risk
3. **Composes** an operational resume (State / Drift / Confidence / Open First / Must Reverify / Next Moves)
4. **Warns** about anything stale, missing, or changed

## What drift detection tells you

This is the key feature. On load, you see:
- Which files changed since save
- Which evidence anchors still exist, changed, or are gone
- Which findings may be stale (with the specific reason)
- Which recommendations may be unsafe
- Severity: NONE / LOW / MEDIUM / HIGH
- Per-section confidence: Findings strong, Evidence partial, Recommendations STALE

## Storage

| Location | Path | Purpose |
|----------|------|---------|
| Global | `~/.context-handoff-bundles/` | Cross-terminal bundles (default) |
| Repo-local | `.context-handoffs/` | Per-project bundles (`--repo-local`) |

Both use `index.json` registries. `load` searches both. The global store is the default so bundles are accessible from any terminal regardless of which directory it opened in.

## Useful commands

```bash
# Save
context-handoff-bundle save --title "description"
context-handoff-bundle save --title "description" --notes notes.md
context-handoff-bundle save --update                    # refresh latest bundle
context-handoff-bundle save --tag auth --tag refactor   # with tags

# Load
context-handoff-bundle load                # latest for this repo
context-handoff-bundle load auth-refactor  # by slug
context-handoff-bundle load --deep         # full context

# Inspect
context-handoff-bundle list
context-handoff-bundle show latest
context-handoff-bundle diff <bundle-a> <bundle-b>

# Manage
context-handoff-bundle prune --keep 1
context-handoff-bundle delete <bundle-id>
```

## Slash commands

Install globally (available in any Claude Code session):

```bash
cp commands/handoff-*.md ~/.claude/commands/
```

Or copy to `.claude/commands/` in a specific project for project-local access.

- `/handoff-save` -- authors a notes file from the live session, then calls `context-handoff-bundle save --notes <file>`
- `/handoff-load` -- calls `context-handoff-bundle load`
- `/handoff-list` -- calls `context-handoff-bundle list`
- `/handoff-show` -- calls `context-handoff-bundle show`

Note: `/handoff-save` requires Claude to author the notes — it cannot simply call `save` without `--notes` or the result will be a low-quality blind scan stub.

## Quality ratings

| Rating | Score | Meaning |
|--------|-------|---------|
| strong | >= 0.6 | Trust for continuation |
| acceptable | >= 0.35 | Usable, may have gaps |
| weak | < 0.35 | Saved but flagged |

Quality weights trustworthiness (evidence, honesty, specificity) over prettiness (formatting, entity count).

## Tips

- `save --update` avoids accumulating duplicates when iterating on the same work
- `prune --keep 1` cleans up test artifacts
- `diff` between two bundles shows what evolved (resolved questions, new findings)
- `load --deep` shows full evidence and assumptions -- useful for complex architecture work
- Always use `--notes` in Claude Code (the `/handoff-save` command handles this automatically); bare `save` is useful only for quick CLI checkpoints where quality doesn't matter
