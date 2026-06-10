# Changelog

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
