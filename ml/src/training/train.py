"""
SnapMenu ML - Training Script
==============================
Trains an EfficientNetV2 model for ingredient classification.

Two-phase training strategy:
  Phase 1: Frozen backbone, train classifier head only (fast convergence)
  Phase 2: Unfreeze all layers, fine-tune with low LR (high accuracy)

Usage:
    python -m src.training.train --config configs/training_config.yaml --data-dir ./data/splits

On Kaggle Notebook:
    Automatically detects GPU and adjusts settings.
"""

import os
import sys
import time
import argparse
from pathlib import Path
from typing import Optional

import yaml
import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import DataLoader
from torch.cuda.amp import GradScaler, autocast
from torchvision import datasets, transforms, models
from sklearn.metrics import f1_score, classification_report
import numpy as np


def load_config(config_path: str) -> dict:
    """Load YAML training configuration."""
    with open(config_path, 'r') as f:
        return yaml.safe_load(f)


def get_device(config: dict) -> torch.device:
    """Determine training device (GPU/CPU)."""
    hw = config.get('hardware', {})
    if hw.get('device', 'auto') == 'auto':
        if torch.cuda.is_available():
            device = torch.device('cuda')
            print(f"  🎮 GPU: {torch.cuda.get_device_name(0)}")
            print(f"     Memory: {torch.cuda.get_device_properties(0).total_mem / 1e9:.1f} GB")
        else:
            device = torch.device('cpu')
            print("  ⚠️  No GPU detected, using CPU (training will be slow)")
    else:
        device = torch.device(hw['device'])
    return device


def build_transforms(config: dict, dataset_config: dict) -> dict:
    """Build data augmentation transforms for train/val."""
    img_size = dataset_config.get('preprocessing', {}).get('image_size', 224)
    norm_mean = dataset_config.get('preprocessing', {}).get('normalize', {}).get('mean', [0.485, 0.456, 0.406])
    norm_std = dataset_config.get('preprocessing', {}).get('normalize', {}).get('std', [0.229, 0.224, 0.225])

    aug_config = dataset_config.get('augmentation', {})
    train_aug = aug_config.get('train', {})

    train_transforms = transforms.Compose([
        transforms.RandomResizedCrop(
            img_size,
            scale=train_aug.get('random_resized_crop', {}).get('scale', [0.8, 1.0]),
            ratio=train_aug.get('random_resized_crop', {}).get('ratio', [0.9, 1.1]),
        ),
        transforms.RandomHorizontalFlip() if train_aug.get('horizontal_flip', True) else transforms.Lambda(lambda x: x),
        transforms.RandomRotation(train_aug.get('rotation_degrees', 15)),
        transforms.ColorJitter(
            brightness=train_aug.get('color_jitter', {}).get('brightness', 0.3),
            contrast=train_aug.get('color_jitter', {}).get('contrast', 0.3),
            saturation=train_aug.get('color_jitter', {}).get('saturation', 0.2),
            hue=train_aug.get('color_jitter', {}).get('hue', 0.1),
        ),
        transforms.ToTensor(),
        transforms.Normalize(mean=norm_mean, std=norm_std),
        transforms.RandomErasing(p=train_aug.get('random_erasing', {}).get('probability', 0.1)),
    ])

    val_transforms = transforms.Compose([
        transforms.Resize(256),
        transforms.CenterCrop(img_size),
        transforms.ToTensor(),
        transforms.Normalize(mean=norm_mean, std=norm_std),
    ])

    return {'train': train_transforms, 'val': val_transforms}


