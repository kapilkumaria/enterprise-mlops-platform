# KServe Standard Model Serving

This project serves the customer-churn model with KServe v0.20.0 in
Standard/RawDeployment mode on Amazon EKS.

## Scope

- Namespace: `kserve`
- Internal ClusterIP access only
- No Knative
- No Istio
- No public ingress
- No GPU workloads
- One digest-pinned churn predictor

The model is exported from the MLflow `candidate` alias and stored at:

`s3://enterprise-mlops-platform-dev-931058976119/kserve/customer-churn/v1`

S3 access uses the `kserve-model-reader` ServiceAccount with an
EKS Pod Identity role restricted to the model prefix.

The predictor image and KServe storage initializer are pinned by
SHA-256 digest. The source lock and renderer validate the mode,
namespace, model URI, and image contract.

Live validation confirmed:

- InferenceService Ready=True
- private S3 model download succeeded
- predictor Pod Ready
- named-feature prediction succeeded
- no public endpoint was created
