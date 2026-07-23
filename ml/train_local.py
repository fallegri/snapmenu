"""
SnapMenu ML - Entrenamiento Local (GTX 1070 8GB + 32GB RAM)
===========================================================
Script optimizado para entrenamiento en PC local con GPU NVIDIA.

REQUISITOS:
    pip install torch torchvision --index-url https://download.pytorch.org/whl/cu121
    pip install scikit-learn pillow pyyaml kagglehub

USO:
    python train_local.py

TIEMPO ESTIMADO: ~1-1.5 horas con GTX 1070
"""

import os
import sys
import time
import random
import shutil
import json
from pathlib import Path

import numpy as np
import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import DataLoader
from torch.cuda.amp import GradScaler, autocast
from torchvision import datasets, transforms, models
from sklearn.model_selection import train_test_split
from sklearn.metrics import (
    f1_score, classification_report,
    accuracy_score, top_k_accuracy_score
)
from PIL import ImageFile

ImageFile.LOAD_TRUNCATED_IMAGES = True

# ============================================================
# CONFIGURACIÓN — Ajustar según tu setup
# ============================================================
CONFIG = {
    # RUTAS - Ajusta dataset_path después de descargar con kagglehub
    'dataset_path': None,  # Se auto-detecta abajo
    'output_dir': './output_model',

    # MODELO
    'img_size': 224,
    'dropout': 0.3,

    # ENTRENAMIENTO - Optimizado para GTX 1070 (8GB VRAM)
    'batch_size': 48,           # GTX 1070 aguanta 48 con EfficientNetV2-S
    'num_workers': 4,           # 4 workers con 32GB RAM está perfecto
    'pin_memory': True,

    # DATASET
    'exclude_classes': ['Unlabeled'],
    'max_samples_per_class': 2000,
    'train_ratio': 0.70,
    'val_ratio': 0.15,
    'test_ratio': 0.15,

    # PHASE 1: Classifier head only (rápido)
    'phase1_epochs': 8,
    'phase1_lr': 1e-3,

    # PHASE 2: Fine-tune all (la fase importante)
    'phase2_epochs': 30,
    'phase2_lr': 1e-4,

    # REGULARIZACIÓN
    'label_smoothing': 0.1,
    'mixup_alpha': 0.2,
    'weight_decay': 1e-5,

    # EARLY STOPPING
    'patience': 8,
}

# ============================================================
# SEED para reproducibilidad
# ============================================================
SEED = 42
random.seed(SEED)
np.random.seed(SEED)
torch.manual_seed(SEED)
torch.cuda.manual_seed_all(SEED)
torch.backends.cudnn.benchmark = True  # Optimiza para tu GPU específica


def setup_device():
    """Detectar y configurar GPU."""
    if not torch.cuda.is_available():
        print("❌ CUDA no disponible. Verifica que tienes:")
        print("   1. Drivers NVIDIA actualizados")
        print("   2. PyTorch con CUDA: pip install torch torchvision --index-url https://download.pytorch.org/whl/cu121")
        sys.exit(1)

    device = torch.device('cuda')
    gpu_name = torch.cuda.get_device_name(0)
    vram = torch.cuda.get_device_properties(0).total_mem / 1e9

    print(f"  🎮 GPU: {gpu_name}")
    print(f"  💾 VRAM: {vram:.1f} GB")
    print(f"  🔧 CUDA: {torch.version.cuda}")
    print(f"  📦 PyTorch: {torch.__version__}")

    return device


