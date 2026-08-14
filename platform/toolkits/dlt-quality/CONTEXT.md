---
when: Adding schema contracts or statistical monitors to a pipeline.
rules:
  - Contracts are deterministic and fail at load; monitors are statistical and some deviation is normal.
  - A monitor that always warns and is never acted on is worse than no monitor.
---

# dlt-quality

Two layers that catch different failures. A contract refuses a type change at
load time. A monitor notices that today's volume is unlike every other day's, and
is a signal to weigh rather than an assertion to enforce.

Treating a monitor like a contract trains the team to ignore the channel that
will eventually carry a real failure.
