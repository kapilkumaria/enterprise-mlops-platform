# Kubeflow Pipelines Standalone Deployment

This project deploys Kubeflow Pipelines as a standalone MLOps
orchestration platform. It does not install the complete Kubeflow
distribution.

The existing FastAPI churn API and MLflow deployment remain the
validated baseline. Kubeflow Pipelines is introduced as a separate
workflow-orchestration layer running on dedicated EKS capacity.

## Locked platform versions

| Component | Version |
|---|---:|
| Kubernetes | 1.36 |
| Kubeflow Pipelines | 2.17.0 |
| cert-manager | v1.18.2 |
| Argo workflow controller | v4.0.5 |
| MySQL | 8.4 |
| SeaweedFS | 4.34 |
| ML Metadata | 1.14.0 |

The upstream sources, source checksums, and container image digests are
recorded in
`kubernetes/platform/kubeflow-pipelines/source-lock.json`.

The lock contains immutable registry manifest digests for all 19 locked
container images. The renderer rejects a source checksum mismatch, an
unlocked image, an unused image lock, a `latest` tag, and an unversioned
source image.

## Manifest inventory

The pinned installation contains 143 Kubernetes objects:

| Input | Documents |
|---|---:|
| cert-manager | 49 |
| KFP cluster-scoped resources | 16 |
| KFP platform resources | 78 |
| Total | 143 |

The combined inventory includes:

- 19 CustomResourceDefinitions
- 17 Deployments
- 23 Deployment container and init-container image occurrences
- 18 unique direct Deployment images
- 1 indirect cert-manager ACME solver image
- 19 total immutable image locks

## Rendering model

The project does not manually edit the large upstream YAML streams.

`scripts/render_kfp_manifests.py` performs these operations:

1. Verifies the three upstream SHA-256 checksums.
2. Parses all Kubernetes YAML documents.
3. Preserves existing node selectors.
4. Adds the dedicated advanced-platform selectors.
5. Preserves existing resource values.
6. Adds only missing CPU and memory controls.
7. Replaces every source image with its locked digest.
8. Rejects incomplete or stale image mappings.
9. Produces a machine-readable render report.

The renderer outputs temporary deployment artifacts rather than
committing thousands of lines of generated upstream YAML.

## Scheduling policy

All 17 control-plane Deployments receive these selectors:

- `role: advanced-mlops`
- `workload: ml-platform`

Existing selectors such as `kubernetes.io/os: linux` are preserved.

The dedicated managed node group currently uses:

| Setting | Value |
|---|---:|
| Node group | advanced-mlops |
| Instance type | m7i.large |
| Capacity type | On-Demand |
| Desired size | 2 |
| Minimum size | 1 |
| Maximum size | 2 |
| Root volume | 50 GiB |

The existing churn API and MLflow services remain independent of this
scheduling policy.

## Resource policy

Missing resource fields receive these defaults:

| Resource field | Default |
|---|---:|
| CPU request | 50m |
| Memory request | 128Mi |
| CPU limit | 1 |
| Memory limit | 1Gi |

The renderer never replaces an upstream value that is already present.

The validated rendering adds 54 missing resource fields across 23
container occurrences.

## Immutable image policy

The source lock requires:

- `digest_resolution_status=resolved`
- `resolved_count=18`
- `installation_allowed=true`
- `installation_allowed_while_pending=false`

A valid render requires:

- 18 unique source images
- 18 unique pinned images
- 23 pinned image occurrences
- `all_images_digest_pinned=true`
- zero unlocked images
- zero unused digest locks
- zero missing digest locks

The image digest and resource hardening reduced the Checkov findings
from 165 to 80.

All 17 `CKV_K8S_43` image findings and all 54 resource-management
findings were eliminated.

## Compatibility boundaries

The remaining findings are not globally suppressed.

The renderer deliberately does not:

- disable every service-account token
- replace upstream container security contexts
- force one numeric runtime UID across unrelated images
- force read-only root filesystems without write-path validation
- rewrite controller RBAC
- inject generic health probes
- apply an untested default-deny NetworkPolicy

