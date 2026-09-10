output "vpc_id" {
  description = "ID of the development VPC."
  value       = module.networking.vpc_id
}

output "public_subnet_ids" {
  description = "IDs of the development public subnets."
  value       = module.networking.public_subnet_ids
}

output "private_subnet_ids" {
  description = "IDs of the development private subnets."
  value       = module.networking.private_subnet_ids
}

output "nat_gateway_id" {
  description = "ID of the development NAT Gateway."
  value       = module.networking.nat_gateway_id
}

output "eks_cluster_name" {
  description = "Planned name of the development EKS cluster."
  value       = local.eks_cluster_name
}

output "ecr_repository_name" {
  description = "Name of the API ECR repository."
  value       = module.ecr.repository_name
}

output "ecr_repository_url" {
  description = "URL of the API ECR repository."
  value       = module.ecr.repository_url
}

output "artifact_bucket_name" {
  description = "Name of the DVC and MLflow artifact bucket."
  value       = module.storage.bucket_name
}

output "dvc_remote_uri" {
  description = "S3 URI used for DVC artifacts."
  value       = module.storage.dvc_remote_uri
}

output "mlflow_artifact_uri" {
  description = "S3 URI used for MLflow artifacts."
  value       = module.storage.mlflow_artifact_uri
}

output "eks_cluster_arn" {
  description = "ARN of the development EKS cluster."
  value       = module.eks.cluster_arn
}

output "eks_cluster_endpoint" {
  description = "Endpoint of the development EKS cluster."
  value       = module.eks.cluster_endpoint
}

output "eks_node_group_name" {
  description = "Name of the development EKS node group."
  value       = module.eks.node_group_name
}

output "eks_cluster_role_arn" {
  description = "ARN of the EKS control-plane role."
  value       = module.eks.cluster_role_arn
}

output "eks_node_role_arn" {
  description = "ARN of the EKS worker-node role."
  value       = module.eks.node_role_arn
}

output "mlflow_role_arn" {
  description = "IAM role used by the MLflow Kubernetes service account."
  value       = aws_iam_role.mlflow.arn
}

output "ebs_csi_role_arn" {
  description = "IAM role used by the EBS CSI controller."
  value       = aws_iam_role.ebs_csi.arn
}

output "mlflow_pod_identity_association_id" {
  description = "ID of the MLflow EKS Pod Identity association."
  value       = aws_eks_pod_identity_association.mlflow.association_id
}

output "ebs_csi_pod_identity_association_id" {
  description = "ID of the EBS CSI EKS Pod Identity association."
  value       = aws_eks_pod_identity_association.ebs_csi.association_id
}

output "mlflow_ecr_repository_name" {
  description = "Name of the MLflow server ECR repository."
  value       = module.ecr_mlflow.repository_name
}

output "mlflow_ecr_repository_url" {
  description = "URL of the MLflow server ECR repository."
  value       = module.ecr_mlflow.repository_url
}

output "github_ecr_publisher_role_arn" {
  description = "IAM role assumed by GitHub Actions to publish project images."
  value       = aws_iam_role.github_ecr_publisher.arn
}
