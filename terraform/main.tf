locals {
  name_prefix         = "${var.project_name}-${var.environment}"
  gitlab_access_cidrs = length(var.gitlab_access_cidrs) > 0 ? var.gitlab_access_cidrs : [var.admin_source_cidr]
  common_tags = merge(var.tags, {
    environment = var.environment
    project     = "gitlab-observability-platform"
  })
}

resource "azurerm_resource_group" "monitoring" {
  name     = "${local.name_prefix}-rg"
  location = var.location
  tags     = local.common_tags
}

resource "azurerm_virtual_network" "monitoring" {
  name                = "${local.name_prefix}-vnet"
  address_space       = ["10.42.0.0/16"]
  location            = azurerm_resource_group.monitoring.location
  resource_group_name = azurerm_resource_group.monitoring.name
  tags                = local.common_tags
}

resource "azurerm_subnet" "monitoring" {
  name                 = "monitoring-subnet"
  resource_group_name  = azurerm_resource_group.monitoring.name
  virtual_network_name = azurerm_virtual_network.monitoring.name
  address_prefixes     = ["10.42.1.0/24"]
}

resource "azurerm_subnet" "gitlab" {
  name                 = "gitlab-subnet"
  resource_group_name  = azurerm_resource_group.monitoring.name
  virtual_network_name = azurerm_virtual_network.monitoring.name
  address_prefixes     = ["10.42.2.0/24"]
}

resource "azurerm_public_ip" "monitoring" {
  name                = "${local.name_prefix}-pip"
  location            = azurerm_resource_group.monitoring.location
  resource_group_name = azurerm_resource_group.monitoring.name
  allocation_method   = "Static"
  sku                 = "Standard"
  tags                = local.common_tags
}

resource "azurerm_public_ip" "gitlab" {
  name                = "${local.name_prefix}-gitlab-pip"
  location            = azurerm_resource_group.monitoring.location
  resource_group_name = azurerm_resource_group.monitoring.name
  allocation_method   = "Static"
  sku                 = "Standard"
  tags                = merge(local.common_tags, { component = "gitlab" })
}

resource "azurerm_network_security_group" "monitoring" {
  name                = "${local.name_prefix}-nsg"
  location            = azurerm_resource_group.monitoring.location
  resource_group_name = azurerm_resource_group.monitoring.name
  tags                = local.common_tags
}

resource "azurerm_network_security_group" "gitlab" {
  name                = "${local.name_prefix}-gitlab-nsg"
  location            = azurerm_resource_group.monitoring.location
  resource_group_name = azurerm_resource_group.monitoring.name
  tags                = merge(local.common_tags, { component = "gitlab" })
}

resource "azurerm_network_security_rule" "ssh" {
  name                        = "Allow-SSH-From-Admin"
  priority                    = 100
  direction                   = "Inbound"
  access                      = "Allow"
  protocol                    = "Tcp"
  source_port_range           = "*"
  destination_port_range      = "22"
  source_address_prefix       = var.admin_source_cidr
  destination_address_prefix  = "*"
  resource_group_name         = azurerm_resource_group.monitoring.name
  network_security_group_name = azurerm_network_security_group.monitoring.name
}

resource "azurerm_network_security_rule" "prometheus" {
  count = var.expose_prometheus ? 1 : 0

  name                        = "Allow-Prometheus-From-Admin"
  priority                    = 120
  direction                   = "Inbound"
  access                      = "Allow"
  protocol                    = "Tcp"
  source_port_range           = "*"
  destination_port_range      = "9090"
  source_address_prefix       = var.admin_source_cidr
  destination_address_prefix  = "*"
  resource_group_name         = azurerm_resource_group.monitoring.name
  network_security_group_name = azurerm_network_security_group.monitoring.name
}

resource "azurerm_network_security_rule" "public_frontend" {
  count = var.public_frontend_enabled ? 1 : 0

  name                        = "Allow-CloudSphere-Web-From-Internet"
  priority                    = 130
  direction                   = "Inbound"
  access                      = "Allow"
  protocol                    = "Tcp"
  source_port_range           = "*"
  destination_port_ranges     = ["80", "443"]
  source_address_prefix       = "Internet"
  destination_address_prefix  = "*"
  resource_group_name         = azurerm_resource_group.monitoring.name
  network_security_group_name = azurerm_network_security_group.monitoring.name
}

resource "azurerm_network_security_rule" "gitlab_ssh" {
  name                        = "Allow-GitLab-Host-SSH-From-Admin"
  priority                    = 100
  direction                   = "Inbound"
  access                      = "Allow"
  protocol                    = "Tcp"
  source_port_range           = "*"
  destination_port_range      = "22"
  source_address_prefix       = var.admin_source_cidr
  destination_address_prefix  = "*"
  resource_group_name         = azurerm_resource_group.monitoring.name
  network_security_group_name = azurerm_network_security_group.gitlab.name
}

resource "azurerm_network_security_rule" "gitlab_web" {
  name                        = "Allow-GitLab-Web-From-Trusted-CIDRs"
  priority                    = 110
  direction                   = "Inbound"
  access                      = "Allow"
  protocol                    = "Tcp"
  source_port_range           = "*"
  destination_port_ranges     = ["80", "443"]
  source_address_prefixes     = local.gitlab_access_cidrs
  destination_address_prefix  = "*"
  resource_group_name         = azurerm_resource_group.monitoring.name
  network_security_group_name = azurerm_network_security_group.gitlab.name
}

