output "storage_account_id" {
  value = azurerm_storage_account.evidence.id
}

output "storage_account_name" {
  value = azurerm_storage_account.evidence.name
}

output "evidence_containers" {
  value = [for c in azurerm_storage_container.containers : c.name]
}

