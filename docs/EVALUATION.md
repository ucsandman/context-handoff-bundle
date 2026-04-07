# Bundle Evaluation Rubric

Use this rubric to judge whether a generated Context Handoff Bundle is actually useful.

## Core questions

### 1. Orientation
Can a fresh session understand in under 5-10 minutes:
- what the work was about?
- what was already done?
- why it matters?

### 2. Reuse
Can a fresh session continue without re-reading entire repos or repeating the same research immediately?

### 3. Trust
Are major claims backed by evidence anchors?
Are uncertainties clearly marked instead of hidden?

### 4. Structure
Do `entities.json` and `relations.json` represent real reusable structure, or just fluff copied from prose?

### 5. Resume quality
Does `resume_prompt.txt` actually help a new session start well?

## Red flags
- transcript-like bloat
- vague entities
- weak or generic relations
- conclusions without evidence
- no open questions
- bundle exists but still forces full re-research

## Pass condition
A bundle passes if it materially reduces warm-up cost for a fresh session and preserves the main conclusions with acceptable trust.
