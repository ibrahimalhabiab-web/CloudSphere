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

output "gitlab_public_ip_address" {
  description = "Static public IPv4 address of the GitLab VM."
  value       = azurerm_public_ip.gitlab.ip_address
}

output "gitlab_private_ip_address" {
  description = "Private IPv4 address used by Prometheus to monitor GitLab."
  value       = azurerm_network_interface.gitlab.private_ip_address
}

output "admin_username" {
  description = "Linux administrator account."
  value       = var.admin_username
}

output "grafana_url" {
  description = "Grafana URL. Access is restricted by the NSG to admin_source_cidr."
  value       = "http://${azurerm_public_ip.monitoring.ip_address}:3000"
}

output "gitlab_url" {
  description = "Restricted HTTP URL for the self-managed GitLab service. Add DNS and TLS before production."
  value       = "http://${azurerm_public_ip.gitlab.ip_address}"
}

output "ssh_command" {
  description = "SSH command for administration."
  value       = "ssh ${var.admin_username}@${azurerm_public_ip.monitoring.ip_address}"
}

output "gitlab_ssh_command" {
  description = "SSH command for GitLab host administration."
  value       = "ssh ${var.admin_username}@${azurerm_public_ip.gitlab.ip_address}"
}

output "gitlab_repository_ssh_example" {
  description = "Example repository SSH authority for the GitLab service exposed on port 2222."
  value       = "ssh://git@${azurerm_public_ip.gitlab.ip_address}:2222/GROUP/PROJECT.git"
}

output "prometheus_tunnel_command" {
  description = "SSH tunnel for the private Prometheus interface. Open http://localhost:9090 after connecting."
  value       = "ssh -L 9090:127.0.0.1:9090 ${var.admin_username}@${azurerm_public_ip.monitoring.ip_address}"
}
