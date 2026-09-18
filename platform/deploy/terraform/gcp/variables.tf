variable "project_id" {
  type        = string
  description = "GCP project. One project per environment is the cheapest blast-radius boundary GCP offers."
}

variable "region" {
  type        = string
  description = "Region for Cloud Run, Cloud SQL and the bucket. Keep BigQuery's dataset location consistent with it or every dbt run pays cross-region egress."
  default     = "europe-west1"
}

variable "zone" {
  type        = string
  description = "Zone for the single search VM. Must be inside var.region."
  default     = "europe-west1-b"
}

variable "env" {
  type    = string
  default = "prod"
}

variable "name_prefix" {
  type    = string
  default = "pf"
}

# ------------------------------------------------------------------ image --
variable "stack_image" {
  type        = string
  description = <<-EOT
    The pf_stack image with the repository baked in, in Artifact Registry.

    Cloud Run has no host filesystem to bind-mount, so the repository must be
    inside the image at `repo_path` and workspace.yaml must have been rendered
    against that same path. Mount it anywhere else and every Dagster code
    location loads zero assets while reporting no error.
  EOT
}

variable "repo_path" {
  type    = string
  default = "/opt/pf"
}

variable "search_image" {
  type        = string
  description = "Elasticsearch image for the search VM. GCP has no managed Elasticsearch, so this runs on one Container-Optimized OS instance — see search.tf."
  default     = "docker.elastic.co/elasticsearch/elasticsearch:9.3.0"
}

# ---------------------------------------------------------------- sizing --
variable "service_cpu" {
  type        = string
  description = "Cloud Run vCPU. The stack runs OpenMetadata, Dagster, the code servers and nginx in one container."
  default     = "8"
}

variable "service_memory" {
  type        = string
  description = "Cloud Run memory. 32Gi is the service maximum; OpenMetadata alone asks for ~2 GiB of heap and the code servers are not free."
  default     = "16Gi"
}

variable "db_tier" {
  type    = string
  default = "db-custom-2-7680"
}

variable "db_disk_size" {
  type        = number
  description = "GiB. Autoresize is on, so this is a floor rather than a budget."
  default     = 100
}

variable "search_machine_type" {
  type    = string
  default = "e2-standard-2"
}

variable "search_disk_size" {
  type    = number
  default = 50
}

variable "search_heap" {
  type        = string
  description = "ES_JAVA_OPTS for the search node. Matches compose.yaml's 512m: the index holds ~1200 tables and a glossary, and the extra heap was going to a JVM that never used it."
  default     = "-Xms512m -Xmx512m"
}

# --------------------------------------------------------------- network --
variable "subnet_cidr" {
  type    = string
  default = "10.43.0.0/20"
}

variable "ingress" {
  type        = string
  description = <<-EOT
    Cloud Run ingress. `INGRESS_TRAFFIC_INTERNAL_LOAD_BALANCER` keeps the
    control plane off the public internet and is the default for that reason —
    Dagster's UI can launch runs and there is no authentication in front of it.

    `INGRESS_TRAFFIC_ALL` publishes it. Only pair that with
    `allow_unauthenticated = false`, which puts Google's IAM in front.
  EOT
  default     = "INGRESS_TRAFFIC_INTERNAL_LOAD_BALANCER"

  validation {
    condition = contains([
      "INGRESS_TRAFFIC_ALL",
      "INGRESS_TRAFFIC_INTERNAL_ONLY",
      "INGRESS_TRAFFIC_INTERNAL_LOAD_BALANCER",
    ], var.ingress)
    error_message = "Not a Cloud Run ingress setting."
  }
}

variable "allow_unauthenticated" {
  type        = bool
  description = "Grant roles/run.invoker to allUsers. Leave false: the control plane has no auth of its own."
  default     = false
}

variable "invoker_members" {
  type        = list(string)
  description = "Principals allowed to reach the service, e.g. [\"group:data-platform@example.com\"]. Ignored when allow_unauthenticated is true."
  default     = []
}

# --------------------------------------------------------------- secrets --
variable "warehouse_env" {
  type        = map(string)
  description = <<-EOT
    Warehouse credentials, stored as one Secret Manager secret and injected as
    environment variables. Keys are the names `pf.runtime.targets` expects.

    These land in the state file, so the state bucket must be encrypted and
    access-controlled like a credential store.
  EOT
  default     = {}
  sensitive   = true
}

variable "enable_apis" {
  type        = bool
  description = "Enable the service APIs this module needs. Turn off where a platform team manages API enablement separately."
  default     = true
}
