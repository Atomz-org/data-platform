# Postgres, Blob storage, and the vault the container app reads secrets from.

# -------------------------------------------------------------- identity --
# One user-assigned identity, created before the things that grant it access.
# System-assigned would be simpler, but a container app cannot reference a Key
# Vault secret with an identity that does not exist until the app is created —
# that is a genuine cycle, and this is how it is broken.
resource "azurerm_user_assigned_identity" "stack" {
  name                = "${local.name}-stack"
  location            = azurerm_resource_group.main.location
  resource_group_name = azurerm_resource_group.main.name
}

# ------------------------------------------------------------- postgres --
resource "random_password" "db" {
  length           = 32
  override_special = "!#$%&*()-_=+[]{}<>:?"
}

resource "azurerm_postgresql_flexible_server" "main" {
  name                = local.name
  location            = azurerm_resource_group.main.location
  resource_group_name = azurerm_resource_group.main.name
  version             = "16"

  administrator_login    = "pfadmin"
  administrator_password = random_password.db.result

  sku_name   = var.db_sku
  storage_mb = var.db_storage_mb

  delegated_subnet_id           = azurerm_subnet.database.id
  private_dns_zone_id           = azurerm_private_dns_zone.postgres.id
  public_network_access_enabled = false

  backup_retention_days        = 7
  geo_redundant_backup_enabled = false

  depends_on = [azurerm_private_dns_zone_virtual_network_link.postgres]

  lifecycle {
    # Azure picks a zone at creation and reports it back; without this an
    # unrelated apply plans to move the server, which is a recreate.
    ignore_changes = [zone, high_availability[0].standby_availability_zone]
  }
}

resource "azurerm_postgresql_flexible_server_database" "main" {
  name      = "openmetadata_db"
  server_id = azurerm_postgresql_flexible_server.main.id
  collation = "en_US.utf8"
  charset   = "UTF8"

  lifecycle {
    # Dropping this database drops the catalogue and every Dagster run record.
    prevent_destroy = true
  }
}

# ----------------------------------------------------------------- blob --
# The one backend `pf.artifacts` reaches through its Azure path rather than its
# S3 path — Blob does not answer the S3 API at all, which is why `Store` carries
# a `backend` field.
resource "azurerm_storage_account" "artifacts" {
  name                = local.storage_name
  location            = azurerm_resource_group.main.location
  resource_group_name = azurerm_resource_group.main.name

  account_tier             = "Standard"
  account_replication_type = "LRS"
  min_tls_version          = "TLS1_2"

  # `pf.artifacts` authenticates with an account key, so shared-key access stays
  # on. It is the reason the container below is private and the account is not
  # reachable anonymously.
  shared_access_key_enabled       = true
  allow_nested_items_to_be_public = false
  https_traffic_only_enabled      = true

  blob_properties {
    versioning_enabled = true

    delete_retention_policy {
      days = 90
    }
  }
}

resource "azurerm_storage_container" "artifacts" {
  name                  = "artifacts"
  storage_account_id    = azurerm_storage_account.artifacts.id
  container_access_type = "private"
}

# Azure Files, for the search node's index. Container Apps cannot attach a
# managed disk, so a file share is the only durable volume available to it —
# and the index is derived anyway, so losing it costs a reindex and no data.
resource "azurerm_storage_share" "search" {
  name               = "search"
  storage_account_id = azurerm_storage_account.artifacts.id
  quota              = 50
}

# ----------------------------------------------------------------- vault --
resource "azurerm_key_vault" "main" {
  name                = local.name
  location            = azurerm_resource_group.main.location
  resource_group_name = azurerm_resource_group.main.name
  tenant_id           = data.azurerm_client_config.current.tenant_id
  sku_name            = "standard"

  # RBAC rather than access policies: access policies are per-vault ACLs that
  # nothing else in Azure models, and they drift from whatever manages the rest
  # of the subscription's permissions.
  rbac_authorization_enabled = true
  purge_protection_enabled   = false
  soft_delete_retention_days = 7
}

# The identity running Terraform needs to write secrets; the container app's
# identity needs to read them. Two roles, two principals, no overlap.
resource "azurerm_role_assignment" "tf_secrets" {
  scope                = azurerm_key_vault.main.id
  role_definition_name = "Key Vault Secrets Officer"
  principal_id         = data.azurerm_client_config.current.object_id
}

resource "azurerm_role_assignment" "stack_secrets" {
  scope                = azurerm_key_vault.main.id
  role_definition_name = "Key Vault Secrets User"
  principal_id         = azurerm_user_assigned_identity.stack.principal_id
}

resource "azurerm_role_assignment" "stack_blob" {
  scope                = azurerm_storage_account.artifacts.id
  role_definition_name = "Storage Blob Data Contributor"
  principal_id         = azurerm_user_assigned_identity.stack.principal_id
}

locals {
  # Key Vault secret names allow alphanumerics and hyphens only — no
  # underscores — so the environment variable name is mapped rather than reused.
  stack_secrets = merge(var.warehouse_env, {
    PF_STACK_PG_USER               = azurerm_postgresql_flexible_server.main.administrator_login
    PF_STACK_PG_PASSWORD           = random_password.db.result
    PF_STACK_PG_ADMIN_USER         = azurerm_postgresql_flexible_server.main.administrator_login
    PF_STACK_PG_ADMIN_PASSWORD     = random_password.db.result
    PF_ARTIFACTS_ACCESS_KEY_ID     = azurerm_storage_account.artifacts.name
    PF_ARTIFACTS_SECRET_ACCESS_KEY = azurerm_storage_account.artifacts.primary_access_key
  })

  secret_name = { for k, _ in local.stack_secrets : k => lower(replace(k, "_", "-")) }
}

resource "azurerm_key_vault_secret" "stack" {
  for_each = local.stack_secrets

  name         = local.secret_name[each.key]
  value        = each.value
  key_vault_id = azurerm_key_vault.main.id

  # The role assignment is eventually consistent; without this the first apply
  # fails with a 403 that looks like a missing permission and is a race.
  depends_on = [azurerm_role_assignment.tf_secrets]
}
