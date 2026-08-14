"""Grading a typed agent response against a case's expectations.

The agents return Pydantic models, not prose, which is what makes grading
mechanical: there is no "did it mention X" fuzziness to argue about, only
whether `root_cause` is the literal we expected. That is deliberate — an eval
suite whose pass/fail depends on an LLM judge inherits the judge's variance and
its bill, and for classification into four known classes it buys nothing.

Where fuzziness is unavoidable — a `summary`, a `suggested_fix` — the matchers
stay deliberately weak (`contains`, `not_contains`). A case that pinned exact
prose would fail on a harmless rewording, and a suite that cries wolf gets
turned off.

The one non-obvious matcher is `references_only`, which exists because the
sharpest failure mode of a generation step is not being wrong, it is being
plausible: a proposed metric over a column that does not exist reads perfectly
and breaks at compile time.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from pydantic import BaseModel


@dataclass(frozen=True)
class GradeFailure:
    """One unmet expectation, phrased so the report needs no other context."""

    path: str
    matcher: str
    expected: Any
    actual: Any

    def __str__(self) -> str:
        return (f"{self.path}: expected {self.matcher} {self.expected!r}, "
                f"got {self.actual!r}")


class _Missing:
    """Sentinel for a path that does not resolve. Distinct from a `None` value —
    "the field is absent" and "the field is null" are different bugs."""

    def __repr__(self) -> str:
        return "<missing>"


MISSING = _Missing()


def resolve(obj: Any, path: str) -> Any:
    """Resolve a dotted path, where `[]` maps the rest over a list.

    `proposals[].metric_type` on a `MetricProposals` yields the list of every
    proposal's type, so one expectation can constrain a whole collection.
    """
    current: Any = obj
    for i, segment in enumerate(path.split(".")):
        mapped = segment.endswith("[]")
        key = segment[:-2] if mapped else segment

        if key:
            current = _attr(current, key)
            if current is MISSING:
                return MISSING

        if mapped:
            if not isinstance(current, list):
                return MISSING
            rest = ".".join(path.split(".")[i + 1:])
            if not rest:
                return current
            resolved = [resolve(item, rest) for item in current]
            return [r for r in resolved if r is not MISSING]
    return current


def _attr(obj: Any, key: str) -> Any:
    if isinstance(obj, BaseModel):
        return getattr(obj, key, MISSING)
    if isinstance(obj, dict):
        return obj.get(key, MISSING)
    return getattr(obj, key, MISSING)


def grade(parsed: Any, expect: dict[str, Any]) -> list[GradeFailure]:
    """Check every expectation against a parsed response.

    A refusal or an unparseable response arrives here as `None` and fails every
    expectation rather than being skipped — "the model refused" is a result, and
    a suite that silently passed on it would hide a prompt that had become
    unanswerable.
    """
    failures: list[GradeFailure] = []
    for path, spec in expect.items():
        if parsed is None:
            failures.append(GradeFailure(path, "a response", spec, None))
            continue
        actual = resolve(parsed, path)
        failures.extend(_check(path, actual, spec))
    return failures


def _check(path: str, actual: Any, spec: Any) -> list[GradeFailure]:
    # A bare scalar means equality. This keeps the common case — the whole point
    # of a classification eval — as short as the documented format promised.
    if not isinstance(spec, dict):
        return _elementwise(path, actual, "equals", spec, lambda v: v == spec)

    out: list[GradeFailure] = []
    for matcher, want in spec.items():
        out.extend(_apply(path, actual, matcher, want))
    return out


def _apply(path: str, actual: Any, matcher: str, want: Any) -> list[GradeFailure]:
    match matcher:
        case "equals":
            return _elementwise(path, actual, matcher, want, lambda v: v == want)

        case "one_of":
            return _elementwise(path, actual, matcher, want, lambda v: v in want)

        case "not":
            return _elementwise(path, actual, matcher, want, lambda v: v != want)

        case "contains":
            return _elementwise(path, actual, matcher, want,
                                lambda v: isinstance(v, str)
                                and str(want).lower() in v.lower())

        case "not_contains":
            return _elementwise(path, actual, matcher, want,
                                lambda v: isinstance(v, str)
                                and str(want).lower() not in v.lower())

        case "contains_any":
            return _elementwise(
                path, actual, matcher, want,
                lambda v: isinstance(v, str)
                and any(str(w).lower() in v.lower() for w in want))

        case "matches":
            import re

            pattern = re.compile(want)
            return _elementwise(path, actual, matcher, want,
                                lambda v: isinstance(v, str)
                                and bool(pattern.search(v)))

        case "count" | "min_count" | "max_count":
            return _count(path, actual, matcher, want)

        case "any":
            # At least one element satisfies the nested matcher. Used where a
            # collection must contain something without over-specifying the rest.
            if not isinstance(actual, list):
                return [GradeFailure(path, matcher, want, actual)]
            if any(not _check(path, item, want) for item in actual):
                return []
            return [GradeFailure(path, "any element to satisfy", want, actual)]

        case "all":
            if not isinstance(actual, list):
                return [GradeFailure(path, matcher, want, actual)]
            return [f for item in actual for f in _check(path, item, want)]

        case "references_only":
            return _references_only(path, actual, want)

        case _:
            raise ValueError(
                f"unknown matcher {matcher!r} at {path!r}. Known: equals, one_of, "
                f"not, contains, not_contains, contains_any, matches, count, "
                f"min_count, max_count, any, all, references_only")


def _elementwise(path: str, actual: Any, matcher: str, want: Any,
                 ok: Any) -> list[GradeFailure]:
    """Apply a predicate, mapping over a list path so `field[].x` needs no
    special-casing in every matcher."""
    if actual is MISSING:
        return [GradeFailure(path, matcher, want, MISSING)]
    if isinstance(actual, list):
        bad = [v for v in actual if not ok(v)]
        return [GradeFailure(path, matcher, want, bad)] if bad else []
    return [] if ok(actual) else [GradeFailure(path, matcher, want, actual)]


def _count(path: str, actual: Any, matcher: str, want: Any) -> list[GradeFailure]:
    if not isinstance(actual, list):
        return [GradeFailure(path, matcher, want, actual)]
    n = len(actual)
    ok = {"count": n == want, "min_count": n >= want, "max_count": n <= want}[matcher]
    return [] if ok else [GradeFailure(path, matcher, want, n)]


def _references_only(path: str, actual: Any, allowed: list[str]) -> list[GradeFailure]:
    """Fail if a generated expression names an identifier outside `allowed`.

    The hallucination check. A metric whose expression references a column the
    mart does not have is the failure mode that structured output cannot catch:
    the schema is satisfied, the types are right, and it breaks at compile time.

    The allowlist is written out explicitly in the case rather than parsed back
    out of the input. Deriving it would mean this grader and the fixture could
    drift apart while still agreeing with each other, which is the one way a
    hallucination check can quietly stop checking anything.
    """
    import re

    permitted = {a.lower() for a in allowed}
    values = actual if isinstance(actual, list) else [actual]
    offenders: list[str] = []

    for value in values:
        if not isinstance(value, str):
            continue
        for ident in re.findall(r"[A-Za-z_][A-Za-z0-9_]*", value):
            low = ident.lower()
            if low in permitted or low in _SQL_WORDS:
                continue
            offenders.append(ident)

    if offenders:
        return [GradeFailure(path, "references_only", allowed, sorted(set(offenders)))]
    return []


# Ignored by `references_only`: SQL and MetricFlow grammar, not column names.
_SQL_WORDS = {
    "sum", "count", "count_distinct", "avg", "min", "max", "median", "case",
    "when", "then", "else", "end", "and", "or", "not", "null", "is", "in",
    "distinct", "cast", "as", "coalesce", "nullif", "true", "false",
    "metric", "dimension", "entity", "measure", "date_trunc", "day", "week",
    "month", "quarter", "year",
}
