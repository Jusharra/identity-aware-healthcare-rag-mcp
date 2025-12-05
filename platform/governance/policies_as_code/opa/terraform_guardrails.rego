package terraform.guardrails

# 1) No public storage accounts
deny[msg] {
  some i
  rc := input.resource_changes[i]
  rc.type == "azurerm_storage_account"

  after := rc.change.after
  # defensive: attribute name depends on your TF version
  after.allow_blob_public_access == true

  msg := sprintf("Storage account %s allows public access", [after.name])
}

# 2) Function Apps must use Managed Identity
deny[msg] {
  some i
  rc := input.resource_changes[i]
  rc.type == "azurerm_windows_function_app"  # or linux, adjust to your resource

  after := rc.change.after
  not after.identity.type

  msg := sprintf("Function app %s must use managed identity", [after.name])
}

# 3) Evidence storage must be tagged correctly
deny[msg] {
  some i
  rc := input.resource_changes[i]
  rc.type == "azurerm_storage_account"

  after := rc.change.after
  not after.tags["purpose"]
  msg := sprintf("Storage account %s missing 'purpose' tag", [after.name])
}

deny[msg] {
  some i
  rc := input.resource_changes[i]
  rc.type == "azurerm_storage_account"

  after := rc.change.after
  after.tags["purpose"] != "rag-mcp-evidence"

  msg := sprintf("Storage account %s has wrong 'purpose' tag (expected rag-mcp-evidence)", [after.name])
}
