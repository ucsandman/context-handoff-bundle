# Operator Guide

## 30-second version

```bash
pip install -e .                                           # install
context-handoff-bundle save --title "what you worked on"   # save
# ... close terminal, come back later ...
context-handoff-bundle load                                # resume
```

That's it. The tool handles context gathering, quality scoring, drift detection, and resume formatting.

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
| Repo-local | `.context-handoffs/` | Per-project bundles (default) |
| Global | `~/.context-handoff-bundles/` | Cross-project bundles |

Both use `index.json` registries. `load` searches both. Override with `--global` or `--repo-local`.

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

Available in Claude Code when `.claude/commands/handoff-*.md` is present (repo-local or `~/.claude/commands/`):

- `/handoff-save` -- calls `context-handoff-bundle save`
- `/handoff-load` -- calls `context-handoff-bundle load`
- `/handoff-list` -- calls `context-handoff-bundle list`
- `/handoff-show` -- calls `context-handoff-bundle show`

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
- Save from `--notes` for the strongest bundles, bare `save` for quick checkpoints