def download_dataset():
    """Descargar dataset de Kaggle si no existe."""
    print("\n📥 Buscando dataset...")

    # Intentar encontrar dataset ya descargado
    possible_paths = [
        Path.home() / ".cache/kagglehub/datasets/guigasousa/compilado-de-ingredientesalimentos",
        Path("./dataset"),
    ]

    for base in possible_paths:
        if not base.exists():
            continue
        # Buscar recursivamente la carpeta con ingredientes
        for root, dirs, files in os.walk(base):
            if 'chicken' in dirs and 'avocado' in dirs:
                print(f"  ✅ Dataset encontrado: {root}")
                return root

    # No encontrado, descargar
    print("  📥 Descargando dataset de Kaggle...")
    print("  (Esto puede tomar unos minutos la primera vez)")
    try:
        import kagglehub
        path = kagglehub.dataset_download("guigasousa/compilado-de-ingredientesalimentos")
        print(f"  ✅ Descargado en: {path}")
        # Buscar la carpeta correcta dentro
        for root, dirs, files in os.walk(path):
            if 'chicken' in dirs and 'avocado' in dirs:
                return root
        return path
    except Exception as e:
        print(f"  ❌ Error descargando: {e}")
        print("  Alternativa manual:")
        print("    1. Ir a https://www.kaggle.com/datasets/guigasousa/compilado-de-ingredientesalimentos")
        print("    2. Descargar y extraer en ./dataset/")
        print("    3. Ejecutar de nuevo este script")
        sys.exit(1)


def explore_dataset(base_path):
    """Explorar y mostrar distribución del dataset."""
    base = Path(base_path)
    class_counts = {}

    for class_dir in sorted(base.iterdir()):
        if not class_dir.is_dir():
            continue
        name = class_dir.name
        if name in CONFIG['exclude_classes']:
            continue
        count = len([f for f in class_dir.iterdir()
                     if f.suffix.lower() in {'.jpg', '.jpeg', '.png', '.webp'}])
        if count > 0:
            class_counts[name] = count

    total = sum(class_counts.values())
    print(f"\n📊 Dataset:")
    print(f"   Clases: {len(class_counts)}")
    print(f"   Total imágenes: {total:,}")
    print(f"   Rango: {min(class_counts.values())} - {max(class_counts.values())} imgs/clase")

    return class_counts


def prepare_splits(base_path, class_counts):
    """Crear splits train/val/test."""
    base = Path(base_path)
    splits_dir = Path(CONFIG['output_dir']) / 'splits'

    # Limpiar splits anteriores si existen
    if splits_dir.exists():
        shutil.rmtree(splits_dir)

    class_names = sorted(class_counts.keys())
    for split in ['train', 'val', 'test']:
        for cls in class_names:
            (splits_dir / split / cls).mkdir(parents=True, exist_ok=True)

    stats = {'train': 0, 'val': 0, 'test': 0}

    for cls in class_names:
        cls_dir = base / cls
        images = [f for f in cls_dir.iterdir()
                  if f.suffix.lower() in {'.jpg', '.jpeg', '.png', '.webp'}]

        if len(images) > CONFIG['max_samples_per_class']:
            images = random.sample(images, CONFIG['max_samples_per_class'])

        if len(images) < 3:
            continue

        train_imgs, temp_imgs = train_test_split(
            images, test_size=(CONFIG['val_ratio'] + CONFIG['test_ratio']),
            random_state=SEED
        )
        val_imgs, test_imgs = train_test_split(
            temp_imgs,
            test_size=CONFIG['test_ratio'] / (CONFIG['val_ratio'] + CONFIG['test_ratio']),
            random_state=SEED
        )

        for split_name, split_imgs in [('train', train_imgs), ('val', val_imgs), ('test', test_imgs)]:
            for img in split_imgs:
                dest = splits_dir / split_name / cls / img.name
                if not dest.exists():
                    # Symlink en vez de copiar (más rápido, ahorra espacio)
                    try:
                        os.symlink(img, dest)
                    except (OSError, NotImplementedError):
                        shutil.copy2(img, dest)
            stats[split_name] += len(split_imgs)

    print(f"\n✂️  Splits: Train={stats['train']:,} | Val={stats['val']:,} | Test={stats['test']:,}")
    return splits_dir


