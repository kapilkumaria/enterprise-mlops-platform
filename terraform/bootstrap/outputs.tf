output "state_bucket_name" {
  description = "Name of the Terraform remote-state bucket."
  value       = aws_s3_bucket.terraform_state.bucket
}

output "state_bucket_arn" {
  description = "ARN of the Terraform remote-state bucket."
  value       = aws_s3_bucket.terraform_state.arn
}

output "development_state_key" {
  description = "S3 object key planned for the development state."
  value       = "environments/dev/terraform.tfstate"
}

output "backend_initialization_example" {
  description = "Example command used to initialize the development backend."
  value = join(" ", [
    "terraform -chdir=terraform/environments/dev init",
    "-backend-config=bucket=${aws_s3_bucket.terraform_state.bucket}",
    "-backend-config=key=environments/dev/terraform.tfstate",
    "-backend-config=region=${var.aws_region}",
    "-backend-config=use_lockfile=true",
  ])
}
