"""Render pinned Kubeflow Pipelines manifests with safe local hardening."""

from __future__ import annotations

import argparse
import hashlib
import json
from copy import deepcopy
from pathlib import Path
from typing import Any

import yaml


def read_json(path: Path) -> dict[str, Any]:
    """Read one JSON object."""
    value = json.loads(path.read_text(encoding="utf-8"))

    if not isinstance(value, dict):
        raise ValueError(f"Expected a JSON object: {path}")

    return value


def sha256(path: Path) -> str:
    """Return a file's SHA-256 digest."""
    digest = hashlib.sha256()

    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)

    return digest.hexdigest()


def verify_source(
    path: Path,
    component: dict[str, Any],
) -> None:
    """Verify one source manifest against its locked digest."""
    expected = str(component["sha256"])
    actual = sha256(path)

    if actual != expected:
        raise ValueError(
            f"Checksum mismatch for {path}: expected {expected}, found {actual}"
        )


def read_documents(path: Path) -> list[dict[str, Any]]:
    """Read all Kubernetes objects from a YAML stream."""
    documents = []

    for document in yaml.safe_load_all(path.read_text(encoding="utf-8")):
        if document is None:
            continue

        if not isinstance(document, dict):
            raise ValueError(f"Non-object YAML document found in {path}")

        documents.append(document)

    return documents


def write_documents(
    path: Path,
    documents: list[dict[str, Any]],
) -> None:
    """Write Kubernetes objects as deterministic YAML."""
    rendered = yaml.safe_dump_all(
        documents,
        explicit_start=True,
        sort_keys=False,
        default_flow_style=False,
    )

    path.write_text(rendered, encoding="utf-8")


def pod_spec(document: dict[str, Any]) -> dict[str, Any]:
    """Return the pod specification for a workload."""
    return (
        document.setdefault("spec", {})
        .setdefault("template", {})
        .setdefault("spec", {})
    )


def workload_containers(
    specification: dict[str, Any],
) -> list[dict[str, Any]]:
    """Return regular and initialization containers."""
    return [
        *specification.get("containers", []),
        *specification.get("initContainers", []),
    ]


def harden_deployment(
    document: dict[str, Any],
    policy: dict[str, Any],
) -> tuple[int, int]:
    """Apply approved additive hardening to a Deployment."""
    specification = pod_spec(document)

    node_selector = specification.setdefault(
        "nodeSelector",
        {},
    )

    if not isinstance(node_selector, dict):
        raise ValueError("Deployment nodeSelector is not a mapping")

    target_selector = policy["scheduling"]["node_selector"]

    for key, value in target_selector.items():
        existing = node_selector.get(key)

        if existing is not None and existing != value:
            raise ValueError(f"Conflicting node selector {key}={existing}")

        node_selector[key] = value

    added_fields = 0
    containers = workload_containers(specification)

    defaults = policy["resource_defaults"]

    for container in containers:
        resources = container.setdefault("resources", {})

        for section in ("requests", "limits"):
            values = resources.setdefault(section, {})

            for resource, default in defaults[section].items():
                if resource not in values:
                    values[resource] = default
                    added_fields += 1

    return len(containers), added_fields


def collect_images(
    documents: list[dict[str, Any]],
) -> set[str]:
    """Collect images referenced by rendered workloads."""
    images = set()

    for document in documents:
        if document.get("kind") != "Deployment":
            continue

        for container in workload_containers(pod_spec(document)):
            image = container.get("image")

            if image:
                images.add(str(image))

    return images


def validate_images(images: set[str]) -> None:
    """Reject latest and completely unversioned images."""
    for image in images:
        final_segment = image.rsplit("/", maxsplit=1)[-1]

        if image.endswith(":latest"):
            raise ValueError(f"Latest image is prohibited: {image}")

        if ":" not in final_segment and "@sha256:" not in image:
            raise ValueError(f"Unversioned image is prohibited: {image}")


