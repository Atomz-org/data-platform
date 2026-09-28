"""Guardrails AI bindings for the platform validators — present when the
package is, inert when it is not.

`guardrails-ai` is not a workspace dependency and is not going to be: it pulls
litellm, openai and a tokenizer stack that one lockfile cannot hold beside
dagster and dlt without the version fights `pyproject.toml` already documents
for openmetadata-ingestion. So the validators live in `pf.aidf.validators` with
no import of guardrails, and this module registers them under the names the
specification uses — `atomz/ast_sql_validator`, `atomz/pii_scrubber` — when a
session that has guardrails asks for them:

    uv run --with guardrails-ai python -c "from pf.aidf.guardrails_adapter import register; register()"

or, once the Atomz-org fork is pinned as a submodule (see docs/AIDF.md):

    uv run --with ./vendor/guardrails python ...

Nothing in the engine's decision changes with guardrails present. What it adds
is the `Guard` object — `build_guard()` — for callers that already run their
LLM through Guardrails and want the platform's rules in that pipeline.
"""

from __future__ import annotations

from typing import Any

from pf.aidf.validators import PiiScrubber, SqlAstValidator

_REGISTERED: dict[str, type] = {}


def available() -> bool:
    try:
        import guardrails  # noqa: F401
    except ImportError:
        return False
    return True


def register() -> dict[str, type]:
    """Register both validators with Guardrails. Idempotent; raises ImportError
    with an install hint when guardrails is absent."""
    if _REGISTERED:
        return dict(_REGISTERED)
    try:
        from guardrails.validator_base import (
            FailResult,
            PassResult,
            ValidationResult,
            Validator,
            register_validator,
        )
    except ImportError as exc:
        raise ImportError(
            "guardrails-ai is not installed; it is not a workspace dependency by design. "
            "Run with `uv run --with guardrails-ai ...` or `uv tool install guardrails-ai`."
        ) from exc

    def _fail(verdict) -> ValidationResult:
        return FailResult(error_message="; ".join(f"{f.code}: {f.message}" for f in verdict.errors))

    @register_validator(name="atomz/ast_sql_validator", data_type="string")
    class ASTSqlValidator(Validator):  # type: ignore[misc,valid-type]
        """Read-only, explicit, catalogue-bound SQL (pf.aidf.validators.SqlAstValidator)."""

        def __init__(self, allowed_columns: set[str] | None = None, dialect: str = "duckdb",
                     on_fail: Any = None, **kw: Any) -> None:
            super().__init__(on_fail=on_fail, allowed_columns=allowed_columns, dialect=dialect, **kw)
            self._impl = SqlAstValidator(dialect, allowed_columns=allowed_columns)

        def validate(self, value: Any, metadata: dict[str, Any] | None = None) -> ValidationResult:
            v = self._impl.validate(value if isinstance(value, str) else "")
            return PassResult() if v.ok else _fail(v)

    @register_validator(name="atomz/pii_scrubber", data_type="string")
    class PIIScrubber(Validator):  # type: ignore[misc,valid-type]
        """No e-mail, IP, token, key or IBAN in model output (pf.aidf.validators.PiiScrubber)."""

        def __init__(self, allow: list[str] | None = None, on_fail: Any = None, **kw: Any) -> None:
            super().__init__(on_fail=on_fail, allow=allow, **kw)
            self._impl = PiiScrubber(allow)

        def validate(self, value: Any, metadata: dict[str, Any] | None = None) -> ValidationResult:
            v = self._impl.validate(value if isinstance(value, str) else "")
            return PassResult() if v.ok else _fail(v)

    _REGISTERED.update({"atomz/ast_sql_validator": ASTSqlValidator, "atomz/pii_scrubber": PIIScrubber})
    return dict(_REGISTERED)


def build_guard(allowed_columns: set[str] | None = None, dialect: str = "duckdb", contract: str = "mart_metric"):
    """A Guardrails `Guard` over the platform contract with both validators on
    `on_fail="exception"`. For callers whose LLM already runs through Guardrails."""
    from guardrails import Guard

    from pf.aidf.schemas import CONTRACTS

    kinds = register()
    return (
        Guard.from_pydantic(output_class=CONTRACTS[contract])
        .use(kinds["atomz/ast_sql_validator"](allowed_columns=allowed_columns, dialect=dialect, on_fail="exception"))
        .use(kinds["atomz/pii_scrubber"](on_fail="exception"))
    )
