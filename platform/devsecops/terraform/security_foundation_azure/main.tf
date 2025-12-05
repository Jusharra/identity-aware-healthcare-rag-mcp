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

# Shared resource group for security/monitoring assets
resource "azurerm_resource_group" "security" {
  name     = var.resource_group_name
  location = var.location
}

# Log Analytics workspace for RAG + MCP + platform logs
resource "azurerm_log_analytics_workspace" "rag_mcp" {
  name                = var.log_analytics_name
  location            = azurerm_resource_group.security.location
  resource_group_name = azurerm_resource_group.security.name
  sku                 = "PerGB2018"

  retention_in_days = 30

  tags = {
    environment = var.environment
    owner       = "grc-platform"
    purpose     = "rag-mcp-observability"
  }
}

# Optional: enable Defender for Cloud at the subscription level (sample)
resource "azurerm_security_center_contact" "security_contact" {
  name                = "default"
  email               = var.security_contact_email
  phone               = var.security_contact_phone
  alert_notifications = true
  alerts_to_admins    = true
}
