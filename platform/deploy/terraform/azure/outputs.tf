output "front_door" {
  description = "The control plane. Internal by default — reachable from the VNet, over a VPN or through a private endpoint, not from the internet."
  value       = "https://${azurerm_container_app.stack.ingress[0].fqdn}"
}

output "artifacts_env" {
  description = "Points `pf artifacts` at this deployment's Blob container. No region: the Azure backend does not sign one. The key comes from `tofu output -raw artifacts_key`."
  value = {
    PF_ARTIFACTS_ENDPOINT      = azurerm_storage_account.artifacts.primary_blob_endpoint
    PF_ARTIFACTS_BUCKET        = azurerm_storage_container.artifacts.name
    PF_ARTIFACTS_BACKEND       = "azure"
    PF_ARTIFACTS_ACCESS_KEY_ID = azurerm_storage_account.artifacts.name
  }
}

output "artifacts_key" {
  description = "Storage account key — this is PF_ARTIFACTS_SECRET_ACCESS_KEY."
  value       = azurerm_storage_account.artifacts.primary_access_key
  sensitive   = true
}

output "database_fqdn" {
  description = "Postgres FQDN. Resolves only inside the VNet, through the private DNS zone."
  value       = azurerm_postgresql_flexible_server.main.fqdn
}

output "search_fqdn" {
  description = "Internal FQDN of the search app. Never externally reachable — it has no authentication."
  value       = azurerm_container_app.search.ingress[0].fqdn
}

output "identity_principal_id" {
  description = "The control plane's managed identity. Grant it access to the Databricks workspace rather than issuing it a personal access token."
  value       = azurerm_user_assigned_identity.stack.principal_id
}