def build_model(num_classes):
    """Construir EfficientNetV2-S."""
    model = models.efficientnet_v2_s(weights=models.EfficientNet_V2_S_Weights.DEFAULT)
    in_features = model.classifier[1].in_features
    model.classifier = nn.Sequential(
        nn.Dropout(p=CONFIG['dropout'], inplace=True),
        nn.Linear(in_features, 512),
        nn.ReLU(inplace=True),
        nn.Dropout(p=CONFIG['dropout'] / 2),
        nn.Linear(512, num_classes),
    )
    return model


def get_class_weights(dataset, device):
    """Pesos inversamente proporcionales a frecuencia."""
    targets = [s[1] for s in dataset.samples]
    counts = np.bincount(targets)
    weights = len(targets) / (len(counts) * counts.astype(float))
    weights = np.clip(weights, 0.5, 5.0)
    return torch.FloatTensor(weights).to(device)


def train_one_epoch(model, loader, criterion, optimizer, scaler, device, mixup_alpha=0.0):
    """Entrenar una epoch con mixed precision."""
    model.train()
    running_loss, correct, total = 0.0, 0, 0

    for inputs, labels in loader:
        inputs, labels = inputs.to(device, non_blocking=True), labels.to(device, non_blocking=True)

        # Mixup
        if mixup_alpha > 0 and random.random() > 0.5:
            lam = np.random.beta(mixup_alpha, mixup_alpha)
            idx = torch.randperm(inputs.size(0), device=device)
            inputs = lam * inputs + (1 - lam) * inputs[idx]
            with autocast():
                outputs = model(inputs)
                loss = lam * criterion(outputs, labels) + (1 - lam) * criterion(outputs, labels[idx])
        else:
            with autocast():
                outputs = model(inputs)
                loss = criterion(outputs, labels)

        scaler.scale(loss).backward()
        scaler.step(optimizer)
        scaler.update()
        optimizer.zero_grad(set_to_none=True)

        running_loss += loss.item()
        _, pred = outputs.max(1)
        total += labels.size(0)
        correct += pred.eq(labels).sum().item()

    return running_loss / len(loader), correct / total


@torch.no_grad()
def evaluate(model, loader, criterion, device):
    """Evaluar modelo."""
    model.eval()
    running_loss, correct, total = 0.0, 0, 0
    all_preds, all_labels = [], []

    for inputs, labels in loader:
        inputs, labels = inputs.to(device, non_blocking=True), labels.to(device, non_blocking=True)
        outputs = model(inputs)
        loss = criterion(outputs, labels)

        running_loss += loss.item()
        _, pred = outputs.max(1)
        total += labels.size(0)
        correct += pred.eq(labels).sum().item()
        all_preds.extend(pred.cpu().numpy())
        all_labels.extend(labels.cpu().numpy())

    f1 = f1_score(all_labels, all_preds, average='weighted', zero_division=0)
    return running_loss / len(loader), correct / total, f1


