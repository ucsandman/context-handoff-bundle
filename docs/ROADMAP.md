# Roadmap

## Phase 0 - Scaffold [DONE]
- [x] Repo structure, templates, schemas, minimal CLI, example bundles

## Phase 1 - Initialization [DONE]
- [x] Template-based init with metadata and optional graph

## Phase 2 - Validation [DONE]
- [x] JSON schema validation, markdown checks, human-readable output

## Phase 3 - Generation [DONE]
- [x] `generate` from structured notes
- [x] Task-aware auto-context (no notes required)

## Phase 4 - Storage and Registry [DONE]
- [x] Repo-local and global bundle stores with index.json
- [x] Resolution by id, slug, latest, partial match
- [x] Ambiguity detection, git-aware metadata capture

## Phase 5 - Save/Load/List/Show [DONE]
- [x] `save` with auto-generation, quality scoring, registry persistence
- [x] `save --update` to refresh latest bundle
- [x] `load` with resolution, drift analysis, operational resume output
- [x] `list`, `show`, `score`, `delete`, `prune`

## Phase 6 - Quality Scoring [DONE]
- [x] Weighted scoring (evidence 3x, honesty 2.5x, specificity 2.5x)
- [x] Findings substance dimension (penalizes generic filler)
- [x] Entity/relation de-weighted (0.3-0.5x)
- [x] Honest warnings for weak bundles

## Phase 7 - Drift Intelligence [DONE]
- [x] File-level drift since saved commit
- [x] Evidence anchor impact tracking (ok/changed/deleted)
- [x] Findings at risk with specific reasons
- [x] Recommendations that may be unsafe
- [x] Severity rating (none/low/medium/high)

## Phase 8 - Operational Resume [DONE]
- [x] State / Drift / Pressure / Open First / Must Reverify / Next Moves
- [x] Per-section confidence (Findings, Evidence, Recommendations, Overall)
- [x] Drift-aware finding annotations (strikethrough stale findings)

## Phase 9 - Bundle Comparison [DONE]
- [x] `diff` command comparing two bundles
- [x] New/gone findings, resolved questions, dropped recommendations
- [x] Evidence evolution tracking

## Phase 10 - Claude Code Integration [DONE]
- [x] Slash commands (handoff-save, handoff-load, handoff-list, handoff-show)
- [x] Thin wrappers calling real CLI tool
- [x] Global install to ~/.claude/commands/

## Phase 11 - Auto-Context Depth [DONE]
- [x] Branch work summarization
- [x] File-path area classification (not just commit keywords)
- [x] WIP detection (staged/modified/untracked)
- [x] Test failure detection
- [x] Hot file ranking

---

## Future

### Deeper Auto-Context
- [ ] Parse imports/exports for dependency-aware summaries
- [ ] Detect test coverage gaps from changed files
- [ ] Compare current test results to saved test results
- [ ] Config file change detection (env vars, build config)

### Richer Drift
- [ ] Test pass/fail comparison between save and load
- [ ] Semantic diff (not just file-level -- what kind of change)
- [ ] Drift-aware next moves (rewrite recommendations based on what changed)
- [ ] Auto-invalidation of specific findings when evidence files change

### Multi-Session
- [ ] Merge findings from multiple bundles
- [ ] Session chain tracking (bundle A -> B -> C lineage)
- [ ] Conflict resolution when parallel sessions produce bundles

### Agent Integrations
- [ ] Cursor integration
- [ ] Copilot Workspace integration
- [ ] Aider integration
- [ ] Windsurf integration
- [ ] Generic MCP server for any agent

### Entity/Relation Depth (when extraction is strong enough)
- [ ] AST-aware entity extraction
- [ ] Import graph relations
- [ ] Cross-file dependency mapping
