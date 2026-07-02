"""Export trained PyTorch CNN to ONNX for production inference."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import argparse
import json
from pathlib import Path

import torch

from training.dataset import CLASSES
from training.train import CandleCNN


def export_onnx(weights_path: Path, manifest_path: Path, output_path: Path) -> None:
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    image_size = int(manifest.get("image_size", 64))
    num_classes = len(manifest.get("classes", CLASSES))

    model = CandleCNN(num_classes=num_classes)
    model.load_state_dict(torch.load(weights_path, map_location="cpu"))
    model.eval()

    dummy = torch.randn(1, 1, image_size, image_size)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    torch.onnx.export(
        model,
        dummy,
        str(output_path),
        input_names=["input"],
        output_names=["logits"],
        dynamic_axes={"input": {0: "batch"}, "logits": {0: "batch"}},
        opset_version=17,
    )

    manifest["artifact"] = {"onnx": output_path.name}
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(f"Exported ONNX to {output_path}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Export CNN weights to ONNX")
    parser.add_argument("--weights", type=Path, default=Path("artifacts/candle_cnn.pt"))
    parser.add_argument("--manifest", type=Path, default=Path("artifacts/manifest.json"))
    parser.add_argument("--output", type=Path, default=Path("models/patterns.onnx"))
    args = parser.parse_args()
    export_onnx(args.weights, args.manifest, args.output)


if __name__ == "__main__":
    main()
