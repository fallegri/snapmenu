"""
SnapMenu ML - Evaluation Script
=================================
Evaluates a trained model on the test set and generates detailed metrics.

Outputs:
- Classification report (per-class precision/recall/F1)
- Confusion matrix
- Top-K accuracy analysis
- Per-class accuracy breakdown
- Misclassification analysis (most confused pairs)

Usage:
    python -m src.evaluation.evaluate \
        --model models/snapmenu_classifier_final.pth \
        --data-dir ./data/splits/test \
        --output-dir ./evaluation_results
"""

import os
import json
import argparse
from pathlib import Path

import yaml
import torch
import torch.nn as nn
import numpy as np
from torchvision import datasets, transforms, models
from torch.utils.data import DataLoader
from sklearn.metrics import (
    classification_report,
    confusion_matrix,
    f1_score,
    accuracy_score,
    top_k_accuracy_score,
)


def load_model(model_path: str, device: torch.device) -> tuple:
    """Load trained model and its metadata."""
    checkpoint = torch.load(model_path, map_location=device)

    class_names = checkpoint.get('class_names', [])
    num_classes = checkpoint.get('num_classes', len(class_names))
    config = checkpoint.get('config', {})

    # Rebuild model architecture
    model_arch = config.get('model', {}).get('architecture', 'efficientnet_v2_s')
    dropout = config.get('model', {}).get('dropout', 0.3)

    if model_arch == "efficientnet_v2_s":
        model = models.efficientnet_v2_s(weights=None)
    elif model_arch == "efficientnet_v2_m":
        model = models.efficientnet_v2_m(weights=None)
    else:
        model = models.efficientnet_v2_s(weights=None)

    # Replace classifier head (must match training)
    in_features = model.classifier[1].in_features
    model.classifier = nn.Sequential(
        nn.Dropout(p=dropout, inplace=True),
        nn.Linear(in_features, 512),
        nn.ReLU(inplace=True),
        nn.Dropout(p=dropout / 2),
        nn.Linear(512, num_classes),
    )

    model.load_state_dict(checkpoint['model_state_dict'])
    model = model.to(device)
    model.eval()

    return model, class_names, config


def get_eval_transforms(img_size: int = 224) -> transforms.Compose:
    """Standard evaluation transforms (no augmentation)."""
    return transforms.Compose([
        transforms.Resize(256),
        transforms.CenterCrop(img_size),
        transforms.ToTensor(),
        transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),
    ])


@torch.no_grad()
def run_evaluation(
    model: nn.Module,
    dataloader: DataLoader,
    device: torch.device,
    num_classes: int,
) -> dict:
    """Run full evaluation and collect predictions."""
    all_preds = []
    all_labels = []
    all_probs = []

    for inputs, labels in dataloader:
        inputs = inputs.to(device)
        outputs = model(inputs)
        probs = torch.softmax(outputs, dim=1)

        _, predicted = outputs.max(1)
        all_preds.extend(predicted.cpu().numpy())
        all_labels.extend(labels.numpy())
        all_probs.extend(probs.cpu().numpy())

    return {
        'predictions': np.array(all_preds),
        'labels': np.array(all_labels),
        'probabilities': np.array(all_probs),
    }


def compute_metrics(results: dict, class_names: list) -> dict:
    """Compute comprehensive evaluation metrics."""
    preds = results['predictions']
    labels = results['labels']
    probs = results['probabilities']

    # Basic metrics
    accuracy = accuracy_score(labels, preds)
    f1_weighted = f1_score(labels, preds, average='weighted', zero_division=0)
    f1_macro = f1_score(labels, preds, average='macro', zero_division=0)

    # Top-K accuracy
    top3_acc = top_k_accuracy_score(labels, probs, k=3, labels=range(len(class_names)))
    top5_acc = top_k_accuracy_score(labels, probs, k=5, labels=range(len(class_names)))

    # Per-class report
    report = classification_report(
        labels, preds,
        target_names=class_names,
        output_dict=True,
        zero_division=0,
    )

    # Confusion matrix
    cm = confusion_matrix(labels, preds)

    # Most confused pairs
    confused_pairs = []
    for i in range(len(class_names)):
        for j in range(len(class_names)):
            if i != j and cm[i][j] > 0:
                confused_pairs.append({
                    'true': class_names[i],
                    'predicted': class_names[j],
                    'count': int(cm[i][j]),
                    'percentage': float(cm[i][j]) / max(cm[i].sum(), 1) * 100,
                })
    confused_pairs.sort(key=lambda x: x['count'], reverse=True)

    # Per-class accuracy
    per_class_acc = {}
    for i, name in enumerate(class_names):
        mask = labels == i
        if mask.sum() > 0:
            per_class_acc[name] = float((preds[mask] == i).sum()) / mask.sum()
        else:
            per_class_acc[name] = 0.0

    # Worst performing classes
    worst_classes = sorted(per_class_acc.items(), key=lambda x: x[1])[:10]

    return {
        'overall': {
            'accuracy': float(accuracy),
            'top3_accuracy': float(top3_acc),
            'top5_accuracy': float(top5_acc),
            'f1_weighted': float(f1_weighted),
            'f1_macro': float(f1_macro),
            'total_samples': int(len(labels)),
            'num_classes': len(class_names),
        },
        'per_class_report': report,
        'per_class_accuracy': per_class_acc,
        'worst_classes': worst_classes,
        'top_confused_pairs': confused_pairs[:20],
        'confusion_matrix': cm.tolist(),
    }


