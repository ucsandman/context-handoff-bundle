# Claude Code Execution Prompt

Use this prompt in Claude Code to continue building `context-handoff-bundle`.

---

Continue this project until it reaches a practical, high-value stopping point where I can use Claude Code slash commands to save and later load durable context handoffs across different terminals.

Repo:
`C:\Users\sandm\clawd\projects\context-handoff-bundle`

Read first:
- `README.md`
- `docs/SPEC.md`
- `docs/ROADMAP.md`
- `docs/EVALUATION.md`
- `docs/CLAUDE_CODE_BUILD_SPEC.md`

Your mission:
Build this from an early prototype into a real save/load continuity system for Claude Code.

Primary user-facing commands to enable:
- `/handoff-save`
- `/handoff-load`
- `/handoff-list`
- `/handoff-show`

Core outcome:
I should be able to finish meaningful work in one Claude Code terminal, save a high-quality handoff bundle to disk, open another Claude Code terminal later, load that handoff, and continue without redoing broad repo research.

Important constraints:
- Core behavior must live in code, not just prompt text.
- Slash commands should be thin wrappers over the real local tool.
- Handoffs must be durable and cross-terminal.
- Use disk-backed storage plus a registry/index.
- Support both repo-local and global storage.
- Include freshness checks and honest warnings for weak or stale bundles.
- Do not silently guess when bundle resolution is ambiguous.
- Do not fake certainty when evidence is weak.

Execution priorities:
1. implement durable storage + registry
2. implement CLI commands: `save`, `load`, `list`, `show`
3. implement quality scoring and freshness checks
4. wire Claude Code slash command wrappers
5. improve generation depth if time remains

Definition of done for this pass:
- repo has real `save/load/list/show` flows
- slash command wrappers exist
- handoffs can be stored and loaded across terminals
- load flow emits a useful resume context
- docs are updated to match behavior
- tests or smoke-test fixtures cover the critical workflow

Working style:
- inspect first
- plan explicitly
- implement in phases
- verify with real command runs
- update docs as part of the work
- do not stop at ideas if practical implementation is still reachable

When you finish, leave behind:
- updated code
- updated docs
- at least one realistic example bundle
- a short operator note explaining how to use the commands