def build_model(config: dict) -> nn.Module:
    """Build EfficientNetV2 model with custom classifier head."""
    model_config = config['model']
    architecture = model_config['architecture']
    num_classes = model_config['num_classes']
    dropout = model_config.get('dropout', 0.3)

    print(f"\n🏗️  Building model: {architecture}")
    print(f"   Classes: {num_classes}")
    print(f"   Pretrained: {model_config['pretrained']}")

    # Load pretrained EfficientNetV2
    if architecture == "efficientnet_v2_s":
        weights = models.EfficientNet_V2_S_Weights.DEFAULT if model_config['pretrained'] else None
        model = models.efficientnet_v2_s(weights=weights)
    elif architecture == "efficientnet_v2_m":
        weights = models.EfficientNet_V2_M_Weights.DEFAULT if model_config['pretrained'] else None
        model = models.efficientnet_v2_m(weights=weights)
    else:
        # Fallback to small
        weights = models.EfficientNet_V2_S_Weights.DEFAULT if model_config['pretrained'] else None
        model = models.efficientnet_v2_s(weights=weights)

    # Replace classifier head
    in_features = model.classifier[1].in_features
    model.classifier = nn.Sequential(
        nn.Dropout(p=dropout, inplace=True),
        nn.Linear(in_features, 512),
        nn.ReLU(inplace=True),
        nn.Dropout(p=dropout / 2),
        nn.Linear(512, num_classes),
    )

    print(f"   Classifier: {in_features} → 512 → {num_classes}")

    return model


def freeze_backbone(model: nn.Module):
    """Freeze all layers except classifier head."""
    for param in model.features.parameters():
        param.requires_grad = False
    print("   🔒 Backbone frozen (training classifier only)")


def unfreeze_backbone(model: nn.Module):
    """Unfreeze all layers for fine-tuning."""
    for param in model.parameters():
        param.requires_grad = True
    print("   🔓 Backbone unfrozen (fine-tuning all layers)")


def get_class_weights(dataset: datasets.ImageFolder, device: torch.device) -> torch.Tensor:
    """Compute class weights for imbalanced dataset."""
    targets = [s[1] for s in dataset.samples]
    class_counts = np.bincount(targets)
    total = len(targets)
    weights = total / (len(class_counts) * class_counts.astype(float))
    # Clip extreme weights
    weights = np.clip(weights, 0.5, 5.0)
    return torch.FloatTensor(weights).to(device)


def train_one_epoch(
    model: nn.Module,
    dataloader: DataLoader,
    criterion: nn.Module,
    optimizer: optim.Optimizer,
    device: torch.device,
    scaler: Optional[GradScaler],
    grad_accum_steps: int = 1,
    mixup_alpha: float = 0.0,
) -> dict:
    """Train for one epoch."""
    model.train()
    running_loss = 0.0
    correct = 0
    total = 0
    all_preds = []
    all_labels = []

    optimizer.zero_grad()

    for batch_idx, (inputs, labels) in enumerate(dataloader):
        inputs, labels = inputs.to(device), labels.to(device)

        # Mixup augmentation
        if mixup_alpha > 0 and np.random.random() > 0.5:
            lam = np.random.beta(mixup_alpha, mixup_alpha)
            rand_index = torch.randperm(inputs.size(0)).to(device)
            labels_a, labels_b = labels, labels[rand_index]
            inputs = lam * inputs + (1 - lam) * inputs[rand_index]

            if scaler is not None:
                with autocast():
                    outputs = model(inputs)
                    loss = lam * criterion(outputs, labels_a) + (1 - lam) * criterion(outputs, labels_b)
            else:
                outputs = model(inputs)
                loss = lam * criterion(outputs, labels_a) + (1 - lam) * criterion(outputs, labels_b)
        else:
            if scaler is not None:
                with autocast():
                    outputs = model(inputs)
                    loss = criterion(outputs, labels)
            else:
                outputs = model(inputs)
                loss = criterion(outputs, labels)

        # Gradient accumulation
        loss = loss / grad_accum_steps

        if scaler is not None:
            scaler.scale(loss).backward()
            if (batch_idx + 1) % grad_accum_steps == 0:
                scaler.step(optimizer)
                scaler.update()
                optimizer.zero_grad()
        else:
            loss.backward()
            if (batch_idx + 1) % grad_accum_steps == 0:
                optimizer.step()
                optimizer.zero_grad()

        running_loss += loss.item() * grad_accum_steps
        _, predicted = outputs.max(1)
        total += labels.size(0)
        correct += predicted.eq(labels).sum().item()
        all_preds.extend(predicted.cpu().numpy())
        all_labels.extend(labels.cpu().numpy())

    epoch_loss = running_loss / len(dataloader)
    epoch_acc = correct / total
    epoch_f1 = f1_score(all_labels, all_preds, average='weighted', zero_division=0)

    return {'loss': epoch_loss, 'accuracy': epoch_acc, 'f1': epoch_f1}


