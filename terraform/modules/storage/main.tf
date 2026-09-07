resource "aws_s3_bucket" "artifacts" {
  #checkov:skip=CKV_AWS_18:Dedicated access-log storage is intentionally omitted for the short-lived development bucket.
  #checkov:skip=CKV2_AWS_62:Event notifications are not required by the current DVC and MLflow workflows.
  #checkov:skip=CKV_AWS_144:Cross-region replication is outside the single-region development scope.
  #checkov:skip=CKV_AWS_145:Development artifacts use AWS-managed AES256 encryption to avoid a dedicated KMS key.
  bucket        = var.bucket_name
  force_destroy = var.force_destroy

  tags = merge(
    var.tags,
    {
      Name    = var.bucket_name
      Purpose = "mlops-artifacts"
    }
  )
}

resource "aws_s3_bucket_ownership_controls" "artifacts" {
  bucket = aws_s3_bucket.artifacts.id

  rule {
    object_ownership = "BucketOwnerEnforced"
  }
}

resource "aws_s3_bucket_public_access_block" "artifacts" {
  bucket = aws_s3_bucket.artifacts.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket_versioning" "artifacts" {
  bucket = aws_s3_bucket.artifacts.id

  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "artifacts" {
  bucket = aws_s3_bucket.artifacts.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }

    bucket_key_enabled = true
  }
}

resource "aws_s3_bucket_lifecycle_configuration" "artifacts" {
  bucket = aws_s3_bucket.artifacts.id

  depends_on = [
    aws_s3_bucket_versioning.artifacts
  ]

  rule {
    id     = "artifact-retention"
    status = "Enabled"

    filter {}

    abort_incomplete_multipart_upload {
      days_after_initiation = 7
    }

    noncurrent_version_expiration {
      noncurrent_days = var.noncurrent_version_retention_days
    }
  }
}
