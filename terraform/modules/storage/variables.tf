variable "bucket_name" {
  description = "Globally unique S3 artifact bucket name."
  type        = string
}

variable "force_destroy" {
  description = "Allow development bucket removal with stored objects."
  type        = bool
  default     = false
}

variable "noncurrent_version_retention_days" {
  description = "Days retained for noncurrent object versions."
  type        = number
  default     = 30

  validation {
    condition     = var.noncurrent_version_retention_days >= 1
    error_message = "Retention must be at least one day."
  }
}

variable "tags" {
  description = "Common tags assigned to storage resources."
  type        = map(string)
  default     = {}
}
