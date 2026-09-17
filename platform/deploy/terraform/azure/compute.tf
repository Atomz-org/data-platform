# The control plane and its search node, as two container apps in one
# environment.
#
# ## Why search is a second app rather than a managed service
#
# Azure has no first-party managed Elasticsearch or OpenSearch. Elastic Cloud on
# Azure is a marketplace subscription and a second vendor relationship for one
# index of ~1200 tables; AKS is a cluster to run one pod. A second container app
# with an Azure Files volume is the proportionate answer, and the index is
# derived — `PF_OM_REINDEX=recreate` rebuilds it from Postgres — so its
# durability requirements are genuinely low.
#
# ## Why min = max = 1 on the stack
#
# One container runs OpenMetadata, Dagster's webserver, its code servers and
# nginx. Two replicas would be two Dagster daemons on one run-storage schema,
# racing to launch the same schedules.

resource "azurerm_container_app_environment" "main" {
  name                = local.name
  location            = azurerm_resource_group.main.location
  resource_group_name = azurerm_resource_group.main.name

  log_analytics_workspace_id = azurerm_log_analytics_workspace.main.id
  infrastructure_subnet_id   = azurerm_subnet.apps.id

  # Keeps the environment's load balancer on the VNet. With this false the
  # environment gets a public IP regardless of each app's ingress setting.
  internal_load_balancer_enabled = !var.external_ingress
}

# The file share, registered with the environment so a container app can mount
# it. Container Apps cannot attach a managed disk; this is the durable volume.
resource "azurerm_container_app_environment_storage" "search" {
  name                         = "search"
  container_app_environment_id = azurerm_container_app_environment.main.id
  account_name                 = azurerm_storage_account.artifacts.name
  share_name                   = azurerm_storage_share.search.name
  access_key                   = azurerm_storage_account.artifacts.primary_access_key
  access_mode                  = "ReadWrite"
}

resource "azurerm_container_app" "search" {
  name                         = "${local.name}-search"
  container_app_environment_id = azurerm_container_app_environment.main.id
  resource_group_name          = azurerm_resource_group.main.name
  revision_mode                = "Single"

  template {
    min_replicas = 1
    max_replicas = 1

    volume {
      name         = "data"
      storage_type = "AzureFile"
      storage_name = azurerm_container_app_environment_storage.search.name
    }

    container {
      name   = "search"
      image  = var.search_image
      cpu    = var.search_cpu
      memory = var.search_memory

      env {
        name  = "discovery.type"
        value = "single-node"
      }

      # Off, matching compose.yaml. The access control is that ingress below is
      # internal-only — this must not be given external ingress.
      env {
        name  = "xpack.security.enabled"
        value = "false"
      }

      env {
        name  = "ES_JAVA_OPTS"
        value = var.search_heap
      }

      volume_mounts {
        name = "data"
        path = "/usr/share/elasticsearch/data"
      }
    }
  }

  ingress {
    # Never external. There is no authentication on this Elasticsearch.
    external_enabled = false
    target_port      = 9200
    transport        = "tcp"

    traffic_weight {
      latest_revision = true
      percentage      = 100
    }
  }
}

locals {
  stack_env = {
    PF_REPO      = var.repo_path
    DAGSTER_HOME = "${var.repo_path}/.dagster-stack"

    PF_STACK_PG_HOST   = azurerm_postgresql_flexible_server.main.fqdn
    PF_STACK_PG_PORT   = "5432"
    PF_STACK_PG_DB     = azurerm_postgresql_flexible_server_database.main.name
    PF_STACK_PG_SCHEMA = "dagster"

    OPENMETADATA_HOST_PORT = "http://127.0.0.1:8585"

    # The Azure path through `pf.artifacts`: no region, and an account URL
    # rather than an S3 endpoint. `Store.infer_backend` reads the host and
    # selects the Blob driver on its own.
    PF_ARTIFACTS_ENDPOINT = azurerm_storage_account.artifacts.primary_blob_endpoint
    PF_ARTIFACTS_BUCKET   = azurerm_storage_container.artifacts.name
    PF_ARTIFACTS_BACKEND  = "azure"

    SEARCH_TYPE   = "elasticsearch"
    SEARCH_HOST   = azurerm_container_app.search.ingress[0].fqdn
    SEARCH_PORT   = "9200"
    SEARCH_SCHEME = "http"
  }
}

resource "azurerm_container_app" "stack" {
  name                         = local.name
  container_app_environment_id = azurerm_container_app_environment.main.id
  resource_group_name          = azurerm_resource_group.main.name
  revision_mode                = "Single"

  identity {
    type         = "UserAssigned"
    identity_ids = [azurerm_user_assigned_identity.stack.id]
  }

  dynamic "registry" {
    for_each = var.registry_server == "" ? [] : [var.registry_server]
    content {
      server   = registry.value
      identity = azurerm_user_assigned_identity.stack.id
    }
  }

  # Key Vault references rather than literals: a literal here is readable by
  # anyone with read access to the container app.
  dynamic "secret" {
    for_each = local.stack_secrets
    content {
      name                = local.secret_name[secret.key]
      key_vault_secret_id = azurerm_key_vault_secret.stack[secret.key].versionless_id
      identity            = azurerm_user_assigned_identity.stack.id
    }
  }

  template {
    min_replicas = 1
    max_replicas = 1

    container {
      name   = "stack"
      image  = var.stack_image
      cpu    = var.stack_cpu
      memory = var.stack_memory

      dynamic "env" {
        for_each = local.stack_env
        content {
          name  = env.key
          value = env.value
        }
      }

      dynamic "env" {
        for_each = local.stack_secrets
        content {
          name        = env.key
          secret_name = local.secret_name[env.key]
        }
      }

      # OpenMetadata's migrations run at start and are slow on a cold database.
      # 60 × 10s is ten minutes before Container Apps gives up, which is what
      # keeps a first deploy from presenting as a crash loop.
      startup_probe {
        transport               = "TCP"
        port                    = 8080
        initial_delay           = 30
        interval_seconds        = 10
        failure_count_threshold = 60
      }

      liveness_probe {
        transport               = "HTTP"
        port                    = 8080
        path                    = "/"
        initial_delay           = 60
        interval_seconds        = 30
        failure_count_threshold = 5
      }
    }
  }

  ingress {
    external_enabled = var.external_ingress
    target_port      = 8080
    transport        = "http"

    traffic_weight {
      latest_revision = true
      percentage      = 100
    }
  }

  depends_on = [azurerm_role_assignment.stack_secrets]
}
