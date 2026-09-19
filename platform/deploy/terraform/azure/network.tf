locals {
  name = "${var.name_prefix}-${var.env}"
  # Storage account names are globally unique, 3-24 characters, lower-case
  # alphanumeric only — no hyphens. Derived rather than asked for, so there is
  # one fewer name to keep in agreement.
  storage_name = substr(replace("${var.name_prefix}${var.env}artifacts", "-", ""), 0, 24)
}

data "azurerm_client_config" "current" {}

resource "azurerm_resource_group" "main" {
  name     = local.name
  location = var.location

  tags = {
    platform  = "data-platform"
    component = "control-plane"
    managedby = "opentofu"
    env       = var.env
  }
}

resource "azurerm_virtual_network" "main" {
  name                = local.name
  location            = azurerm_resource_group.main.location
  resource_group_name = azurerm_resource_group.main.name
  address_space       = [var.vnet_cidr]
}

# Container Apps requires a dedicated subnet and will not accept anything
# smaller than a /23 for a workload-profiles environment. Sizing it exactly is a
# false economy: growing it later means recreating the environment.
resource "azurerm_subnet" "apps" {
  name                 = "container-apps"
  resource_group_name  = azurerm_resource_group.main.name
  virtual_network_name = azurerm_virtual_network.main.name
  address_prefixes     = [cidrsubnet(var.vnet_cidr, 7, 0)]
}

# Postgres Flexible Server with private access needs a subnet delegated to it
# exclusively. Nothing else can live here, which is why it is its own.
resource "azurerm_subnet" "database" {
  name                 = "database"
  resource_group_name  = azurerm_resource_group.main.name
  virtual_network_name = azurerm_virtual_network.main.name
  address_prefixes     = [cidrsubnet(var.vnet_cidr, 8, 2)]

  delegation {
    name = "flexibleServers"

    service_delegation {
      name = "Microsoft.DBforPostgreSQL/flexibleServers"
      actions = [
        "Microsoft.Network/virtualNetworks/subnets/join/action",
      ]
    }
  }
}

# Without this zone and its link, a private Flexible Server has no resolvable
# name — the connection string points at a host that does not resolve from
# inside the VNet, and the error is a DNS failure rather than a network one.
resource "azurerm_private_dns_zone" "postgres" {
  name                = "${local.name}.postgres.database.azure.com"
  resource_group_name = azurerm_resource_group.main.name
}

resource "azurerm_private_dns_zone_virtual_network_link" "postgres" {
  name                  = "${local.name}-postgres"
  resource_group_name   = azurerm_resource_group.main.name
  private_dns_zone_name = azurerm_private_dns_zone.postgres.name
  virtual_network_id    = azurerm_virtual_network.main.id
  registration_enabled  = false
}

# ------------------------------------------------------------- telemetry --
# Container Apps requires a Log Analytics workspace to send logs anywhere. This
# is the only record of what the control plane did; thirty days is a floor.
resource "azurerm_log_analytics_workspace" "main" {
  name                = local.name
  location            = azurerm_resource_group.main.location
  resource_group_name = azurerm_resource_group.main.name
  sku                 = "PerGB2018"
  retention_in_days   = 30
}
