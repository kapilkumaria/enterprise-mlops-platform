"""Validate the bounded KServe Standard contract."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import yaml


def render(
    lock_path: Path,
    inference_path: Path,
    runtime_path: Path,
    output_dir: Path,
) -> None:
    lock = json.loads(lock_path.read_text(encoding="utf-8"))
    inference = yaml.safe_load(inference_path.read_text(encoding="utf-8"))
    runtime = yaml.safe_load(runtime_path.read_text(encoding="utf-8"))

    if lock["mode"] != "Standard":
        raise ValueError("KServe mode must be Standard")
    if lock["namespace"] != "kserve":
        raise ValueError("KServe namespace must be kserve")
    if inference["metadata"]["namespace"] != "kserve":
        raise ValueError("InferenceService namespace must be kserve")
    if inference["metadata"]["annotations"].get(
        "serving.kserve.io/deploymentMode"
    ) != "Standard":
        raise ValueError("InferenceService must use Standard mode")
    if inference["spec"]["predictor"]["model"]["storageUri"] != lock["model_uri"]:
        raise ValueError("InferenceService model URI does not match lock")

    image = runtime["spec"]["containers"][0]["image"]
    if image != lock["images"]["predictor"] or "@sha256:" not in image:
        raise ValueError("ServingRuntime image does not match locked predictor")

    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "inference-service.yaml").write_text(
        yaml.safe_dump(inference, sort_keys=False), encoding="utf-8"
    )
    (output_dir / "serving-runtime.yaml").write_text(
        yaml.safe_dump(runtime, sort_keys=False), encoding="utf-8"
    )
    (output_dir / "render-report.json").write_text(
        json.dumps(
            {"status": "PASS", "mode": lock["mode"], "namespace": lock["namespace"]},
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-lock", type=Path, required=True)
    parser.add_argument("--inference-service", type=Path, required=True)
    parser.add_argument("--serving-runtime", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    render(
        args.source_lock,
        args.inference_service,
        args.serving_runtime,
        args.output_dir,
    )
    print("PASS: KServe Standard contract rendered")


if __name__ == "__main__":
    main()
