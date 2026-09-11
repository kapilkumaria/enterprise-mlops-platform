variable "cluster_name" {
  description = "Name of the EKS cluster."
  type        = string
}

variable "kubernetes_version" {
  description = "Kubernetes version used by EKS."
  type        = string
  default     = "1.36"
}

variable "private_subnet_ids" {
  description = "Private subnet IDs used by EKS and its node group."
  type        = list(string)

  validation {
    condition     = length(var.private_subnet_ids) >= 2
    error_message = "At least two private subnets are required."
  }
}

variable "cluster_endpoint_public_access_cidrs" {
  description = "CIDR blocks permitted to access the public EKS API."
  type        = list(string)

  validation {
    condition = (
      length(var.cluster_endpoint_public_access_cidrs) > 0 &&
      !contains(
        var.cluster_endpoint_public_access_cidrs,
        "0.0.0.0/0"
      )
    )
    error_message = "Provide at least one restricted CIDR; 0.0.0.0/0 is prohibited."
  }
}

variable "node_instance_types" {
  description = "EC2 instance types used by the managed node group."
  type        = list(string)
  default     = ["t3.medium"]
}

variable "node_desired_size" {
  description = "Desired number of development worker nodes."
  type        = number
  default     = 2
}

variable "node_min_size" {
  description = "Minimum number of development worker nodes."
  type        = number
  default     = 1
}

variable "node_max_size" {
  description = "Maximum number of development worker nodes."
  type        = number
  default     = 3
}

variable "node_disk_size" {
  description = "Node root-volume size in GiB."
  type        = number
  default     = 30
}

variable "cluster_log_retention_days" {
  description = "CloudWatch retention for EKS control-plane logs."
  type        = number
  default     = 7
}

variable "tags" {
  description = "Common tags assigned to EKS resources."
  type        = map(string)
  default     = {}
}

variable "advanced_node_enabled" {
  description = "Create dedicated worker capacity for advanced MLOps components."
  type        = bool
  default     = false
}

variable "advanced_node_instance_types" {
  description = "EC2 instance types used by the advanced MLOps node group."
  type        = list(string)
  default     = ["m7i.large"]

  validation {
    condition     = length(var.advanced_node_instance_types) > 0
    error_message = "Provide at least one advanced MLOps instance type."
  }
}

variable "advanced_node_desired_size" {
  description = "Desired number of advanced MLOps worker nodes."
  type        = number
  default     = 2
}

variable "advanced_node_min_size" {
  description = "Minimum number of advanced MLOps worker nodes."
  type        = number
  default     = 1
}

variable "advanced_node_max_size" {
  description = "Maximum number of advanced MLOps worker nodes."
  type        = number
  default     = 2
}

variable "advanced_node_disk_size" {
  description = "Root-volume size in GiB for advanced MLOps workers."
  type        = number
  default     = 50
}
