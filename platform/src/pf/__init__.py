"""pf — the shared platform: ontology, knowledge graph, runtime, MCP, UI."""

import warnings

__version__ = "0.1.0"

# sqlglot prints this on import, and dbt imports sqlglot, so it lands in the
# middle of `pf new-project`, `pf seed` and every dbt-backed command — a
# UserWarning in output an agent is reading for a result.
#
# It is suppressed rather than acted on because its advice is wrong *here*, and
# wrong in a way this repo has already paid for. `pyproject.toml` pins
# `sqlglot>=30.17.0` as an override specifically to keep `sqlglotc` out: Wren
# registers its own dialect by subclassing sqlglot's Parser in pure Python, and
# an interpreted class cannot inherit from a compiled one. With sqlglotc present
# every MDL query that resolved a model died in `CTERewriter.rewrite`, which
# reads like a broken engine and is a broken environment.
#
# Narrow on purpose: the message, not the category, and not the module. A blanket
# UserWarning filter here would silence warnings from dlt, dbt and duckdb that
# someone does need to see.
warnings.filterwarnings(
    "ignore",
    message=r".*sqlglot\[rs\] is deprecated.*",
    category=UserWarning,
)
