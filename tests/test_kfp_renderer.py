"""Tests for the pinned Kubeflow Pipelines manifest renderer."""

from __future__ import annotations

import importlib.util
from pathlib import Path
from types import ModuleType

import pytest

RENDERER_PATH = Path("scripts/render_kfp_manifests.py")


def load_renderer() -> ModuleType:
    """Load the renderer script as a testable module."""
    specification = importlib.util.spec_from_file_location(
        "render_kfp_manifests",
        RENDERER_PATH,
    )

    if specification is None or specification.loader is None:
        raise RuntimeError("Unable to load the KFP renderer")

    module = importlib.util.module_from_spec(specification)
    specification.loader.exec_module(module)
    return module


def deployment(
    image: str = "example.invalid/controller:1.0",
) -> dict:
    """Build a small representative Deployment."""
    return {
        "apiVersion": "apps/v1",
        "kind": "Deployment",
        "metadata": {
            "name": "controller",
            "namespace": "test-platform",
        },
        "spec": {
            "template": {
                "spec": {
                    "nodeSelector": {
                        "kubernetes.io/os": "linux",
                    },
                    "containers": [
                        {
                            "name": "controller",
                            "image": image,
                            "resources": {
                                "requests": {
                                    "cpu": "250m",
                                }
                            },
                        }
                    ],
                }
            }
        },
    }


def hardening_policy() -> dict:
    """Return the approved additive test policy."""
    return {
        "scheduling": {
            "node_selector": {
                "role": "advanced-mlops",
                "workload": "ml-platform",
            }
        },
        "resource_defaults": {
            "requests": {
                "cpu": "50m",
                "memory": "128Mi",
            },
            "limits": {
                "cpu": "1",
                "memory": "1Gi",
            },
        },
    }


def test_hardening_is_additive() -> None:
    """Existing selectors and resource values must survive."""
    renderer = load_renderer()
    document = deployment()

    container_count, added_fields = renderer.harden_deployment(
        document,
        hardening_policy(),
    )

    pod_specification = document["spec"]["template"]["spec"]
    selector = pod_specification["nodeSelector"]
    resources = pod_specification["containers"][0]["resources"]

    assert container_count == 1
    assert added_fields == 3
    assert selector == {
        "kubernetes.io/os": "linux",
        "role": "advanced-mlops",
        "workload": "ml-platform",
    }
    assert resources == {
        "requests": {
            "cpu": "250m",
            "memory": "128Mi",
        },
        "limits": {
            "cpu": "1",
            "memory": "1Gi",
        },
    }


def test_conflicting_selector_is_rejected() -> None:
    """A conflicting scheduling policy must fail closed."""
    renderer = load_renderer()
    document = deployment()

    document["spec"]["template"]["spec"]["nodeSelector"]["role"] = "system"

    with pytest.raises(
        ValueError,
        match="Conflicting node selector",
    ):
        renderer.harden_deployment(
            document,
            hardening_policy(),
        )


def test_all_image_occurrences_are_pinned() -> None:
    """Repeated source images must all become immutable."""
    renderer = load_renderer()
    source_image = "example.invalid/controller:1.0"
    pinned_image = "example.invalid/controller@sha256:" + "a" * 64

    first = deployment(source_image)
    second = deployment(source_image)
    second["metadata"]["name"] = "second-controller"

    resolutions = {
        source_image: {
            "digest": "sha256:" + "a" * 64,
            "pinned_image": pinned_image,
        }
    }

    count = renderer.pin_images(
        [first, second],
        resolutions,
    )

    images = renderer.collect_images([first, second])

    assert count == 2
    assert images == {pinned_image}

    renderer.validate_pinned_images(images)


def test_missing_digest_lock_is_rejected() -> None:
    """An image without a lock must stop rendering."""
    renderer = load_renderer()
    document = deployment()

    with pytest.raises(
        ValueError,
        match="No locked digest",
    ):
        renderer.pin_images([document], {})


def test_unused_digest_lock_is_rejected() -> None:
    """Stale digest mappings must stop rendering."""
    renderer = load_renderer()
    source_image = "example.invalid/controller:1.0"

    resolutions = {
        source_image: {
            "digest": "sha256:" + "a" * 64,
            "pinned_image": ("example.invalid/controller@sha256:" + "a" * 64),
        },
        "example.invalid/unused:1.0": {
            "digest": "sha256:" + "b" * 64,
            "pinned_image": "",
        },
    }

    resolutions["example.invalid/unused:1.0"]["pinned_image"] = (
        "example.invalid/unused@sha256:" + "b" * 64
    )

    with pytest.raises(
        ValueError,
        match="Unused locked images",
    ):
        renderer.pin_images(
            [deployment(source_image)],
            resolutions,
        )


