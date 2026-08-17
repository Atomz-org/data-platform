"""The control plane as one deployable: Postgres, OpenMetadata, Dagster, recce.

Three services that were three unrelated deployments — a JVM catalogue, a Python
orchestrator, a per-project review server — sharing one database, one origin and
one image.

- `pf.stack.storage` moves Dagster's run/event/schedule storage off SQLite and
  onto OpenMetadata's Postgres, in its own schema.
- `pf.stack.frontdoor` generates the nginx and supervisor configuration that
  puts all three UIs on one port.

Both are pure renderers: they take the project roster and return text. What
writes the files is `pf stack render`, and what runs them is
`platform/Containerfile.stack`.
"""

from pf.stack import frontdoor, storage

__all__ = ["frontdoor", "storage"]
