data "aws_iam_openid_connect_provider" "github_actions" {
  url = "https://token.actions.githubusercontent.com"
}

data "aws_iam_policy_document" "github_ecr_publisher_assume_role" {
  statement {
    sid    = "GitHubActionsOIDC"
    effect = "Allow"

    principals {
      type = "Federated"
      identifiers = [
        data.aws_iam_openid_connect_provider.github_actions.arn,
      ]
    }

    actions = [
      "sts:AssumeRoleWithWebIdentity",
    ]

    condition {
      test     = "StringEquals"
      variable = "token.actions.githubusercontent.com:aud"

      values = [
        "sts.amazonaws.com",
      ]
    }

    condition {
      test     = "StringEquals"
      variable = "token.actions.githubusercontent.com:sub"

      values = [
        "repo:kapilkumaria@42500918/enterprise-mlops-platform@1359579388:ref:refs/heads/main",
      ]
    }
  }
}

resource "aws_iam_role" "github_ecr_publisher" {
  name                 = "${local.name_prefix}-github-ecr-publisher"
  description          = "Allow the main branch GitHub workflow to publish project container images."
  assume_role_policy   = data.aws_iam_policy_document.github_ecr_publisher_assume_role.json
  max_session_duration = 3600

  tags = merge(
    local.common_tags,
    {
      Name      = "${local.name_prefix}-github-ecr-publisher"
      Component = "continuous-delivery"
    }
  )
}

data "aws_iam_policy_document" "github_ecr_publisher" {
  statement {
    sid    = "RequestECRAuthorizationToken"
    effect = "Allow"

    actions = [
      "ecr:GetAuthorizationToken",
    ]

    resources = ["*"]
  }

  statement {
    sid    = "PublishProjectContainerImages"
    effect = "Allow"

    actions = [
      "ecr:BatchCheckLayerAvailability",
      "ecr:BatchGetImage",
      "ecr:CompleteLayerUpload",
      "ecr:DescribeImages",
      "ecr:GetDownloadUrlForLayer",
      "ecr:InitiateLayerUpload",
      "ecr:PutImage",
      "ecr:UploadLayerPart",
    ]

    resources = [
      module.ecr.repository_arn,
      module.ecr_mlflow.repository_arn,
    ]
  }
}

resource "aws_iam_role_policy" "github_ecr_publisher" {
  name   = "${local.name_prefix}-github-ecr-publisher"
  role   = aws_iam_role.github_ecr_publisher.id
  policy = data.aws_iam_policy_document.github_ecr_publisher.json
}
