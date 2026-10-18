data "aws_eks_addon_version" "pod_identity_agent" {
  addon_name         = "eks-pod-identity-agent"
  kubernetes_version = var.kubernetes_version
  most_recent        = true
}

data "aws_eks_addon_version" "ebs_csi" {
  addon_name         = "aws-ebs-csi-driver"
  kubernetes_version = var.kubernetes_version
  most_recent        = true
}

data "aws_eks_addon_version" "metrics_server" {
  addon_name         = "metrics-server"
  kubernetes_version = var.kubernetes_version
  most_recent        = true
}

data "aws_iam_policy_document" "pod_identity_assume_role" {
  statement {
    effect = "Allow"

    principals {
      type        = "Service"
      identifiers = ["pods.eks.amazonaws.com"]
    }

    actions = [
      "sts:AssumeRole",
      "sts:TagSession",
    ]
  }
}

resource "aws_eks_addon" "pod_identity_agent" {
  cluster_name  = module.eks.cluster_name
  addon_name    = "eks-pod-identity-agent"
  addon_version = data.aws_eks_addon_version.pod_identity_agent.version

  resolve_conflicts_on_create = "OVERWRITE"
  resolve_conflicts_on_update = "PRESERVE"

  tags = merge(
    local.common_tags,
    {
      Name = "${local.name_prefix}-pod-identity-agent"
    }
  )
}

resource "aws_eks_addon" "metrics_server" {
  cluster_name  = module.eks.cluster_name
  addon_name    = "metrics-server"
  addon_version = data.aws_eks_addon_version.metrics_server.version

  resolve_conflicts_on_create = "OVERWRITE"
  resolve_conflicts_on_update = "PRESERVE"

  tags = merge(
    local.common_tags,
    {
      Name = "${local.name_prefix}-metrics-server"
    }
  )
}

resource "aws_iam_role" "ebs_csi" {
  name = "${local.name_prefix}-ebs-csi-role"

  assume_role_policy = (
    data.aws_iam_policy_document.pod_identity_assume_role.json
  )

  tags = merge(
    local.common_tags,
    {
      Name = "${local.name_prefix}-ebs-csi-role"
    }
  )
}

resource "aws_iam_role_policy_attachment" "ebs_csi" {
  role       = aws_iam_role.ebs_csi.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonEBSCSIDriverPolicy"
}

resource "aws_eks_pod_identity_association" "ebs_csi" {
  cluster_name    = module.eks.cluster_name
  namespace       = "kube-system"
  service_account = "ebs-csi-controller-sa"
  role_arn        = aws_iam_role.ebs_csi.arn

  depends_on = [
    aws_eks_addon.pod_identity_agent,
  ]
}

resource "aws_eks_addon" "ebs_csi" {
  cluster_name  = module.eks.cluster_name
  addon_name    = "aws-ebs-csi-driver"
  addon_version = data.aws_eks_addon_version.ebs_csi.version

  resolve_conflicts_on_create = "OVERWRITE"
  resolve_conflicts_on_update = "PRESERVE"

  depends_on = [
    aws_iam_role_policy_attachment.ebs_csi,
    aws_eks_pod_identity_association.ebs_csi,
  ]

  tags = merge(
    local.common_tags,
    {
      Name = "${local.name_prefix}-ebs-csi-driver"
    }
  )
}

resource "aws_iam_role" "mlflow" {
  name = "${local.name_prefix}-mlflow-role"

  assume_role_policy = (
    data.aws_iam_policy_document.pod_identity_assume_role.json
  )

  tags = merge(
    local.common_tags,
    {
      Name = "${local.name_prefix}-mlflow-role"
    }
  )
}

data "aws_iam_policy_document" "mlflow_artifacts" {
  statement {
    sid    = "ListMLflowArtifactPrefix"
    effect = "Allow"

    actions = [
      "s3:ListBucket",
      "s3:GetBucketLocation",
    ]

    resources = [
      module.storage.bucket_arn,
    ]

    condition {
      test     = "StringLike"
      variable = "s3:prefix"

      values = [
        "mlflow",
        "mlflow/*",
      ]
    }
  }

  statement {
    sid    = "ManageMLflowArtifactObjects"
    effect = "Allow"

    actions = [
      "s3:AbortMultipartUpload",
      "s3:DeleteObject",
      "s3:GetObject",
      "s3:GetObjectVersion",
      "s3:ListMultipartUploadParts",
      "s3:PutObject",
    ]

    resources = [
      "${module.storage.bucket_arn}/mlflow/*",
    ]
  }
}

resource "aws_iam_policy" "mlflow_artifacts" {
  name        = "${local.name_prefix}-mlflow-artifacts"
  description = "Permit MLflow to manage its S3 artifact prefix."
  policy      = data.aws_iam_policy_document.mlflow_artifacts.json

  tags = merge(
    local.common_tags,
    {
      Name = "${local.name_prefix}-mlflow-artifacts"
    }
  )
}

resource "aws_iam_role_policy_attachment" "mlflow_artifacts" {
  role       = aws_iam_role.mlflow.name
  policy_arn = aws_iam_policy.mlflow_artifacts.arn
}

resource "aws_eks_pod_identity_association" "mlflow" {
  cluster_name    = module.eks.cluster_name
  namespace       = "mlops"
  service_account = "mlflow"
  role_arn        = aws_iam_role.mlflow.arn

  depends_on = [
    aws_eks_addon.pod_identity_agent,
    aws_iam_role_policy_attachment.mlflow_artifacts,
  ]
}
resource "aws_iam_role" "churn_api" {
  name = "${local.name_prefix}-churn-api-role"

  assume_role_policy = (
    data.aws_iam_policy_document.pod_identity_assume_role.json
  )

  tags = merge(
    local.common_tags,
    {
      Name = "${local.name_prefix}-churn-api-role"
    }
  )
}

data "aws_iam_policy_document" "churn_api_artifacts" {
  statement {
    sid    = "ListMLflowArtifactPrefix"
    effect = "Allow"

    actions = [
      "s3:ListBucket",
      "s3:GetBucketLocation",
    ]

    resources = [
      module.storage.bucket_arn,
    ]

    condition {
      test     = "StringLike"
      variable = "s3:prefix"
      values   = ["mlflow", "mlflow/*"]
    }
  }

  statement {
    sid       = "ReadMLflowArtifactObjects"
    effect    = "Allow"
    actions   = ["s3:GetObject", "s3:GetObjectVersion"]
    resources = ["${module.storage.bucket_arn}/mlflow/*"]
  }
}

resource "aws_iam_policy" "churn_api_artifacts" {
  name        = "${local.name_prefix}-churn-api-artifacts"
  description = "Permit the churn API to read MLflow model artifacts."
  policy      = data.aws_iam_policy_document.churn_api_artifacts.json

  tags = merge(
    local.common_tags,
    {
      Name = "${local.name_prefix}-churn-api-artifacts"
    }
  )
}

resource "aws_iam_role_policy_attachment" "churn_api_artifacts" {
  role       = aws_iam_role.churn_api.name
  policy_arn = aws_iam_policy.churn_api_artifacts.arn
}

resource "aws_eks_pod_identity_association" "churn_api" {
  cluster_name    = module.eks.cluster_name
  namespace       = "mlops"
  service_account = "churn-api"
  role_arn        = aws_iam_role.churn_api.arn

  depends_on = [
    aws_eks_addon.pod_identity_agent,
    aws_iam_role_policy_attachment.churn_api_artifacts,
  ]
}
