"""Train a small CNN on TA-Lib labeled candlestick windows."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import argparse
import json
from pathlib import Path

import numpy as np
import torch
import torch.nn as nn
from torch.utils.data import DataLoader, TensorDataset

from training.dataset import CLASSES, build_dataset, load_bars_json, load_npz_split, save_npz


class CandleCNN(nn.Module):
    def __init__(self, num_classes: int) -> None:
        super().__init__()
        self.net = nn.Sequential(
            nn.Conv2d(1, 16, kernel_size=3, padding=1),
            nn.ReLU(),
            nn.MaxPool2d(2),
            nn.Conv2d(16, 32, kernel_size=3, padding=1),
            nn.ReLU(),
            nn.MaxPool2d(2),
            nn.Conv2d(32, 64, kernel_size=3, padding=1),
            nn.ReLU(),
            nn.AdaptiveAvgPool2d((4, 4)),
            nn.Flatten(),
            nn.Linear(64 * 4 * 4, 128),
            nn.ReLU(),
            nn.Dropout(0.2),
            nn.Linear(128, num_classes),
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.net(x)


def _evaluate(model: nn.Module, loader: DataLoader, device: torch.device) -> float:
    model.eval()
    correct = 0
    total = 0
    with torch.no_grad():
        for batch_x, batch_y in loader:
            batch_x = batch_x.to(device)
            batch_y = batch_y.to(device)
            logits = model(batch_x)
            preds = torch.argmax(logits, dim=1)
            correct += int((preds == batch_y).sum().item())
            total += int(batch_y.numel())
    model.train()
    return correct / total if total else 0.0


def train_from_splits(
    dataset_dir: Path,
    output_dir: Path,
    *,
    epochs: int = 8,
    batch_size: int = 64,
    lr: float = 1e-3,
) -> Path:
    train_x, train_y, classes = load_npz_split(dataset_dir / "train.npz")
    val_path = dataset_dir / "val.npz"
    val_loader = None
    if val_path.is_file():
        val_x, val_y, _ = load_npz_split(val_path)
        val_loader = DataLoader(
            TensorDataset(torch.from_numpy(val_x), torch.from_numpy(val_y)),
            batch_size=batch_size,
        )

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    train_loader = DataLoader(
        TensorDataset(torch.from_numpy(train_x), torch.from_numpy(train_y)),
        batch_size=batch_size,
        shuffle=True,
    )

    model = CandleCNN(num_classes=len(classes)).to(device)
    optimizer = torch.optim.Adam(model.parameters(), lr=lr)
    criterion = nn.CrossEntropyLoss()

    manifest_path = dataset_dir / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8")) if manifest_path.is_file() else {}

    model.train()
    for epoch in range(epochs):
        for batch_x, batch_y in train_loader:
            batch_x = batch_x.to(device)
            batch_y = batch_y.to(device)
            optimizer.zero_grad()
            logits = model(batch_x)
            loss = criterion(logits, batch_y)
            loss.backward()
            optimizer.step()

        if val_loader is not None:
            acc = _evaluate(model, val_loader, device)
            print(f"epoch {epoch + 1}/{epochs} val_accuracy={acc:.4f}")

    output_dir.mkdir(parents=True, exist_ok=True)
    weights_path = output_dir / "candle_cnn.pt"
    torch.save(model.state_dict(), weights_path)

    out_manifest = {
        "version": manifest.get("version", "1.0.0"),
        "window_size": manifest.get("window_size", 10),
        "image_size": manifest.get("image_size", 64),
        "threshold": manifest.get("threshold", 0.65),
        "timeframes": manifest.get("timeframes", ["5Min"]),
        "classes": classes,
        "label_source": manifest.get("label_source", "talib"),
        "weights": str(weights_path.name),
    }
    (output_dir / "manifest.json").write_text(json.dumps(out_manifest, indent=2), encoding="utf-8")
    return weights_path


def train_from_bars(
    bars_path: Path,
    output_dir: Path,
    *,
    epochs: int = 8,
    batch_size: int = 64,
    lr: float = 1e-3,
    window_size: int = 10,
    image_size: int = 64,
) -> Path:
    bars = load_bars_json(bars_path)
    x, y = build_dataset(bars, window_size=window_size, image_size=image_size)
    save_npz(output_dir / "dataset.npz", x, y)

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    dataset = TensorDataset(torch.from_numpy(x), torch.from_numpy(y))
    loader = DataLoader(dataset, batch_size=batch_size, shuffle=True)

    model = CandleCNN(num_classes=len(CLASSES)).to(device)
    optimizer = torch.optim.Adam(model.parameters(), lr=lr)
    criterion = nn.CrossEntropyLoss()

    model.train()
    for _epoch in range(epochs):
        for batch_x, batch_y in loader:
            batch_x = batch_x.to(device)
            batch_y = batch_y.to(device)
            optimizer.zero_grad()
            logits = model(batch_x)
            loss = criterion(logits, batch_y)
            loss.backward()
            optimizer.step()

    output_dir.mkdir(parents=True, exist_ok=True)
    weights_path = output_dir / "candle_cnn.pt"
    torch.save(model.state_dict(), weights_path)

    manifest = {
        "version": "1.0.0",
        "window_size": window_size,
        "image_size": image_size,
        "threshold": 0.65,
        "timeframes": ["5Min"],
        "classes": CLASSES,
        "weights": str(weights_path.name),
    }
    (output_dir / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return weights_path


def main() -> None:
    parser = argparse.ArgumentParser(description="Train candlestick pattern CNN")
    parser.add_argument("--dataset-dir", type=Path, default=None, help="Dir with train.npz/val.npz from generate_talib_dataset.py")
    parser.add_argument("--bars", type=Path, default=None, help="Legacy JSON bars file")
    parser.add_argument("--output", type=Path, default=Path("artifacts"))
    parser.add_argument("--epochs", type=int, default=8)
    args = parser.parse_args()

    if args.dataset_dir is not None:
        path = train_from_splits(args.dataset_dir, args.output, epochs=args.epochs)
    elif args.bars is not None:
        path = train_from_bars(args.bars, args.output, epochs=args.epochs)
    else:
        default_dir = Path("artifacts")
        if (default_dir / "train.npz").is_file():
            path = train_from_splits(default_dir, args.output, epochs=args.epochs)
        else:
            raise SystemExit("Provide --dataset-dir or --bars")

    print(f"Saved weights to {path}")


if __name__ == "__main__":
    main()
