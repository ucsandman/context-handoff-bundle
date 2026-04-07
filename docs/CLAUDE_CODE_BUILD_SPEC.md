# Build Spec: Context Handoff Bundle -> Claude Code Slash Command Workflow

## Purpose

Turn `context-handoff-bundle` from an early notes-driven prototype into a production-usable workflow where Wes can:

1. finish meaningful work in Claude Code
2. run a slash command to save a high-quality handoff bundle
3. open a different Claude Code terminal later
4. run a slash command to load that saved handoff
5. continue work without repeating deep repo research or subagent discovery

The target state is not just "generate a summary." The target state is:

**durable, reusable, cross-terminal session continuity with structured evidence and strong enough quality that it materially replaces repeated warm-up research.**

---

# Product Goal

## End-user outcome

Wes should be able to do this:

```bash
/handoff-save
```

and Claude Code will create a strong handoff bundle for the current project/session.

Then later, in a different terminal or Claude Code session, Wes should be able to do:

```bash
/handoff-load
```

or:

```bash
/handoff-load latest
/handoff-load portfolio-synthesis
/handoff-load 2026-04-06-portfolio-synthesis
```

and Claude Code will load the stored handoff, orient itself quickly, and continue from it.

## Success condition

A saved handoff should be strong enough that a fresh session no longer needs broad exploratory repo rereads or subagent research just to regain architectural context.

Not literally perfect in the abstract. Perfect in the practical sense:
- enough accuracy
- enough evidence
- enough structure
- enough continuity
- enough retrieval ergonomics

that Wes can trust it as the default continuation path.

---

# Current Repo State

Repo path:
- `C:\Users\sandm\clawd\projects\context-handoff-bundle`

Current status:
- repo scaffold exists
- bundle templates exist
- starter schemas exist
- CLI supports `init`, `generate`, `validate`
- generation currently works from structured notes files
- validation currently checks files, JSON validity, and schema conformance

Current weakness:
- generation is still too shallow
- there is no real Claude Code slash command integration yet
- there is no bundle registry/index for cross-terminal reuse
- there is no high-confidence load/resume flow yet

---

# Build This In Phases

## Phase 1 - Make the generator actually good

The current notes-driven generator is a decent scaffold, but it is not enough.

### Required upgrades

#### 1.1 Add richer source ingestion
Support generation from more than one input mode.

Implement at least these:
- `generate --notes <file>`
- `generate --notes-dir <dir>`
- `generate --sources-manifest <json>`
- `generate --bundle-dir <existing-dir>` for regeneration/update

Manifest format should support:
- paths
- repo roots
- important docs
- artifacts created during the session
- optional priority/role labels for evidence weighting

#### 1.2 Improve entity extraction
Current entities are just project names from notes.
That is too weak.

Add extraction layers for:
- projects
- repos
- subsystems
- packages/modules
- major documents/specs
- recurring concepts
- workflows/commands
- risks/open questions

Do not try to solve full ontology design yet. Keep it pragmatic.

#### 1.3 Improve relation extraction
Current relation generation is too thin.

Need multiple useful relation types, such as:
- `depends_on`
- `implements`
- `documents`
- `candidate_for_integration_with`
- `overlaps_with`
- `supersedes`
- `uses`
- `produces_artifact`
- `raises_question_about`
- `supports_claim`

Relations must carry:
- source
- target
- relation type
- confidence
- why
- evidence anchors

#### 1.4 Improve evidence mapping
Every meaningful finding should point back to actual evidence.

At minimum support evidence anchors for:
- file paths
- line ranges when available
- repo-relative references
- artifact references
- session-created docs

The bundle should never pretend unsupported claims are proven.

#### 1.5 Improve markdown handoff quality
`CONTEXT_HANDOFF.md` should become the best human entry point.

It should clearly answer:
- what this work was about
- what was actually learned
- what matters now
- what not to redo
- what still needs verification
- what the next agent should inspect first

The markdown should be concise but not skeletal.

---

## Phase 2 - Add a durable bundle registry for save/load

This is the key step for cross-terminal reuse.

We need a storage and indexing layer, not just folders lying around.

### Required deliverables

#### 2.1 Standard storage location
Design a canonical bundle store.

Support both:
- repo-local storage
- user/global storage

Recommended shape:

Repo-local:
- `.context-handoffs/`

User-global:
- `~/.context-handoff-bundles/`

Each bundle should be stored in its own directory.

#### 2.2 Bundle index / registry
Implement a registry file so load commands can resolve bundles quickly.

Examples:
- `index.json`
- or one file per bundle plus a generated index

Registry should support lookup by:
- bundle id
- slug
- title
- repo path
- tags
- created_at
- updated_at
- latest-for-repo
- latest-for-branch if possible

