---
description: Load a saved context handoff bundle and resume from it.
argument-hint: [latest|slug|bundle-id] [--deep]
---

Load a saved context handoff bundle and orient from it.

## Instructions

Run the `context-handoff-bundle load` CLI command to resolve and load a bundle.

1. Parse user arguments. Map positional text to the query argument. Pass `--deep` through if requested.
2. Run the command:

```bash
context-handoff-bundle load [query] [--deep]
```

If no query is provided, the tool loads the latest bundle for the current repo.

3. The command outputs a formatted resume context with:
   - Executive summary
   - Key findings
   - Open questions
   - Freshness warnings (if any)
   - Guidance on what not to re-research

4. Present the resume context directly to orient yourself.
5. If there are freshness warnings, surface them clearly before proceeding.
6. If the result says "ambiguous match", show the user the candidates and ask them to pick one.

**Do not** manually read bundle files. The CLI handles resolution, freshness checks, and resume composition.

If the CLI is not installed, tell the user to run `pip install -e .` from the context-handoff-bundle repo.
