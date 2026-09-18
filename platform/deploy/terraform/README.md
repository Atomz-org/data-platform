# Running the control plane on a cloud

Three root modules, one per cloud. Each stands up the same five things:

| | AWS | GCP | Azure |
|---|---|---|---|
| container runtime | ECS Fargate + ALB | Cloud Run v2 | Container Apps |
| Postgres | RDS `db.t4g.medium` | Cloud SQL, private IP | Flexible Server, delegated subnet |
| search | **OpenSearch**, managed | **Elasticsearch on one VM** | **Elasticsearch as a 2nd container app** |
| object store | S3 | GCS via its **XML API + HMAC** | Blob, via the **`azure` backend** |
| secrets | Secrets Manager, one JSON | Secret Manager, **one per key** | Key Vault, **one per key** |

The bolded cells are where the clouds genuinely differ and where most of the
work went. Everything else is the same design in three dialects.

---

## Verification status — read this first

| Check | AWS | GCP | Azure |
|---|---|---|---|
| `tofu validate` against the real provider schema | ✅ | ✅ | ✅ |
| `tofu fmt` | ✅ | ✅ | ✅ |
| `tofu plan` against a real subscription | ❌ | ❌ | ❌ |
| `tofu apply` — ever run | ❌ | ❌ | ❌ |

**These have never been applied.** Validation proves the resource types,
argument names and expression types are real and consistent. It does not prove
quotas exist, that an image pulls, that a SKU is available in your region, that
the IAM is sufficient, or that OpenMetadata comes up against a managed Postgres.
Expect the first `apply` of each to need fixes, and run it somewhere you do not
mind destroying.

Validation was done with OpenTofu 1.12.6 against `hashicorp/aws ~> 6.0`,
`hashicorp/google ~> 6.0` and `hashicorp/azurerm ~> 4.0`.

---

## The one deviation from `compose.yaml`

Locally the repository is bind-mounted into the container **at its host path**,
because Dagster's `workspace.yaml` holds absolute `working_directory` entries.
`compose.yaml` is emphatic about this: mount it elsewhere and every code
location loads zero assets while reporting no error.

There is no host path in Fargate, Cloud Run or Container Apps. So for a cloud
deployment the repository has to be **inside the image** at a fixed path, and
`PF_REPO` has to name that same path:

```bash
docker build -f platform/Containerfile.stack \
  --build-arg PF_REPO=/opt/pf \
  -t <registry>/pf-stack:<tag> .
```

`var.repo_path` defaults to `/opt/pf` and must match the path `pf stack render`
generated `workspace.yaml` against. This is the single most likely cause of a
deployment that starts cleanly and orchestrates nothing.

## Why every module pins one replica

The stack image runs OpenMetadata, Dagster's webserver, up to eight Dagster code
servers, the recce servers and nginx in one container. Two replicas are two
Dagster daemons sharing one run-storage schema, racing to launch the same
schedules. Scaling the control plane is a decomposition project, not a replica
count — so all three modules pin `1` and say so at the point of the pin.

## Migrations

OpenMetadata runs schema migrations at start and they are slow on a cold
database. Each cloud handles that differently, and the difference is forced:

- **AWS** — a 600-second `health_check_grace_period_seconds` on the ECS service.
- **Azure** — a startup probe with `failure_count_threshold = 60` at 10s.
- **GCP** — Cloud Run's startup-probe budget does not stretch that far, so
  migrations are a **separate Cloud Run job** running the entrypoint's
  `--migrate-only` mode, and the service starts with `PF_OM_MIGRATE=0`. Run the
  job before the first deploy and after every image bump;
  `tofu output migrate_command` prints the invocation.

  `--migrate-only` runs the entrypoint's real prologue and exits before the
  supervisord hand-off, so the job and a normal start do the same work in the
  same order. It was added for this; the alternative was a copy of the sequence
  in the manifest, which drifts from `stack-entrypoint.sh` the first time the
  order changes there — and the order matters, because `pf stack render` has to
  run before `dagster instance migrate` or Dagster migrates the SQLite file.

