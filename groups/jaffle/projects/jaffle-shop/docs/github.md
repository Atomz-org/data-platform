# GitHub integration — jaffle/jaffle-shop

`pf impact-gate` runs on every PR that touches this project's models or sources.
A change with a breaking blast radius fails the check and names the exposure
owners who need to know.

## What it does not do
It does not open PRs, comment on them, or read repository contents beyond the
diff. Those need a token; this needs none, because it runs inside the repo's own
CI. Add write-scoped automation as a separate capability rather than widening
this one — the whole point of the gate is that it cannot be talked out of a
verdict by the thing it is gating.
