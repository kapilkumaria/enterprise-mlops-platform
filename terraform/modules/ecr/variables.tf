variable "repository_name" {
  description = "Name of the ECR repository."
  type        = string
}

variable "image_retention_count" {
  description = "Number of tagged container images retained."
  type        = number
  default     = 10

  validation {
    condition     = var.image_retention_count >= 2
    error_message = "At least two tagged images must be retained."
  }
}

variable "tags" {
  description = "Common tags assigned to ECR resources."
  type        = map(string)
  default     = {}
}
