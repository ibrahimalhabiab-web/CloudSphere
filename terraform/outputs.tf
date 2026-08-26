output "resource_group_name" {
  description = "Azure resource group containing the platform."
  value       = azurerm_resource_group.monitoring.name
}

output "public_ip_address" {
  description = "Static public IPv4 address of the monitoring VM."
  value       = azurerm_public_ip.monitoring.ip_address
}

output "private_ip_address" {
  description = "Private IPv4 address of the monitoring VM."
  value       = azurerm_network_interface.monitoring.private_ip_address
}

output "admin_username" {
  description = "Linux administrator account."
  value       = var.admin_username
}

output "grafana_url" {
  description = "Grafana URL. Access is restricted by the NSG to admin_source_cidr."
  value       = "http://${azurerm_public_ip.monitoring.ip_address}:3000"
}

output "ssh_command" {
  description = "SSH command for administration."
  value       = "ssh ${var.admin_username}@${azurerm_public_ip.monitoring.ip_address}"
}

output "prometheus_tunnel_command" {
  description = "SSH tunnel for the private Prometheus interface. Open http://localhost:9090 after connecting."
  value       = "ssh -L 9090:127.0.0.1:9090 ${var.admin_username}@${azurerm_public_ip.monitoring.ip_address}"
}
