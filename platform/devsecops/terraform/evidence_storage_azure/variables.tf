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

