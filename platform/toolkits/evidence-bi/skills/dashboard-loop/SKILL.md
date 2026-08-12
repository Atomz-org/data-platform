---
name: dashboard-loop
description: Iterate a dashboard to a world-class standard — draft, score, critique, fix, repeat until it converges. Use when the ask is open-ended about quality ("make this great", "improve this page", "review this dashboard").
---
# The dashboard loop

A dashboard is not finished by one pass. It is finished when a fixed set of checks
stops finding anything and a reader can answer the page's question without asking
a follow-up.

**It terminates** because most of the bar is mechanically checkable —
`pf report audit` scores it — so each pass either moves the score or it does not.
What the score cannot see is judged once per pass against the list below, not
re-litigated freely.

```
0. FRAME     one sentence: who reads this, to decide what
1. DRAFT     build against the anatomy in `build-dashboard`
2. SCORE     pf report audit <group> <project>
3. CRITIQUE  the six questions below, once, in order
4. FIX       the single highest-cost finding, then re-score
5. STOP      when the exit conditions are met
```

## The six critique questions

1. **Does the top of the page answer the page's question?** A reader who leaves
   after four seconds should have the answer.
2. **Is every number governed?** Any figure not traceable to `queries/metrics/`
   is a finding, not a shortcut.
3. **Is any comparison missing its baseline?** A number without a prior period,
   a target or a peer is decoration.
4. **Does any chart encode a job it is wrong for?** Time on a bar chart, category
   on a line, a pie past three slices.
5. **Would this survive being wrong?** If the number moved 20%, would the page
   show why, or only that it moved?
6. **What is on the page that no one will act on?** Delete it.

## Exit conditions — stop when all hold

- `pf report audit` reports no errors.
- Two consecutive passes changed nothing material.
- Every KPI has a comparison or an explicit reason it has none.
- The page answers one question, and a reader could state it back.

**A pass that changes nothing is the signal to stop, not to look harder.**
Record what you rejected and why in `decisions/` — the next pass should not
re-litigate it.