def pin_images(
    documents: list[dict[str, Any]],
    resolutions: dict[str, Any],
) -> int:
    """Replace workload image tags with locked digests."""
    used_sources = set()
    pinned_occurrences = 0

    for document in documents:
        if document.get("kind") != "Deployment":
            continue

        for container in workload_containers(pod_spec(document)):
            source_image = str(container.get("image", ""))

            if not source_image:
                raise ValueError("Deployment container has no image")

            if source_image not in resolutions:
                raise ValueError(f"No locked digest for {source_image}")

            resolution = resolutions[source_image]
            pinned_image = str(resolution.get("pinned_image", ""))
            digest = str(resolution.get("digest", ""))

            if not digest.startswith("sha256:"):
                raise ValueError(f"Invalid locked digest for {source_image}")

            if not pinned_image.endswith(f"@{digest}"):
                raise ValueError(f"Invalid pinned image for {source_image}")

            container["image"] = pinned_image
            used_sources.add(source_image)
            pinned_occurrences += 1

    unused_sources = set(resolutions) - used_sources

    if unused_sources:
        raise ValueError("Unused locked images: " + ", ".join(sorted(unused_sources)))

    return pinned_occurrences


def pin_indirect_images(
    documents: list[dict[str, Any]],
    resolutions: dict[str, Any],
) -> tuple[int, set[str]]:
    """Pin images injected through approved runtime fields."""
    argument_prefixes = ("--acme-http01-solver-image=",)
    positional_arguments = {
        "--executor-image",
    }
    environment_names = {
        "V2_DRIVER_IMAGE",
        "V2_LAUNCHER_IMAGE",
    }

    occurrences = 0
    used_sources: set[str] = set()

    def pin(source_image: str) -> str:
        """Validate and return one locked indirect image."""
        if source_image not in resolutions:
            raise ValueError(f"No locked digest for indirect image {source_image}")

        resolution = resolutions[source_image]
        digest = str(resolution.get("digest", ""))
        pinned_image = str(resolution.get("pinned_image", ""))

        if not digest.startswith("sha256:"):
            raise ValueError(f"Invalid locked digest for indirect image {source_image}")

        if not pinned_image.endswith(f"@{digest}"):
            raise ValueError(f"Invalid pinned indirect image for {source_image}")

        used_sources.add(source_image)
        return pinned_image

    for document in documents:
        if document.get("kind") != "Deployment":
            continue

        for container in workload_containers(pod_spec(document)):
            arguments = container.get("args", [])

            if isinstance(arguments, list):
                for index, argument in enumerate(arguments):
                    if not isinstance(argument, str):
                        continue

                    prefix = next(
                        (
                            candidate
                            for candidate in argument_prefixes
                            if argument.startswith(candidate)
                        ),
                        None,
                    )

                    if prefix is not None:
                        source_image = argument[len(prefix) :]
                        arguments[index] = prefix + pin(source_image)
                        occurrences += 1
                        continue

                    if argument not in positional_arguments:
                        continue

                    value_index = index + 1

                    if value_index >= len(arguments):
                        raise ValueError(
                            f"Indirect image argument {argument} has no value"
                        )

                    source_image = arguments[value_index]

                    if not isinstance(source_image, str):
                        raise ValueError(
                            f"Indirect image argument {argument} has a non-string value"
                        )

                    arguments[value_index] = pin(source_image)
                    occurrences += 1

            environment = container.get("env", [])

            if not isinstance(environment, list):
                continue

            for variable in environment:
                if not isinstance(variable, dict):
                    continue

                name = variable.get("name")

                if name not in environment_names:
                    continue

                source_image = variable.get("value")

                if not isinstance(source_image, str):
                    raise ValueError(
                        f"Indirect image environment {name} has no string value"
                    )

                variable["value"] = pin(source_image)
                occurrences += 1

    return occurrences, used_sources


def apply_storage_compatibility(
    documents: list[dict[str, Any]],
    policy: dict[str, Any],
) -> int:
    """Set explicit storage classes on approved PVCs."""
    storage = policy["platform_compatibility"]["storage"]
    storage_class_name = str(storage["storage_class_name"])
    target_names = set(storage["target_pvcs"])
    preserve_existing = bool(storage.get("preserve_existing_values", True))

    claims = {
        str(document.get("metadata", {}).get("name", "")): document
        for document in documents
        if document.get("kind") == "PersistentVolumeClaim"
    }

    missing_claims = target_names - set(claims)

    if missing_claims:
        raise ValueError(
            "Missing compatibility PVCs: " + ", ".join(sorted(missing_claims))
        )

    added = 0

    for name in sorted(target_names):
        claim = claims[name]
        specification = claim.setdefault("spec", {})
        existing = specification.get("storageClassName")

        if existing is None:
            specification["storageClassName"] = storage_class_name
            added += 1
            continue

        if existing != storage_class_name:
            preservation = (
                " while preserving existing values" if preserve_existing else ""
            )
            raise ValueError(
                f"Conflicting storage class on PVC {name}: {existing}{preservation}"
            )

    return added


