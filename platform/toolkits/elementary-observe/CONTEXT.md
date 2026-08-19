# elementary-observe — data observability with Elementary

Declaring anomaly monitors on models, and triaging what the recording says.
Every dbt build here records itself into the `main_elementary` schema (the
`elementary` tool is on by default); these skills are how that recording gets
*used* rather than merely collected.

- A test asserts a rule; a monitor learns a baseline and flags departures. Add
  monitors where a rule cannot be written down.
- Anomaly monitors are `severity: warn` — an anomaly is a question, not a
  verdict. A monitor that pages on every marketing campaign gets deleted.
- Triage reads the elementary tables (queryable history), not the log output
  of the run that happened to fail.
