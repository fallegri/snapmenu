# ---
# jupyter:
#   title: "SnapMenu - Ingredient Classifier Training"
#   kaggle:
#     accelerator: gpu
#     dataSources:
#       - sourceType: datasetVersion
#         datasetSlug: guigasousa/compilado-de-ingredientesalimentos
# ---

# %% [markdown]
# # 🍽️ SnapMenu — Entrenamiento del Clasificador de Ingredientes
#
# **Objetivo:** Entrenar un modelo EfficientNetV2 para clasificar 35 ingredientes.
#
# **Dataset:** compilado-de-ingredientesalimentos (Kaggle)
# - 43,515 imágenes
# - 35 categorías de ingredientes
# - Sin anotaciones de bounding box (clasificación pura)
#
# **Estrategia:**
# 1. Preparar dataset (limpieza, balance, splits)
# 2. Transfer Learning con EfficientNetV2-S (ImageNet)
# 3. Phase 1: Train classifier head (backbone frozen)
# 4. Phase 2: Fine-tune all layers
# 5. Evaluar y exportar a TFLite
#
# **Hardware:** Kaggle GPU (P100/T4)

# %% [markdown]
# ## 1. Setup e Imports

# %%
import os
import sys
import time
import random
import shutil
import json
from pathlib import Path
from collections import Counter

import numpy as np
import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import DataLoader
from torch.cuda.amp import GradScaler, autocast
from torchvision import datasets, transforms, models
from sklearn.model_selection import train_test_split
from sklearn.metrics import (
    f1_score, classification_report, confusion_matrix,
    accuracy_score, top_k_accuracy_score
)
from PIL import Image, ImageFile

ImageFile.LOAD_TRUNCATED_IMAGES = True

# Reproducibility
SEED = 42
random.seed(SEED)
np.random.seed(SEED)
torch.manual_seed(SEED)
if torch.cuda.is_available():
    torch.cuda.manual_seed_all(SEED)

print(f"PyTorch: {torch.__version__}")
print(f"CUDA available: {torch.cuda.is_available()}")
if torch.cuda.is_available():
    print(f"GPU: {torch.cuda.get_device_name(0)}")

DEVICE = torch.device('cuda' if torch.cuda.is_available() else 'cpu')



# %% [markdown]
# ## 2. Configuración

# %%
# === CONFIGURACIÓN ===
CONFIG = {
    'dataset_path': '/kaggle/input/compilado-de-ingredientesalimentos/ProjetoIntegrador6/train',
    'output_dir': '/kaggle/working/snapmenu_model',
    'img_size': 224,
    'batch_size': 32,
    'num_workers': 2,
    'exclude_classes': ['Unlabeled'],
    'max_samples_per_class': 2000,
    'min_samples_per_class': 50,
    'train_ratio': 0.70,
    'val_ratio': 0.15,
    'test_ratio': 0.15,
    # Phase 1
    'phase1_epochs': 10,
    'phase1_lr': 1e-3,
    # Phase 2
    'phase2_epochs': 40,
    'phase2_lr': 1e-4,
    # Regularization
    'dropout': 0.3,
    'label_smoothing': 0.1,
    'mixup_alpha': 0.2,
    'weight_decay': 1e-5,
    # Early stopping
    'patience': 10,
}

os.makedirs(CONFIG['output_dir'], exist_ok=True)
print("✅ Configuration loaded")



# %% [markdown]
# ## 3. Exploración y Preparación del Dataset

