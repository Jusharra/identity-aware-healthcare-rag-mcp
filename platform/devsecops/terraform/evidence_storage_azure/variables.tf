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
  type        = string
  description = "Resource ID of the Log Analytics Workspace for evidence storage diagnostics."
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

variable "subscription_id" {
  type        = string
  description = "Azure subscription ID used by the evidence storage account"
}

variable "tenant_id" {
  type        = string
  description = "Azure AD tenant ID used by the evidence storage account"
}

variable "service_principal_object_id" {
  description = "The object ID of the service principal for role assignment. If not provided, the role assignment will be skipped."
  type        = string
  default     = ""
  validation {
    condition     = var.service_principal_object_id == "" || can(regex("^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$", var.service_principal_object_id))
    error_message = "The service_principal_object_id must be a valid Azure AD Object ID (GUID)."
  }
}

variable "vnet_resource_group_name" {
  description = "The name of the resource group containing the VNet"
  type        = string
  default     = "RG-RAG-MCP-SEC"
}