def test_latest_and_unversioned_images_are_rejected() -> None:
    """Mutable or unversioned source images must fail."""
    renderer = load_renderer()

    with pytest.raises(
        ValueError,
        match="Latest image is prohibited",
    ):
        renderer.validate_images({"example.invalid/controller:latest"})

    with pytest.raises(
        ValueError,
        match="Unversioned image is prohibited",
    ):
        renderer.validate_images({"example.invalid/controller"})


def test_non_digest_rendered_image_is_rejected() -> None:
    """The final render must contain digest references."""
    renderer = load_renderer()

    with pytest.raises(
        ValueError,
        match="not digest pinned",
    ):
        renderer.validate_pinned_images({"example.invalid/controller:1.0"})


def test_acme_solver_argument_is_digest_pinned() -> None:
    """The cert-manager ACME solver argument must be immutable."""
    renderer = load_renderer()
    source_image = "quay.io/jetstack/cert-manager-acmesolver:v1.18.2"
    pinned_image = "quay.io/jetstack/cert-manager-acmesolver@sha256:" + "c" * 64
    document = deployment()
    container = document["spec"]["template"]["spec"]["containers"][0]
    container["args"] = [
        "--v=2",
        "--acme-http01-solver-image=" + source_image,
    ]
    resolutions = {
        source_image: {
            "digest": "sha256:" + "c" * 64,
            "pinned_image": pinned_image,
        }
    }

    count, used_sources = renderer.pin_indirect_images(
        [document],
        resolutions,
    )

    assert count == 1
    assert used_sources == {source_image}
    assert container["args"] == [
        "--v=2",
        "--acme-http01-solver-image=" + pinned_image,
    ]


def test_missing_acme_solver_lock_is_rejected() -> None:
    """An unlocked indirect ACME solver must stop rendering."""
    renderer = load_renderer()
    document = deployment()
    container = document["spec"]["template"]["spec"]["containers"][0]
    container["args"] = [
        "--acme-http01-solver-image=example.invalid/acmesolver:1.0",
    ]

    with pytest.raises(
        ValueError,
        match="No locked digest for indirect image",
    ):
        renderer.pin_indirect_images(
            [document],
            {},
        )


def compatibility_policy() -> dict:
    """Return the deterministic platform compatibility policy."""
    return {
        "platform_compatibility": {
            "storage": {
                "preserve_existing_values": True,
                "storage_class_name": "ebs-gp3",
                "target_pvcs": [
                    "mysql-pv-claim",
                    "seaweedfs-pvc",
                ],
            },
            "cache_tls": {
                "cache_deployer_name": "cache-deployer-deployment",
                "cache_deployer_replicas": 0,
                "certificate_name": "kfp-cache-cert",
                "disable_legacy_cache_deployer": True,
                "issuer_name": "kfp-cache-selfsigned-issuer",
                "namespace": "kubeflow",
                "secret_name": "webhook-server-tls",
                "service_name": "cache-server",
                "webhook_failure_policy": "Ignore",
                "webhook_name": "cache-webhook-kubeflow",
            },
        },
    }


def persistent_volume_claim(name: str) -> dict:
    """Build a representative KFP PVC."""
    return {
        "apiVersion": "v1",
        "kind": "PersistentVolumeClaim",
        "metadata": {
            "name": name,
            "namespace": "kubeflow",
        },
        "spec": {
            "accessModes": ["ReadWriteOnce"],
            "resources": {
                "requests": {
                    "storage": "20Gi",
                },
            },
        },
    }


def test_storage_compatibility_adds_explicit_class() -> None:
    """Both approved PVCs must receive ebs-gp3."""
    renderer = load_renderer()
    claims = [
        persistent_volume_claim("mysql-pv-claim"),
        persistent_volume_claim("seaweedfs-pvc"),
    ]

    added = renderer.apply_storage_compatibility(
        claims,
        compatibility_policy(),
    )

    assert added == 2
    assert {
        claim["metadata"]["name"]: claim["spec"]["storageClassName"] for claim in claims
    } == {
        "mysql-pv-claim": "ebs-gp3",
        "seaweedfs-pvc": "ebs-gp3",
    }


def test_conflicting_storage_class_is_rejected() -> None:
    """A conflicting PVC class must fail closed."""
    renderer = load_renderer()
    claims = [
        persistent_volume_claim("mysql-pv-claim"),
        persistent_volume_claim("seaweedfs-pvc"),
    ]
    claims[0]["spec"]["storageClassName"] = "gp2"

    with pytest.raises(
        ValueError,
        match="Conflicting storage class",
    ):
        renderer.apply_storage_compatibility(
            claims,
            compatibility_policy(),
        )


