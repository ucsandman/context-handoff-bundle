# Roadmap

## Phase 0 - Scaffold
- [x] repo structure
- [x] starter templates
- [x] minimal CLI
- [x] example bundle
- [x] starter schemas

## Phase 1 - Better initialization
- [x] make `init` copy template content instead of blank placeholders
- [x] support optional graph file creation
- [x] add bundle metadata file

## Phase 2 - Validation
- [x] validate JSON files against schemas
- [x] validate markdown presence and basic headings
- [x] produce human-readable validation output

## Phase 3 - Generation
- [x] `generate` command from notes/artifacts
- [ ] source manifest ingestion
- [ ] evidence extraction helpers
- [ ] entity and relation normalization helpers

## Phase 4 - Durable storage and registry
- [x] repo-local and global bundle stores
- [x] index.json registry with fast lookup
- [x] bundle resolution by id, slug, latest, partial match
- [x] ambiguity detection (no silent guessing)
- [x] git-aware metadata capture (repo, branch, commit, dirty state)

## Phase 5 - Save/Load/List/Show commands
- [x] `save` command with auto-generation, quality scoring, registry persistence
- [x] `load` command with resolution, freshness checks, resume prompt output
- [x] `list` command with repo-local and global support
- [x] `show` command with quality and freshness display
- [x] `score` command for standalone quality evaluation

## Phase 6 - Quality and freshness
- [x] 8-dimension quality scoring
- [x] honest warnings for weak bundles
- [x] age-based freshness checks
- [x] branch and commit drift detection
- [x] evidence file existence verification

## Phase 7 - Claude Code integration
- [x] slash command wrappers (handoff-save, handoff-load, handoff-list, handoff-show)
- [x] commands call real CLI tool, not prompt-only logic
- [x] thin wrapper design

## Phase 8 - Comparison (future)
- [ ] compare two bundles
- [ ] detect changed findings/entities/relations
- [ ] emit drift summary

## Phase 9 - Deeper generation (future)
- [ ] smarter entity extraction from repo inspection
- [ ] stronger relation extraction
- [ ] source manifest ingestion for multi-input generation
- [ ] bundle update/regeneration from existing bundle + new context

## Phase 10 - Advanced integrations (future)
- [ ] optional graph export improvements
- [ ] optional memory-system adapters
- [ ] fleet-wide context sharing for multi-agent governance
