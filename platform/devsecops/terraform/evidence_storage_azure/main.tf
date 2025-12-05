terraform {
  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
      version = "~> 3.100"
    }
  }
}

provider "azurerm" {
  features {}
}

# 1. Evidence Storage Account
resource "azurerm_storage_account" "evidence" {
  name                     = var.storage_account_name
  resource_group_name      = var.resource_group_name
  location                 = var.location
  account_tier             = "Standard"
  account_replication_type = "LRS"

  # Disable public access to blobs and containers
  allow_nested_items_to_be_public = false
  
  # Configure CORS rules if needed
  # share_properties {
  #   cors_rule {
  #     allowed_headers    = ["*"]
  #     allowed_methods    = ["GET", "POST", "PUT"]
  #     allowed_origins    = ["https://yourdomain.com"]
  #     exposed_headers    = ["*"]
  #     max_age_in_seconds = 1800
  #   }
  # }

  blob_properties {
    delete_retention_policy {
      days = 30
    }
  }

  identity {
    type = "SystemAssigned"
  }

  tags = {
    environment = var.environment
    owner       = "grc-platform"
    purpose     = "rag-mcp-evidence"
  }
}

# 2. Evidence Containers
locals {
  containers = ["docs-raw", "logs", "evidence"]
}

resource "azurerm_storage_container" "containers" {
  for_each              = toset(local.containers)
  name                  = each.value
  storage_account_name  = azurerm_storage_account.evidence.name
  container_access_type = "private"
}

# 3. Diagnostic Settings: Storage -> Log Analytics