def test_missing_storage_claim_is_rejected() -> None:
    """Every policy-selected PVC must exist."""
    renderer = load_renderer()

    with pytest.raises(
        ValueError,
        match="Missing compatibility PVCs",
    ):
        renderer.apply_storage_compatibility(
            [persistent_volume_claim("mysql-pv-claim")],
            compatibility_policy(),
        )


def test_cache_tls_compatibility_is_declarative() -> None:
    """Legacy CSR bootstrap must become declarative TLS."""
    renderer = load_renderer()
    cache_deployer = deployment()
    cache_deployer["metadata"]["name"] = "cache-deployer-deployment"
    documents = [cache_deployer]

    disabled, added = renderer.apply_cache_tls_compatibility(
        documents,
        compatibility_policy(),
    )

    assert disabled is True
    assert added == 3
    assert cache_deployer["spec"]["replicas"] == 0

    identities = {
        (
            document["kind"],
            document["metadata"]["name"],
        )
        for document in documents
    }

    assert (
        "Issuer",
        "kfp-cache-selfsigned-issuer",
    ) in identities
    assert (
        "Certificate",
        "kfp-cache-cert",
    ) in identities
    assert (
        "MutatingWebhookConfiguration",
        "cache-webhook-kubeflow",
    ) in identities

    certificate = next(
        document for document in documents if document["kind"] == "Certificate"
    )

    assert certificate["spec"]["secretName"] == ("webhook-server-tls")
    assert certificate["spec"]["dnsNames"] == [
        "cache-server",
        "cache-server.kubeflow",
        "cache-server.kubeflow.svc",
        "cache-server.kubeflow.svc.cluster.local",
    ]

    webhook = next(
        document
        for document in documents
        if document["kind"] == "MutatingWebhookConfiguration"
    )
    webhook_specification = webhook["webhooks"][0]

    assert webhook["metadata"]["annotations"] == {
        "cert-manager.io/inject-ca-from": "kubeflow/kfp-cache-cert",
    }
    assert webhook_specification["failurePolicy"] == "Ignore"
    assert webhook_specification["admissionReviewVersions"] == ["v1"]
    assert webhook_specification["clientConfig"]["service"] == {
        "name": "cache-server",
        "namespace": "kubeflow",
        "path": "/mutate",
        "port": 443,
    }


def test_existing_cache_tls_object_is_rejected() -> None:
    """Duplicate compatibility identities must fail."""
    renderer = load_renderer()
    cache_deployer = deployment()
    cache_deployer["metadata"]["name"] = "cache-deployer-deployment"
    existing_issuer = {
        "apiVersion": "cert-manager.io/v1",
        "kind": "Issuer",
        "metadata": {
            "name": "kfp-cache-selfsigned-issuer",
            "namespace": "kubeflow",
        },
        "spec": {
            "selfSigned": {},
        },
    }

    with pytest.raises(
        ValueError,
        match="Compatibility objects already exist",
    ):
        renderer.apply_cache_tls_compatibility(
            [cache_deployer, existing_issuer],
            compatibility_policy(),
        )


def cache_server_deployment() -> dict:
    """Build a representative cache-server Deployment."""
    document = deployment()
    document["metadata"]["name"] = "cache-server"
    pod_specification = document["spec"]["template"]["spec"]
    pod_specification["volumes"] = [
        {
            "name": "webhook-tls-certs",
            "secret": {
                "secretName": "webhook-server-tls",
            },
        }
    ]
    pod_specification["containers"][0]["volumeMounts"] = [
        {
            "name": "webhook-tls-certs",
            "mountPath": "/etc/webhook/certs",
            "readOnly": True,
        }
    ]
    return document


def test_cache_tls_secret_keys_are_projected() -> None:
    """cert-manager keys must use cache-server filenames."""
    renderer = load_renderer()
    document = cache_server_deployment()
    policy = compatibility_policy()
    cache = policy["platform_compatibility"]["cache_tls"]
    cache.update(
        {
            "certificate_secret_key": "tls.crt",
            "certificate_file_name": "cert.pem",
            "private_key_secret_key": "tls.key",
            "private_key_file_name": "key.pem",
            "ca_secret_key": "ca.crt",
            "ca_file_name": "ca.crt",
        }
    )

    configured = renderer.configure_cache_server_tls_projection(
        [document],
        policy,
    )

    assert configured is True
    assert document["spec"]["template"]["spec"]["volumes"][0]["secret"] == {
        "secretName": "webhook-server-tls",
        "items": [
            {
                "key": "ca.crt",
                "path": "ca.crt",
            },
            {
                "key": "tls.crt",
                "path": "cert.pem",
            },
            {
                "key": "tls.key",
                "path": "key.pem",
            },
        ],
    }


