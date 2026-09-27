"""One module per agent harness — adding a harness is adding a module.

Each module here declares a `SPEC` (`pf.harnesses.base.Spec`): the configs it
renders from the shared sources, its scorecard row(s), and — once the harness
has hooks — its dialect and tool vocabulary for `pf.harness_adapters`.
Discovery is by module, so nothing else is edited when one is added: not
`pf.harness`, not the adapters, not the hook entry point.
"""

from __future__ import annotations

import importlib
import pkgutil
from functools import cache

from pf.harnesses.base import Ctx, Spec

__all__ = ["Ctx", "Spec", "spec", "specs"]


@cache
def specs() -> tuple[Spec, ...]:
    found = []
    for m in pkgutil.iter_modules(__path__):
        if m.name.startswith("_") or m.name == "base":
            continue
        found.append(importlib.import_module(f"{__name__}.{m.name}").SPEC)
    return tuple(sorted(found, key=lambda s: (s.order, s.key)))


def spec(key: str) -> Spec | None:
    return next((s for s in specs() if s.key == key), None)
