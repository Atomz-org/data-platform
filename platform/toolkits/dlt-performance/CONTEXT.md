---
when: A dlt pipeline is slow and needs diagnosis or tuning.
rules:
  - Measure before tuning; the bottleneck is usually extraction or normalisation, not the load.
---

# dlt-performance

Most pipeline slowness is upstream of the warehouse. Tuning the load first is the
common wasted afternoon.
