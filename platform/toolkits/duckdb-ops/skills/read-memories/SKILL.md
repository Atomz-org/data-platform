---
name: read-memories
description: Recover context from earlier sessions in THIS project.
---
# Reading memories

Scoped to this project on purpose: session logs stay inside the project so
recovering context can never leak a sister's business logic.

Look in `.memory/notes/` (one lesson per file) and `decisions/` (ADRs explaining
*why* a grain or a metric filter is what it is). The ADRs are indexed in the
knowledge graph — `kg_search` finds them.

Prefer the context card and the graph over log archaeology; the card exists so
you do not have to reconstruct state. Reach for memories when the question is
"why was it done this way", which the graph cannot answer.

When you learn something durable, write it to `.memory/notes/` as one lesson per
file with a one-line summary on top. Promotion into group or platform rules is a
reviewed, human step — do not edit `platform/` yourself.
