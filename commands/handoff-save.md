---
description: Save a durable context handoff bundle for the current project/session.
argument-hint: "[title-or-slug] [--global|--repo-local] [--tag TAG]"
---

Save a durable context handoff for the current working context.

## Instructions

The point of a handoff bundle is to preserve THIS session's understanding so another terminal
or session can resume. The CLI cannot see the conversation — only you can. So you MUST author a
structured notes file from the live session and pass it with `--notes`. Saving without
`--notes` makes the CLI fall back to a blind directory scan and produces an empty, useless stub.
Never call `save` without `--notes`.

1. Parse user arguments. Map positional text to `--title`. Pass `--global`, `--repo-local`,
   `--tag` through. If no title is provided, use the current project directory name.

2. Author a notes file capturing the actual session, then write it to a working path such as
   `<repo-or-cwd>/.handoff-notes-<slug>.md`. It MUST use these exact `##` headings (the parser
   only reads these) with `- ` bullets under each list section:

   ```markdown
   # Handoff Notes: <title>

   ## Scope
   <1-3 sentences: what this session was about, what was decided, where it paused>

   ## Projects Mentioned
   - <each repo / project / component touched — these become entities>

   ## Findings
   - <each substantive thing established this session; one self-contained statement per bullet>

   ## Opportunities
   - <concrete next opportunities or improvements surfaced>

   ## Open Questions
   - <unresolved questions; include the immediate next step before this handoff>

   ## Evidence Anchors
   - <file path, file:line, URL, or command backing each claim — these populate evidence_index
     and are what lift the score out of "unsupported findings">
   ```

   Write real content from the conversation, not placeholders. Thin or empty sections produce a
   low-quality bundle.

3. Run the command WITH the notes file:

   ```bash
   context-handoff-bundle save --title "<title>" --notes "<path-to-notes>" [--slug <slug>] [--tag <tag>] [--global|--repo-local]
   ```

4. The command outputs JSON with: bundle_id, title, path, storage_mode, quality, score, warnings.
5. Present the result concisely:
   - Bundle ID and where it was saved
   - Quality rating and score
   - Any warnings (these are honest quality signals, not errors)
6. If quality is "weak"/"acceptable" or warnings mention unsupported findings / no evidence
   anchors, your notes were too thin — add more Findings and Evidence Anchors and re-save with
   `--update <bundle-id-or-slug>` (reuses the title/slug/store and supersedes the prior save).

**Do not** hand-edit the generated bundle files (CONTEXT_HANDOFF.md, summary.json, entities.json,
etc.) — the CLI generates those from your notes. Your job is the `--notes` file and the `save`
call.

If the CLI is not installed, tell the user to run `pip install -e .` from the
context-handoff-bundle repo.