# %%
def explore_dataset(base_path):
    """Explore dataset structure and class distribution."""
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
        class_counts[name] = count
    
    total = sum(class_counts.values())
    print(f"📊 Dataset Summary:")
    print(f"   Classes: {len(class_counts)}")
    print(f"   Total images: {total:,}")
    print(f"   Min per class: {min(class_counts.values())} ({min(class_counts, key=class_counts.get)})")
    print(f"   Max per class: {max(class_counts.values())} ({max(class_counts, key=class_counts.get)})")
    print(f"   Mean per class: {total // len(class_counts)}")
    
    # Show distribution
    print(f"\n   Distribution:")
    for name, count in sorted(class_counts.items(), key=lambda x: x[1], reverse=True):
        bar = "█" * (count // 100)
        print(f"   {name:20s} {count:5d} {bar}")
    
    return class_counts

class_counts = explore_dataset(CONFIG['dataset_path'])
NUM_CLASSES = len(class_counts)
CLASS_NAMES = sorted(class_counts.keys())
print(f"\n✅ {NUM_CLASSES} classes identified")



# %%
def prepare_splits(base_path, class_counts, output_dir):
    """Create balanced train/val/test splits."""
    base = Path(base_path)
    splits_dir = Path(output_dir) / 'splits'
    
    for split in ['train', 'val', 'test']:
        for cls in CLASS_NAMES:
            (splits_dir / split / cls).mkdir(parents=True, exist_ok=True)
    
    stats = {'train': 0, 'val': 0, 'test': 0}
    
    for cls in CLASS_NAMES:
        cls_dir = base / cls
        images = [f for f in cls_dir.iterdir() 
                  if f.suffix.lower() in {'.jpg', '.jpeg', '.png', '.webp'}]
        
        # Subsample if too many
        if len(images) > CONFIG['max_samples_per_class']:
            images = random.sample(images, CONFIG['max_samples_per_class'])
        
        if len(images) < 3:
            continue
        
        # Stratified split
        train_imgs, temp_imgs = train_test_split(
            images, test_size=(CONFIG['val_ratio'] + CONFIG['test_ratio']),
            random_state=SEED
        )
        val_imgs, test_imgs = train_test_split(
            temp_imgs, 
            test_size=CONFIG['test_ratio'] / (CONFIG['val_ratio'] + CONFIG['test_ratio']),
            random_state=SEED
        )
        
        # Copy files
        for split_name, split_imgs in [('train', train_imgs), ('val', val_imgs), ('test', test_imgs)]:
            for img in split_imgs:
                dest = splits_dir / split_name / cls / img.name
                if not dest.exists():
                    shutil.copy2(img, dest)
            stats[split_name] += len(split_imgs)
    
    print(f"\n✂️  Splits created:")
    print(f"   Train: {stats['train']:,} images")
    print(f"   Val:   {stats['val']:,} images")
    print(f"   Test:  {stats['test']:,} images")
    return splits_dir

splits_dir = prepare_splits(CONFIG['dataset_path'], class_counts, CONFIG['output_dir'])



# %% [markdown]
# ## 4. Data Augmentation y DataLoaders

# %%
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

train_loader = DataLoader(train_dataset, batch_size=CONFIG['batch_size'], 
                          shuffle=True, num_workers=CONFIG['num_workers'],
                          pin_memory=True, drop_last=True)
val_loader = DataLoader(val_dataset, batch_size=CONFIG['batch_size'],
                        shuffle=False, num_workers=CONFIG['num_workers'], pin_memory=True)
test_loader = DataLoader(test_dataset, batch_size=CONFIG['batch_size'],
                         shuffle=False, num_workers=CONFIG['num_workers'], pin_memory=True)

print(f"✅ DataLoaders ready")
print(f"   Train batches: {len(train_loader)}")
print(f"   Val batches: {len(val_loader)}")
print(f"   Classes: {train_dataset.classes[:5]}... ({len(train_dataset.classes)} total)")



# %% [markdown]
# ## 5. Modelo y Class Weights

# %%
def build_model(num_classes, dropout=0.3):
    """Build EfficientNetV2-S with custom classifier."""
    model = models.efficientnet_v2_s(weights=models.EfficientNet_V2_S_Weights.DEFAULT)
    in_features = model.classifier[1].in_features
    model.classifier = nn.Sequential(
        nn.Dropout(p=dropout, inplace=True),
        nn.Linear(in_features, 512),
        nn.ReLU(inplace=True),
        nn.Dropout(p=dropout / 2),
        nn.Linear(512, num_classes),
    )
    return model

def get_class_weights(dataset, device):
    """Compute inverse frequency class weights."""
    targets = [s[1] for s in dataset.samples]
    counts = np.bincount(targets)
    weights = len(targets) / (len(counts) * counts.astype(float))
    weights = np.clip(weights, 0.5, 5.0)
    return torch.FloatTensor(weights).to(device)

model = build_model(NUM_CLASSES, CONFIG['dropout']).to(DEVICE)
class_weights = get_class_weights(train_dataset, DEVICE)

total_params = sum(p.numel() for p in model.parameters())
print(f"✅ Model built: EfficientNetV2-S")
print(f"   Total parameters: {total_params:,}")
print(f"   Classes: {NUM_CLASSES}")



# %% [markdown]
# ## 6. Training Loop

# %%
def train_one_epoch(model, loader, criterion, optimizer, scaler, mixup_alpha=0.0):
    model.train()
    running_loss, correct, total = 0.0, 0, 0
    
    for inputs, labels in loader:
        inputs, labels = inputs.to(DEVICE), labels.to(DEVICE)
        
        # Mixup
        if mixup_alpha > 0 and random.random() > 0.5:
            lam = np.random.beta(mixup_alpha, mixup_alpha)
            idx = torch.randperm(inputs.size(0)).to(DEVICE)
            inputs = lam * inputs + (1 - lam) * inputs[idx]
            with autocast():
                outputs = model(inputs)
                loss = lam * criterion(outputs, labels) + (1-lam) * criterion(outputs, labels[idx])
        else:
            with autocast():
                outputs = model(inputs)
                loss = criterion(outputs, labels)
        
        scaler.scale(loss).backward()
        scaler.step(optimizer)
        scaler.update()
        optimizer.zero_grad()
        
        running_loss += loss.item()
        _, pred = outputs.max(1)
        total += labels.size(0)
        correct += pred.eq(labels).sum().item()
    
    return running_loss / len(loader), correct / total

@torch.no_grad()
def evaluate(model, loader, criterion):
    model.eval()
    running_loss, correct, total = 0.0, 0, 0
    all_preds, all_labels = [], []
    
    for inputs, labels in loader:
        inputs, labels = inputs.to(DEVICE), labels.to(DEVICE)
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

print("✅ Training functions defined")



# %% [markdown]
# ## 7. Phase 1 — Train Classifier Head (Backbone Frozen)

# %%
print("=" * 60)
print("🔒 PHASE 1: Training Classifier Head (backbone frozen)")
print("=" * 60)

# Freeze backbone
for param in model.features.parameters():
    param.requires_grad = False

criterion = nn.CrossEntropyLoss(weight=class_weights, label_smoothing=CONFIG['label_smoothing'])
optimizer = optim.AdamW(filter(lambda p: p.requires_grad, model.parameters()),
                        lr=CONFIG['phase1_lr'], weight_decay=CONFIG['weight_decay'])
scheduler = optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=CONFIG['phase1_epochs'])
scaler = GradScaler()

