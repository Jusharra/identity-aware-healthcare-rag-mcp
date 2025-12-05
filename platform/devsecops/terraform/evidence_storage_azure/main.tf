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

  # Use geo-redundant replication for critical evidence
  account_replication_type = "GRS"

  # Security hardening
  min_tls_version               = "TLS1_2"        # CKV_AZURE_44
  enable_https_traffic_only     = true
  allow_nested_items_to_be_public = false         # already there
  public_network_access_enabled = false           # CKV_AZURE_59
  shared_access_key_enabled     = false           # CKV2_AZURE_40

  # SAS expiration policy – force short-lived SAS
  sas_policy {                                  # CKV2_AZURE_41
    expiration_action = "Log"
    # ISO-8601 duration, e.g. P7D = 7 days
    expiration_period = "P7D"
  }
  blob_properties {
    delete_retention_policy {
      days = 30
    }
  }

  identity {
    type = "SystemAssigned, UserAssigned"
    identity_ids = [var.user_assigned_identity_id]
  }

  # Customer-managed key for evidence-at-rest encryption
  customer_managed_key {                        # CKV2_AZURE_1 (part 1)
    key_vault_key_id = var.cmk_key_vault_key_id
    user_assigned_identity_id = var.user_assigned_identity_id
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

resource "azurerm_private_endpoint" "evidence_blob" {
  name                = "${var.storage_account_name}-pe-blob"
  location            = var.location
  resource_group_name = var.resource_group_name
  subnet_id           = var.private_endpoint_subnet_id

  private_service_connection {
    name                           = "${var.storage_account_name}-blob-psc"
    private_connection_resource_id = azurerm_storage_account.evidence.id
    subresource_names              = ["blob"]
    is_manual_connection           = false
  }

  tags = {
    environment = var.environment
    owner       = "grc-platform"
  }
}

resource "azurerm_key_vault_key" "evidence_cmk" {
  name         = "evidence-cmk"
  key_vault_id = azurerm_key_vault.security_kv.id
  key_type     = "RSA"
  key_size     = 2048

  key_opts = ["encrypt", "decrypt", "wrapKey", "unwrapKey"]
}

resource "azurerm_monitor_diagnostic_setting" "evidence_storage_diag" {
  name               = "${var.storage_account_name}-diag"
  target_resource_id = azurerm_storage_account.evidence.id

  # Store diagnostics in the same account for the lab;
  # in production you’d point this at a separate log store.
  storage_account_id = azurerm_storage_account.evidence.id

  log {
    category = "StorageRead"
    enabled  = true

    retention_policy {
      enabled = true
      days    = 30
    }
  }

  log {
    category = "StorageWrite"
    enabled  = true

    retention_policy {
      enabled = true
      days    = 30
    }
  }

  log {
    category = "StorageDelete"
    enabled  = true

    retention_policy {
      enabled = true
      days    = 30
    }
  }

  metric {
    category = "Transaction"
    enabled  = true

    retention_policy {
      enabled = true
      days    = 30
    }
  }
}