def generate_report(metrics: dict, class_names: list, output_dir: Path):
    """Generate markdown evaluation report."""
    report_path = output_dir / "evaluation_report.md"

    with open(report_path, 'w') as f:
        f.write("# SnapMenu - Model Evaluation Report\n\n")

        # Overall metrics
        overall = metrics['overall']
        f.write("## Overall Metrics\n\n")
        f.write(f"| Metric | Value | Target | Status |\n")
        f.write(f"|--------|-------|--------|--------|\n")
        f.write(f"| Accuracy | {overall['accuracy']:.4f} | ≥ 0.90 | {'✅' if overall['accuracy'] >= 0.90 else '❌'} |\n")
        f.write(f"| Top-3 Accuracy | {overall['top3_accuracy']:.4f} | ≥ 0.97 | {'✅' if overall['top3_accuracy'] >= 0.97 else '❌'} |\n")
        f.write(f"| Top-5 Accuracy | {overall['top5_accuracy']:.4f} | — | — |\n")
        f.write(f"| F1 (weighted) | {overall['f1_weighted']:.4f} | ≥ 0.88 | {'✅' if overall['f1_weighted'] >= 0.88 else '❌'} |\n")
        f.write(f"| F1 (macro) | {overall['f1_macro']:.4f} | — | — |\n")
        f.write(f"| Total samples | {overall['total_samples']} | — | — |\n")
        f.write(f"| Classes | {overall['num_classes']} | — | — |\n\n")

        # Worst performing classes
        f.write("## Worst Performing Classes (Bottom 10)\n\n")
        f.write("| Class | Accuracy | Action Needed |\n")
        f.write("|-------|----------|---------------|\n")
        for name, acc in metrics['worst_classes']:
            action = "More data / augmentation" if acc < 0.7 else "Review annotations"
            f.write(f"| {name} | {acc:.4f} | {action} |\n")

        # Most confused pairs
        f.write("\n## Most Confused Pairs (Top 10)\n\n")
        f.write("| True Label | Predicted As | Count | % of True Class |\n")
        f.write("|-----------|--------------|-------|------------------|\n")
        for pair in metrics['top_confused_pairs'][:10]:
            f.write(f"| {pair['true']} | {pair['predicted']} | {pair['count']} | {pair['percentage']:.1f}% |\n")

        f.write("\n\n---\n*Report generated by SnapMenu ML Pipeline*\n")

    print(f"  📄 Report saved: {report_path}")


def main():
    parser = argparse.ArgumentParser(description="Evaluate SnapMenu model")
    parser.add_argument('--model', type=str, required=True, help='Path to trained model .pth')
    parser.add_argument('--data-dir', type=str, required=True, help='Path to test dataset')
    parser.add_argument('--output-dir', type=str, default='./evaluation_results')
    parser.add_argument('--batch-size', type=int, default=32)
    args = parser.parse_args()

    print("=" * 60)
    print("🍽️  SnapMenu ML - Model Evaluation")
    print("=" * 60)

    # Device
    device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    print(f"\n  Device: {device}")

    # Load model
    print(f"  Loading model: {args.model}")
    model, class_names, config = load_model(args.model, device)
    print(f"  Classes: {len(class_names)}")

    # Dataset
    transform = get_eval_transforms()
    test_dataset = datasets.ImageFolder(args.data_dir, transform=transform)
    test_loader = DataLoader(test_dataset, batch_size=args.batch_size, shuffle=False, num_workers=2)
    print(f"  Test samples: {len(test_dataset)}")

    # Use folder names if class_names not in checkpoint
    if not class_names:
        class_names = test_dataset.classes

    # Run evaluation
    print("\n  Running evaluation...")
    results = run_evaluation(model, test_loader, device, len(class_names))

    # Compute metrics
    print("  Computing metrics...")
    metrics = compute_metrics(results, class_names)

    # Output
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    # Save metrics JSON
    metrics_path = output_dir / "metrics.json"
    # Remove confusion matrix from JSON (too large) — save separately
    cm = metrics.pop('confusion_matrix')
    with open(metrics_path, 'w') as f:
        json.dump(metrics, f, indent=2, default=str)
    print(f"  📊 Metrics saved: {metrics_path}")

    # Save confusion matrix separately
    np.save(output_dir / "confusion_matrix.npy", np.array(cm))

    # Generate markdown report
    metrics['confusion_matrix'] = cm
    generate_report(metrics, class_names, output_dir)

    # Print summary
    print(f"\n{'='*60}")
    print(f"  📊 RESULTS SUMMARY")
    print(f"{'='*60}")
    overall = metrics['overall']
    print(f"  Accuracy:      {overall['accuracy']:.4f}")
    print(f"  Top-3 Acc:     {overall['top3_accuracy']:.4f}")
    print(f"  F1 (weighted): {overall['f1_weighted']:.4f}")
    print(f"{'='*60}\n")


if __name__ == "__main__":
    main()
