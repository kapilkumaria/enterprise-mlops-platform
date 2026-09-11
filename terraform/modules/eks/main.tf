resource "aws_cloudwatch_log_group" "cluster" {
  #checkov:skip=CKV_AWS_338:Seven-day retention is intentional for the temporary development cluster.
  #checkov:skip=CKV_AWS_158:AWS-managed encryption is sufficient for temporary development control-plane logs.
  name              = "/aws/eks/${var.cluster_name}/cluster"
  retention_in_days = var.cluster_log_retention_days

  tags = merge(
    var.tags,
    {
      Name = "${var.cluster_name}-control-plane-logs"
    }
  )
}

resource "aws_eks_cluster" "this" {
  #checkov:skip=CKV_AWS_38:The public endpoint CIDR is supplied through a validated variable that prohibits 0.0.0.0/0.
  #checkov:skip=CKV_AWS_39:Restricted public access is required from the administrator workstation during the portfolio build.
  #checkov:skip=CKV_AWS_58:A dedicated KMS key is omitted from this temporary cost-controlled development cluster.
  #checkov:skip=CKV_AWS_339:EKS 1.36 was verified through the AWS API as being in standard support.
  name     = var.cluster_name
  role_arn = aws_iam_role.cluster.arn
  version  = var.kubernetes_version

  enabled_cluster_log_types = [
    "api",
    "audit",
    "authenticator",
    "controllerManager",
    "scheduler",
  ]

  access_config {
    authentication_mode                         = "API"
    bootstrap_cluster_creator_admin_permissions = true
  }

  vpc_config {
    subnet_ids = var.private_subnet_ids

    endpoint_private_access = true
    endpoint_public_access  = true
    public_access_cidrs     = var.cluster_endpoint_public_access_cidrs
  }

  depends_on = [
    aws_cloudwatch_log_group.cluster,
    aws_iam_role_policy_attachment.cluster_policy,
  ]

  tags = merge(
    var.tags,
    {
      Name = var.cluster_name
    }
  )
}

resource "aws_eks_node_group" "system" {
  cluster_name    = aws_eks_cluster.this.name
  node_group_name = "system"
  node_role_arn   = aws_iam_role.node.arn
  subnet_ids      = var.private_subnet_ids
  version         = var.kubernetes_version

  capacity_type  = "ON_DEMAND"
  ami_type       = "AL2023_x86_64_STANDARD"
  instance_types = var.node_instance_types
  disk_size      = var.node_disk_size

  scaling_config {
    desired_size = var.node_desired_size
    min_size     = var.node_min_size
    max_size     = var.node_max_size
  }

  update_config {
    max_unavailable = 1
  }

  labels = {
    role        = "system"
    environment = "dev"
  }

  depends_on = [
    aws_iam_role_policy_attachment.worker_node,
    aws_iam_role_policy_attachment.container_registry,
    aws_iam_role_policy_attachment.cni,
  ]

  tags = merge(
    var.tags,
    {
      Name = "${var.cluster_name}-system"
    }
  )
}

resource "aws_eks_node_group" "advanced" {
  count = var.advanced_node_enabled ? 1 : 0

  cluster_name    = aws_eks_cluster.this.name
  node_group_name = "advanced-mlops"
  node_role_arn   = aws_iam_role.node.arn
  subnet_ids      = var.private_subnet_ids
  version         = var.kubernetes_version

  capacity_type  = "ON_DEMAND"
  ami_type       = "AL2023_x86_64_STANDARD"
  instance_types = var.advanced_node_instance_types
  disk_size      = var.advanced_node_disk_size

  scaling_config {
    desired_size = var.advanced_node_desired_size
    min_size     = var.advanced_node_min_size
    max_size     = var.advanced_node_max_size
  }

  update_config {
    max_unavailable = 1
  }

  labels = {
    environment = "dev"
    role        = "advanced-mlops"
    workload    = "ml-platform"
  }

  depends_on = [
    aws_iam_role_policy_attachment.worker_node,
    aws_iam_role_policy_attachment.container_registry,
    aws_iam_role_policy_attachment.cni,
  ]

  tags = merge(
    var.tags,
    {
      Component = "advanced-mlops"
      Name      = "${var.cluster_name}-advanced-mlops"
    }
  )
}
