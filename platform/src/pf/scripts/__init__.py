"""Runnable scripts that are also importable.

Each module here has a `main()` and a library entry point, so the same code
serves a shell, the `pf` CLI and a Dagster asset. Anything that a scheduler
runs belongs here rather than inside a Dagster asset body: an asset that holds
the only copy of a procedure cannot be run by hand when the scheduler is the
thing that is broken.
"""
