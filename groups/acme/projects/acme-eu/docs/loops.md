# Loops — acme/acme-eu

The platform's agents watch this project on a schedule. What they find goes to
`STATE.md`; what they *propose* becomes a pull request once the loop has earned
that right. Nothing here merges on its own.

```bash
pf loop list acme acme-eu          # every loop, born vs earned level
pf loop run-all acme acme-eu       # run them, refresh STATE.md
pf loop ladder acme acme-eu        # what blocks the next rung
pf loop proposals list                      # what loops proposed; accept / reject
pf ask acme acme-eu "revenue by month"   # governed metrics, no SQL
pf logs list acme acme-eu          # every agent run, traced
```

## Memory — `decisions/loop-memory.yaml`

What this project has decided about its own findings. A suppression needs a
reason and should have an expiry; `pf loop memory audit` lists the ones that do
not. Reviewed in pull requests like any decision. Memory filters findings and
nothing else — it cannot name a file or loosen a budget.

## Trace logs — `logs/trace/`

Every loop run, every question and every proposal writes a JSONL transcript:
intent, what the agent understood, the request, the response, each tool call
and result, each deterministic step. `pf logs show <run-id>` renders one.
The directory is gitignored; the ledger (`loop-ledger.json`) is what is committed.

## Delivery

`--notify` posts to the group's channel — `groups/acme/notify.yaml`, which
names an environment variable rather than holding the webhook URL.