resource "azurerm_network_security_rule" "gitlab_repository_ssh" {
  name                        = "Allow-GitLab-Repository-SSH-From-Trusted-CIDRs"
  priority                    = 120
  direction                   = "Inbound"
  access                      = "Allow"
  protocol                    = "Tcp"
  source_port_range           = "*"
  destination_port_range      = "2222"
  source_address_prefixes     = local.gitlab_access_cidrs
  destination_address_prefix  = "*"
  resource_group_name         = azurerm_resource_group.monitoring.name
  network_security_group_name = azurerm_network_security_group.gitlab.name
}

resource "azurerm_network_interface" "monitoring" {
  name                = "${local.name_prefix}-nic"
  location            = azurerm_resource_group.monitoring.location
  resource_group_name = azurerm_resource_group.monitoring.name
  tags                = local.common_tags

  ip_configuration {
    name                          = "primary"
    subnet_id                     = azurerm_subnet.monitoring.id
    private_ip_address_allocation = "Dynamic"
    public_ip_address_id          = azurerm_public_ip.monitoring.id
  }
}

resource "azurerm_network_interface" "gitlab" {
  name                = "${local.name_prefix}-gitlab-nic"
  location            = azurerm_resource_group.monitoring.location
  resource_group_name = azurerm_resource_group.monitoring.name
  tags                = merge(local.common_tags, { component = "gitlab" })

  ip_configuration {
    name                          = "primary"
    subnet_id                     = azurerm_subnet.gitlab.id
    private_ip_address_allocation = "Dynamic"
    public_ip_address_id          = azurerm_public_ip.gitlab.id
  }
}

resource "azurerm_network_interface_security_group_association" "monitoring" {
  network_interface_id      = azurerm_network_interface.monitoring.id
  network_security_group_id = azurerm_network_security_group.monitoring.id
}

resource "azurerm_network_interface_security_group_association" "gitlab" {
  network_interface_id      = azurerm_network_interface.gitlab.id
  network_security_group_id = azurerm_network_security_group.gitlab.id
}

resource "azurerm_linux_virtual_machine" "monitoring" {
  name                            = "${local.name_prefix}-vm"
  computer_name                   = "monitoring-vm"
  resource_group_name             = azurerm_resource_group.monitoring.name
  location                        = azurerm_resource_group.monitoring.location
  size                            = var.vm_size
  admin_username                  = var.admin_username
  disable_password_authentication = true
  provision_vm_agent              = true
  patch_assessment_mode           = "AutomaticByPlatform"
  patch_mode                      = "AutomaticByPlatform"
  secure_boot_enabled             = true
  vtpm_enabled                    = true
  custom_data                     = filebase64("${path.module}/cloud-init.yaml")
  network_interface_ids           = [azurerm_network_interface.monitoring.id]
  tags                            = local.common_tags

  admin_ssh_key {
    username   = var.admin_username
    public_key = file(pathexpand(var.ssh_public_key_path))
  }

  os_disk {
    name                 = "${local.name_prefix}-osdisk"
    caching              = "ReadWrite"
    storage_account_type = "StandardSSD_LRS"
    disk_size_gb         = var.os_disk_size_gb
  }

  source_image_reference {
    publisher = "Canonical"
    offer     = "ubuntu-24_04-lts"
    sku       = "server"
    version   = "latest"
  }

  identity {
    type = "SystemAssigned"
  }

  boot_diagnostics {}

  depends_on = [azurerm_network_interface_security_group_association.monitoring]
}

resource "azurerm_linux_virtual_machine" "gitlab" {
  name                            = "${local.name_prefix}-gitlab-vm"
  computer_name                   = "gitlab-vm"
  resource_group_name             = azurerm_resource_group.monitoring.name
  location                        = azurerm_resource_group.monitoring.location
  size                            = var.gitlab_vm_size
  admin_username                  = var.admin_username
  disable_password_authentication = true
  provision_vm_agent              = true
  patch_assessment_mode           = "AutomaticByPlatform"
  patch_mode                      = "AutomaticByPlatform"
  secure_boot_enabled             = true
  vtpm_enabled                    = true
  custom_data                     = filebase64("${path.module}/gitlab-cloud-init.yaml")
  network_interface_ids           = [azurerm_network_interface.gitlab.id]
  tags                            = merge(local.common_tags, { component = "gitlab" })

  admin_ssh_key {
    username   = var.admin_username
    public_key = file(pathexpand(var.ssh_public_key_path))
  }

  os_disk {
    name                 = "${local.name_prefix}-gitlab-osdisk"
    caching              = "ReadWrite"
    storage_account_type = "StandardSSD_LRS"
    disk_size_gb         = var.gitlab_os_disk_size_gb
  }

  source_image_reference {
    publisher = "Canonical"
    offer     = "ubuntu-24_04-lts"
    sku       = "server"
    version   = "latest"
  }

  identity {
    type = "SystemAssigned"
  }

  boot_diagnostics {}

  depends_on = [azurerm_network_interface_security_group_association.gitlab]
}

resource "azurerm_dev_test_global_vm_shutdown_schedule" "monitoring" {
  count = var.auto_shutdown_enabled ? 1 : 0

  virtual_machine_id = azurerm_linux_virtual_machine.monitoring.id
  location           = azurerm_resource_group.monitoring.location
  enabled            = true

  daily_recurrence_time = var.auto_shutdown_time
  timezone              = var.auto_shutdown_timezone

  notification_settings {
    enabled = false
  }

  tags = local.common_tags
}

resource "azurerm_dev_test_global_vm_shutdown_schedule" "gitlab" {
  count = var.auto_shutdown_enabled ? 1 : 0

  virtual_machine_id = azurerm_linux_virtual_machine.gitlab.id
  location           = azurerm_resource_group.monitoring.location
  enabled            = true

  daily_recurrence_time = var.auto_shutdown_time
  timezone              = var.auto_shutdown_timezone

  notification_settings {
    enabled = false
  }

  tags = local.common_tags
}