def configure_cache_server_tls_projection(
    documents: list[dict[str, Any]],
    policy: dict[str, Any],
) -> bool:
    """Map cert-manager TLS keys to cache-server filenames."""
    cache = policy["platform_compatibility"]["cache_tls"]
    deployment_name = "cache-server"
    volume_name = "webhook-tls-certs"
    secret_name = str(cache["secret_name"])

    deployments = [
        document
        for document in documents
        if document.get("kind") == "Deployment"
        and document.get("metadata", {}).get("name") == deployment_name
    ]

    if len(deployments) != 1:
        raise ValueError(
            f"Expected exactly one cache-server Deployment, found {len(deployments)}"
        )

    specification = pod_spec(deployments[0])
    volumes = [
        volume
        for volume in specification.get("volumes", [])
        if volume.get("name") == volume_name
    ]

    if len(volumes) != 1:
        raise ValueError(
            f"Expected exactly one cache-server TLS volume, found {len(volumes)}"
        )

    secret = volumes[0].get("secret")

    if not isinstance(secret, dict):
        raise ValueError("Cache-server TLS volume is not a Secret")

    existing_secret_name = secret.get("secretName")

    if existing_secret_name != secret_name:
        raise ValueError(f"Unexpected cache-server TLS Secret: {existing_secret_name}")

    expected_items = [
        {
            "key": str(cache["ca_secret_key"]),
            "path": str(cache["ca_file_name"]),
        },
        {
            "key": str(cache["certificate_secret_key"]),
            "path": str(cache["certificate_file_name"]),
        },
        {
            "key": str(cache["private_key_secret_key"]),
            "path": str(cache["private_key_file_name"]),
        },
    ]

    existing_items = secret.get("items")

    if existing_items is not None and existing_items != expected_items:
        raise ValueError("Conflicting cache-server TLS projection")

    secret["items"] = expected_items

    return True


def build_cache_tls_objects(
    policy: dict[str, Any],
) -> list[dict[str, Any]]:
    """Build the repository-managed cache TLS objects."""
    cache = policy["platform_compatibility"]["cache_tls"]
    namespace = str(cache["namespace"])
    issuer_name = str(cache["issuer_name"])
    certificate_name = str(cache["certificate_name"])
    secret_name = str(cache["secret_name"])
    service_name = str(cache["service_name"])
    webhook_name = str(cache["webhook_name"])

    return [
        {
            "apiVersion": "cert-manager.io/v1",
            "kind": "Issuer",
            "metadata": {
                "name": issuer_name,
                "namespace": namespace,
            },
            "spec": {
                "selfSigned": {},
            },
        },
        {
            "apiVersion": "cert-manager.io/v1",
            "kind": "Certificate",
            "metadata": {
                "name": certificate_name,
                "namespace": namespace,
            },
            "spec": {
                "commonName": certificate_name,
                "isCA": True,
                "dnsNames": [
                    service_name,
                    f"{service_name}.{namespace}",
                    f"{service_name}.{namespace}.svc",
                    (f"{service_name}.{namespace}.svc.cluster.local"),
                ],
                "issuerRef": {
                    "kind": "Issuer",
                    "name": issuer_name,
                },
                "secretName": secret_name,
            },
        },
        {
            "apiVersion": "admissionregistration.k8s.io/v1",
            "kind": "MutatingWebhookConfiguration",
            "metadata": {
                "name": webhook_name,
                "annotations": {
                    "cert-manager.io/inject-ca-from": (
                        f"{namespace}/{certificate_name}"
                    ),
                },
            },
            "webhooks": [
                {
                    "name": (f"{service_name}.{namespace}.svc"),
                    "clientConfig": {
                        "service": {
                            "name": service_name,
                            "namespace": namespace,
                            "path": "/mutate",
                            "port": 443,
                        },
                    },
                    "failurePolicy": str(cache["webhook_failure_policy"]),
                    "rules": [
                        {
                            "operations": ["CREATE"],
                            "apiGroups": [""],
                            "apiVersions": ["v1"],
                            "resources": ["pods"],
                        },
                    ],
                    "sideEffects": "None",
                    "timeoutSeconds": 5,
                    "objectSelector": {
                        "matchLabels": {
                            ("pipelines.kubeflow.org/cache_enabled"): "true",
                        },
                    },
                    "admissionReviewVersions": ["v1"],
                },
            ],
        },
    ]


