"""
SnapMenu ML - Dataset Preparation Script
=========================================
Prepares the raw Kaggle dataset for training:
1. Validates and cleans images
2. Balances classes (undersample large, augment small)
3. Creates stratified train/val/test splits
4. Generates dataset statistics report

Usage:
    python -m src.data.prepare_dataset --config configs/dataset_config.yaml
    
On Kaggle:
    Dataset is at /kaggle/input/compilado-de-ingredientesalimentos/ProjetoIntegrador6/train
"""

import os
import sys
import shutil
import random
import argparse
from pathlib import Path
from collections import Counter

import yaml
from PIL import Image, ImageFile
from sklearn.model_selection import train_test_split

# Allow truncated images
ImageFile.LOAD_TRUNCATED_IMAGES = True


def load_config(config_path: str) -> dict:
    """Load YAML configuration file."""
    with open(config_path, 'r') as f:
        return yaml.safe_load(f)


def validate_image(image_path: Path) -> bool:
    """Check if image is valid and not corrupted."""
    try:
        with Image.open(image_path) as img:
            img.verify()
        # Re-open to check it can actually be read
        with Image.open(image_path) as img:
            img.load()
        return True
    except Exception:
        return False


def get_class_distribution(base_path: Path, exclude_classes: list) -> dict:
    """Get number of valid images per class."""
    distribution = {}
    for class_dir in sorted(base_path.iterdir()):
        if not class_dir.is_dir():
            continue
        class_name = class_dir.name
        if class_name in exclude_classes:
            continue
        
        images = [
            f for f in class_dir.iterdir()
            if f.suffix.lower() in {'.jpg', '.jpeg', '.png', '.webp'}
        ]
        distribution[class_name] = len(images)
    
    return distribution


def collect_valid_images(base_path: Path, exclude_classes: list) -> dict:
    """Collect all valid image paths grouped by class."""
    class_images = {}
    total_invalid = 0
    
    for class_dir in sorted(base_path.iterdir()):
        if not class_dir.is_dir():
            continue
        class_name = class_dir.name
        if class_name in exclude_classes:
            print(f"  [SKIP] {class_name} (excluded)")
            continue
        
        images = []
        invalid_count = 0
        
        for img_file in class_dir.iterdir():
            if img_file.suffix.lower() not in {'.jpg', '.jpeg', '.png', '.webp'}:
                continue
            if validate_image(img_file):
                images.append(img_file)
            else:
                invalid_count += 1
        
        class_images[class_name] = images
        total_invalid += invalid_count
        
        status = "✓" if len(images) >= 100 else "⚠ LOW"
        print(f"  [{status}] {class_name}: {len(images)} valid"
              f"{f' ({invalid_count} corrupted)' if invalid_count else ''}")
    
    if total_invalid > 0:
        print(f"\n  Total corrupted images removed: {total_invalid}")
    
    return class_images


def balance_classes(class_images: dict, config: dict) -> dict:
    """Balance classes by undersampling large and noting small ones."""
    min_samples = config['balance']['min_samples_per_class']
    max_samples = config['balance']['max_samples_per_class']
    seed = config['random_seed']
    
    random.seed(seed)
    balanced = {}
    
    print("\n📊 Balancing classes:")
    for class_name, images in class_images.items():
        n = len(images)
        if n > max_samples:
            # Undersample
            balanced[class_name] = random.sample(images, max_samples)
            print(f"  [↓] {class_name}: {n} → {max_samples} (undersampled)")
        elif n < min_samples:
            # Keep all, flag for augmentation during training
            balanced[class_name] = images
            print(f"  [⚠] {class_name}: {n} images (will use heavy augmentation)")
        else:
            balanced[class_name] = images
            print(f"  [=] {class_name}: {n} images (ok)")
    
    return balanced


def create_splits(class_images: dict, config: dict, output_dir: Path):
    """Create stratified train/val/test splits."""
    train_ratio = config['splits']['train']
    val_ratio = config['splits']['val']
    test_ratio = config['splits']['test']
    seed = config['random_seed']
    
    # Create output directories
    for split in ['train', 'val', 'test']:
        for class_name in class_images.keys():
            (output_dir / split / class_name).mkdir(parents=True, exist_ok=True)
    
    stats = {'train': Counter(), 'val': Counter(), 'test': Counter()}
    
    print(f"\n📂 Creating splits (train={train_ratio}/val={val_ratio}/test={test_ratio}):")
    
    for class_name, images in class_images.items():
        if len(images) < 3:
            print(f"  [SKIP] {class_name}: too few images ({len(images)})")
            continue
        
        # First split: train vs (val+test)
        train_imgs, temp_imgs = train_test_split(
            images,
            test_size=(val_ratio + test_ratio),
            random_state=seed
        )
        
        # Second split: val vs test
        relative_test = test_ratio / (val_ratio + test_ratio)
        val_imgs, test_imgs = train_test_split(
            temp_imgs,
            test_size=relative_test,
            random_state=seed
        )
        
        # Copy/symlink images to split directories
        for split_name, split_imgs in [('train', train_imgs), ('val', val_imgs), ('test', test_imgs)]:
            for img_path in split_imgs:
                dest = output_dir / split_name / class_name / img_path.name
                if not dest.exists():
                    shutil.copy2(img_path, dest)
            stats[split_name][class_name] = len(split_imgs)
        
        print(f"  {class_name}: train={len(train_imgs)} | val={len(val_imgs)} | test={len(test_imgs)}")
    
    return stats