@torch.no_grad()
def evaluate(
    model: nn.Module,
    dataloader: DataLoader,
    criterion: nn.Module,
    device: torch.device,
) -> dict:
    """Evaluate model on validation/test set."""
    model.eval()
    running_loss = 0.0
    correct = 0
    top3_correct = 0
    total = 0
    all_preds = []
    all_labels = []

    for inputs, labels in dataloader:
        inputs, labels = inputs.to(device), labels.to(device)
        outputs = model(inputs)
        loss = criterion(outputs, labels)

        running_loss += loss.item()
        _, predicted = outputs.max(1)
        total += labels.size(0)
        correct += predicted.eq(labels).sum().item()

        # Top-3 accuracy
        _, top3_pred = outputs.topk(3, dim=1)
        for i in range(labels.size(0)):
            if labels[i] in top3_pred[i]:
                top3_correct += 1

        all_preds.extend(predicted.cpu().numpy())
        all_labels.extend(labels.cpu().numpy())

    epoch_loss = running_loss / len(dataloader)
    epoch_acc = correct / total
    epoch_top3 = top3_correct / total
    epoch_f1 = f1_score(all_labels, all_preds, average='weighted', zero_division=0)

    return {
        'loss': epoch_loss,
        'accuracy': epoch_acc,
        'top3_accuracy': epoch_top3,
        'f1': epoch_f1,
        'predictions': all_preds,
        'labels': all_labels,
    }


def get_scheduler(optimizer: optim.Optimizer, phase_config: dict, steps_per_epoch: int):
    """Create learning rate scheduler."""
    scheduler_type = phase_config.get('scheduler', 'cosine')
    total_epochs = phase_config['epochs']

    if scheduler_type == 'cosine':
        return optim.lr_scheduler.CosineAnnealingLR(
            optimizer, T_max=total_epochs, eta_min=phase_config.get('min_lr', 1e-7)
        )
    elif scheduler_type == 'cosine_with_restarts':
        return optim.lr_scheduler.CosineAnnealingWarmRestarts(
            optimizer, T_0=10, T_mult=2, eta_min=phase_config.get('min_lr', 1e-7)
        )
    else:
        return optim.lr_scheduler.StepLR(optimizer, step_size=10, gamma=0.5)


