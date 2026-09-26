# Governance

## Policies

| policy | severity | rule |
|---|---|---|
| `agent-authority-is-least-privilege` | error | An agent reaches the filesystem through one path gate, and the paths it may never write are declared rather than remembered. Least privilege that lives in a pro |
| `agent-authority-is-revocable` | error | A control that cannot be switched off mid-incident is a control you find out about afterwards. Revocation is checked before intent is written, and an unreadable |
| `agent-decisions-are-recorded` | error | Every tool call an agent makes is written down before it happens and after it happens, and the gate's verdict is recorded for allows as well as denies. "No rule |
| `agent-settings-schema-valid` | error | A settings file the client rejects loads none of the plugins it declares, and says so nowhere a session can see. The platform's own retrieval tools arrive as pl |
| `anomaly-tests-do-not-gate-merge` | error | An anomaly test judges data; a merge gate judges code. Wiring a statistical test into the gate blocks a correct change because yesterday's load was small, and t |
| `builds-record-observability` | warning | A dbt build that leaves no queryable record cannot be triaged; failures get diagnosed from whichever log happened to survive. Every build must record its run an |
| `change-declares-blast-radius` | error | A model or column change must report what it breaks before it lands, including the human who owns each affected exposure. |
| `change-verified-against-baseline` | warning | A blast radius is a prediction made from lineage. Lineage cannot say whether the numbers actually moved, so a change to a mart must also be compared against a b |
| `control-baseline-is-declared` | error | A risk register that names controls nobody enforces is a document. Each entity declares in `air.yaml` which controls it commits to; those are derived from the r |
| `dev-server-binds-localhost-only` | blocks | A development database served on a routable interface is an exfiltration endpoint with a bearer token. The endpoint is localhost by construction — the host is n |
| `dev-serving-wire-is-read-only` | blocks | Whatever arrives over the quack wire cannot mutate the warehouse. The server holds the database read-only, so the engine refuses writes at the catalog — not a p |
| `entity-isolation-enforced` | error | Business logic does not transfer between entities. A session that can read a sister project will carry an assumption across — a grain, a status enum, a revenue |
| `entity-requires-identity` | error | A class with no identity property cannot participate in a derived join, so every BI and MDL projection of it is a guess. |
| `evidence-chain-is-tamper-evident` | error | A log an agent can edit is not evidence. Each record carries the hash of the one before it, and the head is anchored to a timestamp authority with no stake in w |
| `high-impact-actions-need-a-human` | error | Human oversight is a chain that shows the approval, not a document that asserts it. Approvals are append-only and bound to the action they approve, and an actor |
| `link-must-be-in-topology` | error | A foreign key pointing at a class the topology does not relate to is an undeclared join. Undeclared joins are how two teams compute different revenue from the s |
| `mart-declares-grain` | warning | Grain is the one fact a downstream consumer cannot infer and cannot survive guessing. An undeclared grain is how a join silently fans out. |
| `metric-owns-aggregation` | warning | Aggregation policy — which statuses count, which timestamp, which filter — belongs to exactly one metric definition. A mart column named `revenue` is a second d |
| `model-routing-is-declared` | warning | Which model answers which step is a declared table, not whatever the caller passed. An unregistered step is recorded as such, and the recorded verdict matches w |
| `money-amount-bounded` | warning | A monetary column with no lower bound accepts the negative row that a refund, a sign flip or a bad join produces, and it reaches a metric as a quietly smaller n |
| `money-requires-currency` | error | A monetary amount without its currency is not a number, it is a bug waiting for a second entity to be onboarded. |
| `pii-not-in-consumption` | error | PII may land in raw and staging. It must not reach a mart or an exposure without a masking policy or an explicit, recorded waiver. |
| `quack-token-never-leaves-the-machine` | blocks | The serving token is a bearer credential for the dev warehouse. It is generated fresh per server, lives only in a 0600 state file beside the database, is gitign |
| `quality-floor-derived-from-ontology` | warning | Hand-written test coverage decays to whichever models someone remembered. The floor — an annotated mart is never empty, a declared identity identifies — must be |
| `review-artifacts-exclude-pii` | error | A value-level diff writes the rows it compared into the review tool's state file, which is durable and shared. Diffing a column whose role is PII therefore pers |
| `secrets-never-in-context` | error | A credential placed in a prompt, a model file or a committed artefact is durably persisted and replayed into every later session. |
| `sister-projects-are-isolated` | error | Business logic does not transfer between entities, so an assumption carried from one sister company into another is a bug by construction. A project session may |
| `source-declares-freshness` | warning | A mart is stale because its source was. Monitoring the mart names the wrong artefact to go fix, and monitoring nothing means the first report of a stopped pipel |
| `tool-contribution-may-only-tighten` | error | A tool contributes gate rules, and a plugin system that can widen the policy judging it is not a policy. `Tool.gate_sections()` rejects a contribution to any lo |
| `upstream-licences-are-reviewed` | warning | Every upstream this platform borrowed from carries a licence, and some of them constrain what we may ship. The review is written down per upstream and surfaced |
| `vendor-is-read-only` | error | A vendored upstream is evidence of what an external project actually does. Editing one turns it into a fork wearing a submodule's name, and every later diff aga |
| `warehouse-custody-is-recorded` | warning | Serving, stopping and borrowing are the moments the development database changes hands. Each is written to the provenance ledger as a full action — intent, deci |

## Decisions

| decision | status | what was decided |
|---|---|---|
| ADR-0001 | accepted | Duty rates are back-applied to history, and flagged |
| ADR-0002 | accepted | Prices carry the `unit_price` role, not `money_amount` |
| ADR-0003 | accepted | Mean prices are ratio metrics, not `average` measures |
| ADR-0004 | accepted | dlt Core lands the raw stage; dbt stages it |
| ADR-0005 | accepted | commodity-india is one market of many |
