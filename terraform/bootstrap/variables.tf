variable "aws_region" {
  description = "AWS region used for Terraform state storage."
  type        = string
  default     = "us-east-1"

  validation {
    condition     = var.aws_region == "us-east-1"
    error_message = "Terraform state storage is restricted to us-east-1."
  }
}

variable "project_name" {
  description = "Project name used for resource naming and tagging."
  type        = string
  default     = "enterprise-mlops-platform"
}

variable "environment" {
  description = "Environment represented by the bootstrap resources."
  type        = string
  default     = "shared"
}

variable "owner" {
  description = "Owner tag assigned to bootstrap resources."
  type        = string
  default     = "kapil-kumaria"
}

variable "noncurrent_version_retention_days" {
  description = "Days retained for previous Terraform state versions."
  type        = number
  default     = 30

  validation {
    condition     = var.noncurrent_version_retention_days >= 7
    error_message = "Previous state versions must be retained for at least seven days."
  }
}
