# Minimal Amazon SageMaker Integration

This project includes a cost-controlled SageMaker deployment design for
the customer-churn model. No SageMaker endpoint is created by default.

## Model artifact

The validated model is exported from the MLflow `candidate` alias,
converted to `model.joblib`, and stored in the preserved private S3
bucket:

`s3://enterprise-mlops-platform-dev-931058976119/kserve/customer-churn/v1/model.joblib`

## Deployment contract

A production SageMaker deployment would use:

- Amazon SageMaker Model
- an immutable inference container image
- an S3 model artifact
- a SageMaker Endpoint Configuration
- a managed SageMaker Endpoint
- CloudWatch model and endpoint metrics

The endpoint would be created only through an explicit, approved
Terraform or AWS CLI change. It is intentionally excluded from the
default Project 8 validation to avoid ongoing endpoint charges.

## Security

The model artifact remains private in S3. Production deployment should
use a dedicated SageMaker execution role with read-only access to the
model prefix. Credentials are never stored in the repository.

## Cost boundary

This project does not create:

- a SageMaker real-time endpoint
- a SageMaker serverless endpoint
- a SageMaker notebook instance
- a SageMaker training job

The live KServe deployment is the validated serving implementation.
SageMaker is documented as an optional managed-cloud serving target.