best_f1 = 0.0

for epoch in range(CONFIG['phase1_epochs']):
    t0 = time.time()
    train_loss, train_acc = train_one_epoch(model, train_loader, criterion, optimizer, scaler)
    val_loss, val_acc, val_f1 = evaluate(model, val_loader, criterion)
    scheduler.step()
    elapsed = time.time() - t0
    
    print(f"  Epoch {epoch+1:2d}/{CONFIG['phase1_epochs']} | "
          f"Train Loss: {train_loss:.4f} Acc: {train_acc:.4f} | "
          f"Val Loss: {val_loss:.4f} Acc: {val_acc:.4f} F1: {val_f1:.4f} | {elapsed:.1f}s")
    
    if val_f1 > best_f1:
        best_f1 = val_f1
        torch.save(model.state_dict(), f"{CONFIG['output_dir']}/best_phase1.pth")

print(f"\n✅ Phase 1 complete — Best Val F1: {best_f1:.4f}")



# %% [markdown]
# ## 8. Phase 2 — Fine-Tune All Layers

# %%
print("=" * 60)
print("🔓 PHASE 2: Fine-Tuning All Layers")
print("=" * 60)

# Unfreeze backbone
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
        model, train_loader, criterion, optimizer, scaler, CONFIG['mixup_alpha'])
    val_loss, val_acc, val_f1 = evaluate(model, val_loader, criterion)
    scheduler.step()
    elapsed = time.time() - t0
    
    print(f"  Epoch {epoch+1:2d}/{CONFIG['phase2_epochs']} | "
          f"Train Loss: {train_loss:.4f} Acc: {train_acc:.4f} | "
          f"Val Loss: {val_loss:.4f} Acc: {val_acc:.4f} F1: {val_f1:.4f} | {elapsed:.1f}s")
    
    if val_f1 > best_f1:
        best_f1 = val_f1
        patience_counter = 0
        torch.save({
            'model_state_dict': model.state_dict(),
            'class_names': train_dataset.classes,
            'num_classes': NUM_CLASSES,
            'config': CONFIG,
            'metrics': {'val_acc': val_acc, 'val_f1': val_f1},
        }, f"{CONFIG['output_dir']}/snapmenu_classifier_final.pth")
        print(f"  💾 Best model saved (F1: {best_f1:.4f})")
    else:
        patience_counter += 1
        if patience_counter >= CONFIG['patience']:
            print(f"  ⏹️  Early stopping at epoch {epoch+1}")
            break

print(f"\n✅ Phase 2 complete — Best Val F1: {best_f1:.4f}")



# %% [markdown]
# ## 9. Evaluación Final en Test Set

# %%
print("=" * 60)
print("📊 FINAL EVALUATION ON TEST SET")
print("=" * 60)

# Load best model
checkpoint = torch.load(f"{CONFIG['output_dir']}/snapmenu_classifier_final.pth", map_location=DEVICE)
model.load_state_dict(checkpoint['model_state_dict'])
model.eval()

