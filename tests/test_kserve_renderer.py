from pathlib import Path

import pytest

from scripts.render_kserve_manifests import render

ROOT = Path(__file__).parents[1]


def test_kserve_contract_renders(tmp_path: Path) -> None:
    render(
        ROOT / "kubernetes/platform/kserve/source-lock.json",
        ROOT / "kubernetes/platform/kserve/inference-service.yaml",
        ROOT / "kubernetes/platform/kserve/serving-runtime.yaml",
        tmp_path,
    )
    assert (tmp_path / "render-report.json").exists()


def test_wrong_namespace_is_rejected(tmp_path: Path) -> None:
    path = tmp_path / "bad.yaml"
    source = (
        ROOT / "kubernetes/platform/kserve/inference-service.yaml"
    ).read_text()
    path.write_text(source.replace("namespace: kserve", "namespace: default"))

    with pytest.raises(ValueError, match="namespace"):
        render(
            ROOT / "kubernetes/platform/kserve/source-lock.json",
            path,
            ROOT / "kubernetes/platform/kserve/serving-runtime.yaml",
            tmp_path / "out",
        )
