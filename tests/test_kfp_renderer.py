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

    container_count, added_fields = (
        renderer.harden_deployment(
            document,
            hardening_policy(),
        )
    )

    pod_specification = (
        document["spec"]["template"]["spec"]
    )
    selector = pod_specification["nodeSelector"]
    resources = pod_specification["containers"][0][
        "resources"
    ]

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

    document["spec"]["template"]["spec"][
        "nodeSelector"
    ]["role"] = "system"

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
    pinned_image = (
        "example.invalid/controller@"
        "sha256:"
        + "a" * 64
    )

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

    images = renderer.collect_images(
        [first, second]
    )

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
            "pinned_image": (
                "example.invalid/controller@"
                "sha256:"
                + "a" * 64
            ),
        },
        "example.invalid/unused:1.0": {
            "digest": "sha256:" + "b" * 64,
            "pinned_image": "",
        },
    }

    resolutions["example.invalid/unused:1.0"][
        "pinned_image"
    ] = (
        "example.invalid/unused@"
        "sha256:"
        + "b" * 64
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
        renderer.validate_images(
            {"example.invalid/controller:latest"}
        )

    with pytest.raises(
        ValueError,
        match="Unversioned image is prohibited",
    ):
        renderer.validate_images(
            {"example.invalid/controller"}
        )


def test_non_digest_rendered_image_is_rejected() -> None:
    """The final render must contain digest references."""
    renderer = load_renderer()

    with pytest.raises(
        ValueError,
        match="not digest pinned",
    ):
        renderer.validate_pinned_images(
            {"example.invalid/controller:1.0"}
        )