def test_conflicting_cache_tls_projection_is_rejected() -> None:
    """An unexpected existing mapping must fail closed."""
    renderer = load_renderer()
    document = cache_server_deployment()
    document["spec"]["template"]["spec"]["volumes"][0]["secret"]["items"] = [
        {
            "key": "tls.crt",
            "path": "unexpected.pem",
        }
    ]
    policy = compatibility_policy()
    cache = policy["platform_compatibility"]["cache_tls"]
    cache.update(
        {
            "certificate_secret_key": "tls.crt",
            "certificate_file_name": "cert.pem",
            "private_key_secret_key": "tls.key",
            "private_key_file_name": "key.pem",
            "ca_secret_key": "ca.crt",
            "ca_file_name": "ca.crt",
        }
    )

    with pytest.raises(
        ValueError,
        match="Conflicting cache-server TLS projection",
    ):
        renderer.configure_cache_server_tls_projection(
            [document],
            policy,
        )


def test_runtime_environment_images_are_digest_pinned() -> None:
    """KFP driver and launcher values must be immutable."""
    renderer = load_renderer()
    document = deployment()
    container = document["spec"]["template"]["spec"]["containers"][0]

    driver_source = "ghcr.io/kubeflow/kfp-driver:2.17.0"
    launcher_source = "ghcr.io/kubeflow/kfp-launcher:2.17.0"
    driver_pinned = "ghcr.io/kubeflow/kfp-driver@sha256:" + "d" * 64
    launcher_pinned = "ghcr.io/kubeflow/kfp-launcher@sha256:" + "e" * 64

    container["env"] = [
        {
            "name": "V2_DRIVER_IMAGE",
            "value": driver_source,
        },
        {
            "name": "V2_LAUNCHER_IMAGE",
            "value": launcher_source,
        },
    ]

    resolutions = {
        driver_source: {
            "digest": "sha256:" + "d" * 64,
            "pinned_image": driver_pinned,
        },
        launcher_source: {
            "digest": "sha256:" + "e" * 64,
            "pinned_image": launcher_pinned,
        },
    }

    count, used_sources = renderer.pin_indirect_images(
        [document],
        resolutions,
    )

    assert count == 2
    assert used_sources == {
        driver_source,
        launcher_source,
    }
    assert container["env"] == [
        {
            "name": "V2_DRIVER_IMAGE",
            "value": driver_pinned,
        },
        {
            "name": "V2_LAUNCHER_IMAGE",
            "value": launcher_pinned,
        },
    ]


def test_argo_executor_argument_is_digest_pinned() -> None:
    """The positional Argo executor must be immutable."""
    renderer = load_renderer()
    document = deployment()
    container = document["spec"]["template"]["spec"]["containers"][0]

    source_image = "quay.io/argoproj/argoexec:v4.0.5"
    pinned_image = "quay.io/argoproj/argoexec@sha256:" + "f" * 64

    container["args"] = [
        "--configmap",
        "workflow-controller-configmap",
        "--executor-image",
        source_image,
        "--namespaced",
    ]

    resolutions = {
        source_image: {
            "digest": "sha256:" + "f" * 64,
            "pinned_image": pinned_image,
        },
    }

    count, used_sources = renderer.pin_indirect_images(
        [document],
        resolutions,
    )

    assert count == 1
    assert used_sources == {source_image}
    assert container["args"] == [
        "--configmap",
        "workflow-controller-configmap",
        "--executor-image",
        pinned_image,
        "--namespaced",
    ]


def test_missing_runtime_environment_lock_is_rejected() -> None:
    """An unlocked KFP runtime image must stop rendering."""
    renderer = load_renderer()
    document = deployment()
    container = document["spec"]["template"]["spec"]["containers"][0]

    container["env"] = [
        {
            "name": "V2_DRIVER_IMAGE",
            "value": "example.invalid/kfp-driver:1.0",
        },
    ]

    with pytest.raises(
        ValueError,
        match="No locked digest for indirect image",
    ):
        renderer.pin_indirect_images(
            [document],
            {},
        )


def test_missing_executor_image_value_is_rejected() -> None:
    """An incomplete executor argument must fail closed."""
    renderer = load_renderer()
    document = deployment()
    container = document["spec"]["template"]["spec"]["containers"][0]

    container["args"] = [
        "--configmap",
        "workflow-controller-configmap",
        "--executor-image",
    ]

    with pytest.raises(
        ValueError,
        match="has no value",
    ):
        renderer.pin_indirect_images(
            [document],
            {},
        )