#### 2.3 Bundle metadata model
Extend `bundle_metadata.json` to include:
- bundle id
- title
- slug
- created_at
- updated_at
- repo roots
- branch if available
- source inputs
- generator version
- tags
- quality score if computed
- summary excerpt
- canonical storage path

#### 2.4 Load resolution logic
Implement deterministic bundle selection rules.

`handoff-load` should support:
- exact id
- exact slug
- `latest`
- latest for current repo
- latest for current repo + branch if available
- interactive/manual selection fallback if ambiguous

If ambiguous, do not guess silently.

#### 2.5 Cross-terminal portability
A bundle created in one terminal must be loadable from another terminal without session-local memory.

That means:
- everything needed must live on disk
- registry must be discoverable from a fresh environment
- loading must not depend on hidden chat state

---

## Phase 3 - Claude Code slash command integration

This project needs to become native-feeling inside Claude Code.

### User-facing commands to build

#### 3.1 `/handoff-save`
This command should:
- inspect the current repo/project context
- gather relevant source artifacts
- generate a high-quality handoff bundle
- validate it
- store it in the registry
- return a short success summary with the bundle id/path/title

Support optional args like:
- `/handoff-save`
- `/handoff-save latest-work`
- `/handoff-save --title "DashClaw architecture checkpoint"`
- `/handoff-save --tag dashclaw --tag architecture`
- `/handoff-save --global`
- `/handoff-save --repo-local`

#### 3.2 `/handoff-load`
This command should:
- resolve the correct bundle
- read the most important files from it
- inject a concise orientation summary into the Claude Code continuation flow
- expose the evidence and open questions
- avoid dumping raw giant files unless requested

Support:
- `/handoff-load`
- `/handoff-load latest`
- `/handoff-load <slug-or-id>`
- `/handoff-load --repo-current`
- `/handoff-load --list`

#### 3.3 `/handoff-list`
Useful for debugging and human trust.

Should show:
- recent bundles
- title
- repo
- created date
- tags
- score/status

#### 3.4 `/handoff-show`
Show details for one bundle:
- metadata
- top findings
- open questions
- evidence summary

#### 3.5 `/handoff-delete` or archive support
Optional for now. Prefer archive over delete.
Do not make deletion the main path.

---

## Phase 4 - Define what “good enough to trust” means

We need a quality gate. Wes should not save junk and then trust junk later.

### Required quality rubric in code

Implement a scoring/evaluation pass over generated bundles.

Possible dimensions:
- completeness
- evidence coverage
- entity richness
- relation richness
- open question honesty
- resume usability
- markdown clarity
- repo specificity

Output should include:
- pass/fail or strong/warning
- quality score
- warnings

Examples of warnings:
- too few evidence anchors
- no open questions
- too few entities for repo size
- no relations extracted
- handoff too generic
- too little repo-specific detail

### Required behavior
If the bundle is weak:
- do not pretend it is excellent
- surface warnings clearly
- still allow save if requested, but mark it low confidence

---

## Phase 5 - Make load actually useful inside Claude Code

This is the whole point.

Loading must not just open files. It must orient the agent.

### Load behavior requirements

When loading a bundle, create a compact resume context that includes:
- one short executive summary
- top findings
- top current recommendations
- open questions
- priority evidence anchors to inspect first
- explicit "do not re-research these from scratch unless evidence is stale" guidance

### Deliverables

#### 5.1 Resume prompt composer
Generate a compact resume prompt from the bundle.

This should be derived from:
- `summary.json`
- `CONTEXT_HANDOFF.md`
- `open_questions.json`
- `evidence_index.json`
- bundle metadata

The result should be optimized for fast continuation, not long archival reading.

#### 5.2 Fast-load mode vs deep-load mode
Support two modes:

Fast load:
- minimal orientation
- best for jumping back in

Deep load:
- more detailed context block
- best when resuming a complex architecture thread

#### 5.3 Freshness handling
On load, warn if:
- bundle is old relative to repo changes
- current branch differs
- important evidence files no longer exist
- repo hash/status appears drifted

Do not silently trust stale bundles.

---

# Slash Command Implementation Requirements

Because this is specifically for Claude Code, implement the slash commands in a way that is natural for that environment.

## Requirements
- commands should be easy to install/use locally
- command output should be concise and human-usable
- commands should call the local CLI rather than duplicate core logic in command files
- command definitions should be thin wrappers around the real Python logic
- all durable logic belongs in the repo codebase, not trapped in prompt text

