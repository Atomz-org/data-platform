# Generated expectations

Every `*.sql` here that opens with a GENERATED marker is derived from the
ontology — `contracts/annotations.yaml` maps columns to roles, and
`pf bootstrap` translates what those roles assert into dbt-expectations tests.
Edit the roles, not these files; regeneration discards edits and deletes tests
whose model or role has gone.

Sharper expectations — value ranges, accepted sets, distributions — are
judgements about one table. Declare them in that model's own yml with the
full dbt-expectations vocabulary (the package is installed project-wide).