Controllers including cert-manager, Argo, the KFP API server, the cache
deployer, the persistence agent, and workflow controllers require
Kubernetes API access. Removing their tokens or RBAC without tracing
their behavior could prevent the platform from operating.

The remaining findings require either workload-specific compatibility
testing or documented acceptance of upstream controller permissions.

## Required installation order

Custom resources cannot be created until their corresponding CRDs are
registered.

The installation order is:

1. Render and validate the locked manifests.
2. Apply the hardened cert-manager manifest.
3. Wait for all cert-manager CRDs to become `Established`.
4. Wait for the three cert-manager Deployments.
5. Apply the KFP cluster-scoped manifest.
6. Wait for all KFP and Argo CRDs to become `Established`.
7. Apply the complete KFP platform manifest.
8. Wait for every Kubeflow Deployment.
9. Verify the Kubeflow PVCs are `Bound`.
10. Validate the KFP API and UI with temporary port forwards.

The KFP platform manifest contains a `Certificate` and an `Issuer`
using `cert-manager.io/v1`. Their client-side mapping is expected to
fail before cert-manager CRDs are installed.

## Rendering command

Run the renderer with the following arguments:

    python scripts/render_kfp_manifests.py \
      --cert-manager /tmp/project8-kfp-2.17.0/cert-manager.yaml \
      --kfp-cluster /tmp/project8-kfp-2.17.0/kfp-cluster-scoped.yaml \
      --kfp-platform /tmp/project8-kfp-2.17.0/kfp-platform-native.yaml \
      --source-lock kubernetes/platform/kubeflow-pipelines/source-lock.json \
      --hardening-policy kubernetes/platform/kubeflow-pipelines/hardening-policy.json \
      --output-dir /tmp/project8-kfp-2.17.0/rendered-pinned

A successful report must contain:

- `documents=143`
- `deployments_hardened=17`
- `containers_processed=23`
- `resource_fields_added=54`
- `existing_linux_selectors_preserved=4`
- `unique_source_images=18`
- `unique_images=18`
- `image_references_pinned=23`
- `all_images_digest_pinned=true`
- `cluster_resources_modified=false`

## Validation commands

Before installation, run:

    pytest -q
    ruff check src tests scripts
    git diff --check

The source lock, policy, renderer tests, complete project test suite,
and static analysis must all pass before any Kubernetes apply.

## Access model

The initial KFP deployment remains cluster-internal.

Validation uses temporary `kubectl port-forward` sessions. This phase
does not create:

- a public LoadBalancer
- a public Ingress
- a public DNS record
- an internet-facing Kubeflow endpoint

## Rollback boundary

The KFP rollback boundary includes only:

- the `cert-manager` namespace
- the `kubeflow` namespace
- the pinned cert-manager CRDs
- the pinned KFP and Argo CRDs
- the inventoried cluster-scoped RBAC objects

The rollback process must use the exact pinned inventory. Broad wildcard
deletion is prohibited.

The following baseline resources are outside the rollback boundary:

- the `mlops` namespace
- the churn API Deployment
- the MLflow Deployment
- the MLflow model registry
- the MLflow EBS persistent volume
- the existing ECR repositories
- the DVC and MLflow artifact bucket

## Indirect cert-manager image

The cert-manager controller receives its HTTP-01 solver image through
the `--acme-http01-solver-image` container argument. This image is not
part of the controller Pod specification and therefore requires
separate discovery and validation.

The renderer pins that argument to the locked
`cert-manager-acmesolver` SHA-256 digest. Rendering fails if the
indirect image is missing from the source lock, has an invalid digest,
or remains unused. The installation contract therefore covers:

- 18 unique direct Deployment images
- 23 direct container and init-container image occurrences
- 1 indirect ACME solver image argument
- 19 total immutable image locks
- 24 total pinned image references

## EKS runtime compatibility overlay

The pinned Kubeflow Pipelines 2.17.0 manifests require two additive
compatibility changes for this EKS environment.