## Likely implementation shape
Something like:
- `.claude/commands/handoff-save.md`
- `.claude/commands/handoff-load.md`
- `.claude/commands/handoff-list.md`
- `.claude/commands/handoff-show.md`

Each slash command should:
1. gather minimal args
2. call the local tool / repo script
3. present the result cleanly
4. keep the real behavior in Python code

Do not build a prompt-only toy. Build a real tool with thin prompt wrappers.

---

# CLI/Product Features To Add

## New CLI commands
Implement these commands in the Python tool:

### `save`
Higher-level than `generate`.
Should be the durable user-facing save path.

Responsibilities:
- infer repo context
- gather source artifacts
- run generation
- run quality evaluation
- persist bundle
- register bundle in the registry

### `load`
Resolve bundle and emit a compact, Claude-ready resume output.

Responsibilities:
- bundle lookup
- freshness checks
- resume prompt construction
- optional file previews

### `list`
List stored bundles with filters.

### `show`
Detailed inspection of a bundle.

### `score`
Optional but useful.
Recompute quality score and warnings.

### `compare`
Stretch goal but very valuable.
Compare two bundles and summarize drift.

---

# Storage Design Requirements

## Bundle store
Support configurable store locations via config/env.

Needs:
- default store path
- repo-local override
- global override

## Config file
Add config support, probably one of:
- `context_handoff_bundle.json`
- TOML config
- or env vars plus sane defaults

Store at least:
- default storage mode
- global store path
- repo-local store path name
- validation strictness
- load mode default

## Suggested defaults
- repo-local store: `.context-handoffs/`
- global store: `~/.context-handoff-bundles/`
- registry file: `index.json`

---

# Data Model Expectations

## Bundle ID
Every saved bundle needs a stable id.
Could be:
- timestamp + slug
- UUID
- hash-based id

Just make it stable and unambiguous.

## Tags
Support tags.
Useful for:
- project names
- architecture
- strategy
- consolidation
- audit
- repo review

## Repo awareness
Capture repo details when available:
- repo root
- branch
- maybe HEAD commit
- dirty/clean state

This is important for freshness checks later.

---

# Non-Negotiable Quality Rules

1. **No fake certainty.** If evidence is weak, mark it weak.
2. **No silent ambiguity resolution.** If multiple bundles match, surface ambiguity.
3. **No prompt-only magic.** Core logic must live in code, not only slash-command prose.
4. **No giant raw dumps by default.** Load should orient, not flood.
5. **No loss of evidence links.** Major findings should point somewhere.
6. **No hidden session dependency.** Cross-terminal load must work from disk.
7. **No pretending the bundle is fresh if repo state drifted.**

---

# Concrete Deliverables

## Required code deliverables
- improved generator pipeline
- registry/index implementation
- bundle storage abstraction
- `save` CLI command
- `load` CLI command
- `list` CLI command
- `show` CLI command
- quality scoring/evaluation
- freshness checks
- Claude Code slash command files
- config support
- tests for save/load/validate flows

## Required doc deliverables
- update `README.md`
- add slash command install/use docs
- add storage model docs
- add quality scoring docs
- add troubleshooting doc for stale bundles / ambiguous loads

## Required example deliverables
- at least one realistic saved handoff example
- at least one load example
- at least one ambiguity resolution example

---

# Suggested Execution Order

1. implement bundle registry and storage model
2. implement `save` command on top of current generator
3. implement `load` command with resume prompt output
4. implement `list` and `show`
5. add quality scoring
6. add freshness checks
7. wire Claude Code slash commands
8. improve generation depth
9. add tests and polish docs

Reason:
- save/load ergonomics matter more first than extraction perfection
- once save/load exists, Wes can start actually using the system
- then quality can be iterated upward from real usage

---

# Definition of Done

This build is done when all of the following are true:

1. In Claude Code, Wes can run `/handoff-save` after meaningful work.
2. That command stores a bundle on disk in a durable registry-backed location.
3. In another terminal/session, Wes can run `/handoff-load` and recover the work.
4. The loaded result is strong enough that broad warm-up rereads are usually unnecessary.
5. The system warns honestly about stale or weak bundles.
6. The implementation is code-driven, not prompt-only.
7. The workflow works repeatedly across terminals and sessions.

---

# Important Product Heuristic

Do not optimize for abstract elegance first.
Optimize for this very real question:

**Can Wes stop paying the repeated tax of re-explaining a repo to Claude Code every time he opens a new terminal?**

If the answer becomes yes, the project is succeeding.

---

# Immediate Next Step For Claude Code

Start by implementing the durable storage and registry layer plus these commands:
- `save`
- `load`
- `list`
- `show`

Then wire thin Claude Code slash command wrappers around them.

That is the shortest path to making this genuinely useful.