def apply_cache_tls_compatibility(
    documents: list[dict[str, Any]],
    policy: dict[str, Any],
) -> tuple[bool, int]:
    """Replace the legacy CSR bootstrap declaratively."""
    cache = policy["platform_compatibility"]["cache_tls"]

    if cache.get("disable_legacy_cache_deployer") is not True:
        raise ValueError("Legacy cache deployer must be disabled")

    deployment_name = str(cache["cache_deployer_name"])
    target_replicas = int(cache["cache_deployer_replicas"])

    deployments = [
        document
        for document in documents
        if document.get("kind") == "Deployment"
        and document.get("metadata", {}).get("name") == deployment_name
    ]

    if len(deployments) != 1:
        raise ValueError(
            f"Expected exactly one legacy cache deployer, found {len(deployments)}"
        )

    deployment = deployments[0]
    deployment.setdefault("spec", {})["replicas"] = target_replicas

    compatibility_objects = build_cache_tls_objects(policy)
    new_identities = {
        (
            document["kind"],
            document["metadata"]["name"],
        )
        for document in compatibility_objects
    }
    existing_identities = {
        (
            str(document.get("kind", "")),
            str(
                document.get("metadata", {}).get(
                    "name",
                    "",
                )
            ),
        )
        for document in documents
    }

    conflicts = new_identities & existing_identities

    if conflicts:
        formatted = [f"{kind}/{name}" for kind, name in sorted(conflicts)]
        raise ValueError("Compatibility objects already exist: " + ", ".join(formatted))

    documents.extend(compatibility_objects)

    return True, len(compatibility_objects)


def validate_pinned_images(images: set[str]) -> None:
    """Require every rendered image to use a SHA-256 digest."""
    invalid = [
        image
        for image in images
        if "@sha256:" not in image
        or len(image.rsplit("@sha256:", maxsplit=1)[-1]) != 64
    ]

    if invalid:
        raise ValueError(
            "Rendered images are not digest pinned: " + ", ".join(sorted(invalid))
        )