The upstream MySQL and SeaweedFS claims omit `storageClassName`. Because
the cluster intentionally has no global default StorageClass, the
renderer assigns the existing `ebs-gp3` CSI StorageClass to exactly
`mysql-pv-claim` and `seaweedfs-pvc`. Existing conflicting values are
rejected rather than overwritten.

The upstream cache deployer uses the
`kubernetes.io/kubelet-serving` signer to request the cache-server TLS
certificate. EKS does not sign that workload CSR. The renderer therefore
scales the legacy cache deployer to zero and adds the official
cert-manager-style cache TLS contract:

- `Issuer/kfp-cache-selfsigned-issuer`
- `Certificate/kfp-cache-cert`
- Secret target `webhook-server-tls`
- `MutatingWebhookConfiguration/cache-webhook-kubeflow`

The cache certificate is restricted to cache-server DNS identities and
is not shared with the separate KFP API webhook certificate. The cache
webhook uses `failurePolicy: Ignore` and selects only Pods explicitly
labelled with `pipelines.kubeflow.org/cache_enabled: "true"`.

cert-manager stores the certificate and private key as `tls.crt` and
`tls.key`, while the KFP 2.17.0 cache server reads `cert.pem` and
`key.pem`. The renderer maps those Secret keys to the required filenames
through the Pod volume projection. The CA remains available as
`ca.crt`; the Secret itself is not copied or rewritten.

The immutable upstream inventory remains 143 checksum-verified
documents. Rendering adds three repository-managed compatibility
objects, producing 146 total documents and 81 KFP platform documents.
The renderer continues to validate 17 Deployments, 23 direct image
occurrences, and 18 direct images.

## Generated runtime image pinning

KFP creates support containers dynamically for each v2 pipeline run.
These images do not appear in ordinary Deployment `image` fields.
Instead, they are supplied through three repository-controlled fields:

- `V2_DRIVER_IMAGE` in `Deployment/ml-pipeline`
- `V2_LAUNCHER_IMAGE` in `Deployment/ml-pipeline`
- `--executor-image` in `Deployment/workflow-controller`

The renderer pins the KFP driver, KFP launcher, and Argo executor values
to audited SHA-256 digests. Together with the cert-manager ACME solver,
the installation contains four indirect images, 22 total immutable
image locks, and 27 pinned source occurrences.

Rendering fails if a supported runtime image lacks a lock, has an
invalid digest mapping, or leaves an unused lock. The immutable image
contract therefore covers control-plane Deployments, init containers,
cert-manager solver Pods, and KFP-generated pipeline support Pods.

## Installation validation evidence

The standalone Kubeflow Pipelines 2.17.0 installation was validated
against deployment commit
`1c07e4a54ab6f11b13186c8c474b4a23b7154302`. GitHub Actions run
`34669434256` completed successfully with infrastructure validation,
application tests, container builds, and security scanning passing.

The final post-pinning smoke run
`enterprise-mlops-platform-smoke-runtime-pinned-20260912` completed with
the `SUCCEEDED` state. Its generated Workflow completed all three nodes,
and all three generated Pods succeeded under the `pipeline-runner`
ServiceAccount on the dedicated advanced MLOps node group.

The ten generated container and init-container image occurrences used
only four SHA-256 digest-pinned images:

- the smoke-test Alpine workload
- the KFP v2 driver
- the KFP v2 launcher
- the Argo executor

The smoke workload emitted the expected functional markers, and its
executor logs were published successfully to the persistent
SeaweedFS-backed artifact store. The KFP API, UI, webhook certificates,
cache server, MySQL metadata store, and all 13 active KFP Deployments
were healthy after validation.

The MySQL and SeaweedFS EBS-backed PVC identities remained unchanged
through the compatibility repairs and runtime-image rollout. No public
LoadBalancer, Ingress, DNS record, credential, Secret value, Pod IP,
node hostname, or raw Kubernetes API export is included in the durable
evidence.

The sanitized machine-readable validation record is available at
[`docs/evidence/kubeflow-pipelines-validation.json`](evidence/kubeflow-pipelines-validation.json).
