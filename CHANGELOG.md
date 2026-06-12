# Changelog

## 0.3.0 (2026-06-12)

### Fixed
- **False-GONE drift alarms.** Drift treated composite evidence anchors (`file.py:59 — note`, `git commit 4a135d2 on main`) as literal filesystem paths, so every anchor was reported GONE, every finding flagged stale, and severity escalated to HIGH on perfectly healthy bundles. Anchors are now parsed by a shared parser (`anchors.py`): locator split from the note, `:line`/`:start-end` suffixes stripped, URLs/commits/commands/prose classified and never existence-checked as files.
- **Basename over-matching.** A changed `b/route.ts` no longer marks an anchor on `a/route.ts` as changed; matching is exact repo-relative paths.
- **Blanket staleness flags removed.** Findings are flagged only when their own anchors changed or disappeared; recommendations only when the majority of checkable anchors drifted. Raw commit volume is reported as context, never as "everything is stale".
- Commit anchors are verified with `git cat-file -e` (a commit that is the current HEAD can no longer be reported GONE).

### Added
- **Verified anchors.** `save` now resolves each file anchor against the repo and stores a content hash of the referenced line range (`content_hash`, `resolved_path`, `line_start`/`line_end`, `verified_at_save` in `evidence_index.json`). `load` re-hashes and reports per-anchor status: `verified` / `ok` / `changed` / `gone` / `n/a`. Line-range hashing means unrelated edits elsewhere in a file do not invalidate the anchor. Still zero LLM calls.
- `save` output includes an `anchors` summary and warns about file anchors that did not resolve, so bad paths get fixed at save time instead of poisoning every future load.
- Compact drift reporting: low-impact drift (repo moved, anchors intact) collapses to two lines instead of pages of warnings.

### Changed
- Resume output deduplicated: recommendations appear once (Next Moves, not also Pressure + Drift), and Must Reverify drops items that duplicate Open Questions. Healthy loads are meaningfully smaller.
- Recommendation confidence is no longer downgraded by commit count alone.

## 0.2.0 (2026-06-10)

### Added
- **Token accounting.** Every `save` and `load` now reports estimated token costs: bundle size, resume size, and the estimated cost of re-deriving the same context from source files (`chars/4` heuristic). `load` prints a `[tokens]` summary line with the savings percentage.
- `token_estimates` block in `bundle_metadata.json` and in `save`/`load --json` output.
- `CONTEXT_HANDOFF_HOME` environment variable to relocate the global store. The test suite uses it, so running `pytest` no longer writes into your real `~/.context-handoff-bundles` store.
- GitHub Actions CI: test matrix across Ubuntu/Windows/macOS and Python 3.10-3.13.

### Fixed
- **Installed-package crash.** `templates/` and `schemas/` now ship inside the package, so `init` and schema validation work from a normal `pip install` instead of only from a repo checkout.
- Test runs previously left junk bundles in the real global store; they are now isolated to a temp directory.

## 0.1.0 (2026-04-06)

- Initial release: save/load/list/show/diff/score/prune/delete/validate/init.
- Task-aware auto-context gathering, weighted quality scoring, drift intelligence, per-section confidence, bundle comparison, operational resume output.
- Global + repo-local registry-backed stores, Claude Code slash commands.
