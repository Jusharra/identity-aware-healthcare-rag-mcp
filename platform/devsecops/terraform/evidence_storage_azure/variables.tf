variable "resource_group_name" {
  type = string
}

variable "location" {
  type = string
}

variable "storage_account_name" {
  type = string
}

variable "environment" {
  type = string
}

# This is the ID of the Log Analytics Workspace created by security_foundation_azure
variable "log_analytics_workspace_id" {
  type = string
}

# User Assigned Identity for storage account to access Key Vault
variable "user_assigned_identity_id" {
  description = "The ID of the user-assigned identity to use for Key Vault access"
  type        = string
}

# Customer Managed Key for storage encryption
variable "cmk_key_vault_key_id" {
  description = "The ID of the Key Vault Key to use for storage encryption"
  type        = string
}

variable "private_endpoint_subnet_id" {
  type        = string
  description = "Subnet ID for the private endpoint used by the evidence storage account"
}

