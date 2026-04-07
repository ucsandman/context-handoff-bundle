# How to Create Real-World Before/After Examples

This guide walks you through capturing compelling before/after examples that show the time savings of Context Handoff Bundle on real projects.

## What makes a good before/after

The goal is to show:
- **Before:** A fresh Claude Code session spending 5-15 minutes re-reading files, re-discovering architecture, re-asking questions you already answered yesterday.
- **After:** A fresh Claude Code session that loads a handoff and immediately knows what's going on, what changed, and what to do next.

The contrast should be obvious and honest.

## Step-by-step

### 1. Pick a real project with real complexity

Best candidates:
- A project you've been actively working on for at least a few sessions
- Something with 10+ files across multiple directories
- A project where you've made architectural decisions that take time to re-explain

Good examples from your repos:
- DashClaw (Next.js dashboard + agent governance)
- ClawdBot/OpenClaw (autonomous agent with multiple integrations)
- Context Handoff Bundle itself

### 2. Capture the "before" session

Open a **fresh** Claude Code terminal in the project. Record what happens:

```
Terminal 1 (fresh, no handoff):
> "Continue the auth middleware refactor from yesterday"

Claude Code will:
- Read README.md, CLAUDE.md
- Scan directory structure
- Read 5-10 source files to understand architecture
- Ask clarifying questions about what was done
- Maybe re-read files you already discussed yesterday
- Take 5-15 minutes before doing anything useful
```

**How to capture this:**
1. Start a fresh Claude Code session
2. Give it a continuation prompt like "Continue working on [specific task]"
3. Watch what it does -- count the files it reads, the questions it asks
4. Note the time before it does anything productive
5. Screenshot or copy the first ~20 tool calls

Save this as `examples/before-session-[project].md`:

```markdown
# Before: Fresh session on [Project] without handoff

## Prompt given
"Continue the auth middleware refactor"

## What Claude Code did
1. Read README.md (orientation)
2. Read CLAUDE.md (project rules)
3. Read src/middleware/auth.ts (finding the code)
4. Read src/routes/api.ts (understanding usage)
5. Read tests/auth.test.ts (checking test state)
6. Asked: "What changes have been made so far?"
7. Read git log (trying to figure out recent work)
8. Read src/middleware/session.ts (more context)
9. Asked: "Which auth approach are we using?"
10. Read docs/auth-spec.md
...

## Time to first productive action
~8 minutes

## Context it had to rebuild from scratch
- Project architecture
- Auth middleware design decisions
- What was already tried
- Which tests are passing/failing
- What the next steps were
```

### 3. Save a handoff at the end of a real work session

At the end of a productive session (or mid-session), save a handoff:

```bash
# From notes (strongest):
context-handoff-bundle save \
  --title "DashClaw auth middleware refactor" \
  --notes session-notes.md \
  --tag dashclaw --tag auth

# Or auto-context (still good):
context-handoff-bundle save \
  --title "DashClaw auth middleware refactor" \
  --tag dashclaw --tag auth
```

### 4. Capture the "after" session

Open a **new** Claude Code terminal in the same project. This time, load first:

```
Terminal 2 (with handoff):
> /handoff-load

Claude Code immediately sees:
- State: what the project is, what was established
- Drift: 2 commits since save, tests/auth.test.ts changed
- Section confidence: Findings strong, Evidence partial (1 file changed)
- Open First: src/middleware/auth.ts, src/routes/api.ts
- Must Reverify: session token storage approach (evidence changed)
- Next Moves: 1. Complete token rotation, 2. Add integration tests

> "Continue working on the auth middleware refactor"

Claude Code immediately starts working -- no re-reading, no re-asking.
```

**How to capture this:**
1. Open fresh terminal, run `/handoff-load` (or `context-handoff-bundle load`)
2. Copy the resume output
3. Give the same continuation prompt as the "before" session
4. Note how quickly it starts productive work
5. Count tool calls before first productive action

Save as `examples/after-session-[project].md`:

```markdown
# After: Fresh session on [Project] with handoff

## Handoff loaded
[paste the resume output here]

## Prompt given
"Continue the auth middleware refactor"

## What Claude Code did
1. Loaded handoff (instant)
2. Noted drift: 2 commits, tests changed
3. Read src/middleware/auth.ts (guided by "Open First")
4. Started implementing token rotation (guided by "Next Moves")

## Time to first productive action
~30 seconds

## Context it didn't need to rebuild
- Project architecture (from handoff State)
- Auth design decisions (from handoff Findings)
- Which tests matter (from handoff Evidence)
- What to do next (from handoff Next Moves)
```

### 5. Create the comparison summary

Combine both into `examples/before-after-[project].md`:

```markdown
# Before/After: [Project] Session Recovery

## The task
"Continue the auth middleware refactor from yesterday"

## Without handoff
- 10+ files read for orientation
- 2 clarifying questions asked
- ~8 minutes before productive work
- Had to re-discover: architecture, decisions, test state, next steps

## With handoff
- Resume loaded in <1 second
- 1 file read (guided by drift report)
- ~30 seconds before productive work
- Already knew: architecture, decisions, what changed, what to do

## Time saved
~7 minutes per session restart

## What made the difference
- Drift report showed exactly what changed (not "go re-read everything")
- Section confidence told it which findings to trust
- "Open First" pointed to the 2 files that actually matter
- "Next Moves" gave specific actions, not generic "review the codebase"
```

### 6. Tips for the strongest examples

**Do:**
- Use real projects, not toy repos
- Be honest about what the handoff gets wrong (builds trust)
- Show the drift report catching something useful
- Show confidence marking something as stale
- Time both sessions with a real clock

**Don't:**
- Cherry-pick unrealistically perfect saves
- Hide cases where the handoff missed something
- Compare against a deliberately bad "before" session
- Fake the timing

**Best contrast points:**
- "Before" session reads 12 files. "After" reads 2 (guided).
- "Before" asks "what were you working on?" "After" already knows.
- "Before" misses that tests changed. "After" drift report flags it.
- "Before" re-researches architecture. "After" trusts findings, verifies incrementally.

### 7. Where to put the examples

```
examples/
  before-after-dashclaw.md        # The comparison summary
  before-session-dashclaw.md       # Raw "before" capture
  after-session-dashclaw.md        # Raw "after" capture  
  dashclaw-session-notes.md        # The notes used for save (if any)
```

Then reference them from README.md.

### 8. Quick-start: do it right now

The fastest path to one example:

1. Open a fresh Claude Code terminal in DashClaw
2. Ask: "What is this project and what was I working on most recently?"
3. Time how long it takes to get a useful answer
4. Save notes about what it read and asked
5. Run `context-handoff-bundle save --title "DashClaw checkpoint" --tag dashclaw`
6. Close that terminal
7. Open a new one, run `context-handoff-bundle load`
8. Ask the same question
9. Compare the two experiences

That's your first before/after.
