variable "region" {
  type        = string
  description = "AWS region. Keep the warehouse, the bucket and the stack in one region — cross-region egress on dbt artefacts is the cost nobody budgets for."
  default     = "eu-west-1"
}

variable "env" {
  type        = string
  description = "Environment name. Becomes part of every resource name, so two of these can share an account."
  default     = "prod"
}

variable "name_prefix" {
  type        = string
  description = "Prefix for named resources."
  default     = "pf"
}

# ------------------------------------------------------------------ image --
variable "stack_image" {
  type        = string
  description = <<-EOT
    The pf_stack image, with the repository baked in.

    This is the one place a cloud deployment departs from compose.yaml, and it
    is not optional. Locally the repo is bind-mounted at its host path because
    Dagster's workspace.yaml holds absolute `working_directory` entries. There
    is no host path in Fargate, so the repo has to be inside the image at a
    fixed location and `PF_REPO` has to name it — see `repo_path`.

    Build it from the repository root:

      docker build -f platform/Containerfile.stack \
        --build-arg PF_REPO=/opt/pf -t <account>.dkr.ecr.<region>.amazonaws.com/pf-stack:<tag> .
  EOT
}

variable "repo_path" {
  type        = string
  description = "Where the repository lives inside the image. Must match the path workspace.yaml was rendered against, or every Dagster code location loads zero assets while reporting no error."
  default     = "/opt/pf"
}

# ---------------------------------------------------------------- sizing --
variable "task_cpu" {
  type        = number
  description = "Fargate CPU units. The stack runs OpenMetadata, Dagster, up to eight code servers and nginx in one task, so 2 vCPU is a floor rather than a recommendation."
  default     = 4096
}

variable "task_memory" {
  type        = number
  description = "Fargate memory (MiB). OpenMetadata alone asks for ~2 GiB of heap."
  default     = 16384
}

variable "db_instance_class" {
  type    = string
  default = "db.t4g.medium"
}

variable "db_allocated_storage" {
  type        = number
  description = "GiB. OpenMetadata's 176 tables and Dagster's run history are small; this is headroom for event logs, which are not."
  default     = 100
}

variable "search_instance_type" {
  type        = string
  description = "OpenSearch data node type."
  default     = "t3.small.search"
}

variable "search_instance_count" {
  type        = number
  description = "One node is correct for a single-AZ control plane and is not highly available. Raise it with `search_zone_awareness`."
  default     = 1
}

variable "search_zone_awareness" {
  type        = bool
  description = "Spread OpenSearch across AZs. Requires an even instance count of at least 2."
  default     = false
}

# --------------------------------------------------------------- network --
variable "vpc_cidr" {
  type    = string
  default = "10.42.0.0/16"
}

variable "az_count" {
  type        = number
  description = "Availability zones to spread across. Two is the minimum an ALB will accept."
  default     = 2
}

variable "ingress_cidrs" {
  type        = list(string)
  description = <<-EOT
    Who may reach the front door on 8080.

    There is no default and that is deliberate. The control plane exposes
    OpenMetadata, Dagster and every project's recce review; Dagster's UI can
    launch runs. `0.0.0.0/0` here publishes all of that, so the value has to be
    typed by a person who knows what they are opening.
  EOT
}

# --------------------------------------------------------------- secrets --
variable "warehouse_env" {
  type        = map(string)
  description = <<-EOT
    Warehouse credentials, written to one Secrets Manager entry and injected as
    environment variables. Keys are the names `pf.runtime.targets` expects —
    e.g. DATABRICKS_HOST, DATABRICKS_TOKEN, DATABRICKS_HTTP_PATH,
    DATABRICKS_CATALOG — and the module does not interpret them.

    Pass it from a tfvars file that is not in git, or from your secrets tool.
    Anything put here lands in the state file, so the state backend must be
    encrypted and access-controlled like a credential store.
  EOT
  default     = {}
  sensitive   = true
}
