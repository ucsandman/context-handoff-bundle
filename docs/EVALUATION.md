# Bundle Evaluation Rubric

Use this rubric to judge whether a generated bundle is actually useful for session continuity.

## The real test

Load the bundle in a fresh terminal. Can you start productive work within 60 seconds instead of 10 minutes?

If yes, the bundle works. If you're still re-reading files and re-asking questions, it doesn't.

## Core questions

### 1. State clarity
Can a fresh session understand within 30 seconds:
- What the project is?
- What was being worked on?
- What's true right now?

### 2. Drift awareness
Does the load tell you:
- What changed since save?
- Which findings are still safe?
- Which evidence files moved?
- What severity of drift exists?

### 3. Evidence backing
Are major findings backed by specific file references?
Can you open those files and verify the claims?

### 4. Honest uncertainty
Are open questions real, not generic?
Does the bundle say "I don't know" where it should?
Does it warn "suspiciously certain" when no questions exist?

### 5. Actionable resume
Does the resume give you:
- Specific files to open first (not "review the codebase")?
- Specific next moves (not "verify assumptions")?
- Per-section confidence (not just one overall score)?

### 6. Re-entry speed
Can you skip the orientation phase?
Are the "do not re-research" signals clear?

## Quality dimensions (weighted)

| Dimension | Weight | Good | Bad |
|-----------|--------|------|-----|
| Evidence coverage | 3x | Findings point to real files | Claims with no sources |
| Open question honesty | 2.5x | Specific uncertainties named | No questions, or generic ones |
| Repo specificity | 2.5x | Project-specific detail | Could be about any project |
| Findings substance | 2x | Specific, verifiable claims | "Needs refinement" filler |
| Resume usability | 2x | Operational guidance | "Read the files" |
| Completeness | 1x | All files present | Missing key files |
| Markdown clarity | 1x | Well-structured narrative | Thin or disorganized |
| Entity richness | 0.5x | Relevant entities | Over-extracted noise |
| Relation richness | 0.3x | Meaningful relationships | Structure for its own sake |

## Red flags

- Generic findings that could apply to any project
- "Needs refinement" or "unknown" in the output
- No open questions (suspiciously certain)
- Evidence anchors that don't resolve to real files
- Recommendations without context (stale advice)
- Resume that says "read everything" instead of pointing somewhere specific
- Bundle that forces full re-research despite existing

## Pass condition

A bundle passes if:
1. Loading it materially reduces warm-up time (minutes, not seconds)
2. Drift detection correctly identifies what changed
3. Findings are specific enough to trust provisionally
4. Uncertainties are honest enough to avoid false confidence
5. The resume gives you a specific starting point, not a vague summary
