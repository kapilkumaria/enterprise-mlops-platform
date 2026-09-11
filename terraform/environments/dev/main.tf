module "networking" {
  source = "../../modules/networking"

  name_prefix          = local.name_prefix
  vpc_cidr             = var.vpc_cidr
  availability_zones   = var.availability_zones
  public_subnet_cidrs  = var.public_subnet_cidrs
  private_subnet_cidrs = var.private_subnet_cidrs
  eks_cluster_name     = local.eks_cluster_name
  tags                 = local.common_tags
}

data "aws_caller_identity" "current" {}

module "ecr" {
  source = "../../modules/ecr"

  repository_name       = "${local.name_prefix}-api"
  image_retention_count = var.ecr_image_retention_count
  tags                  = local.common_tags
}


module "ecr_mlflow" {
  source = "../../modules/ecr"

  repository_name       = "${local.name_prefix}-mlflow"
  image_retention_count = var.ecr_image_retention_count
  tags = merge(
    local.common_tags,
    {
      Component = "mlflow"
    }
  )
}

module "storage" {
  source = "../../modules/storage"

  bucket_name = lower(
    "${local.name_prefix}-${data.aws_caller_identity.current.account_id}"
  )
  force_destroy                     = var.force_destroy_storage
  noncurrent_version_retention_days = 30
  tags                              = local.common_tags
}

module "eks" {
  source = "../../modules/eks"

  cluster_name                         = local.eks_cluster_name
  kubernetes_version                   = var.kubernetes_version
  private_subnet_ids                   = module.networking.private_subnet_ids
  cluster_endpoint_public_access_cidrs = var.cluster_endpoint_public_access_cidrs

  node_instance_types = var.eks_node_instance_types
  node_desired_size   = var.eks_node_desired_size
  node_min_size       = var.eks_node_min_size
  node_max_size       = var.eks_node_max_size

  advanced_node_enabled        = var.advanced_node_enabled
  advanced_node_instance_types = var.advanced_node_instance_types
  advanced_node_desired_size   = var.advanced_node_desired_size
  advanced_node_min_size       = var.advanced_node_min_size
  advanced_node_max_size       = var.advanced_node_max_size
  advanced_node_disk_size      = var.advanced_node_disk_size

  cluster_log_retention_days = 7
  tags                       = local.common_tags
}
