# Operator Note: How to Use Context Handoff Bundle

## The short version

1. Install: `pip install -e .` from this repo
2. Do meaningful work in Claude Code
3. Run `/handoff-save` (or `context-handoff-bundle save --title "your title"`)
4. Later, in a new terminal: `/handoff-load` (or `context-handoff-bundle load`)
5. Continue from where you left off

## What actually happens

**Save** generates a structured bundle with findings, entities, relations, evidence anchors, and open questions. It scores the bundle quality across 8 dimensions, stores it in a registry-backed location, and captures git state (branch, commit, dirty status).

**Load** resolves the best matching bundle, checks if it's still fresh relative to the current repo state, and emits a compact resume context. Freshness warnings tell you if the branch changed, commits advanced, or evidence files are missing.

## Storage locations

- **Repo-local (default):** `.context-handoffs/` in the git repo root
- **Global:** `~/.context-handoff-bundles/`

Each location has its own `index.json` registry. Both are searched on load.

## Quality levels

- **strong** (>=0.65): Good enough to trust for continuation
- **acceptable** (>=0.4): Usable but may have gaps
- **weak** (<0.4): Saved but flagged - don't rely on it without enrichment

## Tips

- Use `--notes <file>` to save from structured session notes for richer bundles
- Use `--tag` to organize bundles by project or topic
- Use `load --deep` for detailed context when resuming complex architecture work
- Use `show latest` to inspect what's in a bundle before loading
- Use `list` to see all available bundles across stores

## What makes a good handoff

The best handoffs come from sessions with structured notes that include:
- Clear findings with evidence
- Explicit open questions (not hidden uncertainty)
- Specific repo/file references
- Honest confidence assessments

A handoff saved from `--notes` with real evidence anchors will score much higher than a bare `save` with no context.

## Slash commands in other projects

Copy `.claude/commands/handoff-*.md` to any project's `.claude/commands/` directory. The CLI must be installed (`pip install -e /path/to/context-handoff-bundle`).