def train_phase(
    model: nn.Module,
    train_loader: DataLoader,
    val_loader: DataLoader,
    config: dict,
    phase_config: dict,
    phase_name: str,
    device: torch.device,
    save_dir: Path,
    class_weights: torch.Tensor,
) -> dict:
    """Execute a training phase (frozen or unfrozen)."""
    epochs = phase_config['epochs']
    lr = phase_config['learning_rate']
    wd = phase_config.get('weight_decay', 1e-5)
    grad_accum = config['training'].get('gradient_accumulation_steps', 1)
    mixup_alpha = config['training'].get('mixup_alpha', 0.0)
    label_smoothing = config['training'].get('label_smoothing', 0.0)
    use_amp = config.get('hardware', {}).get('mixed_precision', True) and device.type == 'cuda'

    # Loss function with class weights and label smoothing
    criterion = nn.CrossEntropyLoss(weight=class_weights, label_smoothing=label_smoothing)

    # Optimizer
    optimizer = optim.AdamW(
        filter(lambda p: p.requires_grad, model.parameters()),
        lr=lr,
        weight_decay=wd,
    )

    # Scheduler
    scheduler = get_scheduler(optimizer, phase_config, len(train_loader))

    # Mixed precision scaler
    scaler = GradScaler() if use_amp else None

    # Early stopping
    es_config = config['training'].get('early_stopping', {})
    patience = es_config.get('patience', 10)
    best_metric = 0.0
    patience_counter = 0

    print(f"\n{'='*60}")
    print(f"  {phase_name}")
    print(f"  Epochs: {epochs} | LR: {lr} | AMP: {use_amp}")
    print(f"  Grad Accum: {grad_accum} | Mixup: {mixup_alpha}")
    print(f"{'='*60}")

    history = {'train_loss': [], 'val_loss': [], 'val_acc': [], 'val_f1': [], 'lr': []}

    for epoch in range(epochs):
        t0 = time.time()

        # Train
        train_metrics = train_one_epoch(
            model, train_loader, criterion, optimizer, device,
            scaler, grad_accum, mixup_alpha
        )

        # Validate
        val_metrics = evaluate(model, val_loader, criterion, device)

        # Step scheduler
        scheduler.step()
        current_lr = optimizer.param_groups[0]['lr']

        elapsed = time.time() - t0

        # Log
        print(f"  Epoch {epoch+1:3d}/{epochs} | "
              f"Train Loss: {train_metrics['loss']:.4f} Acc: {train_metrics['accuracy']:.4f} | "
              f"Val Loss: {val_metrics['loss']:.4f} Acc: {val_metrics['accuracy']:.4f} "
              f"F1: {val_metrics['f1']:.4f} Top3: {val_metrics['top3_accuracy']:.4f} | "
              f"LR: {current_lr:.2e} | {elapsed:.1f}s")

        # Track history
        history['train_loss'].append(train_metrics['loss'])
        history['val_loss'].append(val_metrics['loss'])
        history['val_acc'].append(val_metrics['accuracy'])
        history['val_f1'].append(val_metrics['f1'])
        history['lr'].append(current_lr)

        # Early stopping check
        monitor_metric = val_metrics['f1']
        if monitor_metric > best_metric:
            best_metric = monitor_metric
            patience_counter = 0
            # Save best model
            save_path = save_dir / f"best_model_{phase_name.lower().replace(' ', '_')}.pth"
            torch.save({
                'epoch': epoch,
                'model_state_dict': model.state_dict(),
                'optimizer_state_dict': optimizer.state_dict(),
                'val_metrics': val_metrics,
                'config': config,
            }, save_path)
            print(f"  💾 Best model saved (F1: {best_metric:.4f})")
        else:
            patience_counter += 1
            if patience_counter >= patience:
                print(f"  ⏹️  Early stopping triggered (no improvement for {patience} epochs)")
                break

    return history