def generate_report(class_images: dict, stats: dict, output_dir: Path):
    """Generate a summary report of the prepared dataset."""
    report_path = output_dir / "dataset_report.md"
    
    total_images = sum(len(imgs) for imgs in class_images.values())
    num_classes = len(class_images)
    
    with open(report_path, 'w') as f:
        f.write("# SnapMenu Dataset Report\n\n")
        f.write(f"- **Total classes:** {num_classes}\n")
        f.write(f"- **Total images (after cleaning):** {total_images}\n")
        f.write(f"- **Train:** {sum(stats['train'].values())}\n")
        f.write(f"- **Validation:** {sum(stats['val'].values())}\n")
        f.write(f"- **Test:** {sum(stats['test'].values())}\n\n")
        
        f.write("## Class Distribution\n\n")
        f.write("| # | Class | Total | Train | Val | Test |\n")
        f.write("|---|-------|-------|-------|-----|------|\n")
        
        for i, class_name in enumerate(sorted(class_images.keys()), 1):
            total = len(class_images[class_name])
            train = stats['train'].get(class_name, 0)
            val = stats['val'].get(class_name, 0)
            test = stats['test'].get(class_name, 0)
            f.write(f"| {i} | {class_name} | {total} | {train} | {val} | {test} |\n")
    
    print(f"\n📄 Report saved to: {report_path}")


def main():
    parser = argparse.ArgumentParser(description="Prepare SnapMenu dataset")
    parser.add_argument('--config', type=str, default='configs/dataset_config.yaml',
                        help='Path to dataset config YAML')
    parser.add_argument('--source', type=str, default=None,
                        help='Override source dataset path')
    parser.add_argument('--output', type=str, default=None,
                        help='Override output directory')
    parser.add_argument('--skip-validation', action='store_true',
                        help='Skip image validation (faster but risky)')
    args = parser.parse_args()
    
    # Load config
    config = load_config(args.config)
    dataset_config = config['dataset']
    
    # Paths
    source_path = Path(args.source or dataset_config['base_path'])
    output_dir = Path(args.output or config['output']['splits_dir'])
    
    print("=" * 60)
    print("🍽️  SnapMenu ML - Dataset Preparation")
    print("=" * 60)
    print(f"\nSource: {source_path}")
    print(f"Output: {output_dir}")
    print(f"Excluded: {dataset_config['exclude_classes']}")
    
    # Validate source exists
    if not source_path.exists():
        print(f"\n❌ ERROR: Source path does not exist: {source_path}")
        print("   If running on Kaggle, use: --source /kaggle/input/compilado-de-ingredientesalimentos/ProjetoIntegrador6/train")
        sys.exit(1)
    
    # Step 1: Collect and validate images
    print("\n\n📷 Step 1: Collecting and validating images...")
    if args.skip_validation:
        print("  (Skipping validation - using all images)")
        class_images = {}
        for class_dir in sorted(source_path.iterdir()):
            if not class_dir.is_dir() or class_dir.name in dataset_config['exclude_classes']:
                continue
            images = [f for f in class_dir.iterdir() if f.suffix.lower() in {'.jpg', '.jpeg', '.png', '.webp'}]
            class_images[class_dir.name] = images
            print(f"  [=] {class_dir.name}: {len(images)} images")
    else:
        class_images = collect_valid_images(source_path, dataset_config['exclude_classes'])
    
    print(f"\n  Total: {sum(len(v) for v in class_images.values())} images in {len(class_images)} classes")
    
    # Step 2: Balance classes
    print("\n\n⚖️  Step 2: Balancing classes...")
    balanced_images = balance_classes(class_images, dataset_config)
    
    # Step 3: Create splits
    print("\n\n✂️  Step 3: Creating stratified splits...")
    stats = create_splits(balanced_images, dataset_config, output_dir)
    
    # Step 4: Generate report
    print("\n\n📊 Step 4: Generating report...")
    generate_report(balanced_images, stats, output_dir)
    
    print("\n" + "=" * 60)
    print("✅ Dataset preparation complete!")
    print(f"   Output: {output_dir}")
    print("=" * 60)


if __name__ == "__main__":
    main()