# Full evaluation
all_preds, all_labels, all_probs = [], [], []
with torch.no_grad():
    for inputs, labels in test_loader:
        inputs = inputs.to(DEVICE)
        outputs = model(inputs)
        probs = torch.softmax(outputs, dim=1)
        _, pred = outputs.max(1)
        all_preds.extend(pred.cpu().numpy())
        all_labels.extend(labels.numpy())
        all_probs.extend(probs.cpu().numpy())

all_preds = np.array(all_preds)
all_labels = np.array(all_labels)
all_probs = np.array(all_probs)

# Metrics
accuracy = accuracy_score(all_labels, all_preds)
f1_w = f1_score(all_labels, all_preds, average='weighted', zero_division=0)
top3 = top_k_accuracy_score(all_labels, all_probs, k=3, labels=range(NUM_CLASSES))
top5 = top_k_accuracy_score(all_labels, all_probs, k=5, labels=range(NUM_CLASSES))

print(f"\n  ┌─────────────────────────────────┐")
print(f"  │  Accuracy:      {accuracy:.4f}         │")
print(f"  │  Top-3 Acc:     {top3:.4f}         │")
print(f"  │  Top-5 Acc:     {top5:.4f}         │")
print(f"  │  F1 (weighted): {f1_w:.4f}         │")
print(f"  └─────────────────────────────────┘")

# Classification report
print("\n📋 Per-Class Report:")
print(classification_report(all_labels, all_preds, target_names=train_dataset.classes, zero_division=0))



# %% [markdown]
# ## 10. Export a ONNX y TFLite

# %%
print("=" * 60)
print("📦 EXPORT: PyTorch → ONNX → TFLite")
print("=" * 60)

# Export ONNX
model.cpu().eval()
dummy_input = torch.randn(1, 3, CONFIG['img_size'], CONFIG['img_size'])
onnx_path = f"{CONFIG['output_dir']}/snapmenu_v1.onnx"

torch.onnx.export(
    model, dummy_input, onnx_path,
    export_params=True, opset_version=17,
    do_constant_folding=True,
    input_names=['input'], output_names=['output'],
)
onnx_size = os.path.getsize(onnx_path) / (1024*1024)
print(f"  ✅ ONNX exported: {onnx_size:.1f} MB")

# Export TFLite (if tensorflow available)
try:
    import onnx
    from onnx_tf.backend import prepare
    import tensorflow as tf
    
    print("  Converting ONNX → TFLite (INT8)...")
    onnx_model = onnx.load(onnx_path)
    tf_rep = prepare(onnx_model)
    saved_model_dir = f"{CONFIG['output_dir']}/tf_saved_model"
    tf_rep.export_graph(saved_model_dir)
    
    converter = tf.lite.TFLiteConverter.from_saved_model(saved_model_dir)
    converter.optimizations = [tf.lite.Optimize.DEFAULT]
    converter.target_spec.supported_types = [tf.float16]
    tflite_model = converter.convert()
    
    tflite_path = f"{CONFIG['output_dir']}/snapmenu_v1.tflite"
    with open(tflite_path, 'wb') as f:
        f.write(tflite_model)
    tflite_size = os.path.getsize(tflite_path) / (1024*1024)
    print(f"  ✅ TFLite exported: {tflite_size:.1f} MB")
    
    shutil.rmtree(saved_model_dir, ignore_errors=True)
except ImportError:
    print("  ⚠️  TensorFlow not available — ONNX exported only")
    print("     Install: pip install onnx onnx-tf tensorflow")
    print("     Or convert ONNX → TFLite manually")

# %% [markdown]
# ## 11. Guardar Metadata para Flutter

# %%
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
with open(metadata_path, 'w') as f:
    json.dump(metadata, f, indent=2, ensure_ascii=False)

print(f"✅ Metadata saved: {metadata_path}")
print(f"\n📁 Output files in {CONFIG['output_dir']}:")
for f in os.listdir(CONFIG['output_dir']):
    size = os.path.getsize(f"{CONFIG['output_dir']}/{f}") / (1024*1024)
    print(f"   {f} ({size:.1f} MB)")

# %% [markdown]
# ## 12. Instrucciones Finales
#
# ### Para usar en Flutter:
# 1. Descargar `snapmenu_v1.tflite` y `model_metadata.json` de los outputs
# 2. Copiar a `assets/models/` en el proyecto Flutter
# 3. El plugin `tflite_flutter` usa estos archivos para inferencia on-device
#
# ### Para mejorar el modelo:
# - Agregar más imágenes de clases con bajo performance
# - Aumentar epochs si no convergió
# - Probar EfficientNetV2-M si hay más GPU disponible
# - Implementar Test-Time Augmentation (TTA) para mejor accuracy
