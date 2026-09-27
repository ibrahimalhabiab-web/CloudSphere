variable "project_name" {
  description = "Short lowercase name used in Azure resource names."
  type        = string
  default     = "cloudsphere"

  validation {
    condition     = can(regex("^[a-z][a-z0-9-]{2,18}$", var.project_name))
    error_message = "project_name must be 3-19 lowercase letters, digits, or hyphens and start with a letter."
  }
}

variable "environment" {
  description = "Deployment environment label."
  type        = string
  default     = "lab"

  validation {
    condition     = contains(["lab", "dev", "test", "prod"], var.environment)
    error_message = "environment must be one of: lab, dev, test, prod."
  }
}

variable "location" {
  description = "Azure region for all resources."
  type        = string
  default     = "uaenorth"
}

variable "admin_username" {
  description = "Linux administrator account created on the virtual machine."
  type        = string
  default     = "azureadmin"

  validation {
    condition     = can(regex("^[a-z][a-z0-9_-]{2,30}$", var.admin_username))
    error_message = "admin_username must be a valid lowercase Linux account name."
  }
}

variable "ssh_public_key_path" {
  description = "Path to the administrator SSH public key."
  type        = string
  default     = "~/.ssh/id_ed25519.pub"
}

variable "admin_source_cidr" {
  description = "Trusted public IPv4 CIDR allowed to reach administrative SSH and any explicitly enabled private service, normally YOUR_PUBLIC_IP/32."
  type        = string

  validation {
    condition     = can(cidrnetmask(var.admin_source_cidr)) && var.admin_source_cidr != "0.0.0.0/0"
    error_message = "Provide a valid restricted IPv4 CIDR. The open range 0.0.0.0/0 is intentionally rejected."
  }
}

variable "vm_size" {
  description = "Monitoring VM size. Select a two-vCPU SKU available to the subscription and region."
  type        = string
  default     = "Standard_D2ads_v7"
}

variable "os_disk_size_gb" {
  description = "Operating-system disk size in GiB."
  type        = number
  default     = 64

  validation {
    condition     = var.os_disk_size_gb >= 32
    error_message = "os_disk_size_gb must be at least 32 GiB."
  }
}

variable "gitlab_vm_size" {
  description = "GitLab VM size. The default is a constrained training SKU; use at least the current GitLab baseline for production."
  type        = string
  default     = "Standard_D2ads_v7"
}

variable "gitlab_os_disk_size_gb" {
  description = "GitLab operating-system and repository disk size in GiB. Increase it for real repositories and artifacts."
  type        = number
  default     = 128

  validation {
    condition     = var.gitlab_os_disk_size_gb >= 64
    error_message = "gitlab_os_disk_size_gb must be at least 64 GiB."
  }
}

variable "gitlab_access_cidrs" {
  description = "Trusted public IPv4 CIDRs allowed to reach GitLab web and repository SSH. An empty list uses admin_source_cidr."
  type        = list(string)
  default     = []

  validation {
    condition = alltrue([
      for cidr in var.gitlab_access_cidrs : can(cidrnetmask(cidr)) && cidr != "0.0.0.0/0"
    ])
    error_message = "Every GitLab access CIDR must be valid and must not be 0.0.0.0/0."
  }
}

variable "expose_prometheus" {
  description = "Create a public NSG rule for Prometheus. Keep false and use an SSH tunnel unless there is a specific need."
  type        = bool
  default     = false
}

variable "public_frontend_enabled" {
  description = "Allow public HTTP and HTTPS traffic to the monitoring VM for the CloudSphere frontend. Keep false until the reverse proxy and DNS are ready."
  type        = bool
  default     = false
}

variable "public_frontend_domain" {
  description = "Public DNS hostname for the CloudSphere frontend. DNS remains managed outside Terraform."
  type        = string
  default     = "www.cloudsphere-sda.online"

  validation {
    condition = (
      length(var.public_frontend_domain) <= 253 &&
      can(regex("^(?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\\.)+[a-z]{2,63}$", lower(var.public_frontend_domain)))
    )
    error_message = "public_frontend_domain must be a valid DNS hostname without a scheme, port, path, or trailing dot."
  }
}

variable "auto_shutdown_enabled" {
  description = "Enable a daily VM shutdown schedule to control lab cost."
  type        = bool
  default     = true
}

variable "auto_shutdown_time" {
  description = "Daily auto-shutdown time in 24-hour HHmm format."
  type        = string
  default     = "2300"

  validation {
    condition     = can(regex("^(?:[01][0-9]|2[0-3])[0-5][0-9]$", var.auto_shutdown_time))
    error_message = "auto_shutdown_time must use HHmm, for example 2300."
  }
}

variable "auto_shutdown_timezone" {
  description = "Azure DevTest schedule time-zone name."
  type        = string
  default     = "Arab Standard Time"
}

variable "tags" {
  description = "Additional tags applied to Azure resources."
  type        = map(string)
  default = {
    owner       = "cloud-project"
    managed-by  = "terraform"
    application = "gitlab-observability"
  }
}