def main():
    parser = argparse.ArgumentParser(description="Train SnapMenu ingredient classifier")
    parser.add_argument('--config', type=str, default='configs/training_config.yaml')
    parser.add_argument('--data-config', type=str, default='configs/dataset_config.yaml')
    parser.add_argument('--data-dir', type=str, default='./data/splits')
    parser.add_argument('--output-dir', type=str, default='./models')
    parser.add_argument('--resume', type=str, default=None, help='Path to checkpoint to resume from')
    args = parser.parse_args()

    # Load configs
    config = load_config(args.config)
    dataset_config = load_config(args.data_config)

    print("=" * 60)
    print("🍽️  SnapMenu ML - Training")
    print("=" * 60)

    # Device
    device = get_device(config)

    # Transforms
    data_transforms = build_transforms(config, dataset_config)

    # Datasets
    data_dir = Path(args.data_dir)
    print(f"\n📂 Loading data from: {data_dir}")

    train_dataset = datasets.ImageFolder(data_dir / 'train', transform=data_transforms['train'])
    val_dataset = datasets.ImageFolder(data_dir / 'val', transform=data_transforms['val'])

    num_classes = len(train_dataset.classes)
    config['model']['num_classes'] = num_classes

    print(f"   Train: {len(train_dataset)} images")
    print(f"   Val:   {len(val_dataset)} images")
    print(f"   Classes: {num_classes}")
    print(f"   Class names: {train_dataset.classes[:10]}...")

    # DataLoaders
    batch_size = config['training']['batch_size']
    num_workers = config['training'].get('num_workers', 2)

    train_loader = DataLoader(
        train_dataset, batch_size=batch_size, shuffle=True,
        num_workers=num_workers, pin_memory=True, drop_last=True,
    )
    val_loader = DataLoader(
        val_dataset, batch_size=batch_size, shuffle=False,
        num_workers=num_workers, pin_memory=True,
    )

    # Model
    model = build_model(config)
    model = model.to(device)

    # Class weights for imbalanced data
    class_weights = get_class_weights(train_dataset, device)

    # Output directory
    save_dir = Path(args.output_dir)
    save_dir.mkdir(parents=True, exist_ok=True)

    # Save class names mapping
    class_names_path = save_dir / 'class_names.txt'
    with open(class_names_path, 'w') as f:
        for idx, name in enumerate(train_dataset.classes):
            f.write(f"{idx},{name}\n")
    print(f"\n   Class mapping saved to: {class_names_path}")

    # ============ PHASE 1: Train classifier head ============
    freeze_backbone(model)
    phase1_config = config['training']['phase1']

    history_p1 = train_phase(
        model, train_loader, val_loader, config, phase1_config,
        "Phase 1: Classifier Head", device, save_dir, class_weights,
    )

    # ============ PHASE 2: Fine-tune all layers ============
    unfreeze_backbone(model)
    phase2_config = config['training']['phase2']

    history_p2 = train_phase(
        model, train_loader, val_loader, config, phase2_config,
        "Phase 2: Fine-Tune All", device, save_dir, class_weights,
    )

    # ============ Final evaluation ============
    print("\n" + "=" * 60)
    print("📊 Final Evaluation on Validation Set")
    print("=" * 60)

    # Load best model from phase 2
    best_path = save_dir / "best_model_phase_2:_fine-tune_all.pth"
    if best_path.exists():
        checkpoint = torch.load(best_path, map_location=device)
        model.load_state_dict(checkpoint['model_state_dict'])
        print(f"   Loaded best model from Phase 2")

    criterion = nn.CrossEntropyLoss(weight=class_weights)
    final_metrics = evaluate(model, val_loader, criterion, device)

    print(f"\n   ✅ Final Results:")
    print(f"      Accuracy:     {final_metrics['accuracy']:.4f}")
    print(f"      Top-3 Acc:    {final_metrics['top3_accuracy']:.4f}")
    print(f"      F1 (weighted): {final_metrics['f1']:.4f}")

    # Check against targets
    targets = config['evaluation']['targets']
    print(f"\n   📎 Target Check:")
    for metric, target in targets.items():
        actual = final_metrics.get(metric, final_metrics.get(metric.replace('_weighted', ''), 0))
        status = "✅" if actual >= target else "❌"
        print(f"      {status} {metric}: {actual:.4f} (target: {target})")

    # Save final model
    final_path = save_dir / "snapmenu_classifier_final.pth"
    torch.save({
        'model_state_dict': model.state_dict(),
        'class_names': train_dataset.classes,
        'num_classes': num_classes,
        'config': config,
        'metrics': final_metrics,
    }, final_path)
    print(f"\n   💾 Final model saved: {final_path}")

    print("\n" + "=" * 60)
    print("✅ Training complete!")
    print("=" * 60)


if __name__ == "__main__":
    main()
