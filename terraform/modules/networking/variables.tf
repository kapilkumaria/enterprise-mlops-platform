variable "name_prefix" {
  description = "Prefix used for networking resource names."
  type        = string
}

variable "vpc_cidr" {
  description = "IPv4 CIDR block assigned to the VPC."
  type        = string
}

variable "availability_zones" {
  description = "Availability zones used by the VPC subnets."
  type        = list(string)

  validation {
    condition     = length(var.availability_zones) == 2
    error_message = "Exactly two availability zones must be provided."
  }
}

variable "public_subnet_cidrs" {
  description = "CIDR blocks assigned to public subnets."
  type        = list(string)

  validation {
    condition     = length(var.public_subnet_cidrs) == 2
    error_message = "Exactly two public subnet CIDRs must be provided."
  }
}

variable "private_subnet_cidrs" {
  description = "CIDR blocks assigned to private subnets."
  type        = list(string)

  validation {
    condition     = length(var.private_subnet_cidrs) == 2
    error_message = "Exactly two private subnet CIDRs must be provided."
  }
}

variable "eks_cluster_name" {
  description = "EKS cluster name used for Kubernetes subnet discovery."
  type        = string
}

variable "tags" {
  description = "Common tags assigned to networking resources."
  type        = map(string)
  default     = {}
}