Getting this wrong does not look like a timeout. It looks like a crash loop,
which looks like a broken image.

---

## Using it

Each module needs a state backend. None is configured here, deliberately — the
backend is an organisational decision and a wrong default is worse than none.
State holds the database password, the storage account key and everything passed
through `warehouse_env`, so it must be encrypted and access-controlled like a
credential store.

```bash
cd platform/deploy/terraform/aws        # or gcp, or azure
tofu init -backend-config=...
tofu plan  -var-file=prod.auto.tfvars
```

Minimum variables per cloud:

```hcl
# aws
stack_image   = "123456789012.dkr.ecr.eu-west-1.amazonaws.com/pf-stack:2026.09"
ingress_cidrs = ["10.0.0.0/8"]        # no default — see below

# gcp
project_id  = "my-project"
stack_image = "europe-west1-docker.pkg.dev/my-project/pf/pf-stack:2026.09"

# azure
subscription_id = "00000000-0000-0000-0000-000000000000"
stack_image     = "myacr.azurecr.io/pf-stack:2026.09"
registry_server = "myacr.azurecr.io"
```

### Exposure is opt-in, in all three

The control plane serves OpenMetadata, Dagster and every project's recce review,
and **Dagster's UI can launch runs**. There is no authentication in front of any
of it. So:

- **AWS** — `ingress_cidrs` has no default. It has to be typed.
- **GCP** — `ingress` defaults to internal-load-balancer, and
  `allow_unauthenticated` defaults to `false`.
- **Azure** — `external_ingress` defaults to `false`.

Opening any of these is a decision, not a step.

### After apply

```bash
tofu output front_door        # the control plane
tofu output artifacts_env     # export these for `pf artifacts`
pf artifacts status           # backend, region and reachability
```

`pf artifacts status` prints the backend and the signing region, which is the
fastest way to catch the failure described below.

---

## Two things that will bite

**`PF_ARTIFACTS_REGION` is not optional outside R2.** SigV4 signs the region
into every request. R2 requires the literal `auto`; real S3 rejects it with
`AuthorizationHeaderMalformed`, which reads exactly like a bad credential. The
AWS and GCP modules set it from `var.region`; Azure does not sign one at all.

**GCS needs an HMAC key pair, not a service-account JSON.** `pf.artifacts`
speaks S3, and GCS answers S3 only on its XML API, which authenticates with HMAC
keys. Every other GCP integration wants the JSON key and the JSON key does not
work here. The GCP module creates the pair — `tofu output -raw artifacts_key_id`
and `artifacts_secret`.

---

## Out of scope, on purpose

Named rather than half-built, so the gaps are visible:

- **TLS and DNS.** AWS listens on plain 8080 with no ACM certificate, because a
  certificate needs a domain this module does not own. Put a 443 listener in
  front and redirect. GCP and Azure terminate TLS on their own ingress.
- **High availability.** One task, one Cloud Run instance, one container app —
  matching the single-container control plane. Postgres is zonal; search is a
  single node. The search index is *derived* and rebuilt with
  `PF_OM_REINDEX=recreate`, so it is the one piece that genuinely does not need
  backing up.
- **The warehouse.** Not created here. Databricks, Snowflake, BigQuery and
  Redshift are declared in `pf.runtime.targets` and reached with credentials
  passed through `warehouse_env`. `pf capability-add databricks <g> <p>` wires a
  project to one.
- **The projects themselves.** These modules deploy the control plane. dbt still
  runs where you run it — locally, in CI, or as Dagster assets inside the stack.
- **Cost controls.** No budget alerts, no autoscaling, no scheduled shutdown.
  The AWS module's NAT gateway and the GCP module's search VM both bill hourly
  whether or not anyone uses them.
