---
description: Save a durable context handoff bundle for the current project/session.
argument-hint: [title-or-slug] [--global|--repo-local] [--tag TAG]
---

Save a durable context handoff for the current working context.

## Instructions

Run the `context-handoff-bundle save` CLI command to create and store a handoff bundle.

1. Parse user arguments. Map positional text to `--title`. Pass `--global`, `--repo-local`, `--tag` flags through.
2. Run the command:

```bash
context-handoff-bundle save --title "<title>" [--slug <slug>] [--tag <tag>] [--global|--repo-local]
```

If no title is provided, use the current project directory name.

3. The command outputs JSON with: bundle_id, title, path, storage_mode, quality, score, warnings.
4. Present the result concisely:
   - Bundle ID and where it was saved
   - Quality rating and score
   - Any warnings (these are honest quality signals, not errors)
5. If quality is "weak", tell the user the bundle was saved but may not be reliable for continuation.

**Do not** manually generate bundle files. The CLI handles all generation, scoring, and registry persistence.

If the CLI is not installed, tell the user to run `pip install -e .` from the context-handoff-bundle repo.