def render(
    cert_manager_path: Path,
    cluster_path: Path,
    platform_path: Path,
    lock_path: Path,
    policy_path: Path,
    output_dir: Path,
) -> dict[str, Any]:
    """Verify, harden, validate, and render all inputs."""
    lock = read_json(lock_path)
    policy = read_json(policy_path)

    components = lock["components"]

    verify_source(
        cert_manager_path,
        components["cert_manager"],
    )
    verify_source(
        cluster_path,
        components["kubeflow_pipelines_cluster"],
    )
    verify_source(
        platform_path,
        components["kubeflow_pipelines_platform"],
    )

    cert_manager = read_documents(cert_manager_path)
    cluster = read_documents(cluster_path)
    platform = read_documents(platform_path)

    original = {
        "cert-manager": deepcopy(cert_manager),
        "kfp-cluster": deepcopy(cluster),
        "kfp-platform": deepcopy(platform),
    }

    upstream_document_count = len(cert_manager) + len(cluster) + len(platform)

    pvc_storage_classes_added = apply_storage_compatibility(
        platform,
        policy,
    )
    cache_tls_projection_configured = configure_cache_server_tls_projection(
        platform,
        policy,
    )
    (
        legacy_cache_deployer_disabled,
        compatibility_objects_added,
    ) = apply_cache_tls_compatibility(
        platform,
        policy,
    )

    deployment_count = 0
    container_count = 0
    resource_fields_added = 0

    for documents in (cert_manager, platform):
        for document in documents:
            if document.get("kind") != "Deployment":
                continue

            deployment_count += 1
            containers, added = harden_deployment(
                document,
                policy,
            )
            container_count += containers
            resource_fields_added += added

    all_documents = [
        *cert_manager,
        *cluster,
        *platform,
    ]

    source_images = collect_images(all_documents)
    validate_images(source_images)

    image_policy = lock["image_policy"]

    if image_policy.get("digest_resolution_status") != "resolved":
        raise ValueError("Image digest resolution is not complete")

    if image_policy.get("installation_allowed") is not True:
        raise ValueError("The source lock has not opened installation")

    resolutions = image_policy.get(
        "resolved_images",
        {},
    )

    direct_resolutions = {
        image: resolutions[image] for image in source_images if image in resolutions
    }

    missing_direct_locks = source_images - set(direct_resolutions)

    if missing_direct_locks:
        raise ValueError(
            "Missing direct image locks: " + ", ".join(sorted(missing_direct_locks))
        )

    pinned_occurrences = pin_images(
        all_documents,
        direct_resolutions,
    )

    (
        indirect_pinned_occurrences,
        indirect_source_images,
    ) = pin_indirect_images(
        all_documents,
        resolutions,
    )

    used_locked_images = set(direct_resolutions) | indirect_source_images
    unused_locked_images = set(resolutions) - used_locked_images

    if unused_locked_images:
        raise ValueError(
            "Unused locked images: " + ", ".join(sorted(unused_locked_images))
        )

    pinned_images = collect_images(all_documents)
    validate_pinned_images(pinned_images)

    expected = lock["expected_inventory"]
    validation = policy["validation"]

    expected_upstream_documents = validation["expected_upstream_documents"]
    expected_rendered_documents = validation["expected_rendered_documents"]
    expected_platform_documents = validation["expected_platform_documents"]
    expected_storage_classes_added = validation["expected_pvc_storage_classes_added"]
    expected_compatibility_objects_added = validation[
        "expected_compatibility_objects_added"
    ]
    expected_cache_tls_projection = validation[
        "expected_cache_tls_projection_configured"
    ]

    if cache_tls_projection_configured is not expected_cache_tls_projection:
        raise ValueError(
            "Cache TLS projection status does not match the validation contract"
        )

    if upstream_document_count != expected_upstream_documents:
        raise ValueError(
            f"Expected {expected_upstream_documents} upstream "
            f"documents, found {upstream_document_count}"
        )

    if len(all_documents) != expected_rendered_documents:
        raise ValueError(
            f"Expected {expected_rendered_documents} rendered "
            f"documents, found {len(all_documents)}"
        )

    if len(platform) != expected_platform_documents:
        raise ValueError(
            f"Expected {expected_platform_documents} platform "
            f"documents, found {len(platform)}"
        )

    if pvc_storage_classes_added != expected_storage_classes_added:
        raise ValueError(
            f"Expected {expected_storage_classes_added} PVC "
            "storage classes added, found "
            f"{pvc_storage_classes_added}"
        )

    if compatibility_objects_added != expected_compatibility_objects_added:
        raise ValueError(
            f"Expected {expected_compatibility_objects_added} "
            "compatibility objects added, found "
            f"{compatibility_objects_added}"
        )

    if deployment_count != expected["deployments"]:
        raise ValueError(
            f"Expected {expected['deployments']} Deployments, found {deployment_count}"
        )

    if container_count != expected["containers"]:
        raise ValueError(
            f"Expected {expected['containers']} containers, found {container_count}"
        )

    expected_indirect_images = expected.get(
        "indirect_images",
        0,
    )
    expected_total_locked_images = expected.get(
        "total_locked_images",
        expected["unique_images"],
    )

    if len(indirect_source_images) != expected_indirect_images:
        raise ValueError(
            f"Expected {expected_indirect_images} indirect "
            "images, found "
            f"{len(indirect_source_images)}"
        )

    if len(resolutions) != expected_total_locked_images:
        raise ValueError(
            f"Expected {expected_total_locked_images} total "
            f"locked images, found {len(resolutions)}"
        )

    if len(source_images) != expected["unique_images"]:
        raise ValueError(
            f"Expected {expected['unique_images']} source images, "
            f"found {len(source_images)}"
        )

    if len(pinned_images) != expected["unique_images"]:
        raise ValueError(
            f"Expected {expected['unique_images']} pinned images, "
            f"found {len(pinned_images)}"
        )

    if pinned_occurrences != container_count:
        raise ValueError(
            f"Expected {container_count} pinned occurrences, found {pinned_occurrences}"
        )

    expected_added = validation["expected_resource_fields_added"]

    if resource_fields_added != expected_added:
        raise ValueError(
            f"Expected {expected_added} resource fields added, "
            f"found {resource_fields_added}"
        )

    linux_selector_preserved = 0

    for document in all_documents:
        if document.get("kind") != "Deployment":
            continue

        selector = pod_spec(document).get(
            "nodeSelector",
            {},
        )

        if selector.get("kubernetes.io/os") == "linux":
            linux_selector_preserved += 1

        if selector.get("role") != "advanced-mlops":
            raise ValueError("Advanced node role was not applied")

        if selector.get("workload") != "ml-platform":
            raise ValueError("Advanced workload selector was not applied")

    output_dir.mkdir(parents=True, exist_ok=True)

    cert_output = output_dir / "cert-manager.yaml"
    cluster_output = output_dir / "kfp-cluster-scoped.yaml"
    platform_output = output_dir / "kfp-platform-native.yaml"

    write_documents(cert_output, cert_manager)
    write_documents(cluster_output, cluster)
    write_documents(platform_output, platform)

    report = {
        "source_checksums_verified": True,
        "documents": len(all_documents),
        "upstream_documents": upstream_document_count,
        "platform_documents": len(platform),
        "deployments_hardened": deployment_count,
        "pvc_storage_classes_added": (pvc_storage_classes_added),
        "legacy_cache_deployer_disabled": (legacy_cache_deployer_disabled),
        "compatibility_objects_added": (compatibility_objects_added),
        "cache_tls_projection_configured": (cache_tls_projection_configured),
        "containers_processed": container_count,
        "resource_fields_added": resource_fields_added,
        "existing_linux_selectors_preserved": (linux_selector_preserved),
        "unique_source_images": len(source_images),
        "source_images": sorted(source_images),
        "unique_images": len(pinned_images),
        "images": sorted(pinned_images),
        "image_references_pinned": pinned_occurrences,
        "indirect_image_references_pinned": (indirect_pinned_occurrences),
        "total_image_references_pinned": (
            pinned_occurrences + indirect_pinned_occurrences
        ),
        "indirect_source_images": sorted(indirect_source_images),
        "total_locked_images": len(resolutions),
        "all_images_digest_pinned": True,
        "cluster_resources_modified": (original["kfp-cluster"] != cluster),
        "compatibility_boundaries": policy["compatibility_boundaries"],
        "outputs": {
            "cert_manager": str(cert_output),
            "kfp_cluster": str(cluster_output),
            "kfp_platform": str(platform_output),
        },
    }

    report_path = output_dir / "render-report.json"
    report_path.write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    return report


def parse_arguments() -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description=(
            "Render audited Kubeflow Pipelines manifests with additive hardening."
        )
    )
    parser.add_argument(
        "--cert-manager",
        type=Path,
        required=True,
    )
    parser.add_argument(
        "--kfp-cluster",
        type=Path,
        required=True,
    )
    parser.add_argument(
        "--kfp-platform",
        type=Path,
        required=True,
    )
    parser.add_argument(
        "--source-lock",
        type=Path,
        required=True,
    )
    parser.add_argument(
        "--hardening-policy",
        type=Path,
        required=True,
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        required=True,
    )
    return parser.parse_args()


def main() -> None:
    """Run the renderer."""
    arguments = parse_arguments()

    report = render(
        cert_manager_path=arguments.cert_manager,
        cluster_path=arguments.kfp_cluster,
        platform_path=arguments.kfp_platform,
        lock_path=arguments.source_lock,
        policy_path=arguments.hardening_policy,
        output_dir=arguments.output_dir,
    )

    print(json.dumps(report, indent=2, sort_keys=True))
    print("PASS: pinned KFP manifests rendered successfully")


if __name__ == "__main__":
    main()
