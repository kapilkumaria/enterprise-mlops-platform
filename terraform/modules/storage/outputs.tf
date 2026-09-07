output "bucket_name" {
  description = "Name of the artifact bucket."
  value       = aws_s3_bucket.artifacts.bucket
}

output "bucket_arn" {
  description = "ARN of the artifact bucket."
  value       = aws_s3_bucket.artifacts.arn
}

output "dvc_remote_uri" {
  description = "S3 URI intended for DVC object storage."
  value       = "s3://${aws_s3_bucket.artifacts.bucket}/dvc"
}

output "mlflow_artifact_uri" {
  description = "S3 URI intended for MLflow artifacts."
  value       = "s3://${aws_s3_bucket.artifacts.bucket}/mlflow"
}
