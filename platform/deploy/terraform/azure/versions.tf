terraform {
  required_version = ">= 1.6"

  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
      version = "~> 4.0"
    }
    random = {
      source  = "hashicorp/random"
      version = "~> 3.6"
    }
  }
}

provider "azurerm" {
  subscription_id = var.subscription_id

  features {
    key_vault {
      # Soft delete is not optional on Key Vault any more, so a destroyed vault
      # keeps its name reserved. Purging on destroy is what lets a stack be torn
      # down and rebuilt under the same name — which is the normal case for a
      # non-production environment and a trap in production.
      purge_soft_delete_on_destroy    = false
      recover_soft_deleted_key_vaults = true
    }
  }
}