def main():
    print("=" * 60)
    print("🍽️  SnapMenu — Entrenamiento Local")
    print("   GPU: GTX 1070 (8GB) | RAM: 32GB")
    print("=" * 60)

    # 1. Setup GPU
    device = setup_device()

    # 2. Dataset
    dataset_path = download_dataset()
    CONFIG['dataset_path'] = dataset_path
    class_counts = explore_dataset(dataset_path)
    NUM_CLASSES = len(class_counts)

    # 3. Splits
    print("\n⏳ Preparando splits (symlinks, debería ser rápido)...")
    splits_dir = prepare_splits(dataset_path, class_counts)

    # 4. Transforms y DataLoaders
    train_transforms = transforms.Compose([
        transforms.RandomResizedCrop(CONFIG['img_size'], scale=(0.8, 1.0)),
        transforms.RandomHorizontalFlip(),
        transforms.RandomRotation(15),
        transforms.ColorJitter(brightness=0.3, contrast=0.3, saturation=0.2, hue=0.1),
        transforms.ToTensor(),
        transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),
        transforms.RandomErasing(p=0.1),
    ])

    val_transforms = transforms.Compose([
        transforms.Resize(256),
        transforms.CenterCrop(CONFIG['img_size']),
        transforms.ToTensor(),
        transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),
    ])

    train_dataset = datasets.ImageFolder(splits_dir / 'train', transform=train_transforms)
    val_dataset = datasets.ImageFolder(splits_dir / 'val', transform=val_transforms)
    test_dataset = datasets.ImageFolder(splits_dir / 'test', transform=val_transforms)

    train_loader = DataLoader(
        train_dataset, batch_size=CONFIG['batch_size'], shuffle=True,
        num_workers=CONFIG['num_workers'], pin_memory=True, drop_last=True,
        persistent_workers=True,
    )
    val_loader = DataLoader(
        val_dataset, batch_size=CONFIG['batch_size'], shuffle=False,
        num_workers=CONFIG['num_workers'], pin_memory=True,
        persistent_workers=True,
    )
    test_loader = DataLoader(
        test_dataset, batch_size=CONFIG['batch_size'], shuffle=False,
        num_workers=CONFIG['num_workers'], pin_memory=True,
    )

    print(f"\n📦 DataLoaders: Train={len(train_loader)} batches | Val={len(val_loader)} batches")
    print(f"   Clases: {NUM_CLASSES} | Batch size: {CONFIG['batch_size']}")

    # 5. Modelo
    model = build_model(NUM_CLASSES).to(device)
    class_weights = get_class_weights(train_dataset, device)
    criterion = nn.CrossEntropyLoss(weight=class_weights, label_smoothing=CONFIG['label_smoothing'])

    total_params = sum(p.numel() for p in model.parameters()) / 1e6
    print(f"\n🏗️  Modelo: EfficientNetV2-S ({total_params:.1f}M params)")

    os.makedirs(CONFIG['output_dir'], exist_ok=True)

    # ============================================================
    # PHASE 1: Train classifier head
    # ============================================================
    print(f"\n{'='*60}")
    print(f"🔒 PHASE 1: Classifier Head ({CONFIG['phase1_epochs']} epochs)")
    print(f"{'='*60}")

    for param in model.features.parameters():
        param.requires_grad = False

    optimizer = optim.AdamW(
        filter(lambda p: p.requires_grad, model.parameters()),
        lr=CONFIG['phase1_lr'], weight_decay=CONFIG['weight_decay']
    )
    scheduler = optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=CONFIG['phase1_epochs'])
    scaler = GradScaler()

    best_f1 = 0.0
    for epoch in range(CONFIG['phase1_epochs']):
        t0 = time.time()
        train_loss, train_acc = train_one_epoch(
            model, train_loader, criterion, optimizer, scaler, device)
        val_loss, val_acc, val_f1 = evaluate(model, val_loader, criterion, device)
        scheduler.step()
        elapsed = time.time() - t0

        marker = " 💾" if val_f1 > best_f1 else ""
        print(f"  [{epoch+1:2d}/{CONFIG['phase1_epochs']}] "
              f"Loss: {train_loss:.3f}/{val_loss:.3f} | "
              f"Acc: {train_acc:.3f}/{val_acc:.3f} | "
              f"F1: {val_f1:.4f} | {elapsed:.0f}s{marker}")

        if val_f1 > best_f1:
            best_f1 = val_f1
            torch.save(model.state_dict(), f"{CONFIG['output_dir']}/best_phase1.pth")

    print(f"  ✅ Phase 1 done — Best F1: {best_f1:.4f}")

    # ============================================================
    # PHASE 2: Fine-tune all layers
    # ============================================================
    print(f"\n{'='*60}")
    print(f"🔓 PHASE 2: Fine-Tune All ({CONFIG['phase2_epochs']} epochs, patience={CONFIG['patience']})")
    print(f"{'='*60}")

    for param in model.parameters():
        param.requires_grad = True

    optimizer = optim.AdamW(model.parameters(), lr=CONFIG['phase2_lr'], weight_decay=CONFIG['weight_decay'])
    scheduler = optim.lr_scheduler.CosineAnnealingWarmRestarts(optimizer, T_0=10, T_mult=2, eta_min=1e-6)
    scaler = GradScaler()

    best_f1 = 0.0
    patience_counter = 0

    for epoch in range(CONFIG['phase2_epochs']):
        t0 = time.time()
        train_loss, train_acc = train_one_epoch(
            model, train_loader, criterion, optimizer, scaler, device, CONFIG['mixup_alpha'])
        val_loss, val_acc, val_f1 = evaluate(model, val_loader, criterion, device)
        scheduler.step()
        elapsed = time.time() - t0

        marker = ""
        if val_f1 > best_f1:
            best_f1 = val_f1
            patience_counter = 0
            marker = " 💾"
            torch.save({
                'model_state_dict': model.state_dict(),
                'class_names': train_dataset.classes,
                'num_classes': NUM_CLASSES,
                'config': CONFIG,
            }, f"{CONFIG['output_dir']}/snapmenu_classifier_final.pth")
        else:
            patience_counter += 1

        print(f"  [{epoch+1:2d}/{CONFIG['phase2_epochs']}] "
              f"Loss: {train_loss:.3f}/{val_loss:.3f} | "
              f"Acc: {train_acc:.3f}/{val_acc:.3f} | "
              f"F1: {val_f1:.4f} | {elapsed:.0f}s{marker}"
              f"{f' (patience {patience_counter}/{CONFIG[\"patience\"]})' if patience_counter > 0 else ''}")

        if patience_counter >= CONFIG['patience']:
            print(f"  ⏹️  Early stopping!")
            break

    print(f"  ✅ Phase 2 done — Best F1: {best_f1:.4f}")

    # ============================================================
    # EVALUACIÓN FINAL
    # ============================================================
    print(f"\n{'='*60}")
    print(f"📊 EVALUACIÓN FINAL (Test Set)")
    print(f"{'='*60}")

    checkpoint = torch.load(f"{CONFIG['output_dir']}/snapmenu_classifier_final.pth", map_location=device)
    model.load_state_dict(checkpoint['model_state_dict'])
    model.eval()

    all_preds, all_labels, all_probs = [], [], []
    with torch.no_grad():
        for inputs, labels in test_loader:
            inputs = inputs.to(device, non_blocking=True)
            outputs = model(inputs)
            probs = torch.softmax(outputs, dim=1)
            _, pred = outputs.max(1)
            all_preds.extend(pred.cpu().numpy())
            all_labels.extend(labels.numpy())
            all_probs.extend(probs.cpu().numpy())

    all_preds = np.array(all_preds)
    all_labels = np.array(all_labels)
    all_probs = np.array(all_probs)

    accuracy = accuracy_score(all_labels, all_preds)
    f1_w = f1_score(all_labels, all_preds, average='weighted', zero_division=0)
    top3 = top_k_accuracy_score(all_labels, all_probs, k=3, labels=range(NUM_CLASSES))

    print(f"\n  ┌────────────────────────────────────┐")
    print(f"  │  Accuracy:      {accuracy:.4f}            │")
    print(f"  │  Top-3 Acc:     {top3:.4f}            │")
    print(f"  │  F1 (weighted): {f1_w:.4f}            │")
    print(f"  └────────────────────────────────────┘")

    print(f"\n📋 Per-Class Report:")
    print(classification_report(all_labels, all_preds, target_names=train_dataset.classes, zero_division=0))

    # ============================================================
    # EXPORT
    # ============================================================
    print(f"\n{'='*60}")
    print(f"📦 EXPORT")
    print(f"{'='*60}")

    model.cpu().eval()
    dummy_input = torch.randn(1, 3, CONFIG['img_size'], CONFIG['img_size'])
    onnx_path = f"{CONFIG['output_dir']}/snapmenu_v1.onnx"

    torch.onnx.export(
        model, dummy_input, onnx_path,
        export_params=True, opset_version=17,
        do_constant_folding=True,
        input_names=['input'], output_names=['output'],
    )
    onnx_size = os.path.getsize(onnx_path) / (1024 * 1024)
    print(f"  ✅ ONNX: {onnx_path} ({onnx_size:.1f} MB)")

    # Metadata para Flutter
    metadata = {
        "model_name": "snapmenu_ingredient_classifier",
        "version": "1.0.0",
        "architecture": "efficientnet_v2_s",
        "input_size": CONFIG['img_size'],
        "input_channels": 3,
        "normalize": {"mean": [0.485, 0.456, 0.406], "std": [0.229, 0.224, 0.225]},
        "num_classes": NUM_CLASSES,
        "class_names": train_dataset.classes,
        "class_names_es": {
            "apple": "manzana", "apricot": "damasco", "avocado": "palta",
            "bacon": "tocino", "bagels": "bagel", "baking powder": "polvo de hornear",
            "banana": "plátano", "bay leaves": "laurel", "beans": "frijoles",
            "beef": "carne de res", "beetroot": "betarraga", "black beans": "frijoles negros",
            "blackberries": "moras", "black pepper": "pimienta negra", "bread": "pan",
            "broccoli": "brócoli", "brown sugar": "azúcar morena", "butter": "mantequilla",
            "cabbage": "repollo", "capsicum": "pimiento", "carrots": "zanahoria",
            "cauliflower": "coliflor", "celery": "apio", "cheese": "queso",
            "cherries": "cerezas", "chicken": "pollo", "chili powder": "ají en polvo",
            "chilli": "ají", "chocolate": "chocolate", "cilantro leaves": "cilantro",
            "coconut": "coco", "corn": "maíz", "corn starch": "maicena",
            "crab": "cangrejo", "cranberries": "arándanos",
        },
        "confidence_threshold": 0.7,
        "top_k": 3,
        "metrics": {"accuracy": float(accuracy), "f1_weighted": float(f1_w), "top3_accuracy": float(top3)},
    }

    metadata_path = f"{CONFIG['output_dir']}/model_metadata.json"
    with open(metadata_path, 'w', encoding='utf-8') as f:
        json.dump(metadata, f, indent=2, ensure_ascii=False)
    print(f"  ✅ Metadata: {metadata_path}")

    # Guardar class names
    with open(f"{CONFIG['output_dir']}/class_names.txt", 'w') as f:
        for i, name in enumerate(train_dataset.classes):
            f.write(f"{i},{name}\n")

    print(f"\n{'='*60}")
    print(f"🎉 ¡ENTRENAMIENTO COMPLETO!")
    print(f"{'='*60}")
    print(f"\n📁 Archivos en: {CONFIG['output_dir']}/")
    for f_name in sorted(os.listdir(CONFIG['output_dir'])):
        if os.path.isfile(f"{CONFIG['output_dir']}/{f_name}"):
            size = os.path.getsize(f"{CONFIG['output_dir']}/{f_name}") / (1024 * 1024)
            print(f"   {f_name} ({size:.1f} MB)")

    print(f"\n🚀 Siguiente paso:")
    print(f"   Para convertir a TFLite, ejecuta:")
    print(f"   pip install onnx onnx-tf tensorflow")
    print(f"   python -m src.export.export_tflite --model {CONFIG['output_dir']}/snapmenu_classifier_final.pth --output {CONFIG['output_dir']}/snapmenu_v1.tflite")
    print(f"\n   O usa el archivo ONNX directamente con ONNX Runtime en Flutter.")


if __name__ == "__main__":
    main()
