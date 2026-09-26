"""Throwaway probe for the agent-context refresh job; never merged.

Added without `pf test index`, so the test index is stale on purpose and the
`refresh` job must regenerate and push it.
"""


def test_the_refresh_job_probe() -> None:
    assert True
