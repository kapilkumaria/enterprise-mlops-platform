variable "aws_region" {
  description = "AWS region used by the development environment."
  type        = string
  default     = "us-east-1"

  validation {
    condition     = var.aws_region == "us-east-1"
    error_message = "This portfolio environment is restricted to us-east-1."
  }
}

variable "project_name" {
  description = "Project name used for resource naming and tagging."
  type        = string
  default     = "enterprise-mlops-platform"
}

variable "environment" {
  description = "Deployment environment name."
  type        = string
  default     = "dev"

  validation {
    condition     = contains(["dev"], var.environment)
    error_message = "Only the dev environment is currently supported."
  }
}

variable "owner" {
  description = "Owner tag assigned to project resources."
  type        = string
  default     = "kapil-kumaria"
}

variable "vpc_cidr" {
  description = "IPv4 CIDR block assigned to the development VPC."
  type        = string
  default     = "10.80.0.0/16"
}

variable "availability_zones" {
  description = "Availability zones used by the development VPC."
  type        = list(string)
  default = [
    "us-east-1a",
    "us-east-1b",
  ]
}

variable "public_subnet_cidrs" {
  description = "CIDRs assigned to development public subnets."
  type        = list(string)
  default = [
    "10.80.0.0/24",
    "10.80.1.0/24",
  ]
}

variable "private_subnet_cidrs" {
  description = "CIDRs assigned to development private subnets."
  type        = list(string)
  default = [
    "10.80.10.0/24",
    "10.80.11.0/24",
  ]
}

variable "ecr_image_retention_count" {
  description = "Number of tagged API images retained in ECR."
  type        = number
  default     = 10

  validation {
    condition     = var.ecr_image_retention_count >= 2
    error_message = "At least two ECR images must be retained."
  }
}

variable "force_destroy_storage" {
  description = "Allow development artifact storage to be destroyed."
  type        = bool
  default     = true
}

variable "kubernetes_version" {
  description = "Kubernetes version used by the development EKS cluster."
  type        = string
  default     = "1.36"

  validation {
    condition     = contains(["1.34", "1.35", "1.36"], var.kubernetes_version)
    error_message = "Select an EKS version currently in standard support."
  }
}

variable "cluster_endpoint_public_access_cidrs" {
  description = "Restricted CIDRs allowed to access the EKS public endpoint."
  type        = list(string)

  validation {
    condition = (
      length(var.cluster_endpoint_public_access_cidrs) > 0 &&
      !contains(
        var.cluster_endpoint_public_access_cidrs,
        "0.0.0.0/0"
      )
    )
    error_message = "A restricted administrator CIDR is required."
  }
}

variable "eks_node_instance_types" {
  description = "EC2 instance types used by EKS worker nodes."
  type        = list(string)
  default     = ["t3.medium"]
}

variable "eks_node_desired_size" {
  description = "Desired number of EKS worker nodes."
  type        = number
  default     = 2
}

variable "eks_node_min_size" {
  description = "Minimum number of EKS worker nodes."
  type        = number
  default     = 1
}

variable "eks_node_max_size" {
  description = "Maximum number of EKS worker nodes."
  type        = number
  default     = 3
}

variable "advanced_node_enabled" {
  description = "Create dedicated worker capacity for advanced MLOps components."
  type        = bool
  default     = false
}

variable "advanced_node_instance_types" {
  description = "EC2 instance types used by advanced MLOps workers."
  type        = list(string)
  default     = ["m7i.large"]

  validation {
    condition     = length(var.advanced_node_instance_types) > 0
    error_message = "Provide at least one advanced MLOps instance type."
  }
}

variable "advanced_node_desired_size" {
  description = "Desired number of advanced MLOps workers."
  type        = number
  default     = 2
}

variable "advanced_node_min_size" {
  description = "Minimum number of advanced MLOps workers."
  type        = number
  default     = 1
}

variable "advanced_node_max_size" {
  description = "Maximum number of advanced MLOps workers."
  type        = number
  default     = 2
}

variable "advanced_node_disk_size" {
  description = "Root-volume size in GiB for advanced MLOps workers."
  type        = number
  default     = 50
}
