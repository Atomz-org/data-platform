# wren-analytics — a data question, answered through the semantic layer

Conversational analytics over one project's WrenAI MDL workspace
(`mdl/wren/`): the manifest an LLM may see, the rules it is handed, the
questions it answered before, and the gated road every new question takes.

- One project per question. The workspace, the ledger and the warehouse are
  the project's; nothing of another project is visible.
- A governed KPI is answered by its metric (`answer-with-metrics`) — this
  skill is for what no metric covers.
- Read the context first: rules outrank guesses, remembered answers outrank
  fresh plans.
- One read-only SELECT over MDL model names, run only through the gate:
  policy → plan → dry-run → execute → ledger. Never raw SQL, never a second
  connection.
- Three attempts per statement, counted by the ledger; the fourth escalates.
- Personal data is absent from the workspace by design; say so when a question
  needs it.
- A validated answer is stored as a tracked NL→SQL pair and reviewed like code.
