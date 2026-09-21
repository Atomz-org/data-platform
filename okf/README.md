# OKF parallel-run experiment

Not part of the platform. This folder is a one-time comparison: real data
from this repository, converted into [Open Knowledge Format](https://github.com/GoogleCloudPlatform/knowledge-catalog/blob/main/okf/SPEC.md)
bundles and run through [Atomz-org/okf](https://github.com/Atomz-org/okf),
to answer a concrete question — could any of this platform's hand-built
knowledge systems (the graph, the context cards, the vendor registry, the
docs corpus) be replaced by OKF's tooling instead.

Start with **[REPORT.md](REPORT.md)** for the findings. Everything else here
is the evidence:

```
convert_docs.py           docs/*.md (16 files)          -> bundles/docs
convert_vendor.py         registry.yaml (24 upstreams)  -> bundles/vendor
convert_graph_sample.py   jaffle-shop's Table layer      -> bundles/graph-sample
bundles/context-cards/    6 real kg/context_card.md files, converted inline

bundles/    the converted OKF bundles themselves
runs/       captured JSON output of every okf command run against them
```

Read-only for the rest of the platform: nothing here is wired into `pf`,
`gate.yaml`, or any CI workflow. `okf` itself is not vendored or committed —
build it from `github.com/Atomz-org/okf` (`go build ./cmd/okf`) to
reproduce any command in `REPORT.md`.
