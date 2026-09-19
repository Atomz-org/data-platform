variable "subscription_id" {
  type        = string
  description = "Azure subscription. Required by the azurerm v4 provider rather than inferred from the CLI."
}

variable "location" {
  type        = string
  description = "Azure region. Keep the Databricks workspace in the same one — cross-region reads from a SQL warehouse are billed and slow."
  default     = "westeurope"
}

variable "env" {
  type    = string
  default = "prod"
}

variable "name_prefix" {
  type        = string
  description = "Prefix for named resources. Storage account names are globally unique, alphanumeric and 24 characters, so keep this short."
  default     = "pf"

  validation {
    condition     = can(regex("^[a-z][a-z0-9]{1,8}$", var.name_prefix))
    error_message = "Lower-case alphanumeric, 2-9 characters — it has to survive being folded into a storage account name."
  }
}

# ------------------------------------------------------------------ image --
variable "stack_image" {
  type        = string
  description = <<-EOT
    The pf_stack image with the repository baked in.

    Container Apps has no host filesystem to bind-mount, so the repository has to
    be inside the image at `repo_path`, and workspace.yaml must have been
    rendered against that same path. Render it elsewhere and every Dagster code
    location loads zero assets while reporting no error.
  EOT
}

variable "repo_path" {
  type    = string
  default = "/opt/pf"
}

variable "search_image" {
  type        = string
  description = "Elasticsearch image. Azure has no managed Elasticsearch, so this runs as a second container app — see search.tf."
  default     = "docker.elastic.co/elasticsearch/elasticsearch:9.3.0"
}

variable "registry_server" {
  type        = string
  description = "Container registry host, e.g. myacr.azurecr.io. Left empty for a public image."
  default     = ""
}

# ---------------------------------------------------------------- sizing --
variable "stack_cpu" {
  type        = number
  description = "vCPU for the stack container. Container Apps requires cpu and memory to come from a fixed set of pairs — 4 vCPU goes with 8Gi."
  default     = 4
}

variable "stack_memory" {
  type        = string
  default     = "8Gi"
  description = "Must pair with stack_cpu; Container Apps rejects combinations outside its allowed set."
}

variable "search_cpu" {
  type    = number
  default = 1
}

variable "search_memory" {
  type    = string
  default = "2Gi"
}

variable "search_heap" {
  type        = string
  description = "ES_JAVA_OPTS. Matches compose.yaml's 512m for the same reason."
  default     = "-Xms512m -Xmx512m"
}

variable "db_sku" {
  type    = string
  default = "GP_Standard_D2s_v3"
}

variable "db_storage_mb" {
  type    = number
  default = 131072
}

# --------------------------------------------------------------- network --
variable "vnet_cidr" {
  type    = string
  default = "10.44.0.0/16"
}

variable "external_ingress" {
  type        = bool
  description = <<-EOT
    Publish the front door to the internet.

    False by default: the control plane exposes OpenMetadata, Dagster and every
    project's recce review, Dagster's UI can launch runs, and there is no
    authentication in front of any of it. Internal ingress keeps it on the VNet,
    reachable over a VPN or a private endpoint.
  EOT
  default     = false
}

# --------------------------------------------------------------- secrets --
variable "warehouse_env" {
  type        = map(string)
  description = <<-EOT
    Warehouse credentials, stored in Key Vault and referenced by the container
    app through its managed identity. Keys are the names `pf.runtime.targets`
    expects — DATABRICKS_HOST, DATABRICKS_TOKEN, DATABRICKS_HTTP_PATH,
    DATABRICKS_CATALOG for the Azure default.

    These land in the state file. The state backend must be encrypted and
    access-controlled like a credential store.
  EOT
  default     = {}
  sensitive   = true
}
